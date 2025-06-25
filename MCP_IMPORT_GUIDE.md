# 🚀 CursorRules-MCP 导入规则使用指南

## 📋 规则格式要求

### ✅ **正确的YAML格式**
```yaml
rule_id: CR-YOUR-RULE-001
name: 规则名称
description: 规则描述
version: 1.0.0
rule_type: style  # style, content, format, performance, security
languages:
  - python
  - javascript
domains:
  - web
  - backend
tags:
  - style
  - best-practice
author: Your Name
rules:
  - condition: 具体的规则条件
    guideline: 指导原则
    priority: 5  # 1-10
    enforcement: false
    examples:
      - good: "正确的代码示例"
        bad: "错误的代码示例"
        explanation: "解释说明"
```

### ✅ **正确的Markdown格式**
```markdown
---
rule_id: CR-YOUR-RULE-001
name: 规则名称
description: 规则描述
version: 1.0.0
rule_type: style
languages:
  - python
domains:
  - web
tags:
  - style
author: Your Name
---

# 规则名称

## 规则详情

### 1. 规则条件
- **条件**: 具体的规则条件
- **指导原则**: 指导原则
- **优先级**: 5
- **强制性**: false

**示例**:
```python
# 正确示例
def good_example():
    pass

# 错误示例  
def bad_example():
    pass
```
```

## 🔧 **在Cursor中使用MCP导入**

### 步骤1: 准备规则内容
确保您的规则包含所有必需字段，特别是 `rule_id`。

### 步骤2: 调用导入工具
```
@cursorrules 导入以下规则：

rule_id: CR-EXAMPLE-001
name: 示例规则
description: 这是一个示例规则
version: 1.0.0
rule_type: style
languages:
  - python
domains:
  - general
tags:
  - example
author: User
rules:
  - condition: 代码必须有注释
    guideline: 所有函数都应该有文档字符串
    priority: 7
    enforcement: true
    examples:
      - good: "def func():\n    \"\"\"函数文档\"\"\"\n    pass"
        bad: "def func():\n    pass"
        explanation: "函数应该有清晰的文档说明"
```

## 🚨 **常见错误和解决方案**

### 错误1: "规则缺少rule_id字段"
**解决方案**: 确保在规则顶部添加唯一的 `rule_id`
```yaml
rule_id: CR-UNIQUE-ID-001  # 必需！
name: 规则名称
```

### 错误2: "Invalid literal value, expected \"image\""
**解决方案**: 这是MCP格式验证错误，已在最新版本中修复。如果仍然出现：
1. 重启Cursor IDE
2. 重新启动MCP服务器
3. 检查规则格式是否正确

### 错误3: "Expected string, received object"
**解决方案**: 这表明MCP工具返回了非字符串类型。已修复，如果仍出现请：
1. 更新到最新版本的cursorrules-mcp
2. 重启MCP服务

## 🎯 **最佳实践**

1. **规则ID命名规范**: 使用 `CR-[类别]-[名称]-[序号]` 格式
   - 例如: `CR-PY-STYLE-001`, `CR-JS-SECURITY-002`

2. **优先级设置**: 
   - 1-3: 建议性规则
   - 4-6: 重要规则
   - 7-10: 关键规则

3. **示例质量**: 提供清晰的好/坏示例对比

4. **标签使用**: 使用相关的标签便于搜索和分类

## 🔍 **验证导入结果**

导入后可以通过以下方式验证：

1. **搜索规则**: `@cursorrules 搜索 [关键词]`
2. **查看统计**: `@cursorrules 获取统计信息`  
3. **查看规则详情**: 通过规则ID查看具体内容

## ❓ **故障排除**

如果遇到问题：

1. 检查规则格式是否完整
2. 确认所有必需字段都已填写
3. 验证YAML/JSON语法正确性
4. 重启MCP服务器
5. 查看服务器日志获取详细错误信息

---

💡 **提示**: 如果您是第一次使用，建议从简单的规则开始，逐步熟悉格式要求。 

六个气象大模型（含不同层terrain_mask数据）
  计算节点缓存：200G
  固定存储（15日长期预报）：200 GB
  每日增量（24小时6小时步长）为15GB
  已考虑15日后移至冷存储或者删除非必须预报结果
>单步单时次模型大小:
>fengwu 和 fengwuv2：135M。
>fourcastnet：52M。
>fourcastnetv2：145M。
>fuxi：138M。
>pangu：140M。
>terrain_mask：104M
>总共849 MB即接近1GB
>15天缓存数据量:849*4*60/1024=200GB
>每日增量数据:849*4*4/1024=15GB

智能融合模型：
  计算节点缓存：300G
  固定存储：3TB
  每日增量: 5GB
  已考虑15日后移至冷存储或者删除非必须预报结果

>单步单时次模型大小：280MB
>每时次的预报步次：20*4+40+60=180
>15天缓存步次:180*4*15=10,800
>15天缓存数据量:280*10,800=2953.125GB，约3TB
>每日增量数据:280*4*4/1024=4.3GB,约5GB

