# CursorRules-MCP 任务完成检查清单

## 代码质量检查
1. 运行代码格式化
   ```bash
   black src/
   isort src/
   ```

2. 运行静态类型检查
   ```bash
   mypy src/
   ```

3. 运行代码风格检查
   ```bash
   flake8 src/
   ```

## 测试验证
1. 运行单元测试
   ```bash
   pytest tests/
   ```

2. 检查测试覆盖率
   ```bash
   pytest tests/ --cov=src
   ```

## 文档更新
1. 更新相关文档
2. 检查docstrings完整性
3. 更新CHANGELOG.md(如果有重要变更)

## 功能验证
1. 启动服务器测试
   ```bash
   python scripts/start_mcp.py
   ```

2. 使用CLI工具验证
   ```bash
   python scripts/cursorrules_cli.py test
   ```

## 提交代码
1. 添加变更文件
   ```bash
   git add .
   ```

2. 提交变更(使用规范的提交消息)
   ```bash
   git commit -m "type: description"
   ```

3. 推送到远程仓库
   ```bash
   git push
   ```