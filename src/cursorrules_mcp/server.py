#!/usr/bin/env python3
"""
CursorRules-MCP 服务器实现
基于Model Context Protocol提供规则管理和验证服务

Author: Mapoet
Institution: NUS/STAR
Date: 2025-01-23
License: MIT
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import sys
import traceback

# MCP相关导入
try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP库未安装，请运行: pip install mcp")
    sys.exit(1)

from .engine import RuleEngine
from .models import (
    MCPContext, SearchFilter, ValidationSeverity, RuleType,
    ContentType, TaskType
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CursorRulesMCPServer:
    """
    CursorRules MCP服务器
    
    提供规则搜索、内容验证、模板获取等功能
    """
    
    def __init__(self, rules_dir: str = "data/rules"):
        """初始化MCP服务器
        
        Args:
            rules_dir: 规则目录路径
        """
        self.mcp = FastMCP("cursorrules-mcp")
        self.rule_engine = RuleEngine(rules_dir)
        self._initialized = False
        self.setup_handlers()
        
    def setup_handlers(self):
        """设置MCP工具和资源处理器"""
        self._setup_tools()
        self._setup_resources()
    
    def _setup_tools(self):
        """注册MCP工具"""
        
        @self.mcp.tool()
        async def search_rules(
            query: str = "",
            languages: str = "",
            domains: str = "",
            tags: str = "",
            content_types: str = "",
            rule_types: str = "",
            limit: int = 10
        ) -> str:
            """搜索适用的规则
            
            Args:
                query: 搜索关键词
                languages: 编程语言列表（逗号分隔），如：python,cpp,javascript
                domains: 应用领域列表（逗号分隔），如：meteorology,ionosphere
                tags: 标签列表（逗号分隔），如：style,performance,documentation
                content_types: 内容类型列表（逗号分隔），如：code,documentation
                rule_types: 规则类型列表（逗号分隔），如：style,content,format
                limit: 返回结果数量限制
            
            Returns:
                匹配的规则列表
            """
            try:
                # 确保初始化
                await self._ensure_initialized()
                
                # 解析参数
                search_filter = SearchFilter(
                    query=query.strip() if query else None,
                    languages=self._parse_list_param(languages),
                    domains=self._parse_list_param(domains),
                    tags=self._parse_list_param(tags),
                    content_types=self._parse_list_param(content_types),
                    rule_types=[RuleType(rt.strip()) for rt in rule_types.split(',') if rt.strip()] if rule_types else None,
                    limit=max(1, min(50, limit))  # 限制在1-50之间
                )
                
                # 执行搜索
                applicable_rules = await self.rule_engine.search_rules(search_filter)
                
                if not applicable_rules:
                    return "❌ 未找到匹配的规则。请尝试调整搜索条件。"
                
                # 格式化结果
                result_text = f"""
🔍 **搜索摘要**: 
- 查询: "{query}" (如果有)
- 找到 {len(applicable_rules)} 条匹配规则
- 搜索条件: {self._format_search_conditions(search_filter)}

---
"""
                
                for i, applicable_rule in enumerate(applicable_rules, 1):
                    rule = applicable_rule.rule
                    
                    # 构建规则详情文本
                    rule_text = f"""
## {i}. {rule.name}
**ID**: `{rule.rule_id}` | **版本**: {rule.version} | **相关度**: {applicable_rule.relevance_score:.2f}

**描述**: {rule.description}

**分类信息**:
- 🏷️ **类型**: {rule.rule_type.value}
- 💻 **语言**: {', '.join(rule.languages) if rule.languages else '通用'}
- 🌍 **领域**: {', '.join(rule.domains) if rule.domains else '通用'}
- 📝 **内容类型**: {', '.join([ct.value for ct in rule.content_types]) if rule.content_types else '通用'}
- 🏪 **标签**: {', '.join(rule.tags)}

**规则详情**:
"""
                    
                    # 添加规则条件
                    for j, condition in enumerate(rule.rules[:3], 1):  # 最多显示3个条件
                        rule_text += f"""
### {j}. {condition.condition}
**指导原则**: {condition.guideline}
**优先级**: {condition.priority}/10

"""
                        # 添加示例
                        if condition.examples:
                            example = condition.examples[0]
                            if isinstance(example, dict):
                                if example.get('good'):
                                    rule_text += f"**✅ 良好示例**:\n```\n{example['good']}\n```\n\n"
                                if example.get('bad'):
                                    rule_text += f"**❌ 不良示例**:\n```\n{example['bad']}\n```\n\n"
                                if example.get('explanation'):
                                    rule_text += f"**💡 说明**: {example['explanation']}\n\n"
                    
                    # 添加验证信息
                    if rule.validation and rule.validation.tools:
                        rule_text += f"**🔧 验证工具**: {', '.join(rule.validation.tools)}\n"
                        rule_text += f"**⚠️ 违规严重程度**: {rule.validation.severity.value}\n"
                    
                    # 添加使用统计
                    rule_text += f"\n**📊 使用统计**: 使用次数 {rule.usage_count} | 成功率 {rule.success_rate:.1%}\n"
                    
                    rule_text += "\n---\n"
                    
                    result_text += rule_text
                
                return result_text
                
            except Exception as e:
                logger.error(f"搜索规则时发生错误: {e}")
                return f"❌ 搜索失败: {str(e)}"
        
        @self.mcp.tool()
        async def validate_content(
            content: str,
            file_path: str = "",
            languages: str = "",
            domains: str = "",
            content_types: str = "",
            project_context: str = "",
            output_mode: str = "detailed"
        ) -> str:
            """验证内容是否符合规则
            
            Args:
                content: 要验证的内容
                file_path: 文件路径（可选，用于推断语言类型）
                languages: 编程语言（逗号分隔）
                domains: 应用领域（逗号分隔）
                content_types: 内容类型（逗号分隔）
                project_context: 项目上下文信息
                output_mode: 验证结果输出模式
            
            Returns:
                详细的验证报告
            """
            try:
                # 确保初始化
                await self._ensure_initialized()
                
                # 构建MCP上下文
                context = MCPContext(
                    user_query="Content validation request",
                    current_file=file_path.strip() if file_path else None,
                    primary_language=self._parse_list_param(languages)[0] if self._parse_list_param(languages) else None,
                    domain=self._parse_list_param(domains)[0] if self._parse_list_param(domains) else None,
                    project_path=project_context.strip() if project_context else None
                )
                
                # 执行验证
                validation_result = await self.rule_engine.validate_content(
                    content=content,
                    context=context,
                    output_mode=output_mode
                )
                
                # 格式化验证结果
                # 从context获取语言和推断内容类型
                languages = [context.primary_language] if context.primary_language else []
                domains = [context.domain] if context.domain else []
                
                # 推断内容类型
                content_types = []
                if context.current_file:
                    file_ext = Path(context.current_file).suffix.lower()
                    if file_ext in ['.py', '.js', '.ts', '.cpp', '.c', '.java']:
                        content_types.append("code")
                    elif file_ext in ['.md', '.txt', '.rst']:
                        content_types.append("documentation")
                
                result_text = f"""
🔍 **内容验证报告**

**验证内容**: {len(content)} 字符
**文件路径**: {file_path or '未指定'}
**检测到的语言**: {', '.join(languages) if languages else '未知'}
**内容类型**: {', '.join(content_types) if content_types else '未知'}

---

**验证结果**: {'✅ 通过' if validation_result.is_valid else '❌ 发现问题'}
**总体评分**: {validation_result.score:.1%}
"""
                
                # 添加问题详情
                if validation_result.issues:
                    result_text += "\n**发现的问题**:\n"
                    
                    # 按严重程度分组
                    by_severity = {}
                    for issue in validation_result.issues:
                        severity = issue.severity.value
                        if severity not in by_severity:
                            by_severity[severity] = []
                        by_severity[severity].append(issue)
                    
                    # 显示问题
                    for severity in ['error', 'warning', 'info']:
                        if severity in by_severity:
                            issues = by_severity[severity]
                            icon = {'error': '🔴', 'warning': '🟡', 'info': '🔵'}[severity]
                            result_text += f"{icon} **{severity.upper()}** ({len(issues)}个):\n"
                            
                            for issue in issues[:5]:  # 最多显示5个
                                location = f"第{issue.line_number}行" if issue.line_number else "未知位置"
                                result_text += f"- {location}: {issue.message}\n"
                            
                            if len(issues) > 5:
                                result_text += f"- ... 还有 {len(issues) - 5} 个{severity}问题\n"
                
                # 添加建议
                if validation_result.suggestions:
                    result_text += "\n**改进建议**:\n"
                    for suggestion in validation_result.suggestions[:3]:  # 最多显示3个建议
                        result_text += f"💡 {suggestion}\n"
                
                # 添加应用的规则
                if validation_result.applied_rules:
                    result_text += f"\n**应用的规则**: {', '.join(validation_result.applied_rules)}\n"
                
                return result_text
                
            except Exception as e:
                logger.error(f"验证内容时发生错误: {e}")
                return f"❌ 验证失败: {str(e)}"

        @self.mcp.tool()
        async def enhance_prompt(
            base_prompt: str,
            languages: str = "",
            domains: str = "",
            tags: str = "",
            max_rules: int = 5
        ) -> str:
            """根据上下文增强提示
            
            Args:
                base_prompt: 基础提示
                languages: 编程语言（逗号分隔）
                domains: 应用领域（逗号分隔）
                tags: 标签（逗号分隔）
                max_rules: 最大包含规则数量
            
            Returns:
                增强后的提示
            """
            try:
                # 确保初始化
                await self._ensure_initialized()
                
                # 构建上下文
                context = MCPContext(
                    user_query=f"Enhance prompt: {base_prompt[:50]}...",
                    primary_language=self._parse_list_param(languages)[0] if self._parse_list_param(languages) else None,
                    domain=self._parse_list_param(domains)[0] if self._parse_list_param(domains) else None,
                    intent_tags=self._parse_list_param(tags) or []
                )
                
                # 执行提示增强
                enhanced_prompt = await self.rule_engine.enhance_prompt(base_prompt, context)
                
                return f"""
**增强后的提示**:

{enhanced_prompt.content}

---

**应用的规则**: {len(enhanced_prompt.applied_rules)} 条
**总体质量评分**: {enhanced_prompt.quality_score:.1%}
"""
                
            except Exception as e:
                logger.error(f"增强提示时发生错误: {e}")
                return f"❌ 提示增强失败: {str(e)}"

        @self.mcp.tool()
        async def get_statistics(
            languages: str = "",
            domains: str = "",
            rule_types: str = "",
            tags: str = ""
        ) -> str:
            """获取规则库统计信息
            
            Args:
                languages: 过滤的编程语言（逗号分隔）
                domains: 过滤的应用领域（逗号分隔）
                rule_types: 过滤的规则类型（逗号分隔）
                tags: 过滤的标签（逗号分隔）
            
            Returns:
                详细的统计报告
            """
            try:
                # 确保初始化
                await self._ensure_initialized()
                
                # 构建过滤条件
                filter_conditions = {}
                if languages:
                    filter_conditions['languages'] = self._parse_list_param(languages)
                if domains:
                    filter_conditions['domains'] = self._parse_list_param(domains)
                if rule_types:
                    filter_conditions['rule_types'] = [RuleType(rt.strip()) for rt in rule_types.split(',') if rt.strip()]
                if tags:
                    filter_conditions['tags'] = self._parse_list_param(tags)
                
                # 获取统计信息
                stats = self.rule_engine.database.get_database_stats(**filter_conditions)
                
                # 构建标题
                if filter_conditions:
                    filter_desc = []
                    if filter_conditions.get('languages'):
                        filter_desc.append(f"语言: {', '.join(filter_conditions['languages'])}")
                    if filter_conditions.get('domains'):
                        filter_desc.append(f"领域: {', '.join(filter_conditions['domains'])}")
                    if filter_conditions.get('rule_types'):
                        filter_desc.append(f"类型: {', '.join([rt.value for rt in filter_conditions['rule_types']])}")
                    if filter_conditions.get('tags'):
                        filter_desc.append(f"标签: {', '.join(filter_conditions['tags'])}")
                    
                    title = f"📊 **CursorRules-MCP 规则库统计 (过滤条件: {'; '.join(filter_desc)})**"
                else:
                    title = "📊 **CursorRules-MCP 规则库统计**"
                
                result_text = f"""
{title}

**规则统计**:
- 总规则数: {stats['total_rules']}
- 活跃规则数: {stats['active_rules']}
- 版本总数: {stats['total_versions']}

**分类统计**:
- 支持语言: {stats['languages']} 种
- 应用领域: {stats['domains']} 个
- 规则类型: {stats['rule_types']} 种
- 标签总数: {stats['total_tags']} 个

**版本分布**:
"""
                for rule_id, version_count in list(stats['version_distribution'].items())[:5]:
                    result_text += f"- {rule_id}: {version_count} 个版本\n"
                
                if len(stats['version_distribution']) > 5:
                    result_text += f"- ... 还有 {len(stats['version_distribution']) - 5} 个规则\n"
                
                # 添加使用情况统计
                if 'usage_stats' in stats:
                    result_text += f"""
**使用情况**:
- 总使用次数: {stats['usage_stats'].get('total_usage', 0)}
- 平均成功率: {stats['usage_stats'].get('average_success_rate', 0):.1%}
- 最常用规则: {stats['usage_stats'].get('most_used_rule', '无')}
"""
                
                return result_text
                
            except Exception as e:
                logger.error(f"获取统计信息时发生错误: {e}")
                return f"❌ 统计信息获取失败: {str(e)}"

        @self.mcp.tool()
        async def import_rules(
            content: str = "",
            file_path: str = "",
            format: str = "auto",
            validate: bool = True,
            merge: bool = False
        ) -> str:
            """导入规则（仅支持 content 参数）
            
            Args:
                content: 规则内容（必须提供）
                file_path: 规则文件路径（已废弃，不支持）
                format: 格式类型 (auto, markdown, yaml, json)
                validate: 是否验证规则
                merge: 是否合并重复规则
            
            Returns:
                导入结果报告（字符串）
            """
            try:
                await self._ensure_initialized()
                from .rule_import import UnifiedRuleImporter
                importer = UnifiedRuleImporter(save_to_database=True)

                # 只允许 content
                if not content:
                    return "❌ 必须通过 content 上传规则内容，不支持 file_path 参数"
                    if format == "auto":
                        if content.startswith('---'):
                            format = "markdown"
                        elif content.strip().startswith('{'):
                            format = "json"
                        else:
                            format = "yaml"
                    import tempfile
                    import os
                    try:
                        ext_map = {'markdown': '.md', 'yaml': '.yaml', 'json': '.json'}
                        ext = ext_map.get(format, '.txt')
                        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False, encoding='utf-8') as temp_file:
                            temp_file.write(content)
                            temp_path = temp_file.name
                        rules = await importer.import_rules_async([temp_path])
                        os.unlink(temp_path)
                        await self.rule_engine.reload()
                        if rules:
                            rule_ids = ', '.join(rule.rule_id for rule in rules)
                            return f"✅ 成功导入 {len(rules)} 条规则到数据库\n规则ID: {rule_ids}"
                        else:
                            return "⚠️ 未导入任何规则，请检查内容格式。"
                    except Exception as e:
                        return f"❌ 导入失败: {str(e)}"
            except Exception as e:
                logger.error(f"导入规则时发生错误: {e}")
                return f"❌ 导入失败: {str(e)}"
    
    def _setup_resources(self):
        """设置MCP资源"""
        
        @self.mcp.resource("cursorrules://rules/{rule_id}")
        async def get_rule_detail(rule_id: str) -> str:
            """获取特定规则的详细信息
            
            Args:
                rule_id: 规则ID
            
            Returns:
                规则的详细信息
            """
            try:
                # 确保初始化
                await self._ensure_initialized()
                
                # 获取规则
                rule = self.rule_engine.database.get_rule(rule_id)
                if not rule:
                    return f"❌ 未找到规则: {rule_id}"
                
                # 格式化规则详情
                detail_text = f"""
# {rule.name}

**ID**: {rule.rule_id}
**版本**: {rule.version}
**作者**: {rule.author}
**创建时间**: {rule.created_at}

## 描述
{rule.description}

## 分类信息
- **类型**: {rule.rule_type.value}
- **语言**: {', '.join(rule.languages) if rule.languages else '通用'}
- **领域**: {', '.join(rule.domains) if rule.domains else '通用'}
- **内容类型**: {', '.join([ct.value for ct in rule.content_types]) if rule.content_types else '通用'}
- **任务类型**: {', '.join([tt.value for tt in rule.task_types]) if rule.task_types else '通用'}
- **标签**: {', '.join(rule.tags)}

## 规则详情
"""
                
                for i, condition in enumerate(rule.rules, 1):
                    detail_text += f"""
### 规则 {i}: {condition.condition}
**指导原则**: {condition.guideline}
**优先级**: {condition.priority}/10
**强制性**: {'是' if condition.enforcement else '否'}

"""
                    if condition.examples:
                        detail_text += "**示例**:\n"
                        for j, example in enumerate(condition.examples, 1):
                            if isinstance(example, dict):
                                if example.get('good'):
                                    detail_text += f"✅ 良好示例:\n```\n{example['good']}\n```\n"
                                if example.get('bad'):
                                    detail_text += f"❌ 不良示例:\n```\n{example['bad']}\n```\n"
                                if example.get('explanation'):
                                    detail_text += f"💡 说明: {example['explanation']}\n"
                            detail_text += "\n"
                
                # 添加验证信息
                if rule.validation:
                    detail_text += f"""
## 验证配置
- **验证工具**: {', '.join(rule.validation.tools) if rule.validation.tools else '无'}
- **严重程度**: {rule.validation.severity.value}
- **自动修复**: {'启用' if rule.validation.auto_fix else '禁用'}
- **超时时间**: {rule.validation.timeout} 秒
"""
                
                # 添加使用统计
                detail_text += f"""
## 使用统计
- **使用次数**: {rule.usage_count}
- **成功率**: {rule.success_rate:.1%}
- **状态**: {'活跃' if rule.active else '非活跃'}
"""
                
                return detail_text
                
            except Exception as e:
                logger.error(f"获取规则详情时发生错误: {e}")
                return f"❌ 获取规则详情失败: {str(e)}"

        @self.mcp.resource("cursorrules://rules/list")
        async def list_all_rules() -> str:
            """列出所有可用规则的摘要
            
            Returns:
                所有规则的列表
            """
            try:
                # 确保初始化
                await self._ensure_initialized()
                
                # 获取所有规则
                all_rules = list(self.rule_engine.database.rules.values())
                
                if not all_rules:
                    return "❌ 规则库为空"
                
                # 格式化规则列表
                list_text = f"""
# CursorRules-MCP 规则库目录

**总计**: {len(all_rules)} 条规则

## 规则列表

"""
                
                # 按类型分组
                rules_by_type = {}
                for rule in all_rules:
                    rule_type = rule.rule_type.value
                    if rule_type not in rules_by_type:
                        rules_by_type[rule_type] = []
                    rules_by_type[rule_type].append(rule)
                
                for rule_type, rules in rules_by_type.items():
                    list_text += f"### {rule_type.title()} 类规则 ({len(rules)} 条)\n\n"
                    
                    for rule in rules:
                        list_text += f"- **{rule.name}** (`{rule.rule_id}`)\n"
                        list_text += f"  - 版本: {rule.version}\n"
                        list_text += f"  - 语言: {', '.join(rule.languages) if rule.languages else '通用'}\n"
                        list_text += f"  - 领域: {', '.join(rule.domains) if rule.domains else '通用'}\n"
                        list_text += f"  - 描述: {rule.description[:100]}{'...' if len(rule.description) > 100 else ''}\n"
                        list_text += f"  - 使用次数: {rule.usage_count}\n\n"
                
                return list_text
                
            except Exception as e:
                logger.error(f"列出规则时发生错误: {e}")
                return f"❌ 列出规则失败: {str(e)}"

    def _parse_list_param(self, param: str) -> Optional[List[str]]:
        """解析逗号分隔的参数"""
        if not param or not param.strip():
            return None
        return [item.strip() for item in param.split(',') if item.strip()]

    def _infer_languages_from_path(self, file_path: str) -> List[str]:
        """从文件路径推断编程语言"""
        if not file_path:
            return []
            
        path = Path(file_path)
        ext = path.suffix.lower()
        
        # 文件扩展名到语言的映射
        ext_mapping = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'zsh',
            '.fish': 'fish',
            '.sql': 'sql',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.rst': 'rst',
            '.tex': 'latex',
            '.r': 'r',
            '.R': 'r',
            '.m': 'matlab',
            '.jl': 'julia',
            '.pl': 'perl',
            '.lua': 'lua',
            '.vim': 'vim'
        }
        
        language = ext_mapping.get(ext)
        return [language] if language else []

    def _infer_content_types(self, content: str, file_path: str) -> List[str]:
        """从内容和文件路径推断内容类型"""
        content_types = []
        
        # 基于文件路径推断
        if file_path:
            path = Path(file_path)
            
            # 文档文件
            if path.suffix.lower() in ['.md', '.rst', '.txt', '.doc', '.docx', '.pdf']:
                content_types.append('documentation')
            
            # 配置文件
            elif path.suffix.lower() in ['.yaml', '.yml', '.json', '.toml', '.ini', '.conf', '.config']:
                content_types.append('configuration')
            
            # 数据文件
            elif path.suffix.lower() in ['.csv', '.xlsx', '.xls', '.xml', '.jsonl']:
                content_types.append('data')
            
            # 代码文件
            elif path.suffix.lower() in ['.py', '.js', '.ts', '.cpp', '.java', '.go', '.rs', '.php', '.rb']:
                content_types.append('code')
        
        # 基于内容推断
        content_lower = content.lower()
        
        # 检查是否包含代码特征
        code_indicators = ['def ', 'function ', 'class ', 'import ', 'include ', 'if (', 'for (', 'while (']
        if any(indicator in content_lower for indicator in code_indicators):
            if 'code' not in content_types:
                content_types.append('code')
        
        # 检查是否包含文档特征
        doc_indicators = ['# ', '## ', '### ', '====', '----', 'introduction', 'overview', 'description']
        if any(indicator in content_lower for indicator in doc_indicators):
            if 'documentation' not in content_types:
                content_types.append('documentation')
        
        # 如果没有推断出类型，默认为代码
        if not content_types:
            content_types.append('code')
        
        return content_types

    def _format_search_conditions(self, search_filter: SearchFilter) -> str:
        """格式化搜索条件为可读字符串"""
        conditions = []
        
        if search_filter.languages:
            conditions.append(f"语言({', '.join(search_filter.languages)})")
        
        if search_filter.domains:
            conditions.append(f"领域({', '.join(search_filter.domains)})")
        
        if search_filter.tags:
            conditions.append(f"标签({', '.join(search_filter.tags)})")
        
        if search_filter.rule_types:
            conditions.append(f"类型({', '.join([rt.value for rt in search_filter.rule_types])})")
        
        if search_filter.content_types:
            conditions.append(f"内容类型({', '.join(search_filter.content_types)})")
        
        return ', '.join(conditions) if conditions else '无特定条件'

    async def _ensure_initialized(self):
        """确保规则引擎已初始化"""
        if not self._initialized:
            await self.rule_engine.initialize()
            self._initialized = True
            logger.info("规则引擎初始化完成")

    def run(self):
        """运行MCP服务器"""
        try:
            # 运行FastMCP服务器
            self.mcp.run()
            
        except Exception as e:
            logger.error(f"服务器运行时发生错误: {e}")
            raise


async def main():
    """主函数"""
    try:
        from .config import get_config_manager
        
        # 获取配置
        config_manager = get_config_manager()
        config = config_manager.config
        
        print("🚀 启动 CursorRules-MCP 服务器...")
        print(f"📂 规则目录: {config.rules_dir}")
        print(f"🔧 调试模式: {'开启' if config.debug else '关闭'}")
        
        # 创建服务器
        server = CursorRulesMCPServer(config.rules_dir)
        
        # 启动服务器
        await server.run()
        
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())