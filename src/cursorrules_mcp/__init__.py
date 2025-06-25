#!/usr/bin/env python3
"""
CursorRules-MCP: Model Context Protocol for CursorRules Management

This package provides intelligent rule-based context management for LLMs
through the Model Context Protocol (MCP), enabling consistent and
professional code generation and documentation across multiple domains.

Author: Mapoet
Institution: NUS/STAR
Date: 2025-01-23
License: MIT
"""

__version__ = "0.1.0"
__author__ = "Mapoet (NUS/STAR)"
__description__ = "Intelligent rule-based context management for LLMs via MCP"

from .config import ConfigManager, get_config, get_config_manager

# 导入核心模块
from .engine import RuleEngine

# 导入数据模型
from .models import (
    ContentType,
    CursorRule,
    MCPContext,
    RuleType,
    SearchFilter,
    TaskType,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from .server import CursorRulesMCPServer
from .validators import ValidationManager, get_validation_manager

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__description__",
    # 核心模块
    "RuleEngine",
    "CursorRulesMCPServer",
    "ValidationManager",
    "ConfigManager",
    # 数据模型
    "CursorRule",
    "ValidationResult",
    "ValidationIssue",
    "SearchFilter",
    "MCPContext",
    "RuleType",
    "ContentType",
    "TaskType",
    "ValidationSeverity",
    # 工具函数
    "get_config",
    "get_config_manager",
    "get_validation_manager",
]
