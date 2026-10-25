"""Real official-SDK client → stdio subprocess → official-SDK server."""
import asyncio
import json
from pathlib import Path
import sys


async def roundtrip():
    from mcp import Client, StdioServerParameters
    from mcp_types import LATEST_PROTOCOL_VERSION
    parameters = StdioServerParameters(command=sys.executable,
        args=['-m', 'examples.mcp_tools.server'], cwd=Path(__file__).resolve().parents[2])
    async with Client(parameters, read_timeout_seconds=10) as client:
        tools = await client.list_tools()
        calculation = await client.call_tool('calculate', {'expression': '2 + 3 * 4'})
        weather = await client.call_tool('get_weather', {'city': '南京'})
        malicious = await client.call_tool('calculate', {'expression': '__import__("os")'})
        unknown = await client.call_tool('weather', {'city': '南京'})
        return {'transport': 'stdio', 'sdk_protocol_latest': LATEST_PROTOCOL_VERSION,
                'negotiated_protocol': client.protocol_version,
                'tools': [tool.name for tool in tools.tools],
                'calculation': calculation.structured_content,
                'weather': weather.structured_content, 'malicious': malicious.structured_content,
                'unknown_tool_error': unknown.is_error}


def main():
    print(json.dumps(asyncio.run(roundtrip()), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
