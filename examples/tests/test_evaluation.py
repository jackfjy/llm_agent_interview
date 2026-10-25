import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from examples.evaluation.run import evaluate, load_cases, main, run_case, summarize


class EvaluationTests(unittest.TestCase):
    def test_forty_distinct_named_regressions_execute(self):
        cases = load_cases()
        self.assertEqual(len(cases), 40)
        self.assertEqual(len({case.get('name') for case in cases}), 40)
        report = evaluate(cases, repeats=2)
        self.assertEqual(report.get('case_count'), 40)
        self.assertEqual(report['trial_count'], 80)
        self.assertEqual(report['passed_trials'], 80, report.get('failures'))
        self.assertEqual(report['pass_at_k'], 1)
        self.assertEqual(report['pass_power_k'], 1)
        self.assertGreater(report['budgets']['tool_attempts'], 0)
        self.assertEqual(report['budget_accounting'],
                         {'known_trials': 80, 'unknown_trials': 0, 'complete': True})

    def test_any_success_differs_from_all_success(self):
        # Two tasks: one succeeds once, the other succeeds on both attempts.
        summary = summarize([[True, False], [True, True]])
        self.assertEqual(summary, {'expected_outcome_match_rate': 0.75, 'pass_at_k': 1.0, 'pass_power_k': 0.5})

    def test_failure_is_reported_and_not_counted_as_success(self):
        case = {'name': 'intentionally_wrong', 'kind': 'tool', 'tool': 'calculate',
                'arguments': {'expression': '2+2'}, 'expected': {'ok': True, 'result': 5}}
        result = evaluate([case], repeats=1)
        self.assertEqual(result.get('passed_trials'), 0)
        self.assertEqual(result['failures'][0]['name'], 'intentionally_wrong')
        self.assertEqual(result['failures'][0]['actual']['result'], 4)

    def test_invalid_repeat_count_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([], repeats=0)

    def test_exception_preserves_trials_and_reports_only_known_budget(self):
        cases = [
            {'name': 'delivery', 'kind': 'agent', 'options': {'approved': True},
             'actions': ['run'], 'expected': {'status': 'completed', 'effects': 1, 'attempts': 1}},
            {'name': 'arithmetic', 'kind': 'tool', 'tool': 'calculate',
             'arguments': {'expression': '2+2'}, 'expected': {'ok': True, 'result': 4}}]
        first_trial = True

        def fail_once(case):
            nonlocal first_trial
            if first_trial:
                first_trial = False
                raise RuntimeError('unexpected fixture failure')
            return run_case(case)

        with patch('examples.evaluation.run.run_case', side_effect=fail_once):
            report = json.loads(json.dumps(evaluate(cases, repeats=2)))
        self.assertEqual(report['trial_count'], 4)
        self.assertEqual(report['passed_trials'], 3)
        self.assertEqual(report['expected_outcome_match_rate'], 0.75)
        self.assertEqual(report['pass_at_k'], 1)
        self.assertEqual(report['pass_power_k'], 0.5)
        self.assertEqual(report['agent_trials'], 2)
        self.assertEqual(report['agent_completed_trials'], 1)
        self.assertEqual(report['agent_completion_rate'], 0.5)
        self.assertEqual(report['results'], [
            {'name': 'delivery', 'passed': 1, 'trials': 2},
            {'name': 'arithmetic', 'passed': 2, 'trials': 2}])
        self.assertEqual(report['budgets']['tool_attempts'], 1)
        self.assertEqual(report['budgets']['cost_units'], 1)
        self.assertGreaterEqual(report['budgets']['charged_tool_seconds'], 0)
        self.assertEqual(report['budget_accounting'],
                         {'known_trials': 3, 'unknown_trials': 1, 'complete': False})
        self.assertEqual(report['failures'], [{
            'name': 'delivery', 'trial': 1, 'actual': None,
            'expected': cases[0]['expected'], 'budget': None,
            'exception': {'type': 'RuntimeError', 'message': 'unexpected fixture failure'}}])

    def test_cli_serializes_exception_and_exits_nonzero_after_later_success(self):
        cases = [
            {'name': 'broken_action', 'kind': 'agent', 'actions': ['unexpected'],
             'expected': {'status': 'completed'}},
            {'name': 'arithmetic', 'kind': 'tool', 'tool': 'calculate',
             'arguments': {'expression': '2+2'}, 'expected': {'result': 4}}]
        with TemporaryDirectory() as folder:
            output = Path(folder) / 'nested' / 'report.json'
            stdout = io.StringIO()
            with patch('examples.evaluation.run.load_cases', return_value=cases), \
                    patch('sys.argv', ['evaluate', '--repeats', '1', '--output', str(output)]), \
                    redirect_stdout(stdout), self.assertRaises(SystemExit) as stopped:
                main()
            self.assertEqual(stopped.exception.code, 1)
            report = json.loads(output.read_text())
            self.assertEqual(json.loads(stdout.getvalue()), report)
        self.assertEqual(report['trial_count'], 2)
        self.assertEqual(report['passed_trials'], 1)
        self.assertEqual(report['results'][1], {'name': 'arithmetic', 'passed': 1, 'trials': 1})
        self.assertEqual(report['failures'][0]['exception'],
                         {'type': 'ValueError', 'message': 'unknown action: unexpected'})
        self.assertEqual(report['budget_accounting']['unknown_trials'], 1)

    def test_process_control_exceptions_are_not_aggregated(self):
        case = {'name': 'interrupted', 'kind': 'tool', 'expected': {}}
        for exception in (KeyboardInterrupt, SystemExit):
            with self.subTest(exception=exception), \
                    patch('examples.evaluation.run.run_case', side_effect=exception), \
                    self.assertRaises(exception):
                evaluate([case], repeats=1)
