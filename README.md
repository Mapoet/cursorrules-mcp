# CursorRules-MCP

🎯 **智能编程规则与提示模板管理系统** - 基于 Model Context Protocol (MCP) 的下一代代码质量控制平台

一个专业的规则管理与内容验证系统，支持多格式规则/模板导入、智能合规性校验、统计分析与多接口集成，为现代软件开发提供标准化的代码质量保证。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68.0+-00a393.svg)](https://fastapi.tiangolo.com)
[![MCP Protocol](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://modelcontextprotocol.io)

## 🚀 核心功能

### 📋 规则与模板管理
- 🔍 **智能搜索引擎** - 支持多维度过滤（语言、领域、标签、类型）
- 📥 **多格式导入** - Markdown、YAML、JSON格式无缝支持
- 📚 **版本控制** - 规则版本管理、冲突检测与自动合并
- 🏷️ **分类体系** - 按语言、领域、任务类型智能分类

### 🔧 内容验证与校验
- ✅ **多语言支持** - Python、C++、JavaScript、TypeScript等
- 🌍 **领域自适应** - 科学计算、Web开发、移动开发等专业领域
- 🎯 **智能校验** - 代码风格、安全性、性能、可维护性全方位检查
- 📊 **详细报告** - 问题定位、严重程度评估、改进建议

### 🚀 多端接口支持
- 🔌 **MCP协议** - 标准Model Context Protocol集成
- 🌐 **HTTP/REST API** - RESTful风格Web接口
- 💻 **CLI工具** - 命令行批量操作与脚本集成
- 📡 **JSON-RPC** - 轻量级远程过程调用

### 🎯 智能增强功能
- 🤖 **提示增强** - 基于上下文的LLM提示词优化
- 📈 **统计分析** - 使用模式分析与性能监控
- 🧠 **自适应学习** - 根据使用反馈持续优化规则库

### 1. 规则搜索

```bash
# CLI示例
cursorrules-mcp search --query "类型检查" --languages python --domains scientific
cursorrules-mcp search --tags "performance,security" --limit 5
```

```json
// MCP示例
{
  "method": "search_rules",
  "params": {
    "query": "类型检查",
    "languages": "python,cpp",
    "domains": "scientific,web",
    "tags": "performance,security",
    "content_types": "code,documentation",
    "rule_types": "style,content",
    "limit": 5
  },
  "id": 1
}
```

### 2. 内容验证

```bash
# CLI示例
cursorrules-mcp validate "代码内容" --languages python --output_mode detailed
cursorrules-mcp validate --file mycode.py --domains scientific
```

```json
// MCP示例
{
  "method": "validate_content",
  "params": {
    "content": "代码内容",
    "file_path": "mycode.py",
    "languages": "python",
    "domains": "scientific",
    "content_types": "code",
    "output_mode": "full"
  },
  "id": 1
}
```

### 3. 提示增强

```bash
# CLI示例
cursorrules-mcp enhance "基础提示" --languages python --max_rules 3
cursorrules-mcp enhance --file prompt.txt --domains web,ai
```

```json
// MCP示例
{
  "method": "enhance_prompt",
  "params": {
    "base_prompt": "基础提示",
    "languages": "python,typescript",
    "domains": "web,ai",
    "tags": "best_practice,security",
    "max_rules": 5
  },
  "id": 1
}
```

### 4. 统计信息

```bash
# CLI示例
cursorrules-mcp stats --resource_type all
cursorrules-mcp stats --resource_type rules --languages python,cpp
```

```json
// MCP示例
{
  "method": "get_statistics",
  "params": {
    "resource_type": "all",
    "languages": "python,cpp",
    "domains": "scientific,web",
    "rule_types": "style,content",
    "tags": "performance,security"
  },
  "id": 1
}
```

### 5. 资源导入

```bash
# CLI示例
# 导入规则
cursorrules-mcp import rules/ --type rules --recursive --validate
cursorrules-mcp import my_rule.md --type rules --merge

# 导入模板
cursorrules-mcp import templates/ --type templates --mode append
cursorrules-mcp import new_templates/ --type templates --mode replace
```

```json
// MCP示例
{
  "method": "import_resource",
  "params": {
    "content": "规则或模板内容",
    "type": "rules",  // 或 "templates"
    "format": "markdown",
    "validate": true,
    "merge": false,
    "mode": "append"  // 仅对模板有效
  },
  "id": 1
}
```

## 🛠️ 快速开始

### 系统要求
- Python 3.9+
- FastAPI 0.68.0+
- SQLAlchemy 1.4+
- Pydantic 1.8+

### 安装部署

```bash
# 1. 克隆项目
git clone https://github.com/your-org/cursorrules-mcp.git
cd cursorrules-mcp

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -e .

# 4. 初始化配置
cp configs/cursorrules.yaml.example configs/cursorrules.yaml
# 编辑配置文件以适应您的环境

# 5. 初始化数据库
python scripts/migrate_database.py
```

### 服务启动

#### 🔌 MCP服务（推荐 - 适合与LLM工具链集成）
```bash
# 启动MCP服务器
python scripts/start_mcp.py

# 或配置环境变量启动
export CURSORRULES_RULES_DIR="data/rules"
export CURSORRULES_LOG_LEVEL="INFO"
python scripts/start_mcp.py
```

#### 🌐 HTTP服务（适合Web API集成）
```bash
# 启动HTTP服务器
python scripts/start_http_server.py --port 8000 --workers 4

# 后台运行
nohup python scripts/start_http_server.py --port 8000 > server.log 2>&1 &
```

#### 💻 CLI工具（适合批量操作与脚本集成）
```bash
# 查看帮助
python scripts/cursorrules_cli.py --help

# 或安装后使用
cursorrules-mcp --help
```

## 🎯 规则与模板导入

### 支持格式

#### 规则格式
- Markdown（支持元数据与正文分离）
- YAML
- JSON

#### 模板格式
- Markdown（推荐，支持模板内容与元数据分离）
- YAML（支持完整的模板元数据）

### CLI 导入示例
```bash
# 导入规则文件
cursorrules-mcp import my_rule.md --type rules
# 批量导入规则目录
cursorrules-mcp import rules/ --type rules --recursive --validate
# 导入模板文件
cursorrules-mcp import templates/ --type templates --mode append
# 替换现有模板
cursorrules-mcp import new_templates/ --type templates --mode replace
```

### HTTP/MCP 导入示例
```json
{
  "method": "import_resource",
  "params": {
    "content": "规则或模板内容...",
    "format": "markdown",
    "type": "rules",  // 或 "templates"
    "mode": "append"  // 仅对模板有效，可选值: "append", "replace"
  },
  "id": 1
}
```

## 🧑‍💻 内容合规性校验 validate_content

### 参数说明
- content (str): 待校验内容，必填。
- file_path (str, 可选): 文件路径，仅用于推断语言类型。
- languages (str, 可选): 语言，如 python, markdown。
- content_types (str, 可选): 内容类型，如 code, documentation。
- domains (str, 可选): 领域。
- output_mode (str, 可选): 输出模式，支持以下枚举值：
  - result_only：仅返回校验结果（success, passed, problems）
  - result_with_prompt：返回校验结果和 prompt
  - result_with_rules：返回校验结果和规则详情
  - result_with_template：返回校验结果和模板信息
  - full：返回全部信息（校验结果、prompt、规则、模板信息）
  默认值为 result_only。

### CLI 用法示例
```bash
python -m src.cursorrules_mcp.cli validate_content 'def foo(): pass' --languages python --output_mode result_with_prompt
```

### HTTP/MCP JSON-RPC 示例
```json
{
  "method": "validate_content",
  "params": {
    "content": "def foo(): pass",
    "languages": "python",
    "output_mode": "full"
  },
  "id": 1
}
```

### 返回结构示例
- result_only:
```json
{
  "success": true,
  "passed": true,
  "problems": []
}
```
- full:
```json
{
  "success": true,
  "passed": true,
  "problems": [],
  "prompt": "...",
  "rules": [...],
  "template_info": {...}
}
```

## 📊 统计与查询

### CLI 统计查询
```bash
# 查询所有规则统计
cursorrules-mcp stats --resource_type rules
# 查询所有模板统计
cursorrules-mcp stats --resource_type templates
# 查询所有资源统计
cursorrules-mcp stats --resource_type all
# 按语言过滤规则统计
cursorrules-mcp stats --resource_type rules --languages python,cpp
```

### HTTP/MCP 统计示例
```json
{
  "method": "get_statistics",
  "params": {
    "resource_type": "all",  // "rules", "templates", "all"
    "languages": "python,cpp",
    "domains": "scientific,web",
    "rule_types": "style,content",  // 仅对规则有效
    "tags": "pep8,performance"
  },
  "id": 1
}
```

### 参数说明
- resource_type (str): 统计对象类型，支持：
  - rules（规则）
  - templates（模板）
  - all（全部）
  默认值为 rules
- languages: 按语言过滤，逗号分隔
- domains: 按领域过滤，逗号分隔
- rule_types: 按规则类型过滤（仅对规则有效），逗号分隔
- tags: 按标签过滤，逗号分隔

### 返回结构示例
```json
{
  "resource_type": "all",
  "rules_stats": {
    "total": 123,
    "by_language": {"python": 100, "cpp": 23},
    "by_domain": {"scientific": 80, "web": 43},
    "by_type": {"style": 60, "content": 63},
    "by_tag": {"pep8": 40, "performance": 20},
    "active_rules": 120,
    "average_success_rate": 0.95
  },
  "templates_stats": {
    "total": 45,
    "by_language": {"python": 30, "markdown": 15},
    "by_domain": {"scientific": 25, "web": 20},
    "by_priority": {"high": 10, "normal": 35},
    "active_templates": 42,
    "usage_count": 1250
  }
}
```

## 📖 详细用法与API端点

### MCP JSON-RPC端点
- `POST /mcp/jsonrpc` - 标准MCP协议接口

### REST API端点
- `GET /health` - 健康检查
- `POST /api/import` - 规则/模板导入
- `POST /api/validate` - 内容合规性校验
- `GET|POST /api/statistics` - 统计查询
- `GET /api/rules` - 规则列表

## 🧩 典型场景与示例

### 1. 规则/模板导入
- 支持 Markdown/YAML/JSON，自动识别类型
- CLI/HTTP/MCP 均可导入，type 参数区分 rules/templates

### 2. 内容合规性校验
- 支持多语言、多领域、多内容类型
- output_mode 灵活控制输出内容，适配 LLM/Agent/人类专家多场景

### 3. 统计分析
- 支持多维度过滤与分布统计

## 🛠️ 配置与环境变量

### 配置文件
编辑 `configs/cursorrules.yaml`:
```yaml
server:
  host: "localhost"
  port: 8000
  log_level: "INFO"
rules_dir: "data/rules"
templates_dir: "data/templates"  # prompt模板目录
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
export CURSORRULES_TEMPLATES_DIR="data/templates"
export CURSORRULES_LOG_LEVEL="DEBUG"
export CURSORRULES_SERVER_PORT="8001"
export CURSORRULES_WORKERS="4"
```

## 🧪 测试与验证

### 运行测试
```bash
python scripts/test_complete_features.py
```

### 验证安装
```bash
cursorrules-mcp --version
cursorrules-mcp import data/rules/examples/ --validate
cursorrules-mcp stats
```

## 📚 文档与支持

### 核心文档
- 📖 **[技术架构报告](docs/techs.md)** - 完整的技术架构、设计模式与实现细节

### 技术支持
- 🐛 **问题报告**: [GitHub Issues](https://github.com/your-org/cursorrules-mcp/issues)
- 💬 **社区讨论**: [GitHub Discussions](https://github.com/your-org/cursorrules-mcp/discussions)
- 📧 **联系方式**: Mapoet.Niphy@gmail.com

## 🔍 故障排除

### 常见问题
- 服务无法启动：检查端口占用，切换端口
- 导入失败：检查文件格式与内容完整性
- 统计查询为空：检查过滤条件
- 查看日志：`tail -f logs/cursorrules.log`

## 🚀 版本历史

### v1.4.0 (2025-01-23) - 当前版本
- 🔧 **架构重构** - 完整的MCP与HTTP双服务器架构
- 🛠️ **导入功能完善** - 修复所有导入相关错误，支持异步操作
- 🎯 **输出模式优化** - validate_content支持5种输出模式精确控制
- 📊 **统计功能增强** - 规则与模板分离统计，多维度分析
- 🔐 **错误处理完善** - 全链路异常处理与日志记录
- 🚀 **性能优化** - 异步数据库操作，并发处理能力提升

### v1.3.0 (2025-01-09)
- ✅ validate_content 支持 output_mode 枚举参数，输出内容灵活可控
- ✅ 规则/模板导入统一，支持 type 区分
- ✅ CLI/HTTP/MCP 接口参数与文档全面升级

### v1.2.0 (2024-12-15)
- 多格式规则导入、统计增强、版本管理系统

### v1.1.0 (2024-11-20)
- HTTP服务器、规则验证、统计分析

### v1.0.0 (2024-10-15)
- MCP协议基础实现、规则搜索、CLI工具

## 🤝 贡献
欢迎贡献代码、报告问题或提出建议！
1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'feat: ...'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 开启Pull Request

## 📄 许可证
MIT License - 详见 [LICENSE](LICENSE)

## 👥 开发团队
**作者**: Mapoet  
**邮箱**: Mapoet.Niphy@gmail.com  
**机构**: NUS/STAR  
**日期**: 2025-06-09

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！

## 📁 项目结构

```
cursorrules-mcp/
├── src/cursorrules_mcp/          # 核心业务逻辑
│   ├── engine.py                 # 规则引擎核心
│   ├── server.py                 # MCP协议服务器  
│   ├── http_server.py            # HTTP/REST API服务器
│   ├── models.py                 # 数据模型定义
│   ├── database.py               # 数据访问层
│   ├── validators.py             # 验证器系统
│   ├── rule_import.py            # 规则导入模块
│   └── cli.py                    # 命令行接口
├── scripts/                      # 启动脚本
│   ├── start_mcp.py              # MCP服务启动
│   ├── start_http_server.py      # HTTP服务启动
│   └── cursorrules_cli.py        # CLI工具入口
├── data/                         # 数据存储
│   ├── rules/                    # 规则文件存储
│   └── templates/                # 提示模板存储
├── configs/                      # 配置文件
│   └── cursorrules.yaml          # 主配置文件
├── docs/                         # 文档
│   ├── techs.md                  # 技术架构报告
│   └── *.md                      # 其他文档
└── tests/                        # 测试用例
```

### 🔧 配置说明

- **data/rules/**: 存放规则文件（YAML/JSON/MD格式）
- **data/templates/**: 存放 prompt 模板文件
- **configs/cursorrules.yaml**: 系统主配置文件
- **logs/**: 运行日志存储目录（自动创建）
