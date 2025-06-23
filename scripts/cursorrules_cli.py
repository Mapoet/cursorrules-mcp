#!/usr/bin/env python3
"""
CursorRules-MCP 命令行工具启动脚本

Author: Mapoet
Institution: NUS/STAR
Date: 2025-01-23
License: MIT
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from cursorrules_mcp.cli import sync_main

if __name__ == "__main__":
    sys.exit(sync_main())