# LLM & Agent 学习与实战

[本 fork：jackfjy/llm_agent_interview](https://github.com/jackfjy/llm_agent_interview/tree/codex/refresh-2026-10) · [原项目与作者：dirjaker](https://github.com/dirjaker/llm_agent_interview) · [MIT](LICENSE)

保留 47 个编号专题和 9 个工具箱页面，新增 3 个可复现实验及 40 道完整场景练习。47 按 01–47 编号专题文件计数，9 按 docs/工具箱下的页面计数；场景题按独立问题计数，不把旧题库的标题数、代码行数当作质量指标。未宣称题目来自已核实的企业面试或拥有出现频率统计。

## 从这里开始

| 入口 | 用途 |
| --- | --- |
| [实战实验室](docs/实战实验室/index.md) | 企业知识库、可靠 Agent、真实 MCP 工具通信 |
| [场景题 40](docs/实战实验室/场景题40.md) | 参考口述答案、失败条件、追问和来源 |
| [岗位学习路线](docs/实战实验室/学习路线.md) | 从运行实验到交付故障证据 |
| [原有专题导航](docs/index.md) | Python、LLM、RAG、Agent、训练、工程、网关等 47 个专题 |
| [Top50 概念复习](docs/工具箱/TOP50-高频题.md) | 保留旧路径的概念速查；标题不代表频率调查 |
| [公司经验笔记](docs/工具箱/COMPANY-MAP.md) | 待核实的准备假设，不代表公司招聘事实 |
| [术语表](docs/工具箱/GLOSSARY.md) / [更新日志](docs/CHANGELOG.md) | 概念索引与版本变更 |

本分支内容以仓库和本地预览为准。[原作者已发布站点](https://dirjaker.github.io/llm_agent_interview/) 不代表本 fork 的更新版本；本分支没有发布站点。

## 运行与预览

```bash
git clone --branch codex/refresh-2026-10 https://github.com/jackfjy/llm_agent_interview.git
cd llm_agent_interview
npm ci
npm run dev
# 文档构建
npm run build
```

Python 3.11+，从仓库根目录运行默认离线实验：

```bash
python -m unittest discover -s examples/tests -v
python -m examples.rag.demo
python -m examples.reliable_agent.demo
python -m examples.evaluation.run --repeats 3 --output examples/.state/evaluation.json
```

完整 SDK 与真实 MCP stdio 往返：

```bash
python3.11 -m venv examples/.venv
examples/.venv/bin/python -m pip install --require-hashes -r examples/requirements.lock
examples/.venv/bin/python -m unittest discover -s examples/tests -v
examples/.venv/bin/python -m examples.mcp_tools.client
```

`last_verified: 2026-10-26` · `versions: Python 3.11.15; mcp 2.3.0; openai 3.37.0; openai-agents 0.24.0; langgraph 1.2.17` · `example_status: offline-tested + sdk-boundary-tested`。本地 macOS arm64 完整 SDK 环境 40 项测试通过且零跳过；标准库环境 36 项通过、4 项 SDK 测试明确跳过。40 条回归输入 ×3 次共 120 次均匹配预期，包括拒答和应失败的用例；不能冒充线上业务成功率。准确指标与来源见 [examples README](examples/README.md)。

这些数字只描述 examples，未对原有 47 个专题的所有嵌入代码逐段运行。真实 SDK 测试使用传输或模型 fixture，不调用付费 API，未验证真实模型质量。离线哈希向量与短语 rerank 是词项教学近似；Agent 单 worker，外部效果去重依赖模拟服务原子持久幂等合同；MCP 仅本地 stdio。Linux PR 工作流需实际执行后才能声称平台验证通过。

## 维护与归属

[贡献说明](CONTRIBUTING.md) 和 [维护规则](docs/实战实验室/维护规则.md) 规定来源、版本、示例状态及依赖更新流程。PR 检查构建文档、运行离线/SDK 测试和 MCP 往返，不请求模型密钥、不发布站点。原有部署仍仅面向 dev 分支及手动触发，本更新分支不触发自动发布。

原项目作者为 **dirjaker**；此 fork 由 **jackfjy** 维护。保留 [MIT License](LICENSE) 的原始版权声明。
