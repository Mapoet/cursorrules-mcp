# CursorRules-MCP

一个基于Model Context Protocol (MCP)的智能编程规则管理系统，支持多格式规则导入和增强的统计分析。

## 🚀 功能特性

- 🔍 **智能规则搜索**: 支持多维度的规则查询和匹配
- 📥 **多格式导入**: 支持Markdown、YAML、JSON格式的规则导入
- 📚 **规则库管理**: 完整的规则版本管理和冲突检测
- 🔧 **代码验证**: 集成多种代码验证工具(flake8, pylint, eslint等)
- 🚀 **MCP协议**: 基于标准MCP协议，可与各种开发工具集成
- 🎯 **提示增强**: 根据上下文自动增强代码生成提示
- 📊 **统计分析**: 提供详细的规则使用统计和分析，支持多维度过滤
- 🌐 **双接口支持**: 同时支持MCP和HTTP REST API接口

## 🛠️ 快速开始

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd cursorrules-mcp

# 安装依赖
pip install -e .
```

### 启动服务

#### 方式一：MCP服务（推荐）
```bash
python scripts/start_mcp.py
```

#### 方式二：HTTP服务
```bash
# 单进程模式
python scripts/start_http_server.py --port 8000

# 多进程模式（生产环境推荐）
python scripts/start_http_server.py --port 8000 --workers 4
```

### CLI工具使用

```bash
# 查看帮助
cursorrules-mcp --help

# 搜索规则
cursorrules-mcp search --query "python" --languages python --limit 5

# 导入规则
cursorrules-mcp import rules/ --recursive --validate

# 获取统计信息
cursorrules-mcp stats --languages python --domains scientific
```

## 📥 规则导入功能

### 支持的格式

#### 1. Markdown格式
```markdown
---
rule_id: "STYLE-PY-001"
name: "Python代码风格规则"
description: "Python代码应遵循PEP8标准"
version: "1.0.0"
author: "DevTeam"
rule_type: "style"
languages: ["python"]
domains: ["general"]
tags: ["style", "pep8"]
priority: 8
---

# Python代码风格规则

## 规则详情
...
```

#### 2. YAML格式
```yaml
rule_id: "CONTENT-JS-001"
name: "JavaScript函数命名规则"
description: "JavaScript函数应使用驼峰命名法"
version: "1.0.0"
rule_type: "content"
languages:
  - "javascript"
  - "typescript"
rules:
  - condition: "function_naming"
    guideline: "函数名应使用驼峰命名法"
    priority: 7
```

#### 3. JSON格式
```json
{
  "rule_id": "FORMAT-CSS-001",
  "name": "CSS格式化规则",
  "description": "CSS代码应保持一致的格式化风格",
  "version": "1.0.0",
  "rule_type": "format",
  "languages": ["css", "scss"],
  "rules": [...]
}
```

### 导入方法

#### CLI导入
```bash
# 导入单个文件
cursorrules-mcp import my_rule.md --format markdown

# 批量导入目录
cursorrules-mcp import rules/ --recursive --validate --merge

# 指定输出目录
cursorrules-mcp import rules/ --output-dir data/rules/imported
```

#### HTTP API导入
```bash
# JSON格式导入
curl -X POST http://localhost:8000/api/import \
  -H "Content-Type: application/json" \
  -d '{
    "content": "规则内容...",
    "format": "auto",
    "validate": true
  }'

# 文件上传导入
curl -X POST http://localhost:8000/api/import \
  -F "file=@my_rule.yaml" \
  -F "format=yaml" \
  -F "validate=true"
```

#### MCP工具导入
```json
{
  "name": "import_rules",
  "arguments": {
    "content": "规则内容...",
    "format": "auto",
    "validate": true,
    "merge": false
  }
}
```

## 📊 增强的统计功能

### 支持的过滤维度
- **语言过滤**: 按编程语言筛选
- **领域过滤**: 按应用领域筛选
- **类型过滤**: 按规则类型筛选
- **标签过滤**: 按标签筛选

### 统计内容
- 基础统计（总数、活跃数、版本数）
- 分布统计（按类型、语言、领域分布）
- 使用统计（使用次数、成功率等）
- 服务状态（连接数、运行时间等）

### 使用方法

#### CLI统计查询
```bash
# 全局统计
cursorrules-mcp stats

# 按语言过滤
cursorrules-mcp stats --languages python,javascript

# 组合过滤
cursorrules-mcp stats --languages python --domains scientific --tags performance
```

#### HTTP API统计
```bash
# GET请求
curl "http://localhost:8000/api/statistics?languages=python&domains=web"

# POST请求（复杂过滤）
curl -X POST http://localhost:8000/api/statistics \
  -H "Content-Type: application/json" \
  -d '{
    "languages": "python,javascript",
    "domains": "web,api",
    "rule_types": "style,content"
  }'
```

#### MCP统计工具
```json
{
  "name": "get_statistics",
  "arguments": {
    "languages": "python,cpp",
    "domains": "scientific,iot",
    "tags": "performance,optimization"
  }
}
```

## 📖 详细使用方法

### 1. Cursor编辑器配置

#### 步骤1：启动HTTP服务
```bash
# 开发环境
python scripts/start_http_server.py --port 8001

# 生产环境（推荐使用多进程）
python scripts/start_http_server.py --port 8001 --workers 4
```

#### 步骤2：配置Cursor
编辑Cursor的MCP配置文件：
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
配置完成后重启Cursor编辑器即可使用。

### 2. 在Cursor中使用

- **智能规则搜索**: 系统会根据当前代码上下文自动推荐合适的编程规则
- **代码验证**: 实时验证代码是否符合最佳实践
- **提示增强**: 根据项目类型和编程语言自动优化AI提示
- **规则导入**: 直接在编辑器中导入新的编程规则

### 3. 可用的API端点

#### MCP JSON-RPC端点
- `POST /mcp/jsonrpc` - 标准MCP协议接口

#### REST API端点
- `GET /health` - 健康检查
- `GET /mcp/info` - 服务信息
- `POST /api/import` - 规则导入
- `GET|POST /api/statistics` - 统计查询
- `GET /api/rules` - 规则列表
- `POST /api/validate` - 内容验证

### 4. 可用的MCP工具

- `search_rules` - 搜索规则
- `validate_content` - 验证内容
- `enhance_prompt` - 增强提示
- `get_statistics` - 获取统计信息
- `import_rules` - 导入规则（新增）

## 🔧 配置和自定义

### 修改配置文件
编辑 `configs/cursorrules.yaml`:
```yaml
server:
  host: "localhost"
  port: 8000
  log_level: "INFO"

rules_dir: "data/rules"

validation:
  enabled: true
  tools:
    python:
      flake8:
        enabled: true
        args: ["--max-line-length=88"]
```

### 环境变量
```bash
export CURSORRULES_RULES_DIR="data/rules"
export CURSORRULES_LOG_LEVEL="DEBUG"
export CURSORRULES_SERVER_PORT="8001"
export CURSORRULES_WORKERS="4"  # 工作进程数量
```

### 性能优化

#### 工作进程配置
```bash
# CPU密集型任务推荐配置
# workers数量 = CPU核心数 * 2
python scripts/start_http_server.py --workers $(nproc --all)

# 内存有限环境
python scripts/start_http_server.py --workers 2

# 开发调试环境
python scripts/start_http_server.py --workers 1 --reload
```

#### 生产环境建议
- **单核服务器**: `--workers 1`
- **双核服务器**: `--workers 2-4`
- **四核服务器**: `--workers 4-8`
- **八核服务器**: `--workers 8-16`

⚠️ **注意**: 
- `--reload`模式不支持多进程，仅用于开发环境
- 过多的workers可能导致内存不足
- 建议根据实际负载和服务器配置调整

## 🛠️ 支持的语言和工具

### 编程语言支持
- **Python** (flake8, pylint, black)
- **JavaScript/TypeScript** (eslint, prettier)
- **C++** (clang-tidy, cppcheck)
- **Go** (go fmt, go vet)
- **Rust** (rustfmt, clippy)
- **Java** (checkstyle, spotbugs)
- **更多语言持续添加...**

### 应用领域
- Web开发
- 科学计算
- 物联网(IoT)
- 机器学习
- 数据分析
- 系统编程
- 移动开发

## 🧪 测试和验证

### 运行测试
```bash
# 完整功能测试
python scripts/test_complete_features.py
```

### 验证安装
```bash
# 检查CLI工具
cursorrules-mcp --version

# 检查导入功能
cursorrules-mcp import data/rules/examples/ --validate

# 检查统计功能
cursorrules-mcp stats
```

## 📚 文档

- [导入功能指南](docs/IMPORT_GUIDE.md)
- [导入和统计功能详细指南](docs/IMPORT_AND_STATISTICS_GUIDE.md)
- [HTTP服务器指南](docs/HTTP_SERVER_GUIDE.md)
- [开发计划](docs/development_plan.md)

## 🔍 故障排除

### 常见问题

#### 1. 服务无法启动
```bash
# 检查端口占用
lsof -i :8001

# 使用不同端口
python scripts/start_http_server.py --port 8002
```

#### 2. 导入失败
```bash
# 检查文件格式
cursorrules-mcp import my_rule.yaml --validate --format yaml

# 查看详细错误
cursorrules-mcp import my_rule.yaml --log debug
```

#### 3. 统计查询为空
```bash
# 检查过滤条件
cursorrules-mcp stats --languages python

# 查看所有规则
cursorrules-mcp search --limit 100
```

### 查看日志
```bash
# 查看服务日志
tail -f logs/cursorrules.log

# 查看详细调试信息
python scripts/start_http_server.py --log-level DEBUG
```

## 🚀 版本历史

### v1.2.0 (2025-01-23)
- ✅ 新增多格式规则导入功能（Markdown、YAML、JSON）
- ✅ 增强统计查询功能，支持多维度过滤
- ✅ 扩展MCP和HTTP API接口
- ✅ 完善CLI工具功能
- ✅ 新增详细的使用文档和示例

### v1.1.0
- ✅ HTTP服务器支持
- ✅ 规则验证功能
- ✅ 统计分析功能

### v1.0.0
- ✅ 基础MCP协议支持
- ✅ 规则搜索和管理
- ✅ CLI工具

## 🤝 贡献

欢迎贡献代码、报告问题或提出改进建议！

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 👥 开发团队

**作者**: Mapoet  
**邮箱**: Mapoet.Niphy@gmail.com  
**机构**: NUS/STAR  
**日期**: 2025-01-23

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！