# 实战实验室

`last_verified: 2026-10-26` · `versions: Python 3.11.15; mcp 2.3.0; openai 3.37.0; openai-agents 0.24.0; langgraph 1.2.17`

`example_status: offline-tested + sdk-boundary-tested` · 核验范围为 examples 中的实现和固定依赖，不代表旧题库中的全部代码已运行。

先运行一个小实验，再把它的失败条件讲清楚。这里有三个实验、40 道场景题与按岗位选择的学习路线；保留原有 47 个编号专题作为知识索引。

| 入口 | 完成后应能解释 |
| --- | --- |
| [企业知识库](./企业知识库.md) | 权限过滤、引用、更新删除与拒答的关系 |
| [可靠工具 Agent](./可靠工具Agent.md) | 审批、幂等、崩溃恢复、预算与取消 |
| [MCP 工具服务](./MCP工具服务.md) | 官方 SDK 的真实 stdio 通信与两层错误 |
| [场景题 40](./场景题40.md) | 具体取舍、失败条件、追问及证据 |
| [学习路线](./学习路线.md) | 按岗位产出可检查的工程证据 |
| [维护规则](./维护规则.md) | 版本记录、测试与来源如何持续更新 |

## 从零开始

从仓库根目录运行（Python 3.11+）：

```bash
python -m unittest discover -s examples/tests -v
python -m examples.rag.demo
python -m examples.reliable_agent.demo
python -m examples.evaluation.run --repeats 3 --output examples/.state/evaluation.json
```

离线核心只有标准库。完整 SDK 环境安装与 MCP 命令见 [MCP 实验](./MCP工具服务.md)。本地核验：SDK 环境 40 项全部通过且无跳过；纯标准库环境 36 项通过、4 项 SDK 测试明确跳过。40 条回归输入重复 3 次共 120 次均匹配预期，其中包含应该拒绝或失败的案例，不能说业务完成率为 100%。意外试验异常会作为失败记录类型与消息，继续后续试验并写出 JSON；异常用量标为未知，预算只汇总已知试验，CLI 返回非零状态。字段说明见 [examples README](https://github.com/jackfjy/llm_agent_interview/blob/codex/refresh-2026-10/examples/README.md)。

离线向量和 rerank 是词项教学近似；模型 fixture 不代表真实模型质量；Agent 只支持单 worker，副作用去重依赖外部系统的幂等合同。MCP 只验证 stdio，无 HTTP/OAuth 互通承诺。

源码、完整运行说明与锁文件：[examples README](https://github.com/jackfjy/llm_agent_interview/blob/codex/refresh-2026-10/examples/README.md)。所有实验默认不需要模型密钥、不请求付费模型。远端 Linux PR 检查在实际运行后才能作为平台验证证据。
