"""Official SDK server. stdout is reserved for stdio protocol messages."""
from typing import Any
from mcp.server import MCPServer
from examples.mcp_tools.tools import dispatch

server = MCPServer('interview-lab', log_level='ERROR')


@server.tool(structured_output=True)
def calculate(expression: str) -> dict[str, Any]:
    """Bounded arithmetic supporting only numeric + - * / and parentheses."""
    return dispatch('calculate', {'expression': expression})


@server.tool(structured_output=True)
def get_weather(city: str) -> dict[str, Any]:
    """Return a fixed teaching fixture for 南京 or 北京, not a live forecast."""
    return dispatch('get_weather', {'city': city})


if __name__ == '__main__':
    server.run(transport='stdio')
