# CursorRules-MCP 项目概览

## 项目目的
CursorRules-MCP是一个智能的规则管理系统，通过Model Context Protocol (MCP)为LLM提供规则查找、验证和应用服务。项目旨在标准化代码生成和文档编写的质量控制。

## 技术栈
- **语言**: Python 3.9+
- **核心框架**: FastAPI, Pydantic, SQLAlchemy
- **MCP协议**: mcp>=0.3.0
- **数据库**: PostgreSQL, Redis缓存
- **搜索**: ChromaDB, Elasticsearch
- **LLM集成**: OpenAI, Anthropic, LiteLLM
- **工具**: Rich CLI, Typer命令行

## 项目结构
- `src/cursorrules_mcp/`: 核心模块
  - `models.py`: 数据模型定义
  - `engine.py`: 规则引擎核心
  - `server.py`: MCP服务器实现
  - `validators.py`: 验证器系统
  - `config.py`: 配置管理
  - `cli.py`: 命令行接口
- `data/rules/`: 规则数据库
- `examples/`: 示例和演示代码
- `scripts/`: 启动脚本