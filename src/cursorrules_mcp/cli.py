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
                return await self._show_stats(parsed_args)
            elif parsed_args.command == 'test':
                return await self._test_tools(parsed_args)
            elif parsed_args.command == 'import':
                return await self._import_rules(parsed_args)
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
        validate_parser = subparsers.add_parser('validate', help='验证文件内容')
        validate_parser.add_argument('files', nargs='+', help='要验证的文件')
        validate_parser.add_argument('--language', '-l', help='强制指定编程语言')
        validate_parser.add_argument('--format', choices=['text', 'json'], default='text', help='输出格式')
        validate_parser.add_argument('--fix', action='store_true', help='尝试自动修复问题')
        
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
        stats_parser = subparsers.add_parser('stats', help='显示统计信息')
        stats_parser.add_argument('--format', choices=['text', 'json'], default='text', help='输出格式')
        
        # 测试命令
        test_parser = subparsers.add_parser('test', help='测试验证工具')
        test_parser.add_argument('--language', '-l', help='测试特定语言的工具')
        test_parser.add_argument('--tool', '-t', help='测试特定工具')
        
        # 导入命令
        import_parser = subparsers.add_parser('import', help='导入多格式规则文件')
        import_parser.add_argument('paths', nargs='+', help='要导入的文件或目录路径')
        import_parser.add_argument('--format', choices=['auto', 'markdown', 'yaml', 'json'], 
                                 default='auto', help='指定文件格式')
        import_parser.add_argument('--recursive', '-r', action='store_true', help='递归扫描目录')
        import_parser.add_argument('--output-dir', help='输出目录')
        import_parser.add_argument('--validate', action='store_true', help='导入后验证规则')
        import_parser.add_argument('--merge', action='store_true', help='与现有规则合并')
        import_parser.add_argument('--log', help='保存导入日志的文件路径')
        
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
        """验证文件内容"""
        try:
            validation_manager = get_validation_manager()
            all_results = []
            total_score = 0.0
            
            for file_path in args.files:
                path = Path(file_path)
                
                if not path.exists():
                    print(f"❌ 文件不存在: {file_path}")
                    continue
                
                # 读取文件内容
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    print(f"⚠️ 跳过二进制文件: {file_path}")
                    continue
                
                # 推断语言
                language = args.language or self._infer_language(path)
                
                if not language:
                    print(f"⚠️ 无法推断文件语言: {file_path}")
                    continue
                
                # 执行验证
                print(f"🔍 验证文件: {file_path} (语言: {language})")
                
                start_time = datetime.now()
                result = await validation_manager.validate_content(content, language, str(path))
                result.validation_time = datetime.now()
                
                all_results.append({
                    'file': str(path),
                    'language': language,
                    'result': result
                })
                
                total_score += result.score
                
                if args.format == 'text':
                    self._print_validation_result(path, result)
                
                # 尝试自动修复
                if args.fix and not result.is_valid:
                    await self._auto_fix_issues(path, language, result.issues)
            
            if args.format == 'json':
                # JSON输出
                output = []
                for item in all_results:
                    result = item['result']
                    output.append({
                        'file': item['file'],
                        'language': item['language'],
                        'is_valid': result.is_valid,
                        'score': result.score,
                        'issues_count': len(result.issues),
                        'issues': [
                            {
                                'line': issue.line_number,
                                'column': issue.column_number,
                                'message': issue.message,
                                'severity': issue.severity.value,
                                'rule_id': issue.rule_id
                            }
                            for issue in result.issues
                        ]
                    })
                
                print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                # 显示总结
                if len(all_results) > 1:
                    avg_score = total_score / len(all_results)
                    valid_files = sum(1 for item in all_results if item['result'].is_valid)
                    
                    print("\n" + "="*60)
                    print(f"📊 验证总结:")
                    print(f"   总文件数: {len(all_results)}")
                    print(f"   通过验证: {valid_files}")
                    print(f"   平均分数: {avg_score:.1f}")
                    print(f"   总体状态: {'✅ 通过' if valid_files == len(all_results) else '❌ 存在问题'}")
            
            # 返回码：所有文件都通过验证返回0，否则返回1
            return 0 if all(item['result'].is_valid for item in all_results) else 1
            
        except Exception as e:
            logger.error(f"验证文件失败: {e}")
            return 1
    
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
    
    async def _show_stats(self, args) -> int:
        """显示统计信息"""
        try:
            # 初始化规则引擎
            engine = RuleEngine(self.config.rules_dir)
            await engine.initialize()
            
            # 获取统计信息
            stats = await engine.get_statistics()
            
            if args.format == 'json':
                print(json.dumps(stats, ensure_ascii=False, indent=2))
            else:
                print("📊 CursorRules-MCP 统计信息\n")
                print(f"📝 总规则数: {stats['total_rules']}")
                print(f"⏰ 数据加载时间: {stats['loaded_at'] or '未知'}")
                print(f"📈 平均成功率: {stats['average_success_rate']:.1%}")
                
                print("\n🏷️ 规则类型分布:")
                for rule_type, count in stats['rules_by_type'].items():
                    if count > 0:
                        percentage = (count / stats['total_rules']) * 100
                        print(f"  {rule_type}: {count} ({percentage:.1f}%)")
                
                print("\n💻 编程语言分布:")
                for language, count in sorted(stats['rules_by_language'].items()):
                    print(f"  {language}: {count} 条规则")
                
                print("\n🌍 应用领域分布:")
                for domain, count in sorted(stats['rules_by_domain'].items()):
                    print(f"  {domain}: {count} 条规则")
                
                print(f"\n🔍 索引信息:")
                print(f"  标签总数: {stats['total_tags']}")
                print(f"  语言索引: {len(stats['rules_by_language'])} 种语言")
                print(f"  领域索引: {len(stats['rules_by_domain'])} 个领域")
            
            return 0
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return 1
    
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

    async def _import_rules(self, args) -> int:
        """导入多格式规则文件"""
        try:
            from .rule_import import UnifiedRuleImporter
            from .database import get_rule_database
            
            print("🚀 开始导入规则文件...")
            
            # 创建导入器
            importer = UnifiedRuleImporter()
            
            # 执行导入
            rules = importer.import_rules(
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
            
            # 如果启用合并，添加到数据库
            if args.merge:
                print("🔄 正在合并到规则数据库...")
                
                try:
                    database = get_rule_database()
                    await database.initialize()
                    
                    added_count = 0
                    updated_count = 0
                    
                    for rule in rules:
                        existing_rule = database.get_rule_by_id(rule.rule_id)
                        
                        if existing_rule:
                            # 更新现有规则
                            database.update_rule(rule)
                            updated_count += 1
                            print(f"🔄 更新规则: {rule.rule_id}")
                        else:
                            # 添加新规则
                            database.add_rule(rule)
                            added_count += 1
                            print(f"➕ 添加规则: {rule.rule_id}")
                    
                    print(f"📊 合并结果: 新增 {added_count} 条，更新 {updated_count} 条")
                    
                except Exception as e:
                    print(f"⚠️ 合并到数据库时出错: {e}")
                    if args.verbose:
                        import traceback
                        traceback.print_exc()
            
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
            
            return 0 if summary['failed_imports'] == 0 else 1
            
        except Exception as e:
            logger.error(f"导入规则失败: {e}")
            if args.verbose:
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