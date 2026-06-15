# DME API Proxy

透明代理系统，将外部 REST API 请求通过消息队列转发到 DME 环境。

## 架构

```
外部客户端 → REST API → Proxy Server ──► 请求队列 ◄── Proxy Client ──► DME 环境
                                                     ──► 响应队列 ◄──
```

| 组件 | 说明 |
|------|------|
| **Proxy Server** | FastAPI 服务，接收外部 REST API 请求，入队列，等待响应后回复客户端 |
| **Proxy Client** | 轮询 Server 请求队列，调用 DME API 并回调响应（自动登录、session 管理） |
| **请求队列** | 暂存待转发到 DME 的请求（`ProxyRequest`） |
| **响应队列** | 暂存 DME 返回的响应（`ProxyResponse`），按 `request_id` 匹配 |

## 快速开始

### 安装

```bash
pip install -e .
```

### 启动 Server

```bash
python -m cli.server --host 127.0.0.1 --port 26335
```

### 启动 Client

```bash
# 设置认证参数（环境变量）
export DME_PROXY_SERVER=http://127.0.0.1:26335
export DME_API_ENDPOINT=https://your-dme-instance/api/v1
export DME_API_USERNAME=admin
export DME_API_PASSWORD=secret

python -m cli.client
```

**Client 参数**（环境变量 → 构造参数 → CLI 参数）：

| CLI 参数 | 环境变量 | 说明 |
|----------|----------|------|
| `--server` | `DME_PROXY_SERVER` | Proxy Server 地址（默认 `http://127.0.0.1:26335`） |
| `--endpoint` | `DME_API_ENDPOINT` | DME API 基础地址 |
| `--username` | `DME_API_USERNAME` | DME 用户名 |
| `--password` | `DME_API_PASSWORD` | DME 密码 |
| `--once` | — | 单次轮询模式（适合测试） |

### 发送代理请求

```bash
curl -X POST http://127.0.0.1:26335/api/v1/objects \
  -H "Content-Type: application/json" \
  -d '{"name": "test"}'
```

## 认证机制

Client 启动时自动向 DME 发起登录：

```
PUT {endpoint}/rest/plat/smapp/v1/sessions
Body: {"grantType": "password", "userName": "...", "value": "..."}
→ 取出 accessSession 设置 X-Auth-Token 请求头
```

Session 超时（默认 900s）后自动重新登录。外部请求的原始 headers 透传到 DME 请求中。

## 数据模型

### ProxyRequest

| 字段 | 类型 | 说明 |
|------|------|------|
| `request_id` | `str` | UUID，唯一标识 |
| `method` | `str` | HTTP 方法（GET/POST/PUT/DELETE/PATCH...） |
| `uri` | `str` | 请求路径 |
| `headers` | `dict[str,str]` | 请求头（透传到 DME） |
| `params` | `dict[str,str]` | URL 查询参数 |
| `body` | `str \| None` | 请求体（JSON 字符串） |

### ProxyResponse

| 字段 | 类型 | 说明 |
|------|------|------|
| `request_id` | `str` | 关联的请求 ID |
| `status_code` | `int` | HTTP 状态码 |
| `headers` | `dict[str,str]` | 响应头 |
| `body` | `str \| None` | 响应体 |

## API 端点

### Proxy Server

| 路径 | 方法 | 说明 |
|------|------|------|
| `/*` | 任意 | Catch-all 代理入口 |
| `/api/v1/proxy/health` | GET | 健康检查 |
| `/api/v1/proxy/poll` | GET | Client 轮询请求队列 |
| `/api/v1/proxy/respond` | POST | Client 提交响应 |

### Proxy Client

| 方法 | 说明 |
|------|------|
| `DMEProxyClient.run()` | 持续轮询循环 |
| `DMEProxyClient.poll_once()` | 单次轮询 |

## 队列实现

| 实现 | 适用场景 | 依赖 |
|------|----------|------|
| `MemoryQueue` | 单进程开发/测试 | 无（asyncio.Queue） |
| Redis（规划中） | 多进程生产部署 | redis-py |

## 开发

```bash
# 安装
pip install -e .

# 运行测试
pytest tests/ -v

# 启动 Server
python -m cli.server

# 单次 Client 轮询（无需真实 DME 环境，仅测试连接）
python -m cli.client --once --endpoint http://localhost:9999
```

## 项目结构

```
src/
├── proxy/
│   ├── __init__.py
│   ├── models.py              # ProxyRequest, ProxyResponse
│   ├── queue/
│   │   ├── interface.py       # MessageQueue ABC
│   │   └── memory.py          # MemoryQueue 实现
│   ├── server/
│   │   ├── app.py             # FastAPI 应用 + 路由
│   │   └── handler.py         # 请求入队 + 响应等待
│   └── client/
│       ├── config.py          # 参数解析（env/constructor）
│       └── client.py          # DMEProxyClient 轮询 + 自动登录 + 转发
├── cli/
│   ├── __init__.py
│   ├── server.py              # CLI: dme-proxy-server
│   └── client.py              # CLI: dme-proxy-client
tests/
├── test_models.py
├── test_queue_memory.py
├── test_server.py
├── test_client.py
└── test_integration.py
```
