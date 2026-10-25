# MCP 工具服务：真实通信与业务错误

`last_verified: 2026-10-26` · `versions: Python 3.11.15; mcp 2.3.0; openai 3.37.0; openai-agents 0.24.0; langgraph 1.2.17`

`example_status: sdk-boundary-tested` · `protocol: negotiated 2026-07-28` · [客户端](https://github.com/jackfjy/llm_agent_interview/blob/codex/refresh-2026-10/examples/mcp_tools/client.py) · [服务端](https://github.com/jackfjy/llm_agent_interview/blob/codex/refresh-2026-10/examples/mcp_tools/server.py)

## 目标

用官方 Python SDK 启动真实 stdio 子进程，发现并调用工具。实际验证版本为 mcp/mcp-types 2.3.0，实际协商协议为 2026-07-28；不是手写 JSON-RPC，也不是仅凭规范推断 SDK 能力。

## 安装与操作

从仓库根目录运行，建议使用 Python 3.11。锁文件含 59 个运行依赖的精确版本和哈希，在 macOS arm64 Python 3.11.15 全新安装验证：

```bash
python3.11 -m venv examples/.venv
examples/.venv/bin/python -m pip install --require-hashes -r examples/requirements.lock
examples/.venv/bin/python -m unittest discover -s examples/tests -v
examples/.venv/bin/python -m examples.mcp_tools.client
```

Windows 解释器路径改为 `examples\.venv\Scripts\python.exe`；尚无本地 Windows 运行证据。Linux 使用相同锁文件的 PR 检查，只有远端实际运行成功后才可宣称平台通过。需要下载安装包的网络，无模型密钥和付费调用。

客户端用同一个 Python 解释器启动服务端。`MCPServer` 来自 `mcp.server`，`Client` / `StdioServerParameters` 来自 `mcp`；不要套用 v1 FastMCP 的旧导入。

## 预期输出

- `tools` 包含 `calculate` 与 `get_weather`。
- `sdk_protocol_latest` 与 `negotiated_protocol` 本次都是 `2026-07-28`；协商结果需实际读取，不能从 SDK 版本猜测。
- `calculate` 对 `2 + 3 * 4` 返回 14；`get_weather` 的南京结果为 22℃、晴、`fixture: true`。它不是天气网络服务。
- 恶意算术返回业务 `ok=false`；未知工具 `weather` 返回 MCP `is_error=true`。协议通信完成与业务成功必须分开统计。

## 失败实验

```bash
examples/.venv/bin/python -m unittest examples.tests.test_mcp_integration examples.tests.test_tools -v
```

检查除零、函数调用、属性、下标、幂和布尔输入被拒绝。AST 白名单只支持数字、括号、四则运算和正负号，并限制输入 200 字符、64 节点、每个中间结果绝对值不超过 1e9；不是替换字符后执行 eval。

将未知工具名当作 get_weather 的别名会失败，客户端应依据发现结果调用。stdio 的 stdout 必须留给协议；调试日志写 stderr，避免破坏通信。服务端显式开启结构化输出，客户端检查当前 SDK 的 `structured_content`、`is_error` 及业务 `ok`。

## 边界和来源

本例不实现模型选工具、HTTP/OAuth、跨主机、旧客户端或跨 SDK 兼容。远程 MCP 的 audience/scope 与 token 隔离不能从本地 stdio 成功推出；stdio 凭证通常由受信启动环境提供，也不能等同于所有连接都必须 OAuth。

资料核验 2026-10-25：[固定协议](https://modelcontextprotocol.io/specification/2026-07-28)、[授权规范](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)、[Python SDK](https://github.com/modelcontextprotocol/python-sdk)。练习：[场景题 15–20](./场景题40.md#mcp-a2a6题)；原理：[MCP 与工具生态](../02-核心技能/09-MCP与工具生态.md)。
