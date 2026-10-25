import unittest
from examples.evaluation.run import evaluate, load_cases, summarize


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
