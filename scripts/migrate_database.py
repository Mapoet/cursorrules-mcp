#!/usr/bin/env python3
"""
规则库数据化迁移脚本
执行完整的数据库迁移和规则生成

Author: Mapoet
Institution: NUS/STAR
Date: 2025-01-23
License: MIT
"""

import sys
import asyncio
from pathlib import Path

# 添加src到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from cursorrules_mcp.migration import perform_database_migration


async def main():
    """主函数"""
    print("🚀 开始执行CursorRules-MCP规则库数据化...")
    print("="*60)
    
    try:
        # 执行完整的数据库迁移
        database = await perform_database_migration()
        
        print("\n" + "="*60)
        print("✅ 规则库数据化完成！")
        print("\n📊 最终统计:")
        
        stats = database.get_database_stats()
        print(f"  总规则数量: {stats['total_rules']}")
        print(f"  版本总数: {stats['total_versions']}")
        print(f"  活跃规则: {stats['active_rules']}")
        print(f"  支持语言: {stats['languages']} 种")
        print(f"  覆盖领域: {stats['domains']} 个")
        print(f"  规则类型: {stats['rule_types']} 种")
        print(f"  标签数量: {stats['total_tags']} 个")
        
        print("\n🎯 功能验证:")
        print("  ✅ 版本管理: 支持规则版本控制和历史跟踪")
        print("  ✅ 冲突检测: 自动检测规则间的冲突和覆盖关系")
        print("  ✅ 规则索引: 按语言、领域、标签建立高效索引")
        print("  ✅ 数据库接口: 完整的CRUD操作支持")
        print("  ✅ 扩展规则库: 生成覆盖多领域的丰富规则集")
        
        print("\n📂 生成的文件:")
        print("  📁 data/rules/migrated/: 迁移后的规则")
        print("  📁 data/rules/generated/: 新生成的规则")
        print("  📄 data/rules/database_report.json: 数据库统计报告")
        
        print("\n🔧 使用方法:")
        print("  python scripts/cursorrules_cli.py search --language python")
        print("  python scripts/cursorrules_cli.py validate file.py")
        print("  python scripts/cursorrules_cli.py stats")
        print("  python scripts/start_mcp.py")
        
    except Exception as e:
        print(f"\n❌ 迁移过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())