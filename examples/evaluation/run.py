"""40 deterministic regression tasks; repeats measure expected-outcome reliability."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from examples.rag.engine import KnowledgeBase
from examples.reliable_agent.engine import AgentRuntime, ExternalService, InjectedCrash
from examples.mcp_tools.tools import dispatch


def load_cases():
    return json.loads(Path(__file__).with_name('cases.json').read_text())


def summarize(outcomes):
    if not outcomes or any(not row for row in outcomes):
        raise ValueError('nonempty task trials required')
    return {'expected_outcome_match_rate': sum(sum(row) for row in outcomes) / sum(map(len, outcomes)),
            'pass_at_k': sum(any(row) for row in outcomes) / len(outcomes),
            'pass_power_k': sum(all(row) for row in outcomes) / len(outcomes)}


def run_case(case):
    budget = {'tool_attempts': 0, 'cost_units': 0, 'charged_tool_seconds': 0}
    if case['kind'] == 'rag':
        kb = KnowledgeBase()
        for doc_id, text, readers in [
            ('refund', 'Atlas refund window is 30 days.', ['staff']),
            ('warranty', 'Orion warranty lasts 90 days.', ['staff']),
            ('payroll', 'Payroll amount is 999.', ['finance']),
            ('hours', 'Office hours are 9 to 5.', ['*'])]:
            kb.upsert(doc_id, text, readers)
        for change in case.get('changes', []):
            if change['op'] == 'delete':
                kb.delete(change['id'])
            else:
                kb.upsert(change['id'], change['text'], change['readers'], change.get('version', 1))
        answer = kb.answer(case['query'], case['principal'])
        actual = {'refused': answer['refused'], 'sources': [s['id'] for s in answer['sources']],
                  'answer': answer['answer']}
    elif case['kind'] == 'agent':
        with TemporaryDirectory() as folder:
            local, remote = Path(folder) / 'local.db', Path(folder) / 'remote.db'
            service = ExternalService(remote, **case.get('service', {}))
            runtime = AgentRuntime(local, service)
            runtime.create('case-task', 'ship book', **case.get('options', {}))
            for action in case['actions']:
                if action == 'restart':
                    service = ExternalService(remote, **case.get('service', {}))
                    runtime = AgentRuntime(local, service)
                elif action == 'crash':
                    try:
                        runtime.run('case-task', crash_after_effect=True)
                    except InjectedCrash:
                        pass
                    else:
                        raise AssertionError('expected the injected crash')
                elif action == 'run':
                    runtime.run('case-task')
                elif action in ('approve', 'cancel'):
                    getattr(runtime, action)('case-task')
                else:
                    raise ValueError(f'unknown action: {action}')
            state = runtime.state('case-task')
            actual = {'status': state['status'], 'effects': service.count(), 'attempts': state['attempts']}
            budget = {'tool_attempts': state['attempts'], 'cost_units': state['cost_spent'],
                      'charged_tool_seconds': state['time_spent']}
    elif case['kind'] == 'tool':
        actual = dispatch(case['tool'], case['arguments'])
    else:
        raise ValueError('unknown case kind')
    passed = all(actual.get(key) == value for key, value in case['expected'].items())
    if 'contains' in case:
        passed = passed and case['contains'] in actual.get('answer', '')
    return passed, actual, budget


def evaluate(cases, repeats=3):
    if type(repeats) is not int or repeats < 1 or not cases:
        raise ValueError('positive repeats and nonempty cases required')
    outcomes, failures, results = [], [], []
    budgets = {'tool_attempts': 0, 'cost_units': 0, 'charged_tool_seconds': 0.0}
    agent_trials = agent_completed = 0
    for case in cases:
        row = []
        for trial in range(repeats):
            passed, actual, budget = run_case(case)
            row.append(passed)
            for key in budgets:
                budgets[key] += budget[key]
            if case['kind'] == 'agent':
                agent_trials += 1
                agent_completed += actual['status'] == 'completed'
            if not passed:
                failures.append({'name': case['name'], 'trial': trial + 1,
                                 'actual': actual, 'expected': case['expected']})
        outcomes.append(row)
        results.append({'name': case['name'], 'passed': sum(row), 'trials': repeats})
    return {'case_count': len(cases), 'repeats': repeats, 'trial_count': len(cases) * repeats,
            'passed_trials': sum(sum(row) for row in outcomes), **summarize(outcomes),
            'agent_completion_rate': agent_completed / agent_trials if agent_trials else None,
            'agent_completed_trials': agent_completed, 'agent_trials': agent_trials,
            'budgets': budgets, 'failures': failures, 'results': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = evaluate(load_cases(), args.repeats)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + '\n')
    print(rendered)
    raise SystemExit(bool(report['failures']))


if __name__ == '__main__':
    main()
