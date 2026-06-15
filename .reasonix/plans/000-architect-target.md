# 000 — DME API 代理架构设计

## 1. 概述

构建一个 **DME API 代理系统**，包含服务端（Proxy Server）和客户端（Proxy Client）两个组件，实现外部 REST API 请求到 DME 环境的透明代理转发。

```
┌──────────────┐     REST API      ┌──────────────────┐      HTTP       ┌──────────────┐     DME API      ┌──────────┐
│  外部客户端   │ ──────────────►   │  Proxy Server    │ ◄─────────────► │  Proxy Client │ ──────────────► │ DME 环境  │
│  (curl/browser)│                  │  (Python/FastAPI) │                 │  (Python)     │                 │          │
└──────────────┘                   └──────────────────┘                 └──────────────┘                 └──────────┘
                                        │    ▲                               │    ▲
                                        │    │                               │    │
                                        ▼    │                               ▼    │
                                   ┌────────────┐                     ┌──────────────┐
                                   │ 请求队列    │                     │ 响应队列      │
                                   │ (内存/Redis)│                     │ (内存/Redis)  │
                                   └────────────┘                     └──────────────┘
```

---

## 2. 组件职责

### 2.1 Proxy Server（服务端）

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /api/v1/proxy` | 任意 HTTP 方法 | 接收外部 REST API 请求，入请求队列 |
| `GET  /api/v1/proxy/health` | GET | 健康检查 |
| 内部 | — | 异步监听响应队列，将响应回给外部调用者 |

**核心流程**：
1. 接收外部 REST API 请求（方法、URI、headers、params、body）
2. 将请求封装为 `ProxyRequest` 消息，发布到**请求消息队列**
3. 为该请求生成唯一 `request_id`，阻塞等待对应响应
4. 异步协程监听**响应消息队列**，按 `request_id` 匹配
5. 匹配到响应后，以 HTTP 状态码 + headers + body 回复外部客户端

### 2.2 Proxy Client（客户端）

**参数来源**（环境变量 > 构造函数参数）：

| 参数 | 对应环境变量 | 说明 |
|------|-------------|------|
| `server` | `DME_PROXY_SERVER` | Proxy Server 地址 (http://host:port) |
| `endpoint` | `DME_API_ENDPOINT` | DME API 基础地址 |
| `username` | `DME_API_USERNAME` | DME 用户名 |
| `password` | `DME_API_PASSWORD` | DME 密码 |
| `token` | `DME_API_AUTH_TOKEN` | DME 认证 Token（优先于 username/password） |

**核心流程**：
1. 轮询或长轮询 Server 的请求队列（`GET /api/v1/proxy/poll`）
2. 拿到 `ProxyRequest` 后，调用 `pydme.client.DMEAPIClient` 访问 DME 环境
3. 获取 DME 响应后，封装为 `ProxyResponse`，回调 Server 响应队列（`POST /api/v1/proxy/respond`）

### 2.3 pydme 依赖

```bash
pip install git+https://github.com/agentic-data-ops/dme-python-sdk.git
```

入口：`from pydme.client import DMEAPIClient`

---

## 3. 数据结构

### 3.1 ProxyRequest（请求消息）

```python
@dataclass
class ProxyRequest:
    request_id: str          # UUID，唯一标识
    method: str              # HTTP 方法：GET/POST/PUT/DELETE/PATCH...
    uri: str                 # 请求 URI 路径
    headers: dict[str, str]  # 请求头
    params: dict[str, str]   # URL 查询参数
    body: str | None         # 请求体（JSON 字符串）
```

### 3.2 ProxyResponse（响应消息）

```python
@dataclass
class ProxyResponse:
    request_id: str          # 与 ProxyRequest 关联
    status_code: int         # HTTP 状态码 200/404/500...
    headers: dict[str, str]  # 响应头
    body: str | None         # 响应体（JSON 字符串）
```

---

## 4. API 设计

### 4.1 Proxy Server 对外 API

| 路径 | 方法 | 说明 |
|------|------|------|
| `/*` | 任意 | 代理入口，捕获所有外部请求 |
| `/api/v1/proxy/health` | GET | Server 健康检查 |
| `/api/v1/proxy/poll` | GET | Client 轮询请求队列（返回 ProxyRequest） |
| `/api/v1/proxy/respond` | POST | Client 提交响应（Body: ProxyResponse） |

### 4.2 Proxy Client API

| 方法 | 说明 |
|------|------|
| `DMEProxyClient.run()` | 启动轮询循环，持续消费请求并转发 DME |
| `DMEProxyClient.poll_once()` | 单次轮询 + 转发 + 回调 |

---

## 5. 队列设计

两种实现方案，初期用 **内存队列**，后续可平滑切换 Redis：

| 特性 | 内存队列 (asyncio.Queue) | Redis 队列 |
|------|------------------------|------------|
| 适用场景 | 单进程开发 / 测试 | 多进程 / 生产部署 |
| 依赖 | 无 | redis-py |
| 切换成本 | 实现 QueueInterface 抽象 | 继承同一接口 |
| 持久化 | 无，重启丢失 | 可选持久化 |

**QueueInterface 抽象**：

```python
class MessageQueue(ABC):
    @abstractmethod
    async def publish_request(self, req: ProxyRequest): ...
    @abstractmethod
    async def consume_request(self) -> ProxyRequest | None: ...
    @abstractmethod
    async def publish_response(self, resp: ProxyResponse): ...
    @abstractmethod
    async def consume_response(self, request_id: str) -> ProxyResponse | None: ...
```

---

## 6. 项目结构

```
dme-proxy/
├── README.md
├── pyproject.toml
├── setup.cfg / setup.py
├── src/
│   ├── dme_proxy/
│   │   ├── __init__.py
│   │   ├── __main__.py              # python -m dme_proxy.server / client
│   │   ├── models.py                # ProxyRequest, ProxyResponse
│   │   ├── queue/
│   │   │   ├── __init__.py
│   │   │   ├── interface.py         # MessageQueue ABC
│   │   │   └── memory.py            # MemoryQueue (asyncio.Queue)
│   │   ├── server/
│   │   │   ├── __init__.py
│   │   │   ├── app.py               # FastAPI 应用，路由
│   │   │   └── handler.py           # 请求入队 + 响应等待协程管理
│   │   └── client/
│   │       ├── __init__.py
│   │       ├── client.py            # DMEProxyClient
│   │       └── config.py            # 参数解析（env / constructor）
│   ├── dme_proxy_server/
│   │   └── __main__.py              # CLi entry: dme-proxy-server
│   └── dme_proxy_client/
│       └── __main__.py              # CLI entry: dme-proxy-client
├── tests/
│   ├── test_models.py
│   ├── test_queue_memory.py
│   ├── test_server.py
│   ├── test_client.py
│   └── conftest.py
└── .reasonix/
    ├── scripts/                     # 构建/运行脚本（过程性，任务完成后清理）
    └── output/                      # 脚本运行日志（过程性，任务完成后清理）
```

> `.reasonix/scripts` 和 `.reasonix/output` 为中间过程文件，任务完成后自动清理。

---

## 7. 实现步骤

| # | 步骤 | 产出 | 风险 |
|---|------|------|------|
| 1 | 项目骨架：pyproject.toml, 目录结构, `__init__.py` | 可 pip install -e . 的空项目 | 低 |
| 2 | `models.py`：ProxyRequest, ProxyResponse dataclass + JSON 序列化 | 数据结构定型 | 低 |
| 3 | `queue/interface.py` + `queue/memory.py`：消息队列抽象 + 内存实现 | 队列可用 | 低 |
| 4 | `server/app.py`：FastAPI 应用，对外代理路由 + poll/respond 端点 | Server HTTP 接口就绪 | 中 |
| 5 | `server/handler.py`：请求入队列 + 异步等待响应 + 超时清理 | 请求-响应全链路 | 中 |
| 6 | `client/config.py`：环境变量 / 构造参数解析 | 客户端可配置 | 低 |
| 7 | `client/client.py`：DMEProxyClient 轮询 + 转发 DME + 回调 | 客户端完整循环 | 高（依赖 pydme 兼容性） |
| 8 | CLI 入口：`dme-proxy-server`, `dme-proxy-client` | 可直接命令行启动 | 低 |
| 9 | 测试：单元测试 + 集成测试（mock DME） | 质量保障 | 中 |
| 10 | 示例 + README 完善 | 可用文档 | 低 |

---

## 8. 风险与开放问题

| # | 风险 | 缓解 |
|---|------|------|
| R1 | pydme DMEAPIClient 的接口形态未知 | 步骤 7 前先调研 `DMEAPIClient.__init__` 参数 |
| R2 | 同步/异步不匹配：DMEAPIClient 可能是同步 SDK | 用 `asyncio.to_thread()` / `run_in_executor` 包裹 |
| R3 | 请求队列无持久化 → Server 重启丢请求 | 初期可接受，生产切 Redis |
| R4 | 外部客户端 HTTP 长连接超时 | Server 设置合理超时（30s），超时返回 504 |

**开放问题**：
- Q1: DMEAPIClient 是否支持 Token 方式认证？需要确认 SDK 文档。
- Q2: 是否需要在 Server 端做请求去重（幂等性）？
- Q3: 是否需要支持身份认证（外部客户端调用 Server 时的鉴权）？

---

## 9. 未纳入范围（后续迭代）

- Redis 队列实现
- 请求持久化 / 重试机制
- 外部客户端身份认证（API Key）
- 管理面板 / 监控
- 多客户端负载均衡
