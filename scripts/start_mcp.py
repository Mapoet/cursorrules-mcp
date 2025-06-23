#!/usr/bin/env python3
"""
CursorRules-MCP 服务器启动脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cursorrules_mcp.server import CursorRulesMCPServer

def main():
    """主函数"""
    try:
        from src.cursorrules_mcp.config import get_config_manager
        
        # 获取配置
        config_manager = get_config_manager()
        config = config_manager.config
        
        print("🚀 启动 CursorRules-MCP 服务器...")
        print(f"📂 规则目录: {config.rules_dir}")
        print(f"🔧 调试模式: {'开启' if config.debug else '关闭'}")
        
        # 创建服务器
        server = CursorRulesMCPServer(config.rules_dir)
        
        # 直接运行FastMCP服务器，它会自己管理事件循环
        server.mcp.run()
        
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()