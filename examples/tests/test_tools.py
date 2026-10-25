import unittest
from examples.mcp_tools.tools import dispatch


class ToolTests(unittest.TestCase):
    def test_arithmetic_precedence_and_unary(self):
        self.assertEqual(dispatch('calculate', {'expression': '-(2 + 3) * 4 / 2'}), {'ok': True, 'result': -10.0})

    def test_malicious_and_unbounded_arithmetic_are_errors(self):
        for expression in ['__import__("os").system("id")', '2 ** 100000', '1 / 0', 'True + 1', '9' * 201, '[1][0]']:
            with self.subTest(expression=expression):
                self.assertFalse(dispatch('calculate', {'expression': expression})['ok'])

    def test_weather_fixture_and_unknown_city(self):
        self.assertEqual(dispatch('get_weather', {'city': '南京'}), {'ok': True, 'result': {'city': '南京', 'temperature_c': 22, 'condition': '晴', 'fixture': True}})
        self.assertFalse(dispatch('get_weather', {'city': 'Atlantis'})['ok'])

    def test_unknown_tool_and_bad_arguments(self):
        for name, args in [('weather', {'city': '南京'}), ('calculate', {}), ('calculate', {'expression': '1', 'extra': 1}), ('calculate', {'expression': 12})]:
            with self.subTest(name=name, args=args):
                self.assertFalse(dispatch(name, args)['ok'])
