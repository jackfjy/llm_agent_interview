# 可靠工具 Agent：一次投递的恢复边界

`last_verified: 2026-10-26` · `versions: Python 3.11.15; mcp 2.3.0; openai 3.37.0; openai-agents 0.24.0; langgraph 1.2.17`

`example_status: offline-tested + sdk-boundary-tested` · [运行时源码](https://github.com/jackfjy/llm_agent_interview/blob/codex/refresh-2026-10/examples/reliable_agent/engine.py) · [边界测试](https://github.com/jackfjy/llm_agent_interview/blob/codex/refresh-2026-10/examples/tests/test_agent.py)

## 目标与安装

目标是在“外部投递已提交，本地成功 checkpoint 尚未保存”的窗口崩溃，再用新对象恢复，外部投递总数仍为 1。Python 3.11+；核心不需依赖，仓库根目录运行：

```bash
python -m examples.reliable_agent.demo
python -m unittest examples.tests.test_agent -v
```

## 操作与预期输出

`AgentRuntime(local_path, service)` 保存任务、审批、预算和 trace；`ExternalService(remote_path)` 在另一个 SQLite 文件模拟外部服务。两个数据库独立提交，不能靠一笔本地事务掩盖不确定窗口。

1. `create(id, payload, approved=False)` 后 `run(id)` 得到 `waiting_approval`，无外部副作用。
2. `approve(id)` 后，`run(id, crash_after_effect=True)` 注入崩溃。demo 捕获异常，外部记录数为 1。
3. 新建 runtime/service 对象并 `run(id)`，先查外部收据再恢复为 `completed`，外部记录数仍为 1。

预期关键输出：

```json
{"before_approval":"waiting_approval","effects_after_crash":1,"after_recovery":"completed","effects_after_recovery":1,"trace":["created","waiting_approval","approved","attempt","recovered"]}
```

操作键固定为 `<task_id>:deliver:v1`。同一 ID 不允许替换 payload，避免旧审批批准新内容。外部服务必须原子保存“幂等键、内容、副作用和收据”，相同键不同内容应冲突。收据恢复优先于预算耗尽检查，因此最后一次尝试成功但未 checkpoint 也可恢复。

## 失败实验与取舍

- 不审批就运行：停在审批状态。模型适配器只返回 `approved=False` 的提议，模型不能给自己授权。
- 设置 `max_attempts=1` 并注入暂时失败：失败后不继续调用。每次调度前预留尝试数、模拟成本及时间，重启不清零；预留后取消仍可能计入预算。
- 在外部收据查询期间取消：重新读取持久状态，旧快照不得覆盖 `cancelled`；对应测试覆盖这类交错。
- 在投递已经提交后取消：不能撤销记录。最后一次调度前检查之后到达的取消属于在途调用，跨系统原子取消不在本例保证中。
- 把工具换成无限阻塞函数：本例协作式 timeout 不会自动获得强制中断能力；生产场景需进程隔离、远端期限或可取消的工具协议。

本例仅单 worker；不能以 SQLite checkpoint 宣称任意邮件 API 的 exactly-once。没有外部幂等合同，就要承认不确定状态并查询、人工核对或补偿。多 worker 还需租约、抢占和并发状态转换设计。

## 三种 SDK 路径与在线边界

[适配器](https://github.com/jackfjy/llm_agent_interview/blob/codex/refresh-2026-10/examples/reliable_agent/adapters.py) 在同一审批语义外接 Responses、Agents SDK 与 LangGraph。安装 [锁定环境](./MCP工具服务.md#安装与操作) 后运行完整测试：Responses 用真实 SDK 的 MockTransport，Agents 用真实 Runner 配 fixture Model，LangGraph 编译执行真实 StateGraph。它们检验接口合同，未请求真实模型、未测试模型决策质量。LangGraph 节点继续调用本例 SQLite runtime，不代表改用了 LangGraph 持久化。

生产选型可参考 [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) 与 [Agents SDK](https://openai.github.io/openai-agents-python/)（资料核验 2026-10-25）。练习：[场景题 1–8](./场景题40.md#可靠性8题)；延伸：[记忆系统](../02-核心技能/07-记忆系统.md)。
