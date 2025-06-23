# CursorRules-MCP

一个基于Model Context Protocol (MCP)的智能编程规则管理系统。

## 功能特性

- 🔍 **智能规则搜索**: 支持多维度的规则查询和匹配
- 📚 **规则库管理**: 完整的规则版本管理和冲突检测
- 🔧 **代码验证**: 集成多种代码验证工具(flake8, pylint, eslint等)
- 🚀 **MCP协议**: 基于标准MCP协议，可与各种开发工具集成
- 🎯 **提示增强**: 根据上下文自动增强代码生成提示
- 📊 **统计分析**: 提供详细的规则使用统计和分析

## 快速开始

### 安装

```bash
pip install -e .
```

### 启动MCP服务

```bash
python scripts/start_mcp.py
```

### 使用CLI工具

```bash
cursorrules-mcp --help
```

## 📖 详细使用方法

### 1. 服务启动

CursorRules-MCP 支持两种服务模式：

#### 方式一：标准MCP服务（推荐）

```bash
# 启动标准MCP服务
python scripts/start_mcp.py
```

#### 方式二：HTTP服务模式

```bash
# 启动HTTP服务器（默认端口8000）
python scripts/start_http_server.py

# 自定义配置
python scripts/start_http_server.py --host 0.0.0.0 --port 8001 --rules-dir data/rules

# 开发模式（自动重载）
python scripts/start_http_server.py --reload
```

### 2. Cursor编辑器配置

要在Cursor编辑器中使用CursorRules-MCP，需要配置MCP连接：

#### 步骤1：启动服务

首先启动HTTP模式的MCP服务：

```bash
python scripts/start_http_server.py --port 8001
```

#### 步骤2：配置Cursor

编辑Cursor的MCP配置文件（通常在 `~/.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "cursorrules": {
      "url": "http://localhost:8001/mcp/jsonrpc",
      "protocol": "mcp",
      "transport": "http"
    }
  }
}
```

#### 步骤3：重启Cursor

配置完成后重启Cursor编辑器，系统将自动连接到CursorRules-MCP服务。

### 3. 基本使用

#### 在Cursor中使用

配置完成后，您可以在Cursor中直接使用以下功能：

- **智能规则搜索**: 系统会根据当前代码上下文自动推荐合适的编程规则
- **代码验证**: 实时验证代码是否符合最佳实践
- **提示增强**: 根据项目类型和编程语言自动优化AI提示

#### 通过API使用

```bash
# 搜索Python相关规则
curl -X POST http://localhost:8001/mcp/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_rules",
      "arguments": {
        "query": "python best practices",
        "languages": "python",
        "limit": 5
      }
    },
    "id": 1
  }'

# 验证代码内容
curl -X POST http://localhost:8001/mcp/jsonrpc \
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
    "id": 2
  }'
```

### 4. 配置自定义

#### 修改配置文件

编辑 `configs/cursorrules.yaml` 来自定义服务配置：

```yaml
# 服务器配置
server:
  host: "localhost"
  port: 8000
  log_level: "INFO"

# 规则目录
rules_dir: "data/rules"

# 验证工具配置
validation:
  enabled: true
  tools:
    python:
      flake8:
        enabled: true
        args: ["--max-line-length=88"]
```

#### 添加自定义规则

在 `data/rules/` 目录下添加YAML格式的规则文件：

```yaml
# data/rules/my_custom_rules.yaml
name: "我的自定义规则"
version: "1.0.0"
rules:
  - id: "custom-001"
    title: "使用有意义的变量名"
    description: "变量名应该能够清楚表达其用途"
    languages: ["python", "javascript"]
    tags: ["naming", "readability"]
```

### 5. 故障排除

#### 常见问题

1. **服务无法启动**
   ```bash
   # 检查端口是否被占用
   lsof -i :8001
   
   # 使用不同端口
   python scripts/start_http_server.py --port 8002
   ```

2. **Cursor无法连接**
   - 确保服务已正常启动
   - 检查配置文件路径和端口是否正确
   - 重启Cursor编辑器

3. **规则加载失败**
   ```bash
   # 检查规则目录
   ls -la data/rules/
   
   # 验证规则文件格式
   python -c "import yaml; yaml.safe_load(open('data/rules/example.yaml'))"
   ```

#### 查看日志

```bash
# 查看服务日志
tail -f logs/cursorrules.log

# 查看详细调试信息
python scripts/start_http_server.py --log-level DEBUG
```

## 支持的语言

- Python
- C++  
- JavaScript/TypeScript
- Markdown
- YAML
- SQL
- 等更多...

## 项目状态

✅ 生产就绪 - 通过全面测试，可立即投入使用

## 开发团队

CursorRules-MCP开发团队 