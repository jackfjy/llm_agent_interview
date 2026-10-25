# 2026-10 三批更新设计

用户已批准 2026-10-25 评估报告中的三批改造，要求基于当前分支新建分支并实施。基线 dev@3ccec0c01dc12363a67d1831fd245a2d06f2b372；工作分支 codex/refresh-2026-10。

## 目标与边界

保留 47 个既有编号专题；修正高时效结论和示例；提供三条可运行学习主线；新增 40 道有答案、失败场景和追问的场景题。成果推送到独立分支，不合并 dev、不发布 GitHub Pages。原 MIT 许可证与作者归属保留。当前 GitHub 连接写入被 403 拒绝，本机 SSH 已认证为 jackfjy，可用于该分支。

## 第一批：事实与版本

直接修改相关旧段落，不能仅在文末追加更新。
- 02 模型时间线：将 2025 历史与当前核验分开，移除 GPT-5/R2 过期预测；GPT-5 发布为 2025-08-07；DeepSeek-V3 $5.576M 是有假设和边界的正式训练费用，不是整体研发总成本。
- 23/28 前沿：时代依赖排名、闭源架构/参数估计标未公开或缺证据；保留公开原理。不要补未经验证的最新模型清单。
- 09 MCP：基于官方固定规范 2026-07-28 介绍新旧对照。旧握手/会话不混作当前规范；HTTP+SSE 与 SSE 响应区分；OAuth 授权与 stdio 凭证边界；A2A 1.0 系列。修 get_weather/weather 和 eval。示例版本必须与第二批实际测试一致，历史 v1 允许保留为明确标注的兼容案例。
- 11/41：v1 create_agent、middleware、结构化输出；旧 AgentExecutor 等移到明确旧版区；删掉“安装最新版运行旧导入”的误导。不机械全替换其他历史章节，给其兼容说明。
- 06/10/39/40 与术语表：新实践主线引导到 Responses 和 Agents SDK；标记 Assistants 于 2026-08-26 下线，Chat Completions 仍支持。
- 成本计算器：撤掉未经全面核验的“最新”总表；提供可追溯价格样本和参数化公式，按相同口径重算示例。o3 官方普通文本价格样本 $2/$8，缓存输入 $0.5，每百万 tokens；历史模型价格不要标现役推荐。
- 15：修未实现 param_semantic_match 的误导，可移除该伪指标；补多合法路径与最终状态判断说明。
- 每个本批更新章节增加核验日期、适用范围、示例状态和官方来源。

## 第二批：可运行案例

Python >=3.11；examples 独立包与锁定环境。纯离线核心用标准库，API/框架整合用明确固定版本的可选依赖。模型在线调用需显式开关和用户自己的环境变量；测试不能消耗付费 API。
1. examples/rag：本地小知识库，带来源引用、权限先过滤、关键词+向量相似度融合、可解释轻量 rerank、更新和删除、拒答。离线向量仅教学用，文档说明与真实 embedding/cross encoder 的边界。确定性数据与评估集验证权限、引用、变更、拒答。
2. examples/reliable_agent：SQLite 保存任务/步骤与外部操作结果；稳定的工具操作 ID；模拟外部系统接受幂等键；可在副作用后 checkpoint 前注入崩溃并恢复不重复执行。人工审批、失败次数预算、取消、trace；通过原生 Responses 可选适配器、Agents SDK 和 LangGraph 适配示例解释运行时差异（付费调用非默认）。
3. examples/mcp_tools：官方 SDK 的 stdio 客户端/服务端真实往返；有界算术和天气 fixture，不 eval。无网络费用；锁定实测 SDK 版本并明确其协议代际。先检验 registry 包和 API，不能仅按当前规范推断库已实现；不能把手写 JSON-RPC 当作 SDK 互通验证。
4. 离线回归集 30–50 个具名用例，记录任务成功率、重复成功率和预算；正确区分 pass@k/pass^k，指标独立于具体模型排行榜。
5. 测试覆盖非法输入、权限、删除、超时/重试边界、重复副作用、恢复、MCP dispatch；提供可复制运行命令和预期输出。依赖不足不能假报通过。

## 第三批：内容深化和维护

- 新增 docs/实战实验室/ 首页、三个实验说明、40题场景题与岗位路线。40题覆盖可靠性8、上下文/记忆/Skills6、MCP/A2A6、API/框架6、RAG6、评估/成本5、后训练3；每题口述答案、失败/反例、追问、来源或案例链接。
- 在现有相关章节加入准确交叉链接和针对性内容：RAG/权限/删除，长期任务恢复，GRPO/RLVR。已有知识不重复复制。
- docs/TOP50-高频题.md 使用引用/include 统一到工具箱，保留路径；README/首页/导航/CHANGELOG 更新到 fork，原作者署名保留。
- package.json license 与 MIT 对齐；requirements.txt 明确实际安装入口；清理缺依据的真题/必考/最强营销话术，COMPANY-MAP 标经验而非招聘事实。
- CONTRIBUTING/维护页规定 last_verified、versions、sources、example_status；新增 PR CI（文档构建、离线测试、MCP往返），不改自动部署到新分支。
- 不引入模拟面试网页或视频产品。

## 主要权威来源

- https://docs.langchain.com/oss/python/migrate/langchain-v1
- https://docs.langchain.com/oss/python/migrate/langgraph-v1
- https://developers.openai.com/api/docs/assistants/migration
- https://developers.openai.com/api/docs/guides/migrate-to-responses
- https://openai.github.io/openai-agents-python/
- https://modelcontextprotocol.io/specification/2026-07-28/changelog
- https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization
- https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0
- https://a2a-protocol.org/latest/specification/
- https://agentskills.io/specification
- https://www.anthropic.com/research/demystifying-evals-for-ai-agents
- https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- https://arxiv.org/html/2412.19437v2
- https://arxiv.org/abs/2501.12948

## 验收

三批各自提交。文档能构建；三个案例的默认路径离线可运行；MCP 真正客户端往返；>=30 个回归输入；40 道完整场景题；无秘密或运行产物入库。独立审查后修复重要问题，最终 push 到新分支。未调用真实模型的边界要在 README 和交付说明中明确。
