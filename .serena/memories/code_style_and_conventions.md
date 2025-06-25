# CursorRules-MCP 代码风格和约定

## Python代码风格
- 使用Python 3.9+类型注解
- 遵循PEP 8规范
- 使用black格式化工具(默认配置)
- 使用isort管理导入顺序
- 最大行长度88字符

## 命名约定
- 类名: PascalCase (如 `RuleEngine`, `ValidationManager`)
- 函数/方法: snake_case (如 `search_rules`, `validate_content`)
- 变量/属性: snake_case (如 `rule_id`, `content_type`)
- 常量: UPPER_SNAKE_CASE (如 `__VERSION__`, `DEFAULT_CONFIG`)
- 私有成员: 单下划线前缀 (如 `_config`, `_initialize`)

## 文档规范
- 使用Google风格docstrings
- 所有公共API必须有文档字符串
- 文档包含Args, Returns, Raises等标准部分
- 中文注释和文档

## 代码组织
- 每个模块顶部有模块级docstring
- 相关功能组织在同一个模块
- 遵循依赖注入原则
- 使用Pydantic模型进行数据验证

## 错误处理
- 使用自定义异常类
- 适当的日志记录
- 优雅的错误恢复