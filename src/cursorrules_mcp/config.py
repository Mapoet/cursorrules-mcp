#!/usr/bin/env python3
"""
CursorRules-MCP 配置管理模块
提供系统配置、规则配置和环境设置管理
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    from pydantic import BaseModel, Field, validator
except ImportError:
    # 如果没有pydantic，提供基础配置类
    class BaseModel:
        pass
    def Field(*args, **kwargs):
        return None
    def validator(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ValidationToolConfig(BaseModel):
    """验证工具配置"""
    name: str = Field(..., description="工具名称")
    enabled: bool = Field(default=True, description="是否启用")
    command: str = Field(..., description="执行命令")
    args: List[str] = Field(default_factory=list, description="命令参数")
    config_file: Optional[str] = Field(default=None, description="配置文件路径")
    timeout: int = Field(default=30, description="超时时间（秒）")


class DatabaseConfig(BaseModel):
    """数据库配置"""
    type: str = Field(default="sqlite", description="数据库类型")
    host: str = Field(default="localhost", description="主机地址")
    port: int = Field(default=5432, description="端口")
    database: str = Field(default="cursorrules", description="数据库名")
    username: Optional[str] = Field(default=None, description="用户名")
    password: Optional[str] = Field(default=None, description="密码")
    connection_timeout: int = Field(default=30, description="连接超时（秒）")
    pool_size: int = Field(default=10, description="连接池大小")


class CacheConfig(BaseModel):
    """缓存配置"""
    enabled: bool = Field(default=True, description="是否启用缓存")
    type: str = Field(default="memory", description="缓存类型: memory, redis, file")
    redis_url: Optional[str] = Field(default=None, description="Redis连接URL")
    ttl: int = Field(default=3600, description="缓存生存时间（秒）")
    max_size: int = Field(default=1000, description="最大缓存条目数")


class SearchConfig(BaseModel):
    """搜索配置"""
    default_limit: int = Field(default=10, description="默认返回结果数量")
    max_limit: int = Field(default=100, description="最大返回结果数量")
    fuzzy_threshold: float = Field(default=0.7, description="模糊匹配阈值")
    enable_semantic_search: bool = Field(default=True, description="是否启用语义搜索")
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="嵌入模型")


class ValidationConfig(BaseModel):
    """验证配置"""
    enabled: bool = Field(default=True, description="是否启用验证")
    parallel_validation: bool = Field(default=True, description="是否并行验证")
    max_workers: int = Field(default=4, description="最大工作线程数")
    timeout: int = Field(default=60, description="验证超时时间（秒）")
    tools: Dict[str, ValidationToolConfig] = Field(default_factory=dict, description="验证工具配置")


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = Field(default="localhost", description="服务器主机")
    port: int = Field(default=8000, description="服务器端口")
    workers: int = Field(default=1, description="工作进程数")
    reload: bool = Field(default=False, description="是否自动重载")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")


class CursorRulesConfig(BaseModel):
    """CursorRules主配置"""
    # 基础配置
    version: str = Field(default="1.0.0", description="配置版本")
    debug: bool = Field(default=False, description="调试模式")
    
    # 路径配置
    rules_dir: str = Field(default="data/rules", description="规则目录")
    templates_dir: str = Field(default="data/templates", description="模板目录")
    cache_dir: str = Field(default=".cache", description="缓存目录")
    log_dir: str = Field(default="logs", description="日志目录")
    
    # 子系统配置
    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    
    # 功能开关
    features: Dict[str, bool] = Field(default_factory=lambda: {
        "rule_search": True,
        "content_validation": True,
        "prompt_enhancement": True,
        "template_generation": True,
        "knowledge_search": True,
        "auto_learning": False,
        "metrics_collection": True
    })
    
    # 安全配置
    security: Dict[str, Any] = Field(default_factory=lambda: {
        "enable_auth": False,
        "api_key": None,
        "rate_limit": 100,  # 每分钟请求数
        "cors_origins": ["*"]
    })
    
    @validator('rules_dir', 'templates_dir', 'cache_dir', 'log_dir')
    def validate_directories(cls, v):
        """验证目录路径"""
        if v and not Path(v).is_absolute():
            # 相对路径转换为绝对路径
            return str(Path.cwd() / v)
        return v
    
    class Config:
        """Pydantic配置"""
        use_enum_values = True


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file or self._find_config_file()
        self.config: CursorRulesConfig = CursorRulesConfig()
        self.loaded = False
    
    def _find_config_file(self) -> Optional[str]:
        """查找配置文件"""
        # 查找顺序：环境变量 -> 当前目录 -> 用户目录 -> 系统目录
        search_paths = [
            os.environ.get('CURSORRULES_CONFIG'),
            'cursorrules.yaml',
            'cursorrules.yml', 
            'cursorrules.json',
            Path.home() / '.cursorrules.yaml',
            Path.home() / '.cursorrules.yml',
            Path.home() / '.cursorrules.json',
            '/etc/cursorrules/config.yaml',
            '/etc/cursorrules/config.yml'
        ]
        
        for path in search_paths:
            if path and Path(path).exists():
                return str(path)
        
        return None
    
    def load(self) -> None:
        """加载配置"""
        if self.config_file and Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    if self.config_file.endswith('.json'):
                        data = json.load(f)
                    else:
                        data = yaml.safe_load(f)
                
                # 合并配置
                self.config = CursorRulesConfig(**data)
                self.loaded = True
                print(f"✅ 配置已从 {self.config_file} 加载")
                
            except Exception as e:
                print(f"⚠️ 加载配置文件失败 {self.config_file}: {e}")
                print("使用默认配置")
        else:
            print("📝 未找到配置文件，使用默认配置")
        
        # 应用环境变量覆盖
        self._apply_env_overrides()
        
        # 确保目录存在
        self._ensure_directories()
        
        # 初始化验证工具配置
        self._init_validation_tools()
    
    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        env_mappings = {
            'CURSORRULES_DEBUG': ('debug', bool),
            'CURSORRULES_RULES_DIR': ('rules_dir', str),
            'CURSORRULES_LOG_LEVEL': ('server.log_level', str),
            'CURSORRULES_PORT': ('server.port', int),
            'CURSORRULES_HOST': ('server.host', str),
            'CURSORRULES_CACHE_TYPE': ('cache.type', str),
            'CURSORRULES_REDIS_URL': ('cache.redis_url', str),
            'CURSORRULES_DATABASE_URL': ('database.type', str),
        }
        
        for env_var, (config_path, value_type) in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value:
                try:
                    # 解析嵌套配置路径
                    config_obj = self.config
                    keys = config_path.split('.')
                    
                    for key in keys[:-1]:
                        config_obj = getattr(config_obj, key)
                    
                    # 类型转换
                    if value_type == bool:
                        parsed_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif value_type == int:
                        parsed_value = int(env_value)
                    else:
                        parsed_value = env_value
                    
                    setattr(config_obj, keys[-1], parsed_value)
                    print(f"🔧 环境变量覆盖: {config_path} = {parsed_value}")
                    
                except Exception as e:
                    print(f"⚠️ 环境变量 {env_var} 解析失败: {e}")
    
    def _ensure_directories(self) -> None:
        """确保必要目录存在"""
        directories = [
            self.config.rules_dir,
            self.config.templates_dir,
            self.config.cache_dir,
            self.config.log_dir
        ]
        
        for directory in directories:
            path = Path(directory)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                print(f"📁 创建目录: {directory}")
    
    def _init_validation_tools(self) -> None:
        """初始化验证工具配置"""
        default_tools = {
            'python': {
                'flake8': ValidationToolConfig(
                    name='flake8',
                    command='flake8',
                    args=['--max-line-length=79', '--ignore=E203,W503']
                ),
                'pylint': ValidationToolConfig(
                    name='pylint',
                    command='pylint',
                    args=['--disable=C0103,C0114']
                ),
                'black': ValidationToolConfig(
                    name='black',
                    command='black',
                    args=['--check', '--diff']
                ),
                'mypy': ValidationToolConfig(
                    name='mypy',
                    command='mypy',
                    args=['--ignore-missing-imports']
                )
            },
            'javascript': {
                'eslint': ValidationToolConfig(
                    name='eslint',
                    command='eslint',
                    args=['--format=json']
                ),
                'prettier': ValidationToolConfig(
                    name='prettier',
                    command='prettier',
                    args=['--check']
                )
            },
            'cpp': {
                'cppcheck': ValidationToolConfig(
                    name='cppcheck',
                    command='cppcheck',
                    args=['--enable=all', '--xml']
                ),
                'clang-tidy': ValidationToolConfig(
                    name='clang-tidy',
                    command='clang-tidy',
                    args=['-checks=*']
                )
            },
            'markdown': {
                'markdownlint': ValidationToolConfig(
                    name='markdownlint',
                    command='markdownlint',
                    args=['--json']
                )
            }
        }
        
        # 只添加未配置的工具
        for language, tools in default_tools.items():
            if language not in self.config.validation.tools:
                self.config.validation.tools[language] = {}
            
            for tool_name, tool_config in tools.items():
                if tool_name not in self.config.validation.tools[language]:
                    self.config.validation.tools[language][tool_name] = tool_config
    
    def save(self, file_path: Optional[str] = None) -> None:
        """保存配置到文件
        
        Args:
            file_path: 保存路径，默认为当前配置文件路径
        """
        save_path = file_path or self.config_file or 'cursorrules.yaml'
        
        try:
            config_dict = self.config.dict()
            
            with open(save_path, 'w', encoding='utf-8') as f:
                if save_path.endswith('.json'):
                    json.dump(config_dict, f, ensure_ascii=False, indent=2)
                else:
                    yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ 配置已保存到 {save_path}")
            
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套路径
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            value = self.config
            for part in key.split('.'):
                value = getattr(value, part)
            return value
        except (AttributeError, KeyError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套路径
            value: 配置值
        """
        try:
            obj = self.config
            keys = key.split('.')
            
            for part in keys[:-1]:
                obj = getattr(obj, part)
            
            setattr(obj, keys[-1], value)
            
        except (AttributeError, KeyError) as e:
            raise ValueError(f"无效的配置键: {key}") from e
    
    def get_validation_tools(self, language: str) -> Dict[str, ValidationToolConfig]:
        """获取指定语言的验证工具配置
        
        Args:
            language: 编程语言
            
        Returns:
            验证工具配置字典
        """
        return self.config.validation.tools.get(language, {})
    
    def is_feature_enabled(self, feature: str) -> bool:
        """检查功能是否启用
        
        Args:
            feature: 功能名称
            
        Returns:
            是否启用
        """
        return self.config.features.get(feature, False)
    
    def update_from_dict(self, updates: Dict[str, Any]) -> None:
        """从字典更新配置
        
        Args:
            updates: 更新的配置字典
        """
        def update_nested(obj, updates_dict):
            for key, value in updates_dict.items():
                if hasattr(obj, key):
                    current_value = getattr(obj, key)
                    if isinstance(current_value, BaseModel) and isinstance(value, dict):
                        update_nested(current_value, value)
                    else:
                        setattr(obj, key, value)
        
        update_nested(self.config, updates)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            配置字典
        """
        return self.config.dict()
    
    def validate(self) -> List[str]:
        """验证配置
        
        Returns:
            验证错误列表
        """
        errors = []
        
        # 检查必要目录
        for dir_name, dir_path in [
            ('规则目录', self.config.rules_dir),
            ('模板目录', self.config.templates_dir),
            ('缓存目录', self.config.cache_dir),
            ('日志目录', self.config.log_dir)
        ]:
            if not Path(dir_path).exists():
                errors.append(f"{dir_name} 不存在: {dir_path}")
        
        # 检查端口范围
        if not (1 <= self.config.server.port <= 65535):
            errors.append(f"服务器端口超出有效范围: {self.config.server.port}")
        
        # 检查缓存配置
        if self.config.cache.enabled and self.config.cache.type == 'redis':
            if not self.config.cache.redis_url:
                errors.append("启用Redis缓存但未配置redis_url")
        
        # 检查搜索配置
        if not (0.0 <= self.config.search.fuzzy_threshold <= 1.0):
            errors.append(f"模糊匹配阈值超出范围: {self.config.search.fuzzy_threshold}")
        
        return errors


# 全局配置实例
_config_manager: Optional[ConfigManager] = None


def get_config() -> CursorRulesConfig:
    """获取全局配置实例
    
    Returns:
        配置实例
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.load()
    
    return _config_manager.config


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例
    
    Returns:
        配置管理器实例
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.load()
    
    return _config_manager


def reload_config(config_file: Optional[str] = None) -> None:
    """重新加载配置
    
    Args:
        config_file: 配置文件路径
    """
    global _config_manager
    _config_manager = ConfigManager(config_file)
    _config_manager.load()


def create_default_config(file_path: str = 'cursorrules.yaml') -> None:
    """创建默认配置文件
    
    Args:
        file_path: 配置文件保存路径
    """
    config_manager = ConfigManager()
    config_manager.save(file_path)
    print(f"✅ 默认配置文件已创建: {file_path}")


if __name__ == "__main__":
    # 用于生成默认配置文件
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            output_file = sys.argv[2] if len(sys.argv) > 2 else "cursorrules.yaml"
            create_default_config(output_file)
        elif sys.argv[1] == "validate":
            config_file = sys.argv[2] if len(sys.argv) > 2 else None
            manager = ConfigManager(config_file)
            manager.load()
            
            errors = manager.validate()
            if errors:
                print("❌ 配置验证失败:")
                for error in errors:
                    print(f"  - {error}")
                sys.exit(1)
            else:
                print("✅ 配置验证通过")
    else:
        print("用法:")
        print("  python config.py init [file]     # 生成默认配置文件")
        print("  python config.py validate [file] # 验证配置文件")