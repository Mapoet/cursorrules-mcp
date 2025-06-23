#!/usr/bin/env python3
"""
CursorRules-MCP 规则引擎核心模块
提供规则管理、搜索、验证和应用的完整功能

Author: Mapoet
Institution: NUS/STAR
Date: 2025-01-23
License: MIT
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import re

from .models import (
    CursorRule, RuleType, ContentType, TaskType, ValidationSeverity,
    RuleCondition, RuleApplication, RuleValidation, MCPContext,
    ValidationIssue, ValidationResult, ApplicableRule, EnhancedPrompt,
    SearchFilter, KnowledgeItem, KnowledgeType
)

logger = logging.getLogger(__name__)

# 导入数据库模块
from .database import get_rule_database, initialize_rule_database

class RuleEngine:
    """
    CursorRules 规则引擎核心类
    
    负责规则的加载、搜索、匹配、验证和应用逻辑
    """
    
    def __init__(self, rules_dir: str = "data/rules"):
        """初始化规则引擎
        
        Args:
            rules_dir: 规则目录路径
        """
        self.rules_dir = Path(rules_dir)
        self.rules: Dict[str, CursorRule] = {}
        self.tag_index: Dict[str, Set[str]] = {}  # tag -> rule_ids
        self.language_index: Dict[str, Set[str]] = {}  # language -> rule_ids
        self.domain_index: Dict[str, Set[str]] = {}  # domain -> rule_ids
        self.loaded_at: Optional[datetime] = None
        
        # 数据库实例
        self.database = None
        
        # 验证工具映射
        self.validation_tools = {
            'python': ['flake8', 'pylint', 'black', 'mypy'],
            'cpp': ['cppcheck', 'clang-tidy'],
            'javascript': ['eslint', 'prettier'],
            'markdown': ['markdownlint'],
            'yaml': ['yamllint']
        }
    
    async def initialize(self) -> None:
        """异步初始化规则引擎"""
        # 初始化数据库
        self.database = get_rule_database()
        await self.database.initialize()
        
        await self.load_rules()
        self.build_indexes()
        logger.info(f"规则引擎初始化完成，加载了 {len(self.rules)} 条规则")
    
    async def load_rules(self) -> None:
        """加载所有规则文件"""
        self.rules.clear()
        
        if not self.rules_dir.exists():
            logger.warning(f"规则目录不存在: {self.rules_dir}")
            return
        
        # 加载JSON格式规则
        json_files = list(self.rules_dir.rglob("*.json"))
        for json_file in json_files:
            await self._load_json_rules(json_file)
        
        # 加载YAML格式规则
        yaml_files = list(self.rules_dir.rglob("*.yaml")) + list(self.rules_dir.rglob("*.yml"))
        for yaml_file in yaml_files:
            await self._load_yaml_rules(yaml_file)
        
        self.loaded_at = datetime.utcnow()
        logger.info(f"从 {len(json_files) + len(yaml_files)} 个文件加载了 {len(self.rules)} 条规则")
    
    async def _load_json_rules(self, file_path: Path) -> None:
        """加载JSON格式的规则文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if isinstance(data, list):
                    # 多个规则的JSON文件
                    for rule_data in data:
                        rule = await self._parse_rule_data(rule_data, file_path)
                        if rule:
                            self.rules[rule.rule_id] = rule
                elif isinstance(data, dict):
                    # 单个规则的JSON文件
                    rule = await self._parse_rule_data(data, file_path)
                    if rule:
                        self.rules[rule.rule_id] = rule
                        
        except Exception as e:
            logger.error(f"加载JSON规则文件失败 {file_path}: {e}")
    
    async def _load_yaml_rules(self, file_path: Path) -> None:
        """加载YAML格式的规则文件"""
        try:
            import yaml
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
                if isinstance(data, list):
                    for rule_data in data:
                        rule = await self._parse_rule_data(rule_data, file_path)
                        if rule:
                            self.rules[rule.rule_id] = rule
                elif isinstance(data, dict):
                    rule = await self._parse_rule_data(data, file_path)
                    if rule:
                        self.rules[rule.rule_id] = rule
                        
        except ImportError:
            logger.warning("PyYAML未安装，跳过YAML文件加载")
        except Exception as e:
            logger.error(f"加载YAML规则文件失败 {file_path}: {e}")
    
    async def _parse_rule_data(self, data: Dict[str, Any], source_file: Path) -> Optional[CursorRule]:
        """解析规则数据为CursorRule对象"""
        try:
            # 数据转换和适配
            adapted_data = await self._adapt_rule_data(data)
            rule = CursorRule(**adapted_data)
            
            # 添加源文件信息
            if hasattr(rule, 'metadata'):
                rule.metadata = rule.metadata or {}
                rule.metadata['source_file'] = str(source_file)
            
            return rule
            
        except Exception as e:
            logger.error(f"解析规则数据失败 {source_file}: {e}")
            return None
    
    async def _adapt_rule_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """适配不同格式的规则数据"""
        adapted = data.copy()
        
        # 适配旧格式的规则数据
        if 'applicable_to' in data:
            old_applicable = data['applicable_to']
            adapted['languages'] = old_applicable.get('languages', [])
            adapted['domains'] = old_applicable.get('domains', [])
            adapted['content_types'] = [ContentType(ct) for ct in old_applicable.get('content_types', [])]
        
        # 适配规则内容格式
        if 'rule_content' in data:
            rule_content = data['rule_content']
            conditions = []
            
            if 'guideline' in rule_content:
                condition = RuleCondition(
                    condition="default",
                    guideline=rule_content['guideline'],
                    priority=data.get('priority', 5),
                    examples=rule_content.get('examples', [])
                )
                conditions.append(condition)
            
            adapted['rules'] = conditions
        
        # 适配验证规则
        if 'validation' in data:
            val_data = data['validation']
            adapted['validation'] = RuleValidation(
                tools=val_data.get('tools', []),
                severity=ValidationSeverity(val_data.get('severity', 'warning'))
            )
        
        # 确保必需字段存在
        if 'rule_type' not in adapted:
            adapted['rule_type'] = self._infer_rule_type(data)
        
        return adapted
    
    def _infer_rule_type(self, data: Dict[str, Any]) -> RuleType:
        """根据规则数据推断规则类型"""
        category = data.get('category', '').lower()
        
        if category in ['style', 'formatting']:
            return RuleType.STYLE
        elif category in ['content', 'semantic']:
            return RuleType.CONTENT
        elif category in ['format', 'structure']:
            return RuleType.FORMAT
        elif category in ['performance']:
            return RuleType.PERFORMANCE
        elif category in ['security']:
            return RuleType.SECURITY
        else:
            return RuleType.CONTENT
    
    def build_indexes(self) -> None:
        """构建搜索索引"""
        self.tag_index.clear()
        self.language_index.clear()
        self.domain_index.clear()
        
        for rule_id, rule in self.rules.items():
            # 构建标签索引
            for tag in rule.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = set()
                self.tag_index[tag].add(rule_id)
            
            # 构建语言索引
            for language in rule.languages:
                if language not in self.language_index:
                    self.language_index[language] = set()
                self.language_index[language].add(rule_id)
            
            # 构建领域索引
            for domain in rule.domains:
                if domain not in self.domain_index:
                    self.domain_index[domain] = set()
                self.domain_index[domain].add(rule_id)
    
    async def search_rules(self, search_filter: SearchFilter) -> List[ApplicableRule]:
        """搜索匹配的规则
        
        Args:
            search_filter: 搜索过滤器
            
        Returns:
            按相关度排序的规则列表
        """
        candidate_rule_ids = set(self.rules.keys())
        scores = {}
        
        # 应用过滤条件
        if search_filter.languages:
            language_candidates = set()
            for lang in search_filter.languages:
                language_candidates.update(self.language_index.get(lang, set()))
            candidate_rule_ids &= language_candidates
        
        if search_filter.domains:
            domain_candidates = set()
            for domain in search_filter.domains:
                domain_candidates.update(self.domain_index.get(domain, set()))
            candidate_rule_ids &= domain_candidates
        
        if search_filter.tags:
            tag_candidates = set()
            for tag in search_filter.tags:
                tag_candidates.update(self.tag_index.get(tag, set()))
            candidate_rule_ids &= tag_candidates
        
        # 计算相关度分数
        for rule_id in candidate_rule_ids:
            rule = self.rules[rule_id]
            score = await self._calculate_rule_score(rule, search_filter)
            scores[rule_id] = score
        
        # 排序并返回结果
        sorted_rules = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for rule_id, score in sorted_rules[:search_filter.limit]:
            rule = self.rules[rule_id]
            applicable_rule = ApplicableRule(
                rule=rule,
                relevance_score=score,
                matched_conditions=await self._get_matched_conditions(rule, search_filter),
                application_context=await self._get_application_context(rule, search_filter)
            )
            results.append(applicable_rule)
        
        return results
    
    async def _calculate_rule_score(self, rule: CursorRule, search_filter: SearchFilter) -> float:
        """计算规则的相关度分数"""
        score = 0.0
        
        # 基础分数：规则优先级
        if rule.rules:
            avg_priority = sum(r.priority for r in rule.rules) / len(rule.rules)
            score += avg_priority * 0.1
        
        # 文本匹配分数
        if search_filter.query:
            query_lower = search_filter.query.lower()
            if query_lower in rule.name.lower():
                score += 3.0
            if query_lower in rule.description.lower():
                score += 2.0
            for condition in rule.rules:
                if query_lower in condition.guideline.lower():
                    score += 1.5
        
        # 标签匹配分数
        if search_filter.tags:
            matching_tags = set(search_filter.tags) & set(rule.tags)
            score += len(matching_tags) * 2.0
        
        # 语言匹配分数
        if search_filter.languages:
            matching_languages = set(search_filter.languages) & set(rule.languages)
            score += len(matching_languages) * 1.5
        
        # 领域匹配分数
        if search_filter.domains:
            matching_domains = set(search_filter.domains) & set(rule.domains)
            score += len(matching_domains) * 1.5
        
        # 内容类型匹配分数
        if search_filter.content_types:
            rule_content_types = {ct.value for ct in rule.content_types}
            matching_content_types = set(search_filter.content_types) & rule_content_types
            score += len(matching_content_types) * 1.0
        
        # 成功率加权
        score *= (0.5 + rule.success_rate * 0.5)
        
        return score
    
    async def _get_matched_conditions(self, rule: CursorRule, search_filter: SearchFilter) -> List[str]:
        """获取匹配的条件列表"""
        matched = []
        
        if search_filter.languages and set(search_filter.languages) & set(rule.languages):
            matched.append("language_match")
        
        if search_filter.domains and set(search_filter.domains) & set(rule.domains):
            matched.append("domain_match")
        
        if search_filter.tags and set(search_filter.tags) & set(rule.tags):
            matched.append("tag_match")
        
        return matched
    
    async def _get_application_context(self, rule: CursorRule, search_filter: SearchFilter) -> Dict[str, Any]:
        """获取应用上下文信息"""
        return {
            "search_query": search_filter.query,
            "matched_languages": list(set(search_filter.languages or []) & set(rule.languages)),
            "matched_domains": list(set(search_filter.domains or []) & set(rule.domains)),
            "matched_tags": list(set(search_filter.tags or []) & set(rule.tags))
        }
    
    async def validate_content(self, content: str, context: MCPContext) -> ValidationResult:
        """验证内容是否符合规则
        
        Args:
            content: 要验证的内容
            context: MCP上下文
            
        Returns:
            验证结果
        """
        issues = []
        suggestions = []
        applied_rules = []
        
        # 获取适用的规则
        search_filter = SearchFilter(
            languages=context.languages,
            domains=context.domains,
            content_types=context.content_types,
            limit=50
        )
        
        applicable_rules = await self.search_rules(search_filter)
        
        # 对每个规则进行验证
        for applicable_rule in applicable_rules:
            rule = applicable_rule.rule
            
            # 执行规则验证
            rule_issues = await self._validate_rule(content, rule, context)
            issues.extend(rule_issues)
            
            if rule_issues:
                applied_rules.append(rule.rule_id)
            
            # 生成改进建议
            rule_suggestions = await self._generate_suggestions(content, rule, rule_issues)
            suggestions.extend(rule_suggestions)
        
        # 计算总体分数
        total_score = self._calculate_validation_score(issues)
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            score=total_score,
            issues=issues,
            suggestions=suggestions,
            applied_rules=applied_rules,
            validation_time=datetime.utcnow()
        )
    
    async def _validate_rule(self, content: str, rule: CursorRule, context: MCPContext) -> List[ValidationIssue]:
        """对单个规则执行验证"""
        issues = []
        
        for condition in rule.rules:
            # 检查条件是否适用
            if not await self._is_condition_applicable(condition, context):
                continue
            
            # 执行具体验证
            condition_issues = await self._validate_condition(content, condition, rule)
            issues.extend(condition_issues)
        
        return issues
    
    async def _is_condition_applicable(self, condition: RuleCondition, context: MCPContext) -> bool:
        """检查条件是否适用于当前上下文"""
        # 基于条件的触发条件判断
        condition_str = condition.condition.lower()
        
        # 检查文件类型匹配
        if context.file_path:
            file_ext = Path(context.file_path).suffix.lower()
            if any(lang in condition_str for lang in ['python', 'py']) and file_ext != '.py':
                return False
            if any(lang in condition_str for lang in ['cpp', 'c++']) and file_ext not in ['.cpp', '.cc', '.cxx']:
                return False
        
        # 检查内容类型匹配
        if context.content_types:
            content_type_names = [ct.lower() for ct in context.content_types]
            if 'function' in condition_str and 'code' not in content_type_names:
                return False
        
        return True
    
    async def _validate_condition(self, content: str, condition: RuleCondition, rule: CursorRule) -> List[ValidationIssue]:
        """验证特定条件"""
        issues = []
        
        # 基于规则类型执行不同的验证逻辑
        if rule.rule_type == RuleType.STYLE:
            issues.extend(await self._validate_style_rule(content, condition, rule))
        elif rule.rule_type == RuleType.CONTENT:
            issues.extend(await self._validate_content_rule(content, condition, rule))
        elif rule.rule_type == RuleType.FORMAT:
            issues.extend(await self._validate_format_rule(content, condition, rule))
        elif rule.rule_type == RuleType.PERFORMANCE:
            issues.extend(await self._validate_performance_rule(content, condition, rule))
        elif rule.rule_type == RuleType.SECURITY:
            issues.extend(await self._validate_security_rule(content, condition, rule))
        
        return issues
    
    async def _validate_style_rule(self, content: str, condition: RuleCondition, rule: CursorRule) -> List[ValidationIssue]:
        """验证代码风格规则"""
        issues = []
        
        # 示例：检查行长度
        if 'line length' in condition.guideline.lower() or 'line_length' in rule.tags:
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if len(line) > 79:  # PEP8标准
                    issues.append(ValidationIssue(
                        line_number=i,
                        column_number=80,
                        message=f"行长度 {len(line)} 超过79字符限制",
                        severity=rule.validation.severity,
                        rule_id=rule.rule_id,
                        suggestion=f"将长行拆分为多行"
                    ))
        
        # 示例：检查函数命名
        if 'function' in condition.condition.lower() and any(lang in rule.languages for lang in ['python']):
            # 简单的函数名检查
            import re
            function_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
            matches = re.finditer(function_pattern, content)
            
            for match in matches:
                func_name = match.group(1)
                if not func_name.islower() or '__' in func_name:
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append(ValidationIssue(
                        line_number=line_num,
                        column_number=match.start() - content.rfind('\n', 0, match.start()),
                        message=f"函数名 '{func_name}' 不符合snake_case命名规范",
                        severity=rule.validation.severity,
                        rule_id=rule.rule_id,
                        suggestion="使用小写字母和下划线的命名方式"
                    ))
        
        return issues
    
    async def _validate_content_rule(self, content: str, condition: RuleCondition, rule: CursorRule) -> List[ValidationIssue]:
        """验证内容规则"""
        issues = []
        
        # 示例：检查docstring
        if 'docstring' in condition.guideline.lower() and 'python' in rule.languages:
            import re
            # 查找函数定义
            function_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\):'
            matches = re.finditer(function_pattern, content)
            
            for match in matches:
                func_name = match.group(1)
                func_start = match.end()
                
                # 检查函数后是否有docstring
                next_lines = content[func_start:].split('\n')[:5]  # 检查前5行
                has_docstring = False
                
                for line in next_lines:
                    stripped = line.strip()
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        has_docstring = True
                        break
                    elif stripped and not stripped.startswith('#'):
                        break  # 遇到代码行，停止检查
                
                if not has_docstring and not func_name.startswith('_'):
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append(ValidationIssue(
                        line_number=line_num,
                        column_number=0,
                        message=f"公共函数 '{func_name}' 缺少docstring",
                        severity=rule.validation.severity,
                        rule_id=rule.rule_id,
                        suggestion="添加描述函数功能、参数和返回值的docstring"
                    ))
        
        return issues
    
    async def _validate_format_rule(self, content: str, condition: RuleCondition, rule: CursorRule) -> List[ValidationIssue]:
        """验证格式规则"""
        issues = []
        
        # 示例：检查markdown文档结构
        if 'markdown' in rule.languages and 'structure' in condition.guideline.lower():
            lines = content.split('\n')
            has_title = False
            
            for i, line in enumerate(lines[:10], 1):  # 检查前10行
                if line.startswith('# '):
                    has_title = True
                    break
            
            if not has_title:
                issues.append(ValidationIssue(
                    line_number=1,
                    column_number=0,
                    message="文档缺少主标题（# 标题）",
                    severity=rule.validation.severity,
                    rule_id=rule.rule_id,
                    suggestion="在文档开头添加主标题"
                ))
        
        return issues
    
    async def _validate_performance_rule(self, content: str, condition: RuleCondition, rule: CursorRule) -> List[ValidationIssue]:
        """验证性能规则"""
        issues = []
        
        # 示例：检查循环优化
        if 'optimization' in condition.guideline.lower() and any(lang in rule.languages for lang in ['python', 'cpp']):
            # 简单检查：查找可能的性能问题
            if 'for' in content and 'range(len(' in content:
                import re
                pattern = r'for\s+\w+\s+in\s+range\(len\('
                matches = re.finditer(pattern, content)
                
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append(ValidationIssue(
                        line_number=line_num,
                        column_number=match.start() - content.rfind('\n', 0, match.start()),
                        message="建议使用enumerate()替代range(len())",
                        severity=ValidationSeverity.WARNING,
                        rule_id=rule.rule_id,
                        suggestion="使用 'for i, item in enumerate(list):' 替代 'for i in range(len(list)):'"
                    ))
        
        return issues
    
    async def _validate_security_rule(self, content: str, condition: RuleCondition, rule: CursorRule) -> List[ValidationIssue]:
        """验证安全规则"""
        issues = []
        
        # 示例：检查SQL注入风险
        if 'sql' in condition.guideline.lower() or 'security' in rule.tags:
            dangerous_patterns = [
                r'execute\s*\(\s*["\'][^"\']*%[^"\']*["\']',  # SQL字符串拼接
                r'cursor\.execute\s*\(\s*f["\']',  # f-string in SQL
            ]
            
            for pattern in dangerous_patterns:
                import re
                matches = re.finditer(pattern, content, re.IGNORECASE)
                
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append(ValidationIssue(
                        line_number=line_num,
                        column_number=match.start() - content.rfind('\n', 0, match.start()),
                        message="潜在的SQL注入风险",
                        severity=ValidationSeverity.ERROR,
                        rule_id=rule.rule_id,
                        suggestion="使用参数化查询替代字符串拼接"
                    ))
        
        return issues
    
    async def _generate_suggestions(self, content: str, rule: CursorRule, issues: List[ValidationIssue]) -> List[str]:
        """基于规则和问题生成改进建议"""
        suggestions = []
        
        if not issues:
            return suggestions
        
        # 基于问题类型生成建议
        issue_types = set(issue.message.split()[0] for issue in issues)
        
        for issue_type in issue_types:
            if issue_type in ['行长度', 'Line']:
                suggestions.append("考虑使用IDE的自动格式化功能，如black for Python")
            elif issue_type in ['函数名', 'Function']:
                suggestions.append("参考PEP8命名规范，使用描述性的函数名")
            elif issue_type in ['缺少', 'Missing']:
                suggestions.append("添加完整的文档字符串，提高代码可维护性")
        
        # 基于规则类型添加通用建议
        if rule.rule_type == RuleType.STYLE:
            suggestions.append("配置代码格式化工具自动修复风格问题")
        elif rule.rule_type == RuleType.PERFORMANCE:
            suggestions.append("考虑使用性能分析工具识别瓶颈")
        elif rule.rule_type == RuleType.SECURITY:
            suggestions.append("使用安全代码审查工具进行深度检查")
        
        return list(set(suggestions))  # 去重
    
    def _calculate_validation_score(self, issues: List[ValidationIssue]) -> float:
        """计算验证分数"""
        if not issues:
            return 100.0
        
        # 根据问题严重程度计算扣分
        deduction = 0.0
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                deduction += 10.0
            elif issue.severity == ValidationSeverity.WARNING:
                deduction += 5.0
            elif issue.severity == ValidationSeverity.INFO:
                deduction += 1.0
        
        # 确保分数不低于0
        score = max(0.0, 100.0 - deduction)
        return score
    
    async def enhance_prompt(self, base_prompt: str, applicable_rules: List[ApplicableRule]) -> EnhancedPrompt:
        """增强提示词，注入相关规则
        
        Args:
            base_prompt: 基础提示词
            applicable_rules: 适用的规则列表
            
        Returns:
            增强后的提示词
        """
        if not applicable_rules:
            return EnhancedPrompt(
                original_prompt=base_prompt,
                enhanced_prompt=base_prompt,
                injected_rules=[],
                context_info={}
            )
        
        # 按优先级排序规则
        sorted_rules = sorted(applicable_rules, key=lambda x: x.relevance_score, reverse=True)
        
        # 构建规则注入文本
        rules_text = "\n## 适用规则指导\n\n"
        injected_rules = []
        
        for i, applicable_rule in enumerate(sorted_rules[:5], 1):  # 最多注入5条规则
            rule = applicable_rule.rule
            rules_text += f"### 规则 {i}: {rule.name}\n"
            rules_text += f"**描述**: {rule.description}\n"
            
            # 添加最相关的条件
            for condition in rule.rules[:2]:  # 最多2个条件
                rules_text += f"**指导**: {condition.guideline}\n"
                
                # 添加示例
                if condition.examples:
                    example = condition.examples[0]
                    if isinstance(example, dict) and 'good' in example:
                        rules_text += f"**示例**:\n```\n{example['good']}\n```\n"
            
            rules_text += "\n"
            injected_rules.append(rule.rule_id)
        
        # 构建增强提示词
        enhanced_prompt = f"{base_prompt}\n\n{rules_text}"
        enhanced_prompt += "\n请严格遵循上述规则进行输出。\n"
        
        return EnhancedPrompt(
            original_prompt=base_prompt,
            enhanced_prompt=enhanced_prompt,
            injected_rules=injected_rules,
            context_info={
                "total_rules": len(sorted_rules),
                "injected_rules_count": len(injected_rules),
                "highest_relevance": sorted_rules[0].relevance_score if sorted_rules else 0.0
            }
        )
    
    async def get_rule_by_id(self, rule_id: str) -> Optional[CursorRule]:
        """根据ID获取规则"""
        return self.rules.get(rule_id)
    
    async def get_available_tags(self) -> Dict[str, List[str]]:
        """获取所有可用标签，按类别分组"""
        all_tags = set()
        for rule in self.rules.values():
            all_tags.update(rule.tags)
        
        # 按类别分组标签
        categories = {
            "编程语言": ["python", "cpp", "fortran", "shell", "javascript", "typescript", "java", "go"],
            "领域": ["meteorology", "ionosphere", "surveying", "oceanography", "geophysics", "astronomy"],
            "任务类型": ["coding", "documentation", "analysis", "visualization", "testing"],
            "质量类型": ["style", "performance", "security", "readability", "maintainability"],
            "内容类型": ["code", "documentation", "data_interface", "algorithm", "configuration"]
        }
        
        result = {}
        for category, category_tags in categories.items():
            result[category] = [tag for tag in category_tags if tag in all_tags]
        
        # 添加其他未分类的标签
        categorized_tags = set()
        for tags in result.values():
            categorized_tags.update(tags)
        
        other_tags = all_tags - categorized_tags
        if other_tags:
            result["其他"] = sorted(list(other_tags))
        
        return result
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取规则引擎统计信息"""
        return {
            "total_rules": len(self.rules),
            "rules_by_type": {
                rule_type.value: len([r for r in self.rules.values() if r.rule_type == rule_type])
                for rule_type in RuleType
            },
            "rules_by_language": {
                lang: len(rule_ids) 
                for lang, rule_ids in self.language_index.items()
            },
            "rules_by_domain": {
                domain: len(rule_ids)
                for domain, rule_ids in self.domain_index.items()
            },
            "total_tags": len(self.tag_index),
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "average_success_rate": sum(r.success_rate for r in self.rules.values()) / len(self.rules) if self.rules else 0.0
        }