# CursorRules-MCP

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95.0-green.svg)](https://fastapi.tiangolo.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

基于 Model Context Protocol (MCP) 的智能编程规则与提示模板管理系统。

## 目录

- [功能特点](#功能特点)
- [快速开始](#快速开始)
- [核心功能](#核心功能)
- [使用指南](#使用指南)
- [API文档](#api文档)
- [部署说明](#部署说明)
- [贡献指南](#贡献指南)
- [相关文档](#相关文档)

## 功能特点

- 🔍 **智能规则搜索** - 多维度过滤、相关度排序
- ✅ **内容验证** - 多语言支持、自动规则匹配
- 🚀 **提示增强** - 上下文感知、规则智能注入
- 📊 **统计分析** - 多维度统计、使用情况分析
- 📥 **资源导入** - 多格式支持、冲突处理

## 快速开始

### 安装

```bash
pip install cursorrules-mcp
```

### 基本使用

```python
from cursorrules_mcp import RuleEngine

# 初始化规则引擎
engine = RuleEngine()
await engine.initialize()

# 搜索规则
results = await engine.search_rules(query="类型检查", languages=["python"])

# 验证内容
result = await engine.validate_content(content="代码内容", languages=["python"])
```

## 核心功能

### 1. 规则搜索

```bash
# CLI示例
cursorrules-mcp search --query "类型检查" --languages python
cursorrules-mcp search --tags "performance,security" --limit 5

# MCP示例
{
  "method": "search_rules",
  "params": {
    "query": "类型检查",
    "languages": ["python"],
    "tags": ["performance", "security"],
    "limit": 5
  }
}
```

### 2. 内容验证

```bash
# CLI示例
cursorrules-mcp validate "代码内容" --languages python
cursorrules-mcp validate --file mycode.py --output_mode detailed

# MCP示例
{
  "method": "validate_content",
  "params": {
    "content": "代码内容",
    "languages": ["python"],
    "output_mode": "detailed"
  }
}
```

### 3. 提示增强

```bash
# CLI示例
cursorrules-mcp enhance "基础提示" --languages python --domains scientific

# MCP示例
{
  "method": "enhance_prompt",
  "params": {
    "base_prompt": "基础提示",
    "languages": ["python"],
    "domains": ["scientific"]
  }
}
```

### 4. 统计分析

```bash
# CLI示例
cursorrules-mcp stats --resource_type rules
cursorrules-mcp stats --resource_type templates

# MCP示例
{
  "method": "get_statistics",
  "params": {
    "resource_type": "rules",
    "languages": ["python", "cpp"],
    "domains": ["scientific"]
  }
}
```

### 5. 资源导入

```bash
# CLI示例
cursorrules-mcp import rules/ --type rules --validate
cursorrules-mcp import templates/ --type templates --mode append

# MCP示例
{
  "method": "import_resource",
  "params": {
    "content": "规则内容",
    "type": "rules",
    "format": "markdown",
    "validate": true
  }
}
```

## 使用指南

### 配置文件

```yaml
# cursorrules.yaml
server:
  host: localhost
  port: 8000
  workers: 4

rules:
  data_dir: data/rules
  templates_dir: data/templates
  cache_ttl: 3600

validation:
  timeout: 30
  max_rules: 10
  output_mode: detailed
```

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `CURSORRULES_HOST` | 服务器地址 | localhost |
| `CURSORRULES_PORT` | 服务器端口 | 8000 |
| `CURSORRULES_LOG_LEVEL` | 日志级别 | INFO |
| `CURSORRULES_DATA_DIR` | 数据目录 | data/ |

## API文档

- 📚 **[API参考](docs/api.md)** - 详细的API文档
- 📖 **[技术架构](docs/techs.md)** - 技术架构与实现细节
- 📝 **[规则格式](docs/rules.md)** - 规则编写指南
- 🔧 **[配置说明](docs/config.md)** - 配置项说明

## 部署说明

### Docker部署

```bash
# 构建镜像
docker build -t cursorrules-mcp .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -v ./data:/app/data \
  -e CURSORRULES_LOG_LEVEL=INFO \
  cursorrules-mcp
```

### Kubernetes部署

```bash
# 部署服务
kubectl apply -f k8s/

# 查看状态
kubectl get pods -l app=cursorrules-mcp
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 相关文档

- 📖 **[技术架构](docs/techs.md)** - 完整的技术架构

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系我们

**文档版本**: v1.4.0  
**最后更新**: 2025-06-23  
**维护团队**: Mapoet