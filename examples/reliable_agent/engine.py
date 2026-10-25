"""Single-worker state machine; two independent databases model a remote boundary."""
from contextlib import contextmanager
import json
import math
import sqlite3
import time


@contextmanager
def database(path):
    connection = sqlite3.connect(path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


class InjectedCrash(RuntimeError):
    """Simulate process death after external commit and before local checkpoint."""


class ExternalService:
    """A simulated delivery service owns its own atomic idempotency ledger.

    A row in deliveries IS the simulated effect. A real provider must supply the
    same atomic deduplication guarantee; putting a cache around email is not enough.
    """

    def __init__(self, path, *, failures_left=0, latency=0):
        self.path = path
        self.failures_left = failures_left
        self.latency = latency
        with database(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS deliveries (key TEXT PRIMARY KEY, payload TEXT, receipt TEXT)')

    def lookup(self, key, payload):
        with database(self.path) as db:
            row = db.execute('SELECT payload, receipt FROM deliveries WHERE key=?', (key,)).fetchone()
        if row and row[0] != payload:
            raise ValueError('idempotency key already belongs to a different payload')
        return json.loads(row[1]) if row else None

    def execute(self, key, payload, *, timeout):
        receipt = self.lookup(key, payload)
        if receipt:
            return receipt
        if self.latency > timeout:
            time.sleep(max(0, timeout))
            raise TimeoutError('external service deadline exceeded')
        time.sleep(self.latency)
        if self.failures_left:
            self.failures_left -= 1
            raise ConnectionError('temporary external failure')
        receipt = {'operation_id': key, 'delivered': payload}
        with database(self.path) as db:
            db.execute('INSERT OR IGNORE INTO deliveries VALUES (?, ?, ?)',
                       (key, payload, json.dumps(receipt)))
        return self.lookup(key, payload)

    def count(self):
        with database(self.path) as db:
            return db.execute('SELECT count(*) FROM deliveries').fetchone()[0]


class AgentRuntime:
    """Approval and budgets belong here, outside any model/framework adapter."""

    def __init__(self, path, service):
        self.path, self.service = path, service
        with database(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, state TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS trace (seq INTEGER PRIMARY KEY, task_id TEXT, event TEXT, detail TEXT)')

    def create(self, task_id, payload, *, approved=False, max_attempts=3,
               timeout=1.0, time_budget=5.0, cost_budget=3):
        if not task_id or not payload or type(max_attempts) is not int or max_attempts < 1:
            raise ValueError('task, payload and positive max_attempts required')
        if any(not math.isfinite(v) or v <= 0 for v in (timeout, time_budget, cost_budget)):
            raise ValueError('budgets must be positive finite numbers')
        state = dict(id=task_id, payload=payload, approved=approved, status='pending',
                     operation_id=f'{task_id}:deliver:v1', max_attempts=max_attempts,
                     timeout=timeout, time_budget=time_budget, cost_budget=cost_budget,
                     attempts=0, cost_spent=0, time_spent=0, result=None)
        with database(self.path) as db:
            row = db.execute('SELECT state FROM tasks WHERE id=?', (task_id,)).fetchone()
            if row:
                raise ValueError('task id already exists; approval cannot be reused for a new payload')
            db.execute('INSERT INTO tasks VALUES (?, ?)', (task_id, json.dumps(state)))
        self._event(task_id, 'created')

    def state(self, task_id):
        with database(self.path) as db:
            row = db.execute('SELECT state FROM tasks WHERE id=?', (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        return json.loads(row[0])

    def _save(self, state):
        with database(self.path) as db:
            db.execute('UPDATE tasks SET state=? WHERE id=?', (json.dumps(state), state['id']))

    def _event(self, task_id, event, detail=''):
        with database(self.path) as db:
            db.execute('INSERT INTO trace(task_id,event,detail) VALUES (?,?,?)', (task_id, event, detail))

    def trace(self, task_id):
        with database(self.path) as db:
            return [dict(seq=r[0], event=r[1], detail=r[2]) for r in db.execute(
                'SELECT seq,event,detail FROM trace WHERE task_id=? ORDER BY seq', (task_id,))]

    def approve(self, task_id):
        state = self.state(task_id)
        if state['status'] not in ('pending', 'waiting_approval'):
            raise ValueError('task cannot be approved in its current state')
        state['approved'] = True
        self._save(state)
        self._event(task_id, 'approved')

    def cancel(self, task_id):
        state = self.state(task_id)
        if state['status'] not in ('completed', 'failed', 'cancelled'):
            state['status'] = 'cancelled'
            self._save(state)
            self._event(task_id, 'cancelled')

    def run(self, task_id, *, crash_after_effect=False):
        while True:
            state = self.state(task_id)
            if state['status'] in ('completed', 'failed', 'cancelled'):
                return state
            if not state['approved']:
                state['status'] = 'waiting_approval'
                self._save(state)
                self._event(task_id, 'waiting_approval')
                return state
            # Reconcile an uncertain result BEFORE checking retry budgets.
            receipt = self.service.lookup(state['operation_id'], state['payload'])
            if receipt is not None:
                state.update(status='completed', result=receipt)
                self._save(state)
                self._event(task_id, 'recovered')
                return state
            remaining = state['time_budget'] - state['time_spent']
            if (state['attempts'] >= state['max_attempts'] or remaining <= 0
                    or state['cost_spent'] + 1 > state['cost_budget']):
                state['status'] = 'failed'
                self._save(state)
                self._event(task_id, 'budget_exhausted')
                return state
            allotted = min(state['timeout'], remaining)
            state.update(status='running', attempts=state['attempts'] + 1,
                         cost_spent=state['cost_spent'] + 1,
                         time_spent=state['time_spent'] + allotted)
            # Reserve attempts, cost units and worst-case time BEFORE crossing the boundary.
            self._save(state)
            self._event(task_id, 'attempt', state['operation_id'])
            started = time.monotonic()
            try:
                receipt = self.service.execute(state['operation_id'], state['payload'], timeout=allotted)
            except (TimeoutError, ConnectionError) as exc:
                state['time_spent'] += time.monotonic() - started - allotted
                # Preserve cancellation arriving while a cooperative tool is in progress.
                if self.state(task_id)['status'] == 'cancelled':
                    return self.state(task_id)
                self._save(state)
                self._event(task_id, 'timeout' if isinstance(exc, TimeoutError) else 'retry', str(exc))
                continue
            if crash_after_effect:
                raise InjectedCrash('external commit succeeded; local result not checkpointed')
            if self.state(task_id)['status'] == 'cancelled':
                return self.state(task_id)
            state.update(status='completed', result=receipt,
                         time_spent=state['time_spent'] + time.monotonic() - started - allotted)
            self._save(state)
            self._event(task_id, 'completed')
            return state
