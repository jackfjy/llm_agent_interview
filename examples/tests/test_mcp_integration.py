import asyncio
import importlib.util
import unittest
from examples.mcp_tools.client import roundtrip


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'official MCP SDK missing; install examples/requirements.lock')
class MCPIntegrationTests(unittest.TestCase):
    def test_real_stdio_subprocess_tool_contract(self):
        result = asyncio.run(roundtrip())
        self.assertEqual(result.get('negotiated_protocol'), '2026-07-28')
        self.assertEqual(set(result['tools']), {'calculate', 'get_weather'})
        self.assertEqual(result['calculation'], {'ok': True, 'result': 14})
        self.assertEqual(result['weather']['result']['temperature_c'], 22)
        self.assertFalse(result['malicious']['ok'])
        self.assertTrue(result['unknown_tool_error'])
