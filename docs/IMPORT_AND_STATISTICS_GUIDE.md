# CursorRules-MCP 导入和统计功能指南

## 概述

CursorRules-MCP 已增强支持多格式规则导入和灵活的统计查询功能。现在支持通过MCP和HTTP JSON-RPC接口进行规则导入和统计查询。

## 🚀 新增功能

### 1. 多格式规则导入
- **Markdown格式**：支持frontmatter + 内容格式
- **YAML格式**：完整的结构化配置
- **JSON格式**：标准JSON规则格式
- **自动格式检测**：智能识别文件格式

### 2. 增强的统计查询
- **无参数模式**：返回全局统计信息
- **过滤模式**：支持按语言、领域、类型、标签过滤
- **详细分布**：提供规则分布和使用统计

### 3. 双接口支持
- **MCP接口**：通过工具调用方式
- **HTTP REST API**：直接的API端点访问

---

## 📋 MCP接口使用

### 1. 导入规则工具

#### 工具名称
`import_rules`

#### 参数说明
```json
{
  "content": "规则内容（如果提供了content，则忽略file_path）",
  "file_path": "规则文件路径",
  "format": "格式类型 (auto, markdown, yaml, json)",
  "validate": "是否验证规则 (true/false)",
  "merge": "是否合并重复规则 (true/false)"
}
```

#### 使用示例

**从内容导入Markdown规则**：
```json
{
  "name": "import_rules",
  "arguments": {
    "content": "---\nrule_id: \"MY-RULE-001\"\nname: \"我的规则\"\n...\n---\n# 规则内容",
    "format": "markdown",
    "validate": true,
    "merge": false
  }
}
```

**从文件导入YAML规则**：
```json
{
  "name": "import_rules",
  "arguments": {
    "file_path": "/path/to/my_rule.yaml",
    "format": "auto",
    "validate": true
  }
}
```

### 2. 统计查询工具

#### 工具名称
`get_statistics`

#### 参数说明
```json
{
  "languages": "过滤的编程语言（逗号分隔）",
  "domains": "过滤的应用领域（逗号分隔）",
  "rule_types": "过滤的规则类型（逗号分隔）",
  "tags": "过滤的标签（逗号分隔）"
}
```

#### 使用示例

**全局统计**：
```json
{
  "name": "get_statistics",
  "arguments": {}
}
```

**按语言过滤**：
```json
{
  "name": "get_statistics",
  "arguments": {
    "languages": "python,cpp,javascript"
  }
}
```

**组合过滤**：
```json
{
  "name": "get_statistics",
  "arguments": {
    "languages": "python",
    "domains": "scientific,meteorology",
    "rule_types": "style,content",
    "tags": "performance,optimization"
  }
}
```

---

## 🌐 HTTP REST API使用

### 1. 导入API端点

#### POST `/api/import`

**JSON请求**：
```bash
curl -X POST http://localhost:8000/api/import \
  -H "Content-Type: application/json" \
  -d '{
    "content": "规则内容...",
    "format": "auto",
    "validate": true,
    "merge": false
  }'
```

**文件上传**：
```bash
curl -X POST http://localhost:8000/api/import \
  -F "file=@my_rule.yaml" \
  -F "format=yaml" \
  -F "validate=true"
```

**响应格式**：
```json
{
  "success": true,
  "message": "✅ 规则导入成功\n\n**导入统计**:\n- 处理文件: 1\n- 导入规则: 1\n..."
}
```

### 2. 统计API端点

#### GET `/api/statistics`

**无过滤查询**：
```bash
curl "http://localhost:8000/api/statistics"
```

**带过滤参数查询**：
```bash
curl "http://localhost:8000/api/statistics?languages=python,cpp&domains=scientific"
```

#### POST `/api/statistics`

**复杂过滤查询**：
```bash
curl -X POST http://localhost:8000/api/statistics \
  -H "Content-Type: application/json" \
  -d '{
    "languages": "python,javascript",
    "domains": "web,api",
    "rule_types": "style,content",
    "tags": "performance,security"
  }'
```

**响应格式**：
```json
{
  "success": true,
  "statistics": "📊 **CursorRules-MCP 规则库统计**\n\n**规则统计**:\n- 总规则数: 15\n..."
}
```

### 3. 其他API端点

#### GET `/api/rules` - 规则列表
```bash
curl "http://localhost:8000/api/rules?query=测试&languages=python&limit=10"
```

#### POST `/api/validate` - 内容验证
```bash
curl -X POST http://localhost:8000/api/validate \
  -H "Content-Type: application/json" \
  -d '{
    "content": "def test(): pass",
    "languages": "python",
    "file_path": "test.py"
  }'
```

---

## 📝 支持的导入格式

### 1. Markdown格式 (.md)

**特点**：
- frontmatter包含元数据
- 主体内容为Markdown格式
- 支持代码示例和说明

**示例**：
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
tags: ["style", "pep8", "python"]
priority: 8
enforcement: true
---

# Python代码风格规则

本规则确保Python代码遵循PEP8标准。

## 规则详情

### 条件1：行长度限制
**指导原则**: 每行代码不应超过88个字符
**优先级**: 8

#### 示例

**良好示例**:
```python
def long_function_name(
    parameter_one, parameter_two, parameter_three
):
    return parameter_one + parameter_two
```

**不良示例**:
```python
def long_function_name(parameter_one, parameter_two, parameter_three, parameter_four):
    return parameter_one + parameter_two + parameter_three + parameter_four
```
```

### 2. YAML格式 (.yaml, .yml)

**特点**：
- 完整的结构化配置
- 支持复杂嵌套结构
- 人类可读性好

**示例**：
```yaml
rule_id: "CONTENT-JS-001"
name: "JavaScript函数命名规则"
description: "JavaScript函数应使用驼峰命名法"
version: "1.0.0"
author: "FrontendTeam"
created_at: "2025-01-23T10:00:00Z"
updated_at: "2025-01-23T10:00:00Z"
rule_type: "content"
languages:
  - "javascript"
  - "typescript"
domains:
  - "web"
  - "frontend"
task_types:
  - "development"
content_types:
  - "code"
tags:
  - "naming"
  - "javascript"
  - "functions"
rules:
  - condition: "function_naming"
    guideline: "函数名应使用驼峰命名法，动词开头"
    priority: 7
    enforcement: true
    examples:
      - good: |
          function calculateTotal() { ... }
          function getUserById(id) { ... }
        bad: |
          function calculate_total() { ... }
          function GetUserById(id) { ... }
        explanation: "驼峰命名法提高代码的一致性和可读性"
applies_to:
  file_patterns:
    - "*.js"
    - "*.ts"
  project_types:
    - "web"
  contexts:
    - "frontend"
validation:
  tools:
    - "eslint"
  severity: "warning"
  auto_fix: true
  timeout: 30
active: true
usage_count: 0
success_rate: 0.0
```

### 3. JSON格式 (.json)

**特点**：
- 标准JSON结构
- 机器易解析
- 支持所有字段

**示例**：
```json
{
  "rule_id": "FORMAT-CSS-001",
  "name": "CSS格式化规则",
  "description": "CSS代码应保持一致的格式化风格",
  "version": "1.0.0",
  "author": "StyleTeam",
  "created_at": "2025-01-23T10:00:00Z",
  "updated_at": "2025-01-23T10:00:00Z",
  "rule_type": "format",
  "languages": ["css", "scss", "less"],
  "domains": ["web", "design"],
  "task_types": ["styling"],
  "content_types": ["code"],
  "tags": ["css", "formatting", "style"],
  "rules": [
    {
      "condition": "css_indentation",
      "guideline": "使用2个空格进行缩进",
      "priority": 6,
      "enforcement": false,
      "examples": [
        {
          "good": ".container {\n  margin: 0 auto;\n  padding: 20px;\n}",
          "bad": ".container{\nmargin:0 auto;\npadding:20px;\n}",
          "explanation": "一致的缩进和空格提高CSS的可读性"
        }
      ]
    }
  ],
  "applies_to": {
    "file_patterns": ["*.css", "*.scss", "*.less"],
    "project_types": ["web"],
    "contexts": ["styling"]
  },
  "validation": {
    "tools": ["stylelint"],
    "severity": "info",
    "auto_fix": true,
    "timeout": 30
  },
  "active": true,
  "usage_count": 0,
  "success_rate": 0.0
}
```

---

## 📊 统计查询功能

### 过滤参数说明

| 参数 | 描述 | 示例值 |
|------|------|--------|
| `languages` | 编程语言过滤 | `"python,javascript,cpp"` |
| `domains` | 应用领域过滤 | `"web,scientific,iot"` |
| `rule_types` | 规则类型过滤 | `"style,content,format"` |
| `tags` | 标签过滤 | `"performance,security,testing"` |

### 统计输出内容

#### 基本统计
- 总规则数
- 活跃规则数
- 版本总数
- 支持语言数量
- 应用领域数量
- 规则类型数量
- 标签总数

#### 分布统计
- 按类型分布
- 按语言分布
- 按领域分布
- 版本分布

#### 使用统计
- 总使用次数
- 平均成功率
- 最常用规则

#### 服务状态
- 活跃连接数
- 服务器运行时间

---

## 🧪 测试和验证

### 运行测试脚本
```bash
# 运行完整的功能测试
python scripts/test_mcp_import_features.py

# 测试CLI导入功能
python scripts/cursorrules_cli.py import data/rules/examples/ --recursive --validate

# 启动HTTP服务器进行API测试
python scripts/start_http_server.py --port 8000
```

### 验证导入结果
```bash
# 查看导入的规则
python scripts/cursorrules_cli.py search --query "测试" --limit 10

# 获取统计信息
python scripts/cursorrules_cli.py stats
```

---

## ⚠️ 注意事项

### 1. 格式要求
- **Markdown**: 必须包含有效的frontmatter
- **YAML**: 必须符合YAML语法规范
- **JSON**: 必须是有效的JSON格式

### 2. 验证规则
- 启用验证时会检查必需字段
- 无效的规则会被跳过
- 验证错误会在结果中报告

### 3. 合并策略
- 启用合并时，相同rule_id的规则会被合并
- 新版本会覆盖旧版本
- 建议在生产环境中谨慎使用合并功能

### 4. 性能考虑
- 大量规则导入可能需要时间
- 建议分批导入大量规则
- 统计查询在大数据集上可能较慢

---

## 🔧 故障排除

### 常见问题

#### 1. 导入失败
```
错误: "导入失败: module 'rule_import' not found"
解决: 确保rule_import.py文件存在且可导入
```

#### 2. 格式检测错误
```
错误: "无法自动检测格式"
解决: 明确指定format参数
```

#### 3. 验证失败
```
错误: "规则验证失败: 缺少必需字段"
解决: 检查规则格式，确保包含所有必需字段
```

#### 4. 统计查询为空
```
问题: 过滤后没有结果
解决: 检查过滤条件，确保存在匹配的规则
```

### 调试技巧

1. **启用详细日志**：
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **检查导入结果**：
   ```bash
   # 查看导入目录
   ls -la data/rules/imported/
   
   # 检查日志文件
   tail -f logs/import.log
   ```

3. **验证数据库状态**：
   ```python
   from cursorrules_mcp.database import RuleDatabase
   db = RuleDatabase("data/rules")
   print(db.get_database_stats())
   ```

---

## 📚 扩展阅读

- [CLI使用指南](./CLI_GUIDE.md)
- [HTTP服务器指南](./HTTP_SERVER_GUIDE.md)
- [规则格式规范](./RULE_FORMAT_SPEC.md)
- [开发者指南](./DEVELOPMENT_GUIDE.md)

---

## 🤝 贡献

如果您发现问题或有改进建议，请：

1. 创建Issue描述问题
2. 提交Pull Request
3. 更新相关文档
4. 添加测试用例

---

**最后更新**: 2025-01-23  
**版本**: 1.0.0  
**作者**: Mapoet