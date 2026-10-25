# 可复现的 LLM 工程实验

`last_verified: 2026-10-26` · `example_status: offline-tested + sdk-boundary-tested`

Python **3.11+**；最低版本实测为 Python **3.11.15**。三个实验不需要模型密钥，不调用付费 API。离线核心只用标准库；MCP 通信和三个框架适配器使用固定版本 SDK。此处展示工程机制，不是生产框架或模型排行榜。

## 运行入口

以下命令均从**仓库根目录**运行。

```bash
python -m unittest discover -s examples/tests -v
python -m examples.rag.demo
python -m examples.reliable_agent.demo
python -m examples.evaluation.run --repeats 3 --output examples/.state/evaluation.json
```

本次完整 SDK 环境运行 37 项测试全部通过、0 跳过；纯标准库环境运行同一套 37 项测试，33 项通过、4 个可选 SDK 测试明确跳过。测试包含 40 个回归输入的重复执行。不要把 `skipped` 当作 SDK 验证通过。

安装 SDK 环境后，用同一个解释器重跑全部测试和真实 MCP 往返：

```bash
python3.11 -m venv examples/.venv
examples/.venv/bin/python -m pip install --require-hashes -r examples/requirements.lock
examples/.venv/bin/python -m unittest discover -s examples/tests -v
examples/.venv/bin/python -m examples.mcp_tools.client
```

Windows 使用 `examples\.venv\Scripts\python.exe`。锁文件锁定全部 59 个 SDK 运行依赖及包校验值；在 macOS Python 3.11 全新环境实装验证。Linux CI 可使用相同锁文件，但本地验证不等于所有平台已验证。更新依赖应重新生成锁并跑测试：

```bash
uv pip compile examples/pyproject.toml --extra sdk --python-version 3.11 \
  --generate-hashes -o examples/requirements.lock
```

| 依赖 | 锁定实测版本 | 测试边界 |
| --- | --- | --- |
| `mcp` / `mcp-types` | 2.3.0 / 2.3.0 | 真实 stdio 子进程、工具发现、调用和错误 |
| `openai` | 3.37.0 | 真实 Responses SDK + `httpx2.MockTransport` |
| `openai-agents` | 0.24.0 | 真实 `Agent` / `Runner` + fixture `Model` |
| `langgraph` | 1.2.17 | 编译并执行真实 `StateGraph` |
| `httpx2` | 2.16.0 | 与当前 OpenAI SDK 匹配的 HTTP 测试边界 |

## 实验一：带权限和引用的 RAG

入口：[rag/demo.py](rag/demo.py)，算法：[rag/engine.py](rag/engine.py)。

`KnowledgeBase.upsert(id, text, readers, version=1)` 添加或替换文档；`delete(id)` 删除；`retrieve(query, principal, limit=3)` 返回带分数的候选；`answer(query, principal)` 返回 `{refused, answer, sources}`。`sources` 中每条都有 `id`、`version`、`text`。

检索先检查每条文档的读权限，再对可访问的文本分词和打分。`principal` 必须由可信应用根据登录身份传入，不能让模型或用户任意声明身份；`'*'` 表示公开。一次 `upsert` 替换内容、版本和权限，下一次检索即生效。删除后本地内存索引不再包含旧内容。示例没有缓存、外部索引、聊天历史或持久化副本，因此没有声称清除了这些系统中的历史信息。

每份文档视为一个小 chunk。英文词和中文双字组组成关键词集合；SHA-256 将词映射到 64 维并归一化，余弦相似度是 `vector` 分数。融合分数为 `0.7 × keyword + 0.3 × vector`，轻量 rerank 给完整短语命中加 `0.2`。返回 `matched`、`phrase_bonus` 等字段可解释排序。

**哈希向量不理解语义**，会碰撞，不是 embedding；rerank 也不是 cross-encoder。没有共同词项时，即使发生哈希碰撞也拒答。回答直接摘录并引用可访问证据，没有调用生成模型；有词项重叠不代表证据足以回答复杂问题，生产系统还需要可回答性判断和引用核验。

demo 的预期行为：员工看到报销政策引用，访客拒答；更新后的引用版本为 2；删除后员工也拒答。测试还验证权限变更、私有文档不参与向量化、旧词项不可检索及不同命中的排序。

## 实验二：可恢复、可审批、可取消的 Agent

入口：[reliable_agent/demo.py](reliable_agent/demo.py)，状态机：[reliable_agent/engine.py](reliable_agent/engine.py)。

`AgentRuntime(local_path, service)` 使用一个 SQLite 保存任务、预算、结果 checkpoint 和 trace；`ExternalService(remote_path)` 使用**另一个数据库**模拟远程投递服务。`create(id, payload, approved=False, max_attempts=3, timeout=1, time_budget=5, cost_budget=3)` 创建任务；`approve(id)`、`cancel(id)`、`run(id)`、`state(id)`、`trace(id)` 操作同一持久化任务。

```text
pending → waiting_approval → running → completed
                               ├─ transient error → retry / failed
                               ├─ cancellation → cancelled
                               └─ crash → restart → reconcile external receipt → completed
```

操作 ID 固定为 `<task_id>:deliver:v1`，任务 ID 在同一外部服务范围内必须唯一。任务创建后不能用同一个 ID 替换 payload，也不能借旧审批批准新内容。每次调用前先保存尝试数、成本单位和时间预留，恢复不会重置预算。每次调用成本为 1 个**模拟单位**，不是美元或 token。`max_attempts` 包含首次尝试。

模拟服务原子提交投递记录与幂等键；重复请求返回原收据，相同键配不同 payload 会报错。`run(..., crash_after_effect=True)` 在外部成功提交、但本地未保存成功结果时抛出 `InjectedCrash`。创建新的 runtime 和 service 对象后，运行先查外部收据，再决定是否重试；即使最后一次尝试已经消耗完预算，也可以恢复已有成功结果。demo 应显示：

```json
{
  "before_approval": "waiting_approval",
  "effects_after_crash": 1,
  "after_recovery": "completed",
  "effects_after_recovery": 1,
  "trace": ["created", "waiting_approval", "approved", "attempt", "recovered"]
}
```

这里的外部副作用就是 `deliveries` 表中新增一条投递记录。去重成立依赖于外部服务对“幂等键 + 副作用”的原子保证、持久保留收据，以及恢复时能查询该收据。**不能把这个示例泛化成任意外部工具的 exactly-once**：普通发邮件接口若没有这样的协议，本地 checkpoint 本身无法消除不确定窗口。真实系统还要处理幂等键过期、外部查询失败、补偿、认证和多 worker 竞争；本例只支持单 worker。

取消在启动前、查询外部收据后、实际调度前和每次工具返回后检查，阻止后续调用。状态写入在 SQLite 事务内检查当前终态，旧快照不能把已取消任务重新写成运行、完成或失败；它不能撤销已经提交的投递。调用前最后一次检查之后到达的取消仍按在途调用处理，不能与远程副作用建立跨系统原子取消。超时由此模拟服务协作执行：等待至给定 timeout 后抛出 `TimeoutError`，整体 `time_budget` 会截短最后一次调用。它不是可以强行打断任意 Python 函数的通用超时器。正常返回时按实际耗时记账；崩溃时保留已预留的最长时间，预算采取保守估计。trace 记录审批、取消、尝试、超时、预算耗尽、完成和恢复。

### 三种可选 SDK 适配

[reliable_agent/adapters.py](reliable_agent/adapters.py) 中：

- `responses_proposal(client, prompt, model=...)` 调用真实 `client.responses.create`，`store=False`，返回 `{payload, approved: False}`。测试在 HTTP 传输层提供固定 Responses 响应，并校验请求字段。
- `await agents_proposal(model, prompt)` 运行真实 `Agent` 和 `Runner`。测试提供实现 SDK `Model` 接口的 fixture，覆盖 Runner 的请求和结果转换；禁用 tracing 导出。
- `graph_run(runtime, task_id)` 编译并执行真实 LangGraph 节点，调用同一 SQLite 状态机，保留审批与恢复语义；禁用此调用的 LangSmith tracing。没有声称使用 LangGraph checkpoint 替代外部幂等账本。

模型路径只产生待审核的提议，不直接创建已批准任务。主程序可用 `runtime.create(task_id, **proposal)` 保存提议，再由人批准。没有提供默认在线 demo；真实 client/model 必须由调用方主动构造并提供自己的凭证。**实测范围不包括在线模型质量、真实模型服务或真实外部投递服务**。

## 实验三：官方 SDK 的真实 MCP 往返

服务端：[mcp_tools/server.py](mcp_tools/server.py)，客户端：[mcp_tools/client.py](mcp_tools/client.py)，纯工具逻辑：[mcp_tools/tools.py](mcp_tools/tools.py)。

`MCPServer` 来自 `mcp.server`，`Client` / `StdioServerParameters` 来自 `mcp`。客户端用当前 Python 解释器启动实际服务端进程，进行工具发现和调用；并非手写 JSON-RPC 模仿。实测 SDK 支持且本次连接实际协商到 **2026-07-28**；输出同时给出 `sdk_protocol_latest` 和 `negotiated_protocol`，不能仅由包版本推断协商结果。

服务端显式启用结构化工具输出，客户端读取此 SDK 的 `structured_content` 和 `is_error` 字段。预期工具列表为 `calculate`、`get_weather`，算术 `2 + 3 * 4` 返回 14，南京固定天气为 22℃、晴。`fixture: true` 明确它不是实时天气。

算术只遍历 AST 白名单，支持数字、括号、`+ - * /` 和正负号；不使用 `eval`。限制输入 200 字符、64 AST 节点以及每个中间值绝对值不超过 `1e9`。函数调用、属性、下标、幂、布尔值、非有限数和除零均拒绝。未知工具由 MCP 返回协议工具错误；合法工具内的非法算术返回 `{ok: false, error: ...}`，调用方必须检查 `ok`，不能把 MCP 请求完成视为业务成功。stdio 的 stdout 专供协议使用。

该实验不验证 HTTP、OAuth、跨主机部署、其他客户端互通或旧协议兼容性。

## 40 条回归和指标

输入：[evaluation/cases.json](evaluation/cases.json)；执行器：[evaluation/run.py](evaluation/run.py)。包括 14 条 RAG、12 条 Agent、14 条工具案例。每个输入的权限、查询、变更、故障、预算或参数不同，并检查实际输出、引用、最终状态、执行次数或尝试次数。MCP 协议往返单独由 SDK 集成测试验证，回归中的工具用例是纯 dispatch 测试。

默认将**每条相同任务独立重建状态运行 3 次**，共 120 次，输出每个任务的通过次数、失败详情和预算。成功的含义由该任务的预期结果定义，包含应该拒答、应该拒绝和应该失败的场景：

- `expected_outcome_match_rate`：匹配预期的试验次数 / 总试验次数。这是回归正确率，不能冒充模型业务成功率。
- `agent_completion_rate`：Agent 最终完成次数 / Agent 试验次数。此集合故意含拒绝和预算失败，因此全通过时为 `5/12`，不是 100%；这也不是线上业务的代表性样本。
- `pass_at_k`：同一任务 k 次至少一次匹配预期的任务比例。
- `pass_power_k`（pass^k）：同一任务 k 次全部匹配预期的任务比例。

后两个是本次重复试验的**观测值**，并未用 40 条不同任务伪装成同一任务的 40 次采样。只有在每次独立同分布、单次成功率为 p 时，理论值才分别为 `1-(1-p)^k` 和 `p^k`；这个确定性小实验不支持估计真实模型的独立成功概率。另有混合成败测试，验证 any/all 指标不会混淆。

全通过预期：`case_count=40`、`trial_count=120`、`passed_trials=120`、`pass_at_k=1`、`pass_power_k=1`、`agent_completed_trials=15`、`agent_trials=36`。预算字段 `tool_attempts` / `cost_units` 表示 Agent 已预留尝试数及模拟成本；预留后、调度前取消也保留这笔预算，因此不等于真正发出的调用数。`charged_tool_seconds` 包含崩溃后保留的保守时间预留，不是精确性能基准。输出文件和 SQLite 状态放在已忽略的 `examples/.state/`，demo 使用临时目录并自动清理。

## 来源与验证边界

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)；[固定协议 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28)
- [OpenAI Python SDK](https://github.com/openai/openai-python)；[Agents SDK](https://openai.github.io/openai-agents-python/)
- [LangGraph 持久化](https://docs.langchain.com/oss/python/langgraph/persistence)

这些链接用于继续学习。这里的可运行承诺只针对以上固定版本、测试和命令；不以当前 SDK 的安装成功推断未运行的功能，也不将 fixture 模型当作在线模型验证。
