from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from examples.reliable_agent.engine import AgentRuntime, ExternalService, InjectedCrash


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.local = Path(self.tmp.name) / 'local.sqlite'
        self.remote = Path(self.tmp.name) / 'external.sqlite'
        self.service = ExternalService(self.remote)
        self.agent = AgentRuntime(self.local, self.service)

    def test_approval_gates_effect_and_then_completes(self):
        self.agent.create('a', 'ship book')
        self.assertEqual(self.agent.run('a')['status'], 'waiting_approval')
        self.assertEqual(self.service.count(), 0)
        self.agent.approve('a')
        self.assertEqual(self.agent.run('a')['status'], 'completed')
        self.assertEqual(self.service.count(), 1)

    def test_crash_after_effect_before_checkpoint_survives_new_objects(self):
        self.agent.create('a', 'ship book', approved=True)
        with self.assertRaises(InjectedCrash):
            self.agent.run('a', crash_after_effect=True)
        self.assertEqual(self.service.count(), 1)
        restarted = AgentRuntime(self.local, ExternalService(self.remote))
        self.assertEqual(restarted.run('a')['status'], 'completed')
        self.assertEqual(ExternalService(self.remote).count(), 1)
        self.assertIn('recovered', [e['event'] for e in restarted.trace('a')])

    def test_cancel_prevents_later_tool_execution(self):
        self.agent.create('a', 'ship book', approved=True)
        self.agent.cancel('a')
        self.assertEqual(self.agent.run('a')['status'], 'cancelled')
        self.assertEqual(self.service.count(), 0)

    def test_retry_budget_persists_and_exhausts(self):
        self.service.failures_left = 4
        self.agent.create('a', 'ship book', approved=True, max_attempts=2)
        result = self.agent.run('a')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['attempts'], 2)
        self.assertEqual(self.service.count(), 0)
        self.assertEqual(self.agent.run('a')['attempts'], 2)

    def test_transient_failure_retries_with_stable_key(self):
        self.service.failures_left = 1
        self.agent.create('a', 'ship book', approved=True)
        result = self.agent.run('a')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['attempts'], 2)
        self.assertEqual(self.service.count(), 1)

    def test_timeout_and_total_time_budget(self):
        self.service.latency = 0.02
        self.agent.create('a', 'ship book', approved=True, timeout=0.001, time_budget=0.002)
        result = self.agent.run('a')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(self.service.count(), 0)
        self.assertIn('timeout', [e['event'] for e in self.agent.trace('a')])
        self.assertGreaterEqual(result['time_spent'], 0.002)

    def test_cost_budget_blocks_next_attempt(self):
        self.service.failures_left = 1
        self.agent.create('a', 'ship book', approved=True, cost_budget=1)
        result = self.agent.run('a')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['attempts'], 1)
        self.assertEqual(result['cost_spent'], 1)

    def test_same_task_id_cannot_change_approved_payload(self):
        self.agent.create('a', 'ship book', approved=True)
        with self.assertRaises(ValueError):
            self.agent.create('a', 'ship laptop', approved=True)

    def test_duplicate_run_is_terminal_and_key_payload_conflicts_fail(self):
        self.agent.create('a', 'ship book', approved=True)
        self.agent.run('a')
        self.assertEqual(self.agent.run('a')['attempts'], 1)
        self.assertEqual(self.service.count(), 1)
        with self.assertRaises(ValueError):
            self.service.execute('a:deliver:v1', 'different payload', timeout=1)

    def test_cancellation_during_failed_call_stops_retry(self):
        runtime = self.agent
        class CancellingService(ExternalService):
            def execute(self, *args, **kwargs):
                runtime.cancel('a')
                raise ConnectionError('cancel arrived while tool was running')
        self.agent.service = CancellingService(self.remote)
        self.agent.create('a', 'ship book', approved=True)
        result = self.agent.run('a')
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(result['attempts'], 1)
        self.assertEqual(self.service.count(), 0)

    def test_cancellation_cannot_undo_already_committed_effect(self):
        runtime = self.agent
        class CancellingService(ExternalService):
            def execute(self, *args, **kwargs):
                receipt = super().execute(*args, **kwargs)
                runtime.cancel('a')
                return receipt
        self.agent.service = CancellingService(self.remote)
        self.agent.create('a', 'ship book', approved=True)
        self.assertEqual(self.agent.run('a')['status'], 'cancelled')
        self.assertEqual(self.agent.run('a')['attempts'], 1)
        self.assertEqual(self.service.count(), 1)
