#!/usr/bin/env python3
"""
CursorRules-MCP 命令行接口
提供规则管理、验证和服务器控制的命令行工具

Author: Mapoet
Institution: NUS/STAR
Date: 2025-01-23
License: MIT
"""

import asyncio
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from .config import get_config_manager, create_default_config, ConfigManager
from .engine import RuleEngine
from .server import CursorRulesMCPServer
from .validators import get_validation_manager
from .models import SearchFilter, MCPContext

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CLI:
    """命令行接口主类"""
    
    def __init__(self):
        """初始化CLI"""
        self.config_manager = get_config_manager()
        self.config = self.config_manager.config
        
    async def run(self, args: List[str]) -> int:
        """运行CLI命令
        
        Args:
            args: 命令行参数
            
        Returns:
            退出代码
        """
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)
        
        # 设置日志级别
        if hasattr(parsed_args, 'verbose') and parsed_args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        elif hasattr(parsed_args, 'quiet') and parsed_args.quiet:
            logging.getLogger().setLevel(logging.WARNING)
        
        try:
            # 执行对应的命令
            if parsed_args.command == 'server':
                return await self._run_server(parsed_args)
            elif parsed_args.command == 'search':
                return await self._search_rules(parsed_args)
            elif parsed_args.command == 'validate':
                return await self._validate_content(parsed_args)
            elif parsed_args.command == 'config':
                return await self._manage_config(parsed_args)
            elif parsed_args.command == 'stats':
                return await self._get_statistics(parsed_args)
            elif parsed_args.command == 'test':
                return await self._test_tools(parsed_args)
            elif parsed_args.command == 'import':
                return await self._import_resources(parsed_args)
            else:
                parser.print_help()
                return 1
                
        except KeyboardInterrupt:
            print("\n👋 操作已取消")
            return 1
        except Exception as e:
            logger.error(f"执行命令失败: {e}")
            if hasattr(parsed_args, 'verbose') and parsed_args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """创建命令行解析器"""
        parser = argparse.ArgumentParser(
            prog='cursorrules-mcp',
            description='CursorRules-MCP 命令行工具',
            epilog="""
示例:
  cursorrules-mcp server                    # 启动MCP服务器
  cursorrules-mcp search --language python # 搜索Python规则
  cursorrules-mcp validate file.py         # 验证Python文件
  cursorrules-mcp config init               # 初始化配置文件
  cursorrules-mcp stats                     # 显示统计信息
            """,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # 全局选项
        parser.add_argument('--config', type=str, help='配置文件路径')
        parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
        parser.add_argument('--quiet', '-q', action='store_true', help='静默模式')
        parser.add_argument('--version', action='version', version='cursorrules-mcp 1.0.0')
        
        # 子命令
        subparsers = parser.add_subparsers(dest='command', help='可用命令')
        
        # 服务器命令
        server_parser = subparsers.add_parser('server', help='启动MCP服务器')
        server_parser.add_argument('--host', default='localhost', help='服务器主机地址')
        server_parser.add_argument('--port', type=int, default=8000, help='服务器端口')
        server_parser.add_argument('--reload', action='store_true', help='启用自动重载')
        
        # 搜索命令
        search_parser = subparsers.add_parser('search', help='搜索规则')
        search_parser.add_argument('query', nargs='?', default='', help='搜索关键词')
        search_parser.add_argument('--language', '-l', action='append', help='编程语言')
        search_parser.add_argument('--domain', '-d', action='append', help='应用领域')
        search_parser.add_argument('--tag', '-t', action='append', help='标签')
        search_parser.add_argument('--limit', type=int, default=10, help='结果数量限制')
        search_parser.add_argument('--format', choices=['text', 'json'], default='text', help='输出格式')
        
        # 验证命令
        validate_parser = subparsers.add_parser('validate_content', help='校验内容合规性')
        validate_parser.add_argument('content', help='待校验内容')
        validate_parser.add_argument('--file_path', help='文件路径，仅用于推断语言类型')
        validate_parser.add_argument('--languages', help='语言，如python,markdown')
        validate_parser.add_argument('--content_types', help='内容类型，如code,documentation')
        validate_parser.add_argument('--domains', help='领域')
        validate_parser.add_argument('--output_mode', choices=['result_only', 'result_with_prompt', 'result_with_rules', 'result_with_template', 'full'], default='result_only', help='输出模式：\n'
            '  result_only: 仅返回校验结果（success, passed, problems）\n'
            '  result_with_prompt: 返回校验结果和 prompt\n'
            '  result_with_rules: 返回校验结果和规则详情\n'
            '  result_with_template: 返回校验结果和模板信息\n'
            '  full: 返回全部信息（校验结果、prompt、规则、模板信息）\n'
            '默认 result_only')
        
        # 配置命令
        config_parser = subparsers.add_parser('config', help='配置管理')
        config_subparsers = config_parser.add_subparsers(dest='config_action', help='配置操作')
        
        # 配置子命令
        config_subparsers.add_parser('init', help='初始化默认配置文件')
        config_subparsers.add_parser('validate', help='验证配置文件')
        config_subparsers.add_parser('show', help='显示当前配置')
        
        config_set_parser = config_subparsers.add_parser('set', help='设置配置值')
        config_set_parser.add_argument('key', help='配置键')
        config_set_parser.add_argument('value', help='配置值')
        
        config_get_parser = config_subparsers.add_parser('get', help='获取配置值')
        config_get_parser.add_argument('key', help='配置键')
        
        # 统计命令
        stats_parser = subparsers.add_parser('stats', help='获取规则与模板统计信息')
        stats_parser.add_argument('--resource_type', choices=['rules', 'templates', 'all'], default='rules', help='统计对象类型：rules（规则）、templates（模板）、all（全部）')
        stats_parser.add_argument('--languages', help='语言过滤')
        stats_parser.add_argument('--domains', help='领域过滤')
        stats_parser.add_argument('--rule_types', help='规则类型过滤（仅规则）')
        stats_parser.add_argument('--tags', help='标签过滤')
        
        # 测试命令
        test_parser = subparsers.add_parser('test', help='测试验证工具')
        test_parser.add_argument('--language', '-l', help='测试特定语言的工具')
        test_parser.add_argument('--tool', '-t', help='测试特定工具')
        
        # 导入命令
        import_parser = subparsers.add_parser('import', help='导入规则或模板文件')
        import_parser.add_argument('paths', nargs='+', help='要导入的文件或目录路径')
        import_parser.add_argument('--format', choices=['auto', 'markdown', 'yaml', 'json'], 
                                 default='auto', help='指定文件格式')
        import_parser.add_argument('--recursive', '-r', action='store_true', help='递归扫描目录')
        import_parser.add_argument('--output-dir', help='输出目录')
        import_parser.add_argument('--validate', action='store_true', help='导入后验证规则')
        import_parser.add_argument('--merge', action='store_true', help='与现有规则合并')
        import_parser.add_argument('--log', help='保存导入日志的文件路径')
        import_parser.add_argument('--type', choices=['rules', 'templates'], help='资源类型')
        import_parser.add_argument('--mode', choices=['append', 'replace'], help='导入模式')
        
        return parser
    
    async def _migrate_database(self, args) -> None:
            """执行数据库迁移"""
            from .migration import perform_database_migration
            
            print("🚀 开始执行规则库数据化迁移...")
            
            try:
                database = await perform_database_migration()
                
                print("✅ 迁移完成！")
                stats = database.get_database_stats()
                
                print(f"\n📊 迁移结果:")
                print(f"  总规则数: {stats['total_rules']}")
                print(f"  版本数: {stats['total_versions']}")
                print(f"  活跃规则: {stats['active_rules']}")
                print(f"  支持语言: {stats['languages']} 种")
                print(f"  覆盖领域: {stats['domains']} 个")
                
            except Exception as e:
                print(f"❌ 迁移失败: {e}")
                import traceback
                if args.verbose:
                    traceback.print_exc()    
    async def _run_server(self, args) -> int:
        """运行MCP服务器"""
        try:
            print("🚀 启动 CursorRules-MCP 服务器...")
            
            # 更新配置
            if args.host != 'localhost':
                self.config.server.host = args.host
            if args.port != 8000:
                self.config.server.port = args.port
            if args.reload:
                self.config.server.reload = True
            
            # 创建并启动服务器
            server = CursorRulesMCPServer(self.config.rules_dir)
            await server.run()
            
            return 0
            
        except Exception as e:
            logger.error(f"服务器启动失败: {e}")
            return 1
    
    async def _search_rules(self, args) -> int:
        """搜索规则"""
        try:
            # 初始化规则引擎
            engine = RuleEngine(self.config.rules_dir)
            await engine.initialize()
            
            if len(engine.rules) == 0:
                print("❌ 未找到任何规则，请检查规则目录配置")
                return 1
            
            # 构建搜索过滤器
            search_filter = SearchFilter(
                query=args.query if args.query else None,
                languages=args.language or [],
                domains=args.domain or [],
                tags=args.tag or [],
                limit=args.limit
            )
            
            # 执行搜索
            results = await engine.search_rules(search_filter)
            
            if args.format == 'json':
                # JSON输出
                output = []
                for applicable_rule in results:
                    rule = applicable_rule.rule
                    output.append({
                        'rule_id': rule.rule_id,
                        'name': rule.name,
                        'description': rule.description,
                        'relevance_score': applicable_rule.relevance_score,
                        'languages': rule.languages,
                        'domains': rule.domains,
                        'tags': rule.tags
                    })
                
                print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                # 文本输出
                if not results:
                    print("❌ 未找到匹配的规则")
                    return 1
                
                print(f"🔍 找到 {len(results)} 条匹配规则:\n")
                
                for i, applicable_rule in enumerate(results, 1):
                    rule = applicable_rule.rule
                    print(f"{i}. **{rule.name}** (ID: {rule.rule_id})")
                    print(f"   相关度: {applicable_rule.relevance_score:.2f}")
                    print(f"   描述: {rule.description}")
                    print(f"   语言: {', '.join(rule.languages) if rule.languages else '通用'}")
                    print(f"   领域: {', '.join(rule.domains) if rule.domains else '通用'}")
                    print(f"   标签: {', '.join(rule.tags)}")
                    print()
            
            return 0
            
        except Exception as e:
            logger.error(f"搜索规则失败: {e}")
            return 1
    
    async def _validate_content(self, args) -> int:
        """CLI调用，参数化校验内容合规性"""
        from src.cursorrules_mcp.engine import OutputMode
        from src.cursorrules_mcp.models import MCPContext
        
        # 构建MCP上下文
        context = MCPContext(
            user_query="Content validation request",
            current_file=getattr(args, 'file_path', None),
            primary_language=getattr(args, 'languages', None),
            domain=getattr(args, 'domains', None),
            project_path=None
        )
        
        result = await self.rule_engine.validate_content(
            content=args.content,
            context=context,
            output_mode=OutputMode(args.output_mode)
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    
    def _print_validation_result(self, file_path: Path, result) -> None:
        """打印验证结果"""
        status = "✅ 通过" if result.is_valid else "❌ 存在问题"
        print(f"   结果: {status} (分数: {result.score:.1f}/100)")
        
        if result.issues:
            print(f"   发现 {len(result.issues)} 个问题:")
            
            # 按严重程度分组
            by_severity = {}
            for issue in result.issues:
                severity = issue.severity.value
                if severity not in by_severity:
                    by_severity[severity] = []
                by_severity[severity].append(issue)
            
            # 显示问题
            for severity in ['error', 'warning', 'info']:
                if severity in by_severity:
                    issues = by_severity[severity]
                    icon = {'error': '🔴', 'warning': '🟡', 'info': '🔵'}[severity]
                    print(f"     {icon} {severity.upper()} ({len(issues)}个):")
                    
                    for issue in issues[:5]:  # 最多显示5个
                        location = f"{issue.line_number}:{issue.column_number}"
                        print(f"       {location} {issue.message}")
                    
                    if len(issues) > 5:
                        print(f"       ... 还有 {len(issues) - 5} 个{severity}问题")
        
        if result.suggestions:
            print(f"   建议:")
            for suggestion in result.suggestions[:3]:  # 最多显示3个建议
                print(f"     💡 {suggestion}")
        
        print()
    
    async def _auto_fix_issues(self, file_path: Path, language: str, issues) -> None:
        """尝试自动修复问题"""
        if language == 'python':
            # 尝试使用black格式化
            try:
                import subprocess
                result = subprocess.run(
                    ['black', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print(f"   🔧 已使用black格式化: {file_path}")
                else:
                    print(f"   ⚠️ black格式化失败: {result.stderr}")
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print(f"   ⚠️ black工具不可用")
        
        # 可以添加其他语言的自动修复逻辑
    
    def _infer_language(self, file_path: Path) -> Optional[str]:
        """推断文件的编程语言"""
        ext = file_path.suffix.lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.c++': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.sh': 'shell',
            '.bash': 'shell',
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json'
        }
        
        return language_map.get(ext)
    
    async def _manage_config(self, args) -> int:
        """管理配置"""
        try:
            if args.config_action == 'init':
                # 初始化配置文件
                output_file = 'cursorrules.yaml'
                create_default_config(output_file)
                return 0
                
            elif args.config_action == 'validate':
                # 验证配置
                errors = self.config_manager.validate()
                if errors:
                    print("❌ 配置验证失败:")
                    for error in errors:
                        print(f"  - {error}")
                    return 1
                else:
                    print("✅ 配置验证通过")
                    return 0
                    
            elif args.config_action == 'show':
                # 显示配置
                print(json.dumps(self.config_manager.to_dict(), ensure_ascii=False, indent=2))
                return 0
                
            elif args.config_action == 'set':
                # 设置配置值
                try:
                    # 尝试将值转换为合适的类型
                    value = args.value
                    if value.lower() in ['true', 'false']:
                        value = value.lower() == 'true'
                    elif value.isdigit():
                        value = int(value)
                    
                    self.config_manager.set(args.key, value)
                    self.config_manager.save()
                    print(f"✅ 配置已更新: {args.key} = {value}")
                    return 0
                except Exception as e:
                    print(f"❌ 设置配置失败: {e}")
                    return 1
                    
            elif args.config_action == 'get':
                # 获取配置值
                value = self.config_manager.get(args.key)
                if value is not None:
                    print(f"{args.key} = {value}")
                    return 0
                else:
                    print(f"❌ 配置键不存在: {args.key}")
                    return 1
            else:
                print("❌ 无效的配置操作")
                return 1
                
        except Exception as e:
            logger.error(f"配置管理失败: {e}")
            return 1
    
    async def _get_statistics(self, args) -> int:
        """CLI调用，获取规则与模板统计信息"""
        result = self.rule_engine.get_statistics(
            resource_type=getattr(args, 'resource_type', 'rules'),
            languages=getattr(args, 'languages', ''),
            domains=getattr(args, 'domains', ''),
            rule_types=getattr(args, 'rule_types', ''),
            tags=getattr(args, 'tags', '')
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
    
    async def _test_tools(self, args) -> int:
        """测试验证工具"""
        try:
            validation_manager = get_validation_manager()
            available_validators = validation_manager.get_available_validators()
            
            if not available_validators:
                print("❌ 未找到可用的验证工具")
                return 1
            
            print("🔧 可用的验证工具:\n")
            
            languages_to_test = [args.language] if args.language else available_validators.keys()
            
            for language in languages_to_test:
                if language not in available_validators:
                    print(f"❌ 不支持的语言: {language}")
                    continue
                
                tools = available_validators[language]
                if args.tool and args.tool not in tools:
                    print(f"❌ 语言 {language} 不支持工具: {args.tool}")
                    continue
                
                tools_to_test = [args.tool] if args.tool else tools
                
                print(f"💻 {language.upper()}:")
                
                for tool in tools_to_test:
                    if validation_manager.is_tool_available(language, tool):
                        # 测试工具
                        test_content = self._get_test_content(language)
                        
                        try:
                            result = await validation_manager.validate_content(
                                test_content, language
                            )
                            
                            status = "✅ 正常" if result.score > 0 else "⚠️ 有问题"
                            print(f"  {tool}: {status} (分数: {result.score:.1f})")
                            
                        except Exception as e:
                            print(f"  {tool}: ❌ 错误 ({e})")
                    else:
                        print(f"  {tool}: ❌ 不可用")
                
                print()
            
            return 0
            
        except Exception as e:
            logger.error(f"测试验证工具失败: {e}")
            return 1
    
    def _get_test_content(self, language: str) -> str:
        """获取测试内容"""
        test_contents = {
            'python': '''def test_function():
    x = 1
    return x
''',
            'javascript': '''function testFunction() {
    let x = 1;
    return x;
}
''',
            'markdown': '''# Test Document

This is a test document.

## Section

Content here.
''',
            'cpp': '''#include <iostream>

int main() {
    std::cout << "Hello World" << std::endl;
    return 0;
}
'''
        }
        
        return test_contents.get(language, '// Test content')

    async def _import_resources(self, args) -> int:
        """导入规则或模板文件"""
        try:
            from .rule_import import UnifiedRuleImporter
            from .engine import RuleEngine
            from .database import get_rule_database
            print("🚀 开始导入资源文件...")
            # 自动识别类型
            resource_type = args.type or None
            if not resource_type:
                # 根据第一个文件后缀自动判断
                ext = os.path.splitext(args.paths[0])[1].lower()
                if ext in ['.yaml', '.yml', '.md']:
                    resource_type = 'templates'
                else:
                    resource_type = 'rules'
            if resource_type == 'templates':
                # 导入模板
                engine = RuleEngine(self.config.rules_dir)
                engine.load_prompt_templates(args.paths, mode=getattr(args, 'mode', 'append'))
                print(f"✅ 成功导入 {len(args.paths)} 个模板文件")
                return 0
            else:
                # 导入规则
            importer = UnifiedRuleImporter(save_to_database=True)
            rules = await importer.import_rules_async(
                paths=args.paths,
                recursive=args.recursive,
                format_hint=args.format if args.format != 'auto' else None
            )
            if not rules:
                print("❌ 未能导入任何规则")
                return 1
            print(f"✅ 成功解析 {len(rules)} 条规则")
            # 如果指定了输出目录，保存到文件
            if args.output_dir:
                output_dir = Path(args.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # 保存为JSON格式
                output_file = output_dir / "imported_rules.json"
                rules_data = [rule.dict() for rule in rules]
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(rules_data, f, indent=2, ensure_ascii=False, default=str)
                
                print(f"💾 规则已保存到: {output_file}")
            
            # 如果启用验证，验证导入的规则
            if args.validate:
                print("🔍 正在验证导入的规则...")
                
                valid_count = 0
                invalid_count = 0
                
                for rule in rules:
                    try:
                        # 简单验证：检查必需字段
                        if not rule.rule_id or not rule.name or not rule.rules:
                            print(f"❌ 规则验证失败: {rule.rule_id} - 缺少必需字段")
                            invalid_count += 1
                        else:
                            print(f"✅ 规则验证通过: {rule.rule_id}")
                            valid_count += 1
                    except Exception as e:
                        print(f"❌ 规则验证失败: {rule.rule_id} - {e}")
                        invalid_count += 1
                
                print(f"📊 验证结果: 通过 {valid_count} 条，失败 {invalid_count} 条")
            
            # 显示导入摘要
            summary = importer.get_import_summary()
            
            print("\n" + "="*60)
            print("📊 导入摘要:")
            print(f"  总文件数: {summary['total_files']}")
            print(f"  成功导入: {summary['successful_imports']}")
            print(f"  导入失败: {summary['failed_imports']}")
            print(f"  成功率: {summary['success_rate']:.1%}")
            print(f"  总规则数: {len(rules)}")
            
            # 按格式统计
            format_stats = {}
            for log_entry in summary['import_log']:
                if log_entry['status'] == 'success':
                    file_path = Path(log_entry['file'])
                    ext = file_path.suffix.lower()
                    format_name = {
                        '.md': 'Markdown',
                        '.markdown': 'Markdown', 
                        '.yaml': 'YAML',
                        '.yml': 'YAML',
                        '.json': 'JSON'
                    }.get(ext, 'Unknown')
                    
                    format_stats[format_name] = format_stats.get(format_name, 0) + 1
            
            if format_stats:
                print("\n📁 按格式统计:")
                for format_name, count in format_stats.items():
                    print(f"  {format_name}: {count} 个文件")
            
            # 保存导入日志
            if args.log:
                log_path = Path(args.log)
                importer.save_import_log(log_path)
                print(f"📝 导入日志已保存: {log_path}")
            
            print(f"\n🔄 规则已保存到数据库，下次搜索将包含新导入的规则")
            
            return 0 if summary['failed_imports'] == 0 else 1
            
        except Exception as e:
            logger.error(f"导入资源失败: {e}")
            if getattr(args, 'verbose', False):
                import traceback
                traceback.print_exc()
            return 1


async def main() -> int:
    """主入口函数"""
    cli = CLI()
    return await cli.run(sys.argv[1:])


def sync_main() -> int:
    """同步主入口函数"""
    return asyncio.run(main())


if __name__ == "__main__":
    sys.exit(sync_main())