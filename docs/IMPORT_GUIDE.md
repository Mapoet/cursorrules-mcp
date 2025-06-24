# 多格式规则导入指南

CursorRules-MCP 现在支持从多种格式导入规则文件，包括 Markdown、YAML 和 JSON 格式。

## 支持的格式

### 1. Markdown 格式 (推荐)

Markdown 格式使用 frontmatter 来定义规则元数据，正文部分用于详细描述。

```markdown
---
rule_id: "CR-MD-FORMAT-001"
name: "Markdown标题格式规范"
description: "确保Markdown文档使用正确的标题层级和格式"
version: "1.0.0"
author: "Mapoet"
rule_type: "format"
languages: ["markdown"]
domains: ["documentation"]
tags: ["markdown", "formatting", "headers"]
condition: "markdown_heading_format"
priority: 8
---

# 规则内容

## 指导原则

规则的详细说明...

## 示例

### 正确示例
\```markdown
# 标题
\```

### 错误示例
\```markdown
## 跳过了一级标题
\```
```

### 2. YAML 格式

完整的 YAML 结构定义：

```yaml
rule_id: "CR-PY-NAMING-001"
name: "Python函数命名规范"
description: "Python函数应使用snake_case命名"
version: "1.0.0"
author: "Mapoet"
rule_type: "style"
languages: ["python"]
domains: ["software_development"]
tags: ["python", "naming", "functions"]

rules:
  - condition: "python_function_naming"
    guideline: "函数名应使用snake_case风格"
    priority: 8
    examples:
      - good: "def calculate_total():"
        bad: "def calcTotal():"
        explanation: "snake_case更符合Python规范"

applies_to:
  file_patterns: ["*.py"]

validation:
  tools: ["pylint", "flake8"]
  severity: "warning"
```

### 3. JSON 格式

标准的 JSON 结构：

```json
{
  "rule_id": "CR-CPP-MEMORY-001",
  "name": "C++智能指针使用规范",
  "description": "优先使用智能指针管理动态内存",
  "version": "1.0.0",
  "author": "Mapoet",
  "rule_type": "security",
  "languages": ["cpp"],
  "domains": ["system_programming"],
  "tags": ["cpp", "memory_management"],
  "guideline": "使用std::unique_ptr而不是原始指针",
  "priority": 9,
  "examples": [
    {
      "good": "auto data = std::make_unique<Data>();",
      "bad": "Data* data = new Data();",
      "explanation": "智能指针自动管理内存"
    }
  ]
}
```

## 使用方法

### 命令行导入

```bash
# 导入单个文件
cursorrules-mcp import rules/sample.md

# 导入多个文件
cursorrules-mcp import rules/*.md rules/*.yaml

# 递归导入目录
cursorrules-mcp import rules/ --recursive

# 指定格式
cursorrules-mcp import rules/ --format markdown --recursive

# 导入并保存到指定目录
cursorrules-mcp import rules/ --output-dir output/ --recursive

# 导入并合并到数据库
cursorrules-mcp import rules/ --merge --recursive

# 导入后验证规则
cursorrules-mcp import rules/ --validate --recursive

# 保存导入日志
cursorrules-mcp import rules/ --log import.log --recursive
```

### 命令参数说明

- `paths`: 要导入的文件或目录路径（必需）
- `--format`: 指定文件格式 (`auto`, `markdown`, `yaml`, `json`)，默认为 `auto`
- `--recursive, -r`: 递归扫描目录
- `--output-dir`: 输出目录，保存解析后的规则
- `--validate`: 导入后验证规则的完整性
- `--merge`: 将规则合并到现有数据库中
- `--log`: 保存详细导入日志的文件路径

### Python API 使用

```python
from pathlib import Path
from cursorrules_mcp.import import UnifiedRuleImporter

# 创建导入器
importer = UnifiedRuleImporter()

# 导入规则
rules = importer.import_rules(
    paths=[Path("rules/sample.md"), Path("rules/")],
    recursive=True,
    format_hint="auto"
)

# 获取导入摘要
summary = importer.get_import_summary()
print(f"成功导入 {len(rules)} 条规则")
print(f"成功率: {summary['success_rate']:.1%}")

# 保存导入日志
importer.save_import_log(Path("import_log.json"))
```

## 规则字段说明

### 必需字段

- `rule_id`: 唯一标识符，格式为 "CR-类别-编号"
- `name`: 规则名称
- `description`: 规则描述

### 可选字段

- `version`: 版本号，默认 "1.0.0"
- `author`: 作者，默认 "Unknown"
- `rule_type`: 规则类型 (`style`, `content`, `format`, `performance`, `security`)
- `languages`: 适用编程语言列表
- `domains`: 适用领域列表
- `task_types`: 任务类型列表
- `content_types`: 内容类型列表
- `tags`: 标签列表
- `priority`: 优先级 (1-10)，默认 8
- `active`: 是否激活，默认 true

### 规则条件字段

- `condition`: 条件名称
- `guideline`: 指导原则
- `examples`: 示例列表
- `pattern`: 正则表达式模式

### 验证字段

- `tools`: 验证工具列表
- `severity`: 严重程度 (`error`, `warning`, `info`)
- `auto_fix`: 是否支持自动修复
- `timeout`: 超时时间（秒）

## 格式转换

系统会自动将不同格式的规则转换为统一的内部格式：

1. **字符串到枚举**: `rule_type`, `severity` 等字段自动转换
2. **时间戳**: 自动添加 `created_at` 和 `updated_at`
3. **默认值**: 自动填充缺失的可选字段
4. **验证**: 检查必需字段的完整性

## 错误处理

- 单个文件解析失败不会影响其他文件的导入
- 详细的错误日志和位置信息
- 支持 `--verbose` 模式查看完整错误堆栈

## 示例文件

项目包含以下示例文件：

- `data/rules/examples/sample_markdown_rule.md`: Markdown 格式示例
- `data/rules/examples/sample_yaml_rule.yaml`: YAML 格式示例
- `data/rules/examples/sample_json_rule.json`: JSON 格式示例（通过测试脚本生成）

## 测试

运行测试脚本验证导入功能：

```bash
python scripts/test_import.py
```

该脚本会：
1. 测试格式检测功能
2. 创建示例JSON文件
3. 导入所有格式的示例文件
4. 显示导入摘要和日志