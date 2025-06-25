# CursorRules-MCP

一个基于 Model Context Protocol (MCP) 的智能编程规则与提示模板管理系统，支持多格式规则/模板导入、内容合规性校验、统计分析与多接口集成。

## 🚀 功能特性
- 🔍 智能规则与模板搜索与管理
- 📥 多格式导入（Markdown、YAML、JSON）
- 📚 规则与模板库版本管理、冲突检测
- 🔧 代码与文档内容合规性校验（支持多语言、多领域）
- 🚀 MCP/HTTP/CLI 多端接口
- 🎯 上下文自适应提示增强
- 📊 规则与模板使用统计分析

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
python scripts/start_http_server.py --port 8000
```

### CLI 工具
```bash
# 查看帮助
cursorrules-mcp --help
```

## 📥 规则与模板导入

### 支持格式
- Markdown（推荐，支持元数据与正文分离）
- YAML
- JSON

### CLI 导入示例
```bash
# 导入规则文件
cursorrules-mcp import my_rule.md --format markdown
# 批量导入目录
cursorrules-mcp import rules/ --recursive --validate
# 导入模板文件
cursorrules-mcp import my_template.yaml --type templates
```

### HTTP/MCP 导入示例
```json
{
  "method": "import_resource",
  "params": {
    "content": "规则或模板内容...",
    "format": "markdown",
    "type": "rules"  // 或 "templates"
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
cursorrules-mcp stats --resource_type templates --languages python
cursorrules-mcp stats --resource_type all
```

### HTTP/MCP 统计示例
```json
{
  "method": "get_statistics",
  "params": {
    "resource_type": "all",
    "languages": "python,cpp"
  },
  "id": 1
}
```

### 参数说明
- resource_type (str): 统计对象类型，支持 rules（规则）、templates（模板）、all（全部），默认 rules。
- languages, domains, rule_types, tags: 过滤参数，模板统计时部分字段可忽略。

### 返回结构示例
```json
{
  "resource_type": "all",
  "rules_stats": {
    "total": 123,
    "by_language": {"python": 100, "cpp": 23},
    "by_domain": {"scientific": 80, "web": 43},
    "by_type": {"style": 60, "content": 63},
    "by_tag": {"pep8": 40, "performance": 20}
  },
  "templates_stats": {
    "total": 45,
    "by_language": {"python": 30, "markdown": 15},
    "by_group": {"default": 20, "advanced": 25},
    "by_priority": {"high": 10, "normal": 35}
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
- [导入功能指南](docs/IMPORT_GUIDE.md)
- [导入和统计功能详细指南](docs/IMPORT_AND_STATISTICS_GUIDE.md)
- [HTTP服务器指南](docs/HTTP_SERVER_GUIDE.md)
- [开发计划](docs/development_plan.md)

## 🔍 故障排除

### 常见问题
- 服务无法启动：检查端口占用，切换端口
- 导入失败：检查文件格式与内容完整性
- 统计查询为空：检查过滤条件
- 查看日志：`tail -f logs/cursorrules.log`

## 🚀 版本历史

### v1.3.0 (2025-06-09)
- ✅ validate_content 支持 output_mode 枚举参数，输出内容灵活可控
- ✅ 规则/模板导入统一，支持 type 区分
- ✅ CLI/HTTP/MCP 接口参数与文档全面升级

### v1.2.0
- 多格式规则导入、统计增强
### v1.1.0
- HTTP服务器、规则验证、统计分析
### v1.0.0
- MCP协议、规则搜索、CLI工具

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

## 📁 目录结构与配置

- `data/rules/` 及其子目录：专门存放规则文件（YAML/JSON/MD等）
- `data/templates/`：专门存放 prompt 模板文件（YAML/MD等）
