# CursorRules-MCP HTTP服务器使用指南

## 📋 概述

CursorRules-MCP HTTP服务器提供基于HTTP/SSE（Server-Sent Events）的MCP（Model Context Protocol）服务，支持通过标准HTTP协议访问所有MCP功能。

## 🚀 快速开始

### 1. 安装依赖

确保已安装所有必要的依赖：

```bash
pip install fastapi uvicorn httpx
```

或者安装完整的项目依赖：

```bash
pip install -e .
```

### 2. 启动HTTP服务器

#### 使用命令行脚本

```bash
# 默认配置启动
python scripts/start_http_server.py

# 自定义配置
python scripts/start_http_server.py --host 0.0.0.0 --port 8080 --rules-dir /path/to/rules

# 开发模式（自动重载）
python scripts/start_http_server.py --reload
```

#### 使用已安装的包

```bash
# 如果已安装包
cursorrules-mcp-http --port 8080
```

#### 使用Python代码

```python
from src.cursorrules_mcp.http_server import MCPHttpServer

# 创建服务器
server = MCPHttpServer(
    rules_dir="data/rules",
    host="localhost", 
    port=8000
)

# 启动服务器
server.run()
```

### 3. 验证服务器状态

```bash
# 健康检查
curl http://localhost:8000/health

# MCP服务信息
curl http://localhost:8000/mcp/info
```

## 📡 API 端点

### 基础端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/mcp/info` | GET | MCP服务信息和统计 |
| `/docs` | GET | API文档 (Swagger UI) |
| `/redoc` | GET | API文档 (ReDoc) |

### MCP 协议端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/mcp/connect` | POST | 建立MCP连接 |
| `/mcp/jsonrpc` | POST | JSON-RPC请求处理 |
| `/mcp/sse` | GET | Server-Sent Events流 |

## 🔧 使用 JSON-RPC

### 连接流程

1. **建立连接**
```bash
curl -X POST http://localhost:8000/mcp/connect
```

2. **初始化MCP会话**
```bash
curl -X POST http://localhost:8000/mcp/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {"tools": {}, "resources": {}},
      "clientInfo": {"name": "my-client", "version": "1.0.0"}
    },
    "id": 1
  }'
```

### 工具操作

#### 列出可用工具
```bash
curl -X POST http://localhost:8000/mcp/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 2
  }'
```

#### 搜索规则
```bash
curl -X POST http://localhost:8000/mcp/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_rules",
      "arguments": {
        "query": "python",
        "languages": "python",
        "limit": 5
      }
    },
    "id": 3
  }'
```

#### 验证内容
```bash
curl -X POST http://localhost:8000/mcp/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "validate_content",
      "arguments": {
        "content": "def hello():\n    print(\"Hello World\")",
        "languages": "python"
      }
    },
    "id": 4
  }'
```

#### 获取统计信息
```bash
curl -X POST http://localhost:8000/mcp/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_statistics",
      "arguments": {}
    },
    "id": 5
  }'
```

### 资源操作

#### 列出资源
```bash
curl -X POST http://localhost:8000/mcp/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "resources/list",
    "id": 6
  }'
```

#### 读取资源
```bash
curl -X POST http://localhost:8000/mcp/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "resources/read",
    "params": {
      "uri": "cursorrules://rules/list"
    },
    "id": 7
  }'
```

## 📡 Server-Sent Events (SSE)

### 连接SSE流

```bash
# 基本连接
curl -N http://localhost:8000/mcp/sse

# 带连接ID的连接
curl -N "http://localhost:8000/mcp/sse?connection_id=your-connection-id"
```

### JavaScript示例

```javascript
// 建立SSE连接
const eventSource = new EventSource('http://localhost:8000/mcp/sse');

// 监听连接事件
eventSource.addEventListener('connection', (event) => {
    const data = JSON.parse(event.data);
    console.log('连接建立:', data);
});

// 监听心跳事件
eventSource.addEventListener('heartbeat', (event) => {
    const data = JSON.parse(event.data);
    console.log('心跳:', data.timestamp);
});

// 监听错误事件
eventSource.addEventListener('error', (event) => {
    const data = JSON.parse(event.data);
    console.error('错误:', data.message);
});

// 关闭连接
// eventSource.close();
```

## 🧪 测试

### 使用内置测试脚本

```bash
# 完整测试
python test_http_client.py

# 快速测试
python test_http_client.py --quick

# 自定义服务器地址
python test_http_client.py --base-url http://your-server:8080
```

### 使用Python客户端

```python
import asyncio
from test_http_client import MCPHttpClient

async def test_client():
    async with MCPHttpClient("http://localhost:8000") as client:
        # 健康检查
        health = await client.health_check()
        print(f"服务状态: {health['status']}")
        
        # 建立连接
        await client.connect()
        await client.initialize()
        
        # 搜索规则
        result = await client.call_tool("search_rules", {
            "query": "python",
            "limit": 3
        })
        print("搜索结果:", result)

# 运行测试
asyncio.run(test_client())
```

## 🔧 配置选项

### 命令行参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| `--rules-dir` | `data/rules` | 规则目录路径 |
| `--host` | `localhost` | 服务器主机地址 |
| `--port` | `8000` | 服务器端口 |
| `--log-level` | `INFO` | 日志级别 |
| `--reload` | `False` | 开发模式自动重载 |

### 环境变量

```bash
export CURSORRULES_RULES_DIR=/path/to/rules
export CURSORRULES_HTTP_HOST=0.0.0.0
export CURSORRULES_HTTP_PORT=8080
export CURSORRULES_LOG_LEVEL=DEBUG
```

## 🛠️ 开发指南

### 添加新的工具

1. 在`http_server.py`的`_list_tools()`方法中添加工具定义
2. 在`_call_tool()`方法中添加工具调用逻辑
3. 实现具体的工具方法

```python
async def _my_new_tool(self, param1: str, param2: int) -> str:
    """新工具的实现"""
    try:
        # 工具逻辑
        result = f"处理结果: {param1} + {param2}"
        return result
    except Exception as e:
        logger.error(f"新工具执行失败: {e}")
        return f"❌ 执行失败: {str(e)}"
```

### 添加新的资源

1. 在`_list_resources()`方法中添加资源定义
2. 在`_read_resource()`方法中添加资源读取逻辑

### 自定义中间件

```python
from fastapi import Request, Response

@self.app.middleware("http")
async def custom_middleware(request: Request, call_next):
    # 请求预处理
    start_time = time.time()
    
    # 调用下一个中间件/端点
    response = await call_next(request)
    
    # 响应后处理
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    return response
```

## 🐛 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 查找占用端口的进程
   lsof -i :8000
   
   # 或者使用不同端口
   python scripts/start_http_server.py --port 8080
   ```

2. **规则目录不存在**
   ```bash
   # 创建规则目录
   mkdir -p data/rules
   
   # 或者指定现有目录
   python scripts/start_http_server.py --rules-dir /path/to/existing/rules
   ```

3. **CORS问题**
   - 服务器默认允许所有来源，生产环境中应该限制
   - 如需自定义CORS，修改`_setup_middleware()`方法

4. **SSE连接断开**
   - 检查防火墙设置
   - 确保客户端支持Server-Sent Events
   - 网络代理可能会中断长连接

### 日志分析

```bash
# 启用调试日志
python scripts/start_http_server.py --log-level DEBUG

# 查看详细错误信息
tail -f logs/cursorrules-mcp.log
```

## 🔐 安全考虑

### 生产环境配置

1. **限制CORS来源**
   ```python
   self.app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-domain.com"],  # 限制来源
       allow_credentials=True,
       allow_methods=["GET", "POST"],
       allow_headers=["Content-Type", "Authorization"],
   )
   ```

2. **添加认证**
   ```python
   from fastapi import Depends, HTTPException, status
   from fastapi.security import HTTPBearer
   
   security = HTTPBearer()
   
   async def verify_token(token: str = Depends(security)):
       # 验证token逻辑
       if not is_valid_token(token.credentials):
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Invalid token"
           )
   ```

3. **使用HTTPS**
   ```bash
   # 使用反向代理（推荐）
   # 或者配置SSL证书
   uvicorn main:app --host 0.0.0.0 --port 443 --ssl-keyfile key.pem --ssl-certfile cert.pem
   ```

## 📈 性能优化

### 生产部署

```bash
# 使用Gunicorn
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.cursorrules_mcp.http_server:app

# 使用Docker
docker build -t cursorrules-mcp-http .
docker run -p 8000:8000 cursorrules-mcp-http
```

### 监控

```python
# 添加监控指标
from prometheus_client import Counter, Histogram
import time

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests')
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.inc()
    REQUEST_DURATION.observe(duration)
    
    return response
```

---

## 📚 相关文档

- [MCP协议规范](https://spec.modelcontextprotocol.io/)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [JSON-RPC 2.0规范](https://www.jsonrpc.org/specification)

## 🤝 贡献

欢迎贡献代码、报告问题或提出改进建议！请查看项目的贡献指南。

---

**CursorRules-MCP HTTP服务器** - 让MCP协议通过HTTP变得简单易用！ 🚀 