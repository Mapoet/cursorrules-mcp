---
rule_id: "CR-MD-FORMAT-001"
name: "Markdown标题格式规范"
description: "确保Markdown文档使用正确的标题层级和格式"
version: "1.0.0"
author: "Mapoet"
rule_type: "format"
languages: ["markdown"]
domains: ["documentation"]
task_types: ["documentation"]
content_types: ["documentation"]
tags: ["markdown", "formatting", "headers", "documentation"]
condition: "markdown_heading_format"
priority: 8
validation_tools: ["markdownlint"]
severity: "warning"
auto_fix: true
timeout: 30
file_patterns: ["*.md", "*.markdown"]
---

# Markdown标题格式规范

## 指导原则

Markdown标题应该遵循以下规范：

1. **层级递进**：标题层级应该按顺序递进，不跳级
2. **唯一H1**：文档应该只有一个一级标题（H1）
3. **空行分隔**：标题前后应该有空行分隔
4. **无尾随空格**：标题行末尾不应有多余空格
5. **ATX风格**：优先使用ATX风格标题（# ## ###）而不是Setext风格

## 示例

### 正确示例

```markdown
# 文档标题

这是文档的介绍内容。

## 主要章节

### 子章节

这里是子章节的内容。

#### 更细的分节

这里是更细分节的内容。
```

### 错误示例

```markdown
# 文档标题
## 主要章节
没有空行分隔的内容
#### 跳过了三级标题   
末尾有空格的标题    

# 多个一级标题
这是不好的做法
```

## 相关工具

- markdownlint: 自动检查Markdown格式
- prettier: 可以格式化Markdown文件
- Vale: 用于文档风格检查

## 例外情况

在某些特殊情况下，可能需要放宽这些规则：
- API文档生成的Markdown文件
- 从其他格式转换的文档
- 特定工具生成的技术文档