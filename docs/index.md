---
layout: home

hero:
  name: "LLM & Agent 面试题全集"
  text: "面试题与实战难题全集"
  tagline: "47 个编号专题 · 3 个可复现实验 · 40 道场景练习 · 9 个工具箱页面"
  actions:
    - theme: brand
      text: 运行实战实验
      link: /实战实验室/
    - theme: alt
      text: 速查手册
      link: /工具箱/CHEATSHEET
    - theme: alt
      text: GitHub
      link: https://github.com/jackfjy/llm_agent_interview/tree/codex/refresh-2026-10

features:
  - icon: 🧪
    title: 实战实验室
    details: 三条离线主线、真实 MCP 往返、40 道带失败条件的场景题
    link: /实战实验室/
  - icon: 🟢
    title: Phase 1 · 基础知识
    details: Python 高级编程、大模型发展脉络、LLM 基础原理
    link: /01-基础知识/01-Python高级编程
  - icon: 🔵
    title: Phase 2 · 核心技能
    details: Prompt 工程、RAG 系统、Agent 架构、记忆系统、多智能体、MCP、LangChain
    link: /02-核心技能/04-Prompt工程
  - icon: 🟣
    title: Phase 3 · 模型优化
    details: 模型微调与训练、模型部署与推理优化
    link: /03-模型优化/12-模型微调与训练
  - icon: 🟠
    title: Phase 4 · 工程化
    details: FastAPI、评估测试、安全防护、CI/CD、语音交互、数据工程
    link: /04-工程化/14-FastAPI与服务开发
  - icon: 🔴
    title: Phase 5 · 生产实战
    details: 生产环境实战、系统设计题、算法与编码题
    link: /05-生产实战/20-生产环境实战
  - icon: 🟡
    title: Phase 6 · 面试冲刺
    details: 前沿方向、行为面试、多模态、Embedding、知识图谱
    link: /06-面试冲刺/23-大模型前沿方向
  - icon: 🟢
    title: Phase 7 · 前沿专题
    details: 前沿大模型架构、Agent Loop、Context Engineering、Agentic Coding
    link: /07-前沿专题/28-前沿大模型架构
  - icon: 🔵
    title: Phase 8 · ML/DL 基础
    details: 经典机器学习、深度学习机制、优化器、NLP 技术演进、RLHF
    link: /34-经典机器学习基础
  - icon: 🟣
    title: Phase 9 · 实战工程
    details: Agent 开发实战、LLM 应用工程实践
    link: /39-Agent开发实战
  - icon: 🟠
    title: Phase 10 · 进阶专题
    details: LangChain 进阶实战、RAG 进阶工程、Agent 多智能体进阶
    link: /08-进阶专题/41-LangChain进阶实战
  - icon: ⚪
    title: Phase 11 · 网关运维
    details: LLM 网关架构、Token 治理、可观测性、高可用
    link: /09-大模型网关与运维/44-LLM网关架构设计
  - icon: 📦
    title: 面试工具箱
    details: 速查表、Top50 概念复习、术语表、公司经验笔记、调试场景、系统设计模板
    link: /工具箱/CHEATSHEET
---

<div style="text-align: center; padding: 2rem 0; color: var(--vp-c-text-2);">
  <p>面向大模型应用工程师 / Agent 开发工程师的系统化面试准备</p>
  <p>原作者 dirjaker · fork 维护 jackfjy · MIT</p>
</div>


## 验证范围

`last_verified: 2026-10-26` · 新实验的版本与状态见 [实验入口](./实战实验室/index.md)。固定 SDK 环境本地通过 37 项测试（零跳过），标准库环境 33 项通过、4 项 SDK 测试明确跳过；40 条回归 ×3 次均匹配预期。未验证真实模型质量，也未逐段运行旧题库的全部代码。

统计口径：01–47 编号专题、工具箱目录的 9 个页面，以及新增独立场景题 40 道；不表示出现频率或企业招聘事实。本分支没有自动发布站点。参阅 [岗位学习路线](./实战实验室/学习路线.md) 和 [维护规则](./实战实验室/维护规则.md)。
