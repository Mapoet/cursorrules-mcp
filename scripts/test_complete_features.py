#!/usr/bin/env python3
"""
测试MCP和HTTP服务器的导入和统计功能

Author: Mapoet
Date: 2025-01-23
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from cursorrules_mcp.server import CursorRulesMCPServer
from cursorrules_mcp.http_server import MCPHttpServer
from cursorrules_mcp.engine import RuleEngine

# 测试数据
TEST_MARKDOWN_RULE = """---
rule_id: "TEST-MD-001"
name: "Markdown测试规则"
description: "用于测试Markdown格式导入的规则"
version: "1.0.0"
author: "TestUser"
rule_type: "style"
languages: ["python", "markdown"]
domains: ["documentation"]
tags: ["testing", "markdown", "import"]
priority: 8
enforcement: true
---

# Markdown测试规则

这是一个用于测试Markdown格式导入的规则。

## 规则内容

### 条件1：文档格式要求
**指导原则**: 所有Markdown文档应该有清晰的标题层次结构
**优先级**: 8

#### 示例

**良好示例**:
```markdown
# 主标题
## 次级标题
### 三级标题
```

**不良示例**:
```markdown
### 直接使用三级标题
# 主标题
#### 跳过二级标题
```

**说明**: 保持标题层次的连续性有助于文档的可读性和结构化。
"""

TEST_YAML_RULE = """
rule_id: "TEST-YAML-001"
name: "YAML测试规则"
description: "用于测试YAML格式导入的规则"
version: "1.0.0"
author: "TestUser"
created_at: "2025-01-23T10:00:00Z"
updated_at: "2025-01-23T10:00:00Z"
rule_type: "content"
languages:
  - "yaml"
  - "python"
domains:
  - "configuration"
  - "testing"
task_types:
  - "data_processing"
content_types:
  - "configuration"
tags:
  - "testing"
  - "yaml"
  - "configuration"
rules:
  - condition: "yaml_formatting"
    guideline: "YAML配置文件应该有清晰的结构和注释"
    priority: 7
    enforcement: true
    examples:
      - good: |
          # 数据库配置
          database:
            host: localhost
            port: 5432
            name: myapp
        bad: |
          database:
          host:localhost
          port:5432
          name:myapp
        explanation: "适当的缩进和空格使YAML更易读"
applies_to:
  file_patterns:
    - "*.yaml"
    - "*.yml"
  project_types: []
  contexts: []
conflicts_with: []
overrides: []
validation:
  tools:
    - "yamllint"
  severity: "warning"
  auto_fix: false
  timeout: 30
  custom_config: {}
  code_style: null
  documentation: null
  testing: null
  custom_validators: []
active: true
usage_count: 0
success_rate: 0.0
"""

TEST_JSON_RULE = {
    "rule_id": "TEST-JSON-001",
    "name": "JSON测试规则",
    "description": "用于测试JSON格式导入的规则",
    "version": "1.0.0",
    "author": "TestUser",
    "created_at": "2025-01-23T10:00:00Z",
    "updated_at": "2025-01-23T10:00:00Z",
    "rule_type": "format",
    "languages": ["json", "javascript"],
    "domains": ["api", "configuration"],
    "task_types": ["data_processing"],
    "content_types": ["data"],
    "tags": ["testing", "json", "format"],
    "rules": [
        {
            "condition": "json_formatting",
            "guideline": "JSON文件应该有适当的格式和验证",
            "priority": 6,
            "enforcement": False,
            "examples": [
                {
                    "good": '{\n  "name": "test",\n  "version": "1.0.0"\n}',
                    "bad": '{"name":"test","version":"1.0.0"}',
                    "explanation": "适当的缩进使JSON更易读"
                }
            ],
            "pattern": None
        }
    ],
    "applies_to": {
        "file_patterns": ["*.json"],
        "project_types": [],
        "contexts": []
    },
    "conflicts_with": [],
    "overrides": [],
    "validation": {
        "tools": ["jsonlint"],
        "severity": "info",
        "auto_fix": True,
        "timeout": 30,
        "custom_config": {},
        "code_style": None,
        "documentation": None,
        "testing": None,
        "custom_validators": []
    },
    "active": True,
    "usage_count": 0,
    "success_rate": 0.0
}


class TestMCPImportFeatures:
    """测试MCP导入和统计功能的类"""
    
    def __init__(self):
        self.test_dir = None
        self.mcp_server = None
        self.rule_engine = None
    
    async def setup(self):
        """设置测试环境"""
        print("🔧 设置测试环境...")
        
        # 创建临时测试目录
        self.test_dir = tempfile.mkdtemp(prefix="cursorrules_test_")
        print(f"📁 测试目录: {self.test_dir}")
        
        # 创建规则引擎和MCP服务器
        self.rule_engine = RuleEngine(self.test_dir)
        await self.rule_engine.initialize()
        
        self.mcp_server = CursorRulesMCPServer(self.test_dir)
        await self.mcp_server._ensure_initialized()
        
        print("✅ 测试环境设置完成")
    
    async def cleanup(self):
        """清理测试环境"""
        if self.test_dir:
            import shutil
            shutil.rmtree(self.test_dir, ignore_errors=True)
            print(f"🧹 清理测试目录: {self.test_dir}")
    
    async def test_markdown_import(self):
        """测试Markdown格式导入"""
        print("\n📝 测试Markdown格式导入...")
        
        try:
            # 使用MCP工具导入Markdown规则
            result = await self.mcp_server._setup_tools()
            
            # 获取import_rules工具
            import_tool = None
            for tool_name, tool_func in self.mcp_server.mcp._tools.items():
                if tool_name == "import_rules":
                    import_tool = tool_func
                    break
            
            if import_tool:
                result = await import_tool(
                    content=TEST_MARKDOWN_RULE,
                    format="markdown",
                    validate=True,
                    merge=False
                )
                print(f"✅ Markdown导入结果: {result[:200]}...")
            else:
                print("❌ 未找到import_rules工具")
                
        except Exception as e:
            print(f"❌ Markdown导入测试失败: {e}")
    
    async def test_yaml_import(self):
        """测试YAML格式导入"""
        print("\n📄 测试YAML格式导入...")
        
        try:
            # 创建临时YAML文件
            yaml_file = Path(self.test_dir) / "test_rule.yaml"
            yaml_file.write_text(TEST_YAML_RULE)
            
            # 使用文件路径导入
            import_tool = None
            for tool_name, tool_func in self.mcp_server.mcp._tools.items():
                if tool_name == "import_rules":
                    import_tool = tool_func
                    break
            
            if import_tool:
                result = await import_tool(
                    file_path=str(yaml_file),
                    format="yaml",
                    validate=True,
                    merge=False
                )
                print(f"✅ YAML导入结果: {result[:200]}...")
            else:
                print("❌ 未找到import_rules工具")
                
        except Exception as e:
            print(f"❌ YAML导入测试失败: {e}")
    
    async def test_json_import(self):
        """测试JSON格式导入"""
        print("\n🔧 测试JSON格式导入...")
        
        try:
            # 将JSON转换为字符串
            json_content = json.dumps(TEST_JSON_RULE, indent=2, ensure_ascii=False)
            
            # 使用内容导入
            import_tool = None
            for tool_name, tool_func in self.mcp_server.mcp._tools.items():
                if tool_name == "import_rules":
                    import_tool = tool_func
                    break
            
            if import_tool:
                result = await import_tool(
                    content=json_content,
                    format="json",
                    validate=True,
                    merge=False
                )
                print(f"✅ JSON导入结果: {result[:200]}...")
            else:
                print("❌ 未找到import_rules工具")
                
        except Exception as e:
            print(f"❌ JSON导入测试失败: {e}")
    
    async def test_statistics_without_filters(self):
        """测试无过滤条件的统计"""
        print("\n📊 测试无过滤条件的统计...")
        
        try:
            # 获取统计工具
            stats_tool = None
            for tool_name, tool_func in self.mcp_server.mcp._tools.items():
                if tool_name == "get_statistics":
                    stats_tool = tool_func
                    break
            
            if stats_tool:
                result = await stats_tool()
                print(f"✅ 全局统计结果: {result[:300]}...")
            else:
                print("❌ 未找到get_statistics工具")
                
        except Exception as e:
            print(f"❌ 全局统计测试失败: {e}")
    
    async def test_statistics_with_filters(self):
        """测试带过滤条件的统计"""
        print("\n🔍 测试带过滤条件的统计...")
        
        try:
            # 获取统计工具
            stats_tool = None
            for tool_name, tool_func in self.mcp_server.mcp._tools.items():
                if tool_name == "get_statistics":
                    stats_tool = tool_func
                    break
            
            if stats_tool:
                # 按语言过滤
                result = await stats_tool(languages="python,yaml")
                print(f"✅ Python/YAML统计: {result[:200]}...")
                
                # 按领域过滤
                result = await stats_tool(domains="testing,configuration")
                print(f"✅ 测试/配置领域统计: {result[:200]}...")
                
                # 按规则类型过滤
                result = await stats_tool(rule_types="style,content")
                print(f"✅ 样式/内容类型统计: {result[:200]}...")
                
                # 按标签过滤
                result = await stats_tool(tags="testing,import")
                print(f"✅ 测试/导入标签统计: {result[:200]}...")
                
                # 组合过滤
                result = await stats_tool(
                    languages="python",
                    domains="testing",
                    tags="import"
                )
                print(f"✅ 组合过滤统计: {result[:200]}...")
            else:
                print("❌ 未找到get_statistics工具")
                
        except Exception as e:
            print(f"❌ 过滤统计测试失败: {e}")
    
    async def test_search_imported_rules(self):
        """测试搜索已导入的规则"""
        print("\n🔎 测试搜索已导入的规则...")
        
        try:
            # 获取搜索工具
            search_tool = None
            for tool_name, tool_func in self.mcp_server.mcp._tools.items():
                if tool_name == "search_rules":
                    search_tool = tool_func
                    break
            
            if search_tool:
                # 搜索测试规则
                result = await search_tool(
                    query="测试",
                    tags="testing,import",
                    limit=10
                )
                print(f"✅ 搜索测试规则: {result[:300]}...")
                
                # 搜索特定语言
                result = await search_tool(
                    languages="python,yaml",
                    limit=5
                )
                print(f"✅ 搜索Python/YAML规则: {result[:300]}...")
            else:
                print("❌ 未找到search_rules工具")
                
        except Exception as e:
            print(f"❌ 搜索规则测试失败: {e}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行MCP导入和统计功能测试...")
        
        try:
            await self.setup()
            
            # 测试导入功能
            await self.test_markdown_import()
            await self.test_yaml_import()
            await self.test_json_import()
            
            # 等待一下确保导入完成
            await asyncio.sleep(1)
            
            # 测试统计功能
            await self.test_statistics_without_filters()
            await self.test_statistics_with_filters()
            
            # 测试搜索功能
            await self.test_search_imported_rules()
            
            print("\n✅ 所有测试完成!")
            
        except Exception as e:
            print(f"\n❌ 测试运行失败: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await self.cleanup()


async def test_http_api():
    """测试HTTP API端点"""
    print("\n🌐 测试HTTP API端点...")
    
    try:
        import aiohttp
        import asyncio
        
        # 启动HTTP服务器（这里只是演示，实际需要在后台运行）
        print("📝 注意：HTTP API测试需要手动启动服务器")
        print("请运行: python scripts/start_http_server.py")
        print("然后可以使用以下curl命令测试：")
        
        print("\n🔧 测试导入API:")
        print('curl -X POST http://localhost:8000/api/import \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"content": "...规则内容...", "format": "auto"}\'')
        
        print("\n📊 测试统计API:")
        print('curl "http://localhost:8000/api/statistics"')
        print('curl "http://localhost:8000/api/statistics?languages=python&domains=testing"')
        
        print("\n🔍 测试搜索API:")
        print('curl "http://localhost:8000/api/rules?query=测试&limit=5"')
        
        print("\n✅ 验证内容API:")
        print('curl -X POST http://localhost:8000/api/validate \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"content": "def test(): pass", "languages": "python"}\'')
        
    except ImportError:
        print("❌ aiohttp未安装，跳过HTTP API测试")


def main():
    """主函数"""
    async def run_tests():
        # 运行MCP测试
        tester = TestMCPImportFeatures()
        await tester.run_all_tests()
        
        # 运行HTTP API测试说明
        await test_http_api()
    
    # 运行异步测试
    asyncio.run(run_tests())


if __name__ == "__main__":
    main()