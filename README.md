# Teal AI Agent —— AI 超级智能体（Python 版）

> 作者：程序猿Teal · 个人开源项目 · https://github.com/Teal-loading/ai-agent-two
>
> 技术栈：Python 3 · FastAPI · LangChain · LangGraph · PostgreSQL / pgvector · MCP · SSE · Docker

基于 **FastAPI + LangChain + LangGraph** 的超级智能体应用，包含两个可独立对话的 Agent：

- **AI 运动健康助手（FitApp）**：运动科学与健康管理顾问，支持多轮对话、RAG 知识库、工具调用与 MCP
- **AI 超级智能体（TealManus）**：基于 LangGraph `StateGraph` 编排的 Think–Act 自主规划智能体

---

## 一、技术栈

| 领域 | 选型 | 说明 |
|---|---|---|
| Web 框架 | FastAPI + Uvicorn | RESTful API、依赖注入、SSE 流式响应 |
| Agent 编排 | LangGraph（StateGraph + Checkpointer） | Think–Act 循环、条件路由、状态持久化与会话恢复 |
| 大模型 | LangChain + 阿里云百炼（OpenAI 兼容协议）/ Ollama | Tool Calling、Prompt Template、结构化输出、流式输出 |
| RAG | LangChain + pgvector（可切内存向量库） | 文档解析、分块、Embedding、检索与上下文注入 |
| 工具 | LangChain `@tool` + httpx + BeautifulSoup + ReportLab | 联网搜索、网页抓取、文件读写、PDF 生成、终端执行 |
| MCP | MCP Python SDK（Server）+ langchain-mcp-adapters（Client） | stdio / SSE 两种传输，工具发现与参数化调用 |
| 存储 | PostgreSQL + pgvector、本地文件 | 向量库、Agent 状态、会话记忆 |
| 部署 | Docker / docker-compose | 应用打包、pgvector、MCP 服务编排 |

## 二、模块结构

| 模块 | 说明 |
|---|---|
| `app/api` | HTTP 接口（SSE、同步、结构化输出） |
| `app/agent` | LangGraph 智能体：状态、节点、图、Checkpointer |
| `app/apps` | FitApp 业务应用 |
| `app/memory` | 会话记忆（窗口裁剪 + 内存/文件存储） |
| `app/rag` | 文档加载、切分、关键词增强、查询重写、向量库、检索顾问 |
| `app/tools` | 8 个内置工具与统一注册 |
| `app/advisor` | 日志回调、Re2 提示词增强 |
| `app/llm` | 大模型 / Embedding 工厂 |
| `app/middleware` | 调用日志 ASGI 中间件 |
| `mcp_servers/teal_image_search` | 图片搜索 MCP Server |
| `teal-ai-agent-frontend` | Vue3 + Vite 前端 |

```
app/
├── api/            routes_ai.py  routes_health.py  sse.py
├── agent/          state.py  nodes.py  teal_manus.py  checkpoint.py
├── apps/           fit_app.py
├── memory/         chat_memory.py
├── rag/            loader.py  splitter.py  enricher.py  rewriter.py  store.py  advisors.py  cloud.py
├── tools/          file_operation.py  pdf_generation.py  web_search.py  ...
├── advisor/        logger_advisor.py  re_reading_advisor.py
├── llm/            factory.py
├── middleware/     logging.py
├── resources/document/   三篇运动健康知识库
├── config.py  prompts.py  main.py
mcp_servers/teal_image_search/    server.py  tools.py  config.py
tests/                            51 个用例，覆盖提示词、文档、工具、图路由、接口、MCP
```

## 三、快速开始

### 1. 环境准备

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
# 至少填写 DASHSCOPE_API_KEY；使用工具搜索再填 SEARCH_API_KEY
```

### 3. 启动

```bash
uvicorn app.main:app --port 8123
# 或
python -m app.main
```

- 接口文档：http://localhost:8123/api/swagger-ui.html
- 健康检查：http://localhost:8123/api/health

### 4. 前端（可选）

```bash
cd teal-ai-agent-frontend
npm install && npm run dev     # http://localhost:3000
```

## 四、接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/ai/fit_app/chat/sync` | 同步对话（多轮记忆） |
| GET | `/api/ai/fit_app/chat/sse` | SSE 流式对话 |
| GET | `/api/ai/fit_app/chat/server_sent_event` | SSE 流式对话（等价别名） |
| GET | `/api/ai/fit_app/chat/sse_emitter` | SSE 流式对话（等价别名） |
| POST | `/api/ai/fit_app/chat/report` | 结构化输出：运动健康报告 |
| GET | `/api/ai/manus/chat` | Manus 超级智能体（SSE，逐步推送） |
| GET | `/api/health` | 健康检查 |

参数为 `message`、`chatId`，SSE 报文格式为 `data:<chunk>\n\n`，结束时补发 `data: [DONE]`。

```bash
# 流式对话
curl -N "http://localhost:8123/api/ai/fit_app/chat/sse?message=我是新手，怎么开始减脂&chatId=fit_001"

# 超级智能体（自动规划 + 多工具协作）
curl -N "http://localhost:8123/api/ai/manus/chat?message=帮我制定一份四周新手减脂计划并导出 PDF"
```

## 五、核心实现

### 1. ReAct 智能体（LangGraph）

```
START → think ─┬─(有工具调用)→ act ─┬─(未终止)→ think
               └─(无工具调用)→ END  └─(终止/异常)→ END
```

- `think`：追加 `next_step_prompt` → 调用带工具的大模型 → 记录 `AIMessage`（含 tool_calls）
- `act`：按 `tool_calls` 执行工具 → 回写 `ToolMessage` → 命中 `doTerminate` 则结束任务
- 每步结果写入 `logs`，通过 `astream(stream_mode="updates")` 逐条推送前端
- 状态由 Checkpointer 管理：默认 `MemorySaver`，配置 `MANUS_CHECKPOINTER=postgres` 后使用 `AsyncPostgresSaver`，同一 `thread_id` 可续跑

### 2. RAG 知识库

1. `FitAppDocumentLoader`：按 Markdown 分隔线切分，剔除代码块与引用块，补 `filename` / `status`（起步/突破/康复）元信息
2. `MyKeywordEnricher`：模型为每个片段抽取 5 个关键词写入元数据
3. `VectorStoreManager`：默认内存向量库，`VECTOR_STORE=pgvector` 时切换为 PostgreSQL + pgvector（HNSW / COSINE）
4. `QueryRewriter` + `RagService`：查询重写 → 相似度检索 → 按 `QuestionAnswerAdvisor` 模板注入上下文
5. `FitAppRagCustomAdvisor`：按身体阶段过滤 + 相似度阈值 0.5 + 空上下文兜底文案

### 3. 工具与 MCP

- 内置工具：`readFile`、`writeFile`、`searchWeb`、`scrapeWebPage`、`downloadResource`、`executeTerminalCommand`、`generatePDF`、`doTerminate`
- 工具名 / 参数名 / 描述属于模型可见的 Tool Schema，由 `tests/test_tools.py` 守护
- MCP Client 读取 `mcp-servers.json`，把外部 MCP 服务（高德地图、图片搜索）转为 LangChain 工具供 FitApp 调用
- MCP Server 提供 `searchImage` 工具，返回文本 URL 列表 + 首图预览（TextContent / ImageContent）

```bash
# 启动图片搜索 MCP 服务（SSE 模式）
MCP_TRANSPORT=sse MCP_PORT=8127 python -m mcp_servers.teal_image_search.server
```

### 4. 会话记忆与可观测性

- `WindowChatMemory`：保留最近 20 条消息，支持内存（默认）与文件持久化（JSON）两种存储
- `RequestLoggingMiddleware`（纯 ASGI）：记录方法、路径、状态码、耗时、会话 ID，不缓冲 SSE
- `MyLoggerCallback`：打印单次请求提示词与模型回复

## 六、配置说明

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `DASHSCOPE_API_KEY` | — | 阿里云百炼 API Key（必需） |
| `LLM_PROVIDER` | `dashscope` | `dashscope` 或 `ollama` |
| `CHAT_MODEL` | `qwen-plus` | 对话模型 |
| `VECTOR_STORE` | `memory` | `memory` / `pgvector` |
| `DATABASE_URL` | — | LangGraph Checkpointer 连接串 |
| `VECTOR_DATABASE_URL` | 复用 `DATABASE_URL` | pgvector 连接串（自动补 `+psycopg`） |
| `CHAT_MEMORY` | `memory` | `memory` / `file` |
| `MANUS_MAX_STEPS` | `20` | 智能体最大步数 |
| `MANUS_CHECKPOINTER` | `memory` | `memory` / `postgres` |
| `SEARCH_API_KEY` | — | SearchAPI（百度引擎）Key |
| `PEXELS_API_KEY` | — | 图片搜索 MCP 使用的 Key |

完整清单见 [`.env.example`](.env.example)。

## 七、Docker 部署

```bash
# 仅应用
docker build -t teal-agent .
docker run -p 8123:8123 -e DASHSCOPE_API_KEY=sk-xxx teal-agent

# 应用 + PostgreSQL/pgvector + 图片搜索 MCP 服务
export DASHSCOPE_API_KEY=sk-xxx
docker compose up -d --build
```

## 八、测试

```bash
pytest                      # 51 个用例
ruff check app mcp_servers  # 代码规范
```

覆盖范围：提示词完整性、知识库文档指纹校验、工具 Schema 与执行、LangGraph 路由（含终止/超步/异常）、
会话记忆、SSE 报文格式、接口错误处理、MCP 工具 Schema 与图片返回。

## 九、契约内容

以下内容属于「不可改写」的契约，均有测试守护，改动会直接导致测试失败：

- `app/resources/document/*.md`：三篇运动健康知识库正文（MD5 指纹校验）
- `app/prompts.py`：全部系统提示词、问答模板与运行期文案
- `app/tools/schemas.py`：工具描述与参数描述（模型可见的 Tool Schema，保留驼峰参数名）
