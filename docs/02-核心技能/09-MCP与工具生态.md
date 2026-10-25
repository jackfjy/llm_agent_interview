# 09. MCP 与工具生态

> last_verified: 2026-10-25
> versions: MCP 2026-07-28；Python mcp==2.3.0 服务端 API；legacy v1 对照
> 适用范围：规范分代、工具接入和安全；SDK 版本不等于规范日期
> example_status: 正文为教学片段或伪代码，未逐段执行；不等同于可运行项目验收。
> sources: [固定规范变更](https://modelcontextprotocol.io/specification/2026-07-28/changelog)、[授权规范](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)、[Python SDK v2](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0)、[A2A 1.0 系列](https://a2a-protocol.org/latest/specification/)

> **难度标记**：⭐ 基础 ⭐⭐ 进阶 ⭐⭐⭐ 高级
> **热度**：🔥🔥🔥 2025 年最高频新增考点

---

## 知识图谱

```
MCP 与工具生态
├── MCP 协议基础 ⭐⭐⭐ 必考
│   ├── 协议架构（Client-Server-Host）
│   ├── 核心能力（Tools / Resources / Prompts）
│   ├── 传输层（stdio / Streamable HTTP；区分历史 HTTP+SSE）
│   └── 与 OpenAI Function Calling 的区别
├── 工程实现 ⭐⭐ 进阶
│   ├── MCP Server 开发
│   ├── MCP Client 集成
│   ├── 安全与权限控制
│   └── 错误处理与重试
├── 工具生态 ⭐⭐ 进阶
│   ├── 工具发现与注册
│   ├── 工具编排（Tool Orchestration）
│   ├── 工具组合模式
│   └── 工具版本管理
└── 实战难题 ⭐⭐⭐
    ├── 多工具并发调用
    ├── 工具结果缓存
    ├── 工具沙箱与隔离
    └── 跨平台工具标准化
```

---

## 一、MCP 协议基础

### 1. ⭐⭐⭐ Q: 什么是 MCP（Model Context Protocol）？解决什么问题？

**答**：

MCP 是 Anthropic 于 2024 年 11 月发布的**开放协议标准**，定义了 LLM 应用与外部数据源、工具之间的通信方式。

**解决的核心问题**：

```
传统方式（M × N 问题）：
┌──────┐     ┌──────┐     ┌──────┐
│App 1 │────▶│Tool A│     │App 2 │────▶ Tool A（重复集成）
│      │────▶│Tool B│     │      │────▶ Tool B（重复集成）
│      │────▶│Tool C│     │      │────▶ Tool C（重复集成）
└──────┘     └──────┘     └──────┘
每个 App 都要写 N 个工具适配器 = M × N 个适配器

MCP 方式（M + N 问题）：
┌──────┐     ┌──────┐     ┌──────────┐
│App 1 │────▶│MCP   │────▶│Server A  │（工具实现一次）
│App 2 │────▶│Client│────▶│Server B  │（工具实现一次）
│App 3 │────▶│      │────▶│Server C  │（工具实现一次）
└──────┘     └──────┘     └──────────┘
每个 App 只需 1 个 MCP Client = M + N 个适配器
```

**类比**：MCP 之于 LLM 工具，就像 USB 之于外设 —— 统一接口，即插即用。

**与 Function Calling 的区别**：

| 维度 | Function Calling | MCP |
|------|-----------------|-----|
| 层级 | 模型层能力 | 应用层协议 |
| 定义 | 模型识别调用意图 | 标准化工具通信 |
| 范围 | 单次调用 | 完整生命周期（发现→调用→结果） |
| 依赖 | 绑定特定模型 API | 模型无关，跨平台 |
| 生态 | 各厂商私有格式 | 开放标准，统一生态 |

---

### 2. ⭐⭐⭐ Q: MCP 的架构由哪几部分组成？各自职责是什么？

**答**：

MCP 采用 **Host → Client → Server** 三层架构：

```
┌─────────────────────────────────────────────┐
│                  Host 层                     │
│  (Claude Desktop / IDE / 你的Agent应用)       │
│  ┌─────────────┐  ┌─────────────┐           │
│  │ MCP Client 1│  │ MCP Client 2│           │
│  └──────┬──────┘  └──────┬──────┘           │
└─────────┼────────────────┼──────────────────┘
          │                │
    ┌─────▼─────┐    ┌─────▼─────┐
    │MCP Server │    │MCP Server │
    │  (GitHub) │    │  (Slack)  │
    │  Tools:   │    │  Tools:   │
    │ - create_ │    │ - send_   │
    │   issue   │    │   message │
    │ - search  │    │ - list    │
    └───────────┘    └───────────┘
```

**Host（宿主）**：
- 运行 LLM 的应用程序（如 Claude Desktop、Cursor、你的 Agent）
- 管理 MCP Client 的生命周期
- 控制权限和安全策略

**Client（客户端）**：
- 与 MCP Server 建立一对一连接
- 处理版本选择和能力发现；2026 规范采用逐请求元数据
- 转发工具调用请求和结果

**Server（服务端）**：
- 暴露具体的工具（Tools）、资源（Resources）、提示（Prompts）
- 处理实际的业务逻辑
- 可以是本地进程（stdio）或远程服务（Streamable HTTP）

---

### 3. ⭐⭐⭐ Q: MCP 的三大核心能力是什么？举例说明。

**答**：

MCP Server 可以暴露三种类型的能力：

**① Tools（工具）** —— 模型可以调用的函数
```json
{
  "name": "create_issue",
  "description": "Create a GitHub issue",
  "inputSchema": {
    "type": "object",
    "properties": {
      "title": { "type": "string" },
      "body": { "type": "string" },
      "labels": { "type": "array", "items": { "type": "string" } }
    },
    "required": ["title"]
  }
}
```
特点：**模型主动调用**，需要用户确认（安全敏感操作）

**② Resources（资源）** —— 应用可以读取的数据
```json
{
  "uri": "file:///project/README.md",
  "name": "Project README",
  "mimeType": "text/markdown"
}
```
特点：**应用层读取**，类似 GET 请求，可以订阅更新

**③ Prompts（提示模板）** —— 预定义的交互模板
```json
{
  "name": "code_review",
  "description": "Review code for best practices",
  "arguments": [
    { "name": "code", "required": true },
    { "name": "language", "required": false }
  ]
}
```
特点：**用户/应用选择触发**，生成结构化的消息序列

**类比理解**：
- Tools = 函数调用（动词）
- Resources = 文件/数据库（名词）
- Prompts = 提示模板（动词+名词的组合）

---

### 4. ⭐⭐ Q: MCP 的传输方式与协议版本有什么关系？

**答**：先说明目标规范，再说明 SDK。不能把“stdio、SSE、Streamable HTTP”视作同一年代的三个并列选项。

| 规范年代 | 传输与生命周期 | 维护时注意 |
|---|---|---|
| 2024-11-05 | stdio；旧 HTTP+SSE 双端点 | 只用于历史兼容 |
| 2025 系列 | stdio；Streamable HTTP，含 initialize 握手与可选协议会话 | SSE 可以作为响应编码；不是另一套同义传输 |
| 2026-07-28 | stdio；无协议级会话的 Streamable HTTP | 请求携带版本/能力元数据，使用 server/discover 发现能力；不再先 initialize |

当前规范删除 `Mcp-Session-Id`，将独立通知流改为 `subscriptions/listen`，长交互可采用 Multi Round-Trip Requests（MRTR）。这不等于应用不能存状态：业务可显式传递服务端生成的句柄。SSE 仍可用于请求范围内的流式响应；旧 HTTP+SSE 被替代不代表 SSE 机制整体不可用。

2026 规范不提供旧式 SSE 断线续传保证；断流后重新请求时，业务写操作要携带稳定幂等键。协议 request ID 用于关联消息，不能代替业务去重 ID。多版本服务应显式协商/回退，不能从包版本号猜测对端行为。

stdio 适合本地子进程，stdout 只写协议消息，日志写 stderr。远程 Streamable HTTP 适合网关与网络部署，其身份、授权、超时与背压都需要单独设计。

---

### 5. ⭐⭐⭐ Q: 如何实现一个 MCP Server？以 Python 为例。

**答**：以下使用已检查可安装的 `mcp==2.3.0` 服务端接口：`MCPServer` 从 `mcp.server` 导入。装饰器和启动签名已核对；本章嵌入片段尚未完成客户端往返验收，不能以文档构建代替互通测试。完整实验应在独立环境锁定依赖，区分 SDK 与协议版本。

```python
# server.py；依赖 mcp==2.3.0
import math
from mcp.server import MCPServer

server = MCPServer("teaching-tools")

@server.tool()
def calculate(a: float, b: float, operation: str) -> float:
    """对两个有限且有界的数字执行 add/multiply。"""
    if not all(math.isfinite(x) and abs(x) <= 1_000_000 for x in (a, b)):
        raise ValueError("数字必须有限且绝对值不超过一百万")
    if operation == "add":
        return a + b
    if operation == "multiply":
        return a * b
    raise ValueError("只支持 add/multiply")

@server.tool()
def get_weather(city: str) -> dict:
    """返回教学天气 fixture，并非实时天气查询。"""
    fixtures = {"北京": {"condition": "晴", "temperature_c": 26}}
    if city not in fixtures:
        raise ValueError("fixture 只包含北京")
    return {"city": city, **fixtures[city], "source": "offline-fixture"}

if __name__ == "__main__":
    server.run(transport="stdio")
```

注册名和调用名均为 `get_weather`；调用 `weather` 应被视作未知工具。计算工具接收数值与操作枚举，不执行用户表达式。SDK 生成 schema 不能替代业务校验；部署时仍要检查权限、范围和调用预算。

**legacy v1 对照**：旧 `Server`/`FastMCP`、`ClientSession` 与 `initialize()` 代码属于 v1 兼容路线。若维护旧项目，可使用 `mcp>=1.28,<2` 的独立环境并锁定实际解析版本，不能将这些导入与本节 v2 启动参数拼接。官方 v2.0.0 发布说明已经支持 2026-07-28，但该版本也列出功能缺口，因此不宣称任何 SDK 自动实现全部规范。

---

### 6. ⭐⭐⭐ Q: 如何在 Agent 应用中集成 MCP Client？

**答**：客户端负责发现工具和传递结果，模型调用仍属于 Host。按目标 SDK 的文档管理连接生命周期，离开上下文时同时关闭传输与客户端，避免手工调用 `__aenter__()` 后遗留子进程。

```python
# client.py；mcp==2.3.0，签名已核对，完整往返测试另见独立实验
import asyncio
import sys
from mcp import Client, StdioServerParameters

async def main():
    params = StdioServerParameters(command=sys.executable, args=["server.py"])
    async with Client(params) as client:
        tools = await client.list_tools()
        print([tool.name for tool in tools.tools])
        result = await client.call_tool("get_weather", {"city": "北京"})
        print(result)  # 同时检查错误字段和所有返回内容，不只取第一段文本

if __name__ == "__main__":
    asyncio.run(main())
```

上述是客户端教学片段，未将签名核对宣称为互通通过。当前规范通过发现与逐请求元数据选择版本，不需添加旧版 `initialize()`。Responses 使用 `call_id`，Chat Completions 使用 `tool_call_id`；不要把 `result.content[0].text` 假设为全部结果，工具可能返回多段文本、结构化内容或错误。不要把协议无会话误读为无需管理网络连接或业务对话状态。

---

### 7. ⭐⭐ Q: MCP 的安全模型是怎样的？

**答**：

MCP 在多个层面实现安全控制：

**① Host 层权限控制**

Host 决定暴露哪些工具、哪些操作需要用户审批，并在执行前校验权限；这些是应用策略，不是服务端可以调用的标准 `host.confirm` RPC。工具提示和返回内容均视作不可信输入。

**② 传输与授权边界**

- 远程 HTTP 授权是独立可选能力；启用时按 OAuth 2.1、Protected Resource Metadata、授权服务器发现与 scope 校验实现。核对 issuer、resource/audience，不将为别的服务签发的 token 任意透传给下游。
- stdio 不套用 HTTP OAuth 流程；凭证可由 Host 通过环境等受控机制提供，限制子进程权限，避免日志泄漏。
- TLS 只保护传输，不等于用户身份与数据访问已获授权。当前授权规范推荐 Client ID Metadata Documents，DCR 属兼容路线；以固定版本规范核对细节。


**③ 工具层安全**

以下是应用策略伪代码，`validate_input`、权限上下文和限流器由应用实现，不是 v2 SDK 的可直接运行回调。

```python
# 工具实现中的安全措施
# 应用层执行包装，伪代码
async def guarded_dispatch(name, arguments):
    # 1. 输入验证
    validate_input(arguments)
    
    # 2. 权限检查
    if not has_permission(current_user, name):
        raise PermissionError("无权限")
    
    # 3. 速率限制
    if rate_limiter.is_limited(name):
        raise RateLimitError("请求过于频繁")
    
    # 4. 沙箱执行
    result = sandbox_execute(name, arguments)
    
    # 5. 输出过滤
    return sanitize_output(result)
```

**④ 最小权限原则**
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxx"  // 使用 fine-grained token，只给必要权限
      }
    }
  }
}
```

---

## 二、工程实践

### 8. ⭐⭐⭐ Q: MCP 与 OpenAI Function Calling、Tool Use 有什么区别？什么时候用哪个？

**答**：

| 维度 | OpenAI Function Calling | Anthropic Tool Use | MCP |
|------|------------------------|-------------------|-----|
| 层级 | 模型 API 能力 | 模型 API 能力 | 应用层协议 |
| 范围 | 单次调用 | 单次调用 | 完整生命周期 |
| 标准化 | 各厂商私有 | 各厂商私有 | 开放标准 |
| 工具发现 | 手动定义 | 手动定义 | 自动发现 |
| 状态管理 | 应用自行管理 | 应用自行管理 | 2026 规范无协议级会话，业务状态显式管理 |
| 生态 | OpenAI 生态 | Anthropic 生态 | 跨平台 |

**选择策略**：

```
需要跨平台/跨模型？ ──是──▶ 用 MCP
        │
        否
        ▼
只用单一模型？ ──是──▶ 用该模型的原生 Function Calling
        │
        否
        ▼
需要工具复用？ ──是──▶ 用 MCP（写一次，到处用）
        │
        否
        ▼
简单场景 ──▶ Function Calling 足够
```

**实际项目中的最佳实践**：
```
┌─────────────────────────────────────────┐
│              你的 Agent 应用              │
│  ┌───────────────────────────────────┐  │
│  │         统一工具抽象层             │  │
│  │  (将 MCP 工具转为 Function Call)   │  │
│  └─────────────┬─────────────────────┘  │
│                │                         │
│    ┌───────────┼───────────┐            │
│    ▼           ▼           ▼            │
│  OpenAI    Anthropic    本地模型         │
│  Function  Tool Use     MCP Tools       │
│  Calling                              │
└─────────────────────────────────────────┘
```

---

### 9. ⭐⭐ Q: 如何实现 MCP 工具的动态发现和热更新？

**答**：

```python
class MCPToolRegistry:
    """MCP 工具注册中心 — 支持动态发现和热更新"""
    
    def __init__(self):
        self.servers: dict[str, MCPServerConnection] = {}
        self.tools: dict[str, Tool] = {}
        self._watchers: list[Callable] = []
    
    async def register_server(self, name: str, config: dict):
        """注册一个 MCP Server"""
        conn = MCPServerConnection(config)
        await conn.connect()
        self.servers[name] = conn
        
        # 获取该 Server 的所有工具
        tools = await conn.list_tools()
        for tool in tools:
            tool_id = f"{name}/{tool.name}"  # 命名空间隔离
            self.tools[tool_id] = tool
        
        # 启动工具变更监听
        asyncio.create_task(self._watch_server(name, conn))
    
    async def _watch_server(self, name: str, conn: MCPServerConnection):
        """监听 Server 工具变更"""
        while True:
            try:
                # 定期轮询或订阅变更通知
                await asyncio.sleep(30)
                new_tools = await conn.list_tools()
                
                # 检测变更
                old_ids = {t.name for t in self.tools.values() if t.name.startswith(name)}
                new_ids = {t.name for t in new_tools}
                
                added = new_ids - old_ids
                removed = old_ids - new_ids
                
                if added or removed:
                    # 更新工具注册表
                    for tool in new_tools:
                        self.tools[f"{name}/{tool.name}"] = tool
                    for r in removed:
                        self.tools.pop(f"{name}/{r}", None)
                    
                    # 通知观察者
                    for watcher in self._watchers:
                        await watcher(name, added, removed)
                    
                    logger.info(f"Server {name} 工具变更: +{added} -{removed}")
            
            except Exception as e:
                logger.error(f"监听 Server {name} 失败: {e}")
                await asyncio.sleep(5)
    
    def on_tools_changed(self, callback: Callable):
        """注册工具变更回调"""
        self._watchers.append(callback)
    
    async def call_tool(self, tool_id: str, arguments: dict):
        """调用工具"""
        if tool_id not in self.tools:
            raise ToolNotFoundError(f"工具 {tool_id} 不存在")
        
        server_name = tool_id.split("/")[0]
        tool_name = tool_id.split("/", 1)[1]
        
        conn = self.servers[server_name]
        return await conn.call_tool(tool_name, arguments)
    
    def get_tools_for_llm(self) -> list[dict]:
        """导出为 LLM function calling 格式"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool_id.replace("/", "__"),  # 避免命名冲突
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            for tool_id, tool in self.tools.items()
        ]
```

---

### 10. ⭐⭐⭐ Q: 多个 MCP Server 的工具如何编排？有哪些模式？

**答**：

**模式一：串行链式调用**
```
用户: "帮我创建一个 Jira ticket，并在 Slack 通知"

Agent 执行链:
1. MCP(Server=jira) → create_issue(title, description)
2. 拿到 issue_id
3. MCP(Server=slack) → send_message(channel, f"新 Issue: {issue_id}")
```

**模式二：并行调用**
```
用户: "查一下 GitHub 和 Jira 的最新状态"

Agent 执行:
┌──────────────────────┬──────────────────────┐
│ MCP(Server=github)   │ MCP(Server=jira)     │
│ → list_recent_prs()  │ → list_my_issues()   │
└──────────┬───────────┴──────────┬───────────┘
           └──────────┬───────────┘
                      ▼
              合并结果返回给用户
```

**模式三：条件分支**
```
用户: "帮我处理这个错误"

Agent 判断:
├── 如果是代码 Bug → MCP(Server=github) → create_issue()
├── 如果是线上告警 → MCP(Server=pagerduty) → create_incident()
└── 如果是用户反馈 → MCP(Server=intercom) → reply_message()
```

**实现代码**：
```python
class MCPToolOrchestrator:
    """MCP 工具编排器"""
    
    def __init__(self, registry: MCPToolRegistry):
        self.registry = registry
    
    async def parallel_call(self, calls: list[dict]) -> list:
        """并行调用多个工具"""
        tasks = [
            self.registry.call_tool(c["tool_id"], c["arguments"])
            for c in calls
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def chain_call(self, calls: list[dict]) -> any:
        """串行链式调用，前一个结果传给下一个"""
        result = None
        for call in calls:
            # 支持动态参数（引用前一步结果）
            arguments = self._resolve_args(call["arguments"], result)
            result = await self.registry.call_tool(call["tool_id"], arguments)
        return result
    
    async def conditional_call(self, condition: str, branches: dict) -> any:
        """条件分支调用"""
        # 让 LLM 判断走哪个分支
        branch = await self._evaluate_condition(condition, branches)
        return await self.registry.call_tool(
            branches[branch]["tool_id"],
            branches[branch]["arguments"]
        )
```

---

## 三、高级话题

### 11. ⭐⭐⭐ Q: MCP 的工具描述（Tool Description）如何优化以提高调用准确率？

**答**：

工具描述是 LLM 决定是否调用、如何调用的关键。优化策略：

**① 描述要具体，不要泛泛**
```json
// ❌ 差
{
  "name": "search",
  "description": "搜索数据"
}

// ✅ 好
{
  "name": "search_documents",
  "description": "在知识库中搜索文档。返回最相关的文档片段，按相关度排序。适用于查找技术文档、产品手册、FAQ 等。不适用于实时数据查询。",
  "inputSchema": {
    "properties": {
      "query": {
        "description": "搜索查询，用自然语言描述你要找的内容。示例: '如何配置 OAuth2 认证'"
      },
      "top_k": {
        "description": "返回结果数量，默认 5。如果需要全面分析可以设为 10-20"
      }
    }
  }
}
```

**② 提供参数约束和示例**
```json
{
  "name": "create_issue",
  "inputSchema": {
    "properties": {
      "priority": {
        "type": "string",
        "enum": ["low", "medium", "high", "critical"],
        "description": "优先级。low=不影响使用, medium=有 workaround, high=影响核心功能, critical=系统不可用"
      },
      "labels": {
        "type": "array",
        "items": { "type": "string" },
        "description": "标签列表。常用: ['bug', 'feature', 'docs', 'performance']"
      }
    }
  }
}
```

**③ 说明使用场景和限制**
```json
{
  "name": "execute_sql",
  "description": "执行只读 SQL 查询。仅支持 SELECT 语句，不支持 INSERT/UPDATE/DELETE。查询超时 30 秒。返回前 1000 行。",
  "inputSchema": {
    "properties": {
      "query": {
        "description": "SQL 查询语句。必须是 SELECT 语句。支持 JOIN、子查询、聚合函数。"
      }
    }
  }
}
```

---

### 12. ⭐⭐⭐ Q: MCP 在生产环境中如何做监控和可观测性？

**答**：

```python
import time
from opentelemetry import trace

tracer = trace.get_tracer("mcp-client")

class ObservableMCPClient:
    """带可观测性的 MCP Client"""
    
    async def call_tool(self, tool_id: str, arguments: dict):
        # 1. 创建 Span
        with tracer.start_as_current_span(
            "mcp.call_tool",
            attributes={
                "mcp.tool_id": tool_id,
                "mcp.server": tool_id.split("/")[0],
                "mcp.tool_name": tool_id.split("/", 1)[1],
            }
        ) as span:
            start = time.time()
            
            try:
                # 2. 调用工具
                result = await self._do_call(tool_id, arguments)
                
                # 3. 记录成功指标
                duration = time.time() - start
                span.set_attribute("mcp.duration_ms", duration * 1000)
                span.set_attribute("mcp.result_size", len(str(result)))
                span.set_status(trace.Status(trace.StatusCode.OK))
                
                # 4. 发送指标
                metrics.histogram("mcp.tool.duration", duration, tags={
                    "tool": tool_id,
                    "status": "success"
                })
                metrics.increment("mcp.tool.calls", tags={"tool": tool_id})
                
                return result
            
            except Exception as e:
                # 5. 记录失败
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                metrics.increment("mcp.tool.errors", tags={
                    "tool": tool_id,
                    "error": type(e).__name__
                })
                raise

# 监控 Dashboard 关键指标
MONITORING_METRICS = {
    "mcp.tool.duration":       "工具调用延迟 (P50/P95/P99)",
    "mcp.tool.calls":          "工具调用 QPS",
    "mcp.tool.errors":         "工具调用错误率",
    "mcp.tool.result_size":    "结果大小分布",
    "mcp.server.connected":    "Server 连接状态",
    "mcp.tool.cache.hit_rate": "工具结果缓存命中率",
}
```

---

### 13. ⭐⭐ Q: MCP 与 A2A（Agent-to-Agent）协议是什么关系？

**答**：

本节 A2A 按 **1.0 系列**说明；官方规范与 SDK/release 版本应分别记录。1.0 对对象包装和 `kind` 等字段有破坏性变化，不直接复制早期 JSON；版本按 Major.Minor 协商。长任务需要描述状态、取消请求、鉴权与 Artifact，取消请求不保证已经发生的外部写入被撤销。

两者解决不同层次的问题：

```
┌─────────────────────────────────────────────────────┐
│                    应用层                             │
│  ┌──────────────────────────────────────────────┐   │
│  │              A2A 协议                         │   │
│  │  Agent 之间发现、协商、协作                    │   │
│  │  (Agent Card → Task → Artifact)              │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                                │
│  ┌──────────────────▼───────────────────────────┐   │
│  │              MCP 协议                         │   │
│  │  Agent 与工具/数据源的标准化连接              │   │
│  │  (Tools → Resources → Prompts)               │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

| 维度 | MCP | A2A |
|------|-----|-----|
| 起源 | Anthropic 发起的开放协议 | Google 发起的开放协议 |
| 解决问题 | Agent ↔ 工具/数据 | Agent ↔ Agent |
| 核心概念 | Tools, Resources, Prompts | Agent Card, Task, Artifact |
| 通信模式 | 请求-响应 | 异步任务，支持长时间运行 |
| 关系 | 互补，不是竞争 | 互补，不是竞争 |

**实际应用中两者结合**：
```
用户 → Orchestrator Agent
         │
         ├──A2A──▶ Research Agent ──MCP──▶ Web Search Tool
         │                                    │
         ├──A2A──▶ Code Agent ────MCP──▶ GitHub Tool
         │                                    │
         └──A2A──▶ Report Agent ──MCP──▶ Docs Tool
```

---

### 14. ⭐⭐⭐ Q: 如何测试 MCP Server？有哪些测试策略？

**答**：把“本地函数能返回结果”与“真实 SDK 客户端可互通”分开验收。只手写 JSON-RPC 报文不能证明 SDK 配套可用。

| 测试层 | 必须检查的行为 |
|---|---|
| 纯工具逻辑 | calculate 的 add/multiply、有限数值、越界输入、非法操作；天气 fixture 的城市范围 |
| SDK stdio 往返 | 子进程启动、工具发现、以 get_weather 注册名调用、参数与返回内容；退出后释放资源 |
| 错误语义 | 未知工具/非法参数；区分协议错误与工具执行失败，不假定总会抛 Python 异常 |
| 故障与预算 | 超时、子进程退出、重试上限、取消、重复写入去重 |
| 版本兼容 | 当前规范与明确保留的旧客户端环境分别运行，不能把旧 initialize 测试标为当前规范 |

性能阈值由环境基线确定，报告 P50/P95、负载与样本数；不要把“本地应小于 100ms”写成协议保证。远程授权需额外验证错误 audience、失效 token 和最小 scope。未启动真实客户端时只记录静态检查，不能记录“互通通过”。

---

### 15. ⭐⭐⭐ Q: 如何设计一个支持多 MCP Server 的 Agent 框架？

**答**：

```python
class MultiMCPAgent:
    """支持多 MCP Server 的 Agent 框架"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.registry = MCPToolRegistry()
        self.tool_call_log = []  # 工具调用日志
    
    async def add_server(self, name: str, config: dict):
        """添加 MCP Server"""
        await self.registry.register_server(name, config)
        logger.info(f"已连接 Server: {name}, 工具数: {len(self.registry.tools)}")
    
    async def run(self, user_message: str, max_iterations: int = 10) -> str:
        """运行 Agent 循环"""
        messages = [{"role": "user", "content": user_message}]
        tools = self.registry.get_tools_for_llm()
        
        for i in range(max_iterations):
            # 1. 调用 LLM
            response = await self.llm.chat(messages=messages, tools=tools)
            
            # 2. 如果没有工具调用，返回结果
            if not response.tool_calls:
                return response.content
            
            # 3. 执行工具调用
            messages.append(response.message)
            
            for tool_call in response.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                # 转换命名空间
                tool_id = tool_name.replace("__", "/")
                
                try:
                    result = await self.registry.call_tool(tool_id, arguments)
                    tool_result = result.content[0].text
                    
                    # 记录调用日志
                    self.tool_call_log.append({
                        "tool": tool_id,
                        "arguments": arguments,
                        "result": tool_result[:500]  # 截断
                    })
                
                except Exception as e:
                    tool_result = f"工具调用失败: {e}"
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
        
        return "达到最大迭代次数"
    
    def get_tool_usage_stats(self) -> dict:
        """获取工具使用统计"""
        from collections import Counter
        tool_counts = Counter(log["tool"] for log in self.tool_call_log)
        return {
            "total_calls": len(self.tool_call_log),
            "tool_distribution": dict(tool_counts),
            "avg_result_size": sum(
                len(log["result"]) for log in self.tool_call_log
            ) / max(len(self.tool_call_log), 1)
        }
```

---

### 16. ⭐⭐⭐ Q: MCP 工具调用失败如何做优雅降级？

**答**：

```python
class ResilientMCPClient:
    """带容错的 MCP Client"""
    
    def __init__(self):
        self.servers: dict[str, MCPServerConnection] = {}
        self.fallback_strategies: dict[str, Callable] = {}
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
    
    async def call_tool_with_fallback(
        self, 
        tool_id: str, 
        arguments: dict,
        max_retries: int = 3
    ) -> str:
        """带重试和降级的工具调用"""
        
        # 1. 熔断器检查
        breaker = self.circuit_breakers.get(tool_id)
        if breaker and breaker.is_open():
            return await self._fallback(tool_id, arguments)
        
        # 2. 重试逻辑
        last_error = None
        for attempt in range(max_retries):
            try:
                result = await asyncio.wait_for(
                    self._do_call(tool_id, arguments),
                    timeout=10.0  # 超时控制
                )
                
                # 成功，重置熔断器
                if breaker:
                    breaker.record_success()
                
                return result
            
            except asyncio.TimeoutError:
                last_error = "工具调用超时"
                logger.warning(f"{tool_id} 超时 (尝试 {attempt+1}/{max_retries})")
            
            except ServerDisconnectedError:
                last_error = "Server 断开连接"
                logger.warning(f"{tool_id} Server 断开 (尝试 {attempt+1}/{max_retries})")
                # 尝试重连
                await self._reconnect(tool_id)
            
            except ToolExecutionError as e:
                last_error = str(e)
                # 工具执行错误不重试
                break
            
            # 指数退避
            await asyncio.sleep(2 ** attempt)
        
        # 3. 所有重试失败，触发熔断
        if breaker:
            breaker.record_failure()
        
        # 4. 降级处理
        return await self._fallback(tool_id, arguments, last_error)
    
    async def _fallback(self, tool_id: str, arguments: dict, error: str = None) -> str:
        """降级策略"""
        
        # 策略 1: 使用缓存结果
        cached = await self.cache.get(f"{tool_id}:{hash(str(arguments))}")
        if cached:
            logger.info(f"{tool_id} 使用缓存结果")
            return cached
        
        # 策略 2: 使用备用 Server
        backup = self.backup_servers.get(tool_id)
        if backup:
            try:
                return await backup.call_tool(tool_id.split("/", 1)[1], arguments)
            except Exception:
                pass
        
        # 策略 3: 返回友好错误信息
        return json.dumps({
            "error": True,
            "message": f"工具 {tool_id} 暂时不可用，请稍后再试",
            "suggestion": "你可以手动完成这个操作，或者换个方式提问"
        })
```

---

### 17. ⭐⭐ Q: MCP 工具结果如何做缓存？缓存策略有哪些？

**答**：

```python
from datetime import timedelta

class MCPToolCache:
    """MCP 工具结果缓存"""
    
    def __init__(self):
        self.cache = {}
        
        # 不同工具的缓存策略
        self.strategies = {
            # 实时数据：不缓存
            "weather/get_current": {"ttl": 0, "key_fields": ["city"]},
            
            # 半静态数据：短期缓存
            "github/list_repos": {"ttl": 300, "key_fields": ["owner"]},
            
            # 静态数据：长期缓存
            "docs/search": {"ttl": 3600, "key_fields": ["query"]},
            
            # 计算结果：永久缓存
            "calculator/evaluate": {"ttl": -1, "key_fields": ["expression"]},
        }
    
    def _build_cache_key(self, tool_id: str, arguments: dict) -> str:
        """构建缓存键"""
        strategy = self.strategies.get(tool_id, {"key_fields": list(arguments.keys())})
        
        # 只用关键字段作为缓存键
        key_parts = []
        for field in strategy["key_fields"]:
            key_parts.append(f"{field}={arguments.get(field)}")
        
        return f"{tool_id}|{'&'.join(key_parts)}"
    
    async def get_or_call(self, tool_id: str, arguments: dict, caller: Callable) -> str:
        """获取缓存结果或调用工具"""
        strategy = self.strategies.get(tool_id, {"ttl": 0})
        
        # 不缓存
        if strategy["ttl"] == 0:
            return await caller(tool_id, arguments)
        
        cache_key = self._build_cache_key(tool_id, arguments)
        
        # 检查缓存
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if strategy["ttl"] == -1 or entry["expires"] > time.time():
                return entry["value"]
        
        # 缓存未命中，调用工具
        result = await caller(tool_id, arguments)
        
        # 写入缓存
        self.cache[cache_key] = {
            "value": result,
            "expires": time.time() + strategy["ttl"] if strategy["ttl"] > 0 else float('inf'),
            "created": time.time()
        }
        
        return result
```

---

### 18. ⭐⭐⭐ Q: MCP Server 如何做版本管理和向后兼容？

**答**：区分三种版本：规范日期、SDK 包版本、业务工具 schema 版本。2026 的逐请求版本元数据属于协议；业务参数 `schema_version` 不能替代它，也不应伪造一个 SDK 不存在的 `protocol_version` 回调参数。

- 规范兼容：通过发现与版本元数据选择支持的协议；旧规范回退由兼容实现处理，不混用握手。
- SDK 兼容：锁定并实际运行客户端/服务端组合，记录缺失能力；升级 SDK 后重新做往返测试。
- 工具兼容：新增可选参数保持原默认语义；破坏性变更可另命名 `search_v2`，给迁移期，不静默选择“最近”行为。
- 状态兼容：2026 工具列表不按连接变化。权限仍需在每次执行时校验，不能依赖曾经发现过工具就放行。

```json
{
  "name": "search_v2",
  "description": "关键词或语义检索；需要调用时权限校验",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "mode": {"type": "string", "enum": ["keyword", "semantic"]}
    },
    "required": ["query", "mode"],
    "additionalProperties": false
  }
}
```

该 JSON 为业务 schema 示意，不是完整 RPC 信封；不要以此冒充协议或 SDK 验收。

---

## 总结

### 面试高频追问

1. **"MCP 和 Function Calling 什么关系？"** → MCP 是应用层协议，Function Calling 是模型层能力，两者互补
2. **"MCP 怎么保证安全？"** → Host 层权限 + 传输加密 + 最小权限 + 沙箱执行
3. **"多个 MCP Server 怎么管理？"** → 工具注册中心 + 命名空间隔离 + 动态发现
4. **"MCP 工具调用失败怎么办？"** → 重试 + 熔断 + 降级（缓存/备用/友好提示）
5. **"MCP 和 A2A 什么关系？"** → MCP 解决 Agent↔Tool，A2A 解决 Agent↔Agent，互补

### 关键数字

| 指标 | 参考值 |
|------|--------|
| MCP 工具调用延迟 | 按部署环境实测 P50/P95，协议不保证固定延迟 |
| 工具描述长度 | 建议 50-200 字 |
| 重试次数 | 2-3 次，指数退避 |
| 缓存 TTL | 静态 1h, 半静态 5min, 实时不缓存 |
