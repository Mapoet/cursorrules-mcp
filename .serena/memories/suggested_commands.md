# CursorRules-MCP 开发命令

## 基本运行命令
```bash
# 启动MCP服务器
python scripts/start_mcp.py

# 使用CLI工具
python scripts/cursorrules_cli.py --help
python scripts/cursorrules_cli.py search --language python
python scripts/cursorrules_cli.py validate file.py
python scripts/cursorrules_cli.py stats

# 配置管理
python scripts/cursorrules_cli.py config init
```

## 开发和测试命令
```bash
# 代码质量检查
black src/ --check
isort src/ --check-only  
flake8 src/
mypy src/

# 格式化代码
black src/
isort src/

# 运行测试
pytest tests/
pytest tests/ --cov=src

# 安装开发依赖
pip install -e ".[dev]"
```

## 系统命令 (Linux)
```bash
# 基本文件操作
ls -la
cd <directory>
find . -name "*.py"
grep -r "pattern" src/
```