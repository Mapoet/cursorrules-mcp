"""
多格式规则导入模块

支持从Markdown、YAML、JSON格式导入规则

Author: Mapoet
Date: 2025-01-23
License: MIT
"""

import json
import yaml
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone
import logging
import os
import requests
from urllib.parse import urlparse

try:
    import frontmatter
except ImportError:
    frontmatter = None
    logging.warning("python-frontmatter not installed. Markdown frontmatter parsing will be limited.")

from .models import (
    CursorRule, RuleType, ContentType, TaskType, ValidationSeverity,
    RuleCondition, RuleApplication, RuleValidation
)
from .database import RuleDatabase

logger = logging.getLogger(__name__)

__all__ = ['YamlRuleParser', 'RuleImportError', 'UnifiedRuleImporter']

class RuleImportError(Exception):
    """规则导入过程中的错误"""
    pass

class RuleParser(ABC):
    """规则解析器抽象基类"""
    
    def __init__(self, db: RuleDatabase):
        """
        初始化规则解析器
        
        Args:
            db: 规则数据库实例
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """检查是否能解析指定文件"""
        pass
    
    @abstractmethod
    def parse(self, file_path: Path) -> List[CursorRule]:
        """解析文件并返回规则列表"""
        pass


class MarkdownRuleParser(RuleParser):
    """Markdown格式规则解析器"""
    
    def __init__(self, db: RuleDatabase):
        """
        初始化Markdown规则解析器
        
        Args:
            db: 规则数据库实例
        """
        super().__init__(db)
    
    def can_parse(self, file_path: Path) -> bool:
        """检查是否为Markdown文件"""
        return file_path.suffix.lower() in ['.md', '.markdown']
    
    def parse(self, file_path: Path) -> List[CursorRule]:
        """解析Markdown文件"""
        if not frontmatter:
            raise ImportError("需要安装python-frontmatter包来解析Markdown格式规则")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # 从frontmatter提取元数据
            metadata = post.metadata
            content = post.content
            
            # 验证必需字段
            if 'rule_id' not in metadata:
                raise ValueError(f"Markdown文件缺少rule_id字段: {file_path}")
            
            if 'name' not in metadata:
                raise ValueError(f"Markdown文件缺少name字段: {file_path}")
            
            # 解析内容部分
            parsed_content = self._parse_markdown_content(content)
            
            # 构建规则对象
            rule_data = self._build_rule_data(metadata, parsed_content, file_path)
            rule = self._create_cursor_rule(rule_data)
            
            return [rule]
            
        except Exception as e:
            logger.error(f"解析Markdown文件失败 {file_path}: {e}")
            raise
    
    def _parse_markdown_content(self, content: str) -> Dict[str, Any]:
        """解析Markdown内容部分，保留全部层级结构"""
        sections = {}
        # 保存完整的内容
        sections['full_content'] = content
        # 提取所有章节结构
        sections['sections'] = self._extract_main_sections(content)
        # 提取不同的章节（兼容原有逻辑）
        patterns = {
            'guideline': r'##?\s*(?:指导原则|Guideline|Guidelines?|规则|Rules?)\s*\n(.*?)(?=\n##|\n---|\Z)',
            'examples': r'##?\s*(?:示例|Examples?|样例)\s*\n(.*?)(?=\n##|\n---|\Z)',
            'description': r'##?\s*(?:描述|Description|说明)\s*\n(.*?)(?=\n##|\n---|\Z)',
            'bad_examples': r'##?\s*(?:错误示例|Bad Examples?|反例)\s*\n(.*?)(?=\n##|\n---|\Z)'
        }
        for section, pattern in patterns.items():
            match = re.search(pattern, content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
            if match:
                sections[section] = match.group(1).strip()
        # 提取代码示例
        examples = []
        if 'examples' in sections:
            examples_text = sections['examples']
            good_examples = re.findall(r'(?:好的|Good|正确).*?\n```(\w+)?\n(.*?)```', examples_text, re.DOTALL | re.IGNORECASE)
            bad_examples = re.findall(r'(?:坏的|Bad|错误).*?\n```(\w+)?\n(.*?)```', examples_text, re.DOTALL | re.IGNORECASE)
            if good_examples:
                for lang, code in good_examples:
                    examples.append({'good': code.strip(), 'explanation': '良好的代码示例'})
            if bad_examples:
                for i, (lang, code) in enumerate(bad_examples):
                    if i < len(examples):
                        examples[i]['bad'] = code.strip()
                    else:
                        examples.append({'bad': code.strip(), 'explanation': '错误的代码示例'})
        code_blocks = re.findall(r'```(\w+)?\n(.*?)```', content, re.DOTALL)
        for lang, code in code_blocks:
            if code.strip():
                examples.append({'code': code.strip(), 'language': lang or 'text', 'explanation': '代码示例'})
        sections['parsed_examples'] = examples
        return sections
    
    def _extract_main_sections(self, content: str) -> List[Dict[str, Any]]:
        """提取主要章节内容"""
        sections = []
        
        # 分割内容为行
        lines = content.split('\n')
        current_section = None
        section_lines = []
        
        for line in lines:
            # 检查是否是标题行
            heading_match = re.match(r'^(#{1,6})\s+(.+)', line)
            if heading_match:
                # 保存之前的章节
                if current_section and section_lines:
                    current_section['content'] = '\n'.join(section_lines).strip()
                    if current_section['content']:  # 只保存有内容的章节
                        sections.append(current_section)
                
                # 开始新章节
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                current_section = {
                    'level': level,
                    'title': title,
                    'content': ''
                }
                section_lines = []
            else:
                # 添加到当前章节内容
                if current_section:
                    section_lines.append(line)
        
        # 处理最后一个章节
        if current_section and section_lines:
            current_section['content'] = '\n'.join(section_lines).strip()
            if current_section['content']:
                sections.append(current_section)
        
        return sections
    
    def _split_content_intelligently(self, content: str, max_length: int = 2000) -> List[str]:
        """智能分割长内容为多个部分"""
        parts = []
        
        # 按章节分割
        sections = content.split('\n##')
        current_part = ""
        
        for i, section in enumerate(sections):
            if i > 0:
                section = '##' + section  # 恢复标题标记
            
            # 如果当前部分加上新章节会超长，先保存当前部分
            if current_part and len(current_part + section) > max_length:
                parts.append(current_part.strip())
                current_part = section
            else:
                current_part += '\n' + section if current_part else section
        
        # 添加最后一部分
        if current_part.strip():
            parts.append(current_part.strip())
        
        # 如果还是太长，按段落分割
        refined_parts = []
        for part in parts:
            if len(part) > max_length:
                # 按段落分割
                paragraphs = part.split('\n\n')
                current_para_part = ""
                
                for para in paragraphs:
                    if current_para_part and len(current_para_part + para) > max_length:
                        refined_parts.append(current_para_part.strip())
                        current_para_part = para
                    else:
                        current_para_part += '\n\n' + para if current_para_part else para
                
                if current_para_part.strip():
                    refined_parts.append(current_para_part.strip())
            else:
                refined_parts.append(part)
        
        return refined_parts if refined_parts else [content[:max_length] + "...[内容已截断]"]
    
    def _build_rule_data(self, metadata: Dict[str, Any], content: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """构建规则数据字典，保留sections结构"""
        rule_data = {
            'rule_id': metadata['rule_id'],
            'name': metadata['name'],
            'description': metadata.get('description', content.get('description', '')),
            'version': metadata.get('version', '1.0.0'),
            'author': metadata.get('author', 'Unknown'),
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        # 分类信息
        rule_data['rule_type'] = self._convert_rule_type(metadata.get('rule_type', metadata.get('type', 'content')))
        rule_data['languages'] = metadata.get('languages', [])
        rule_data['domains'] = metadata.get('domains', [])
        rule_data['task_types'] = self._convert_task_types(metadata.get('task_types', []))
        rule_data['content_types'] = self._convert_content_types(metadata.get('content_types', ['code']))
        rule_data['tags'] = metadata.get('tags', [])
        # 规则条件
        rules = []
        main_sections = content.get('main_sections', [])
        if main_sections:
            # 重新设计章节选择逻辑，确保核心规范内容不被遗漏
            core_sections = []
            
            # 首先选择所有重要的规范性章节（包括level 3）
            for section in main_sections:
                title = section['title'].lower()
                content_text = section['content']
                
                # 识别核心规范章节（不论级别）
                is_core_section = any(keyword in title for keyword in [
                    '结构规范', '写作规范', '引用规范', '图表规范', '数据呈现规范',
                    '标准论文结构', '章节编号', '语言要求', '句式规范',
                    '文献引用格式', '引用原则', '图片要求', '表格要求',
                    '数值表示', '统计分析', '质量检查清单', '内容检查', '格式检查', '学术规范检查'
                ])
                
                # 或者有足够内容的重要章节
                has_substantial_content = len(content_text) > 100
                is_important_level = section['level'] <= 3
                
                if (is_core_section or (has_substantial_content and is_important_level)):
                    core_sections.append(section)
            
            # 如果核心章节过多，优先选择最重要的
            if len(core_sections) > 15:  # 限制规则数量
                # 按重要性排序：规范类章节 > 长内容章节 > 其他
                def section_priority(sec):
                    title_lower = sec['title'].lower()
                    if any(kw in title_lower for kw in ['规范', 'structure', 'format', 'style']):
                        return 1  # 最高优先级
                    elif len(sec['content']) > 200:
                        return 2  # 中等优先级
                    else:
                        return 3  # 低优先级
                
                core_sections = sorted(core_sections, key=section_priority)[:15]
            
            # 为核心章节创建规则
            for i, section in enumerate(core_sections):
                rule_condition = {
                    'condition': f"{metadata.get('condition', 'main_rule')}_{section['level']}_{i+1}",
                    'guideline': f"**{section['title']}**\n\n{section['content']}",
                    'priority': metadata.get('priority', 8) - (section['level'] - 1),
                    'examples': [],
                    'pattern': metadata.get('pattern')
                }
                rules.append(rule_condition)
        
        # 如果没有章节或作为备用，创建完整内容规则
        if not rules:
            condition = metadata.get('condition', 'main_rule')
            guideline = content.get('guideline', metadata.get('guideline', ''))
            
            # 如果有完整内容，使用完整内容作为指导
            if 'full_content' in content and content['full_content'].strip():
                # 对于长内容，创建分段规则而不是单一超长规则
                full_content = content['full_content']
                if len(full_content) > 5000:  # 如果内容太长，分段处理
                    content_parts = self._split_content_intelligently(full_content)
                    for i, part in enumerate(content_parts):
                        rule_condition = {
                            'condition': f"{condition}_part_{i+1}",
                            'guideline': part,
                            'priority': metadata.get('priority', 8) - i,
                            'examples': [],
                            'pattern': metadata.get('pattern')
                        }
                        rules.append(rule_condition)
                else:
                    guideline = full_content
            
            # 如果还没有规则，创建基础规则
            if not rules:
                priority = metadata.get('priority', 8)
                examples = content.get('parsed_examples', [])
                pattern = metadata.get('pattern')
                
                rule_condition = {
                    'condition': condition,
                    'guideline': guideline,
                    'priority': priority,
                    'examples': examples,
                    'pattern': pattern
                }
                rules.append(rule_condition)
        
        # 添加代码示例到第一个规则
        if rules and content.get('parsed_examples'):
            rules[0]['examples'] = content['parsed_examples']
        
        rule_data['rules'] = rules
        
        # 应用范围
        rule_data['applies_to'] = {
            'file_patterns': metadata.get('file_patterns', []),
            'project_types': metadata.get('project_types', []),
            'contexts': metadata.get('contexts', [])
        }
        
        # 冲突和覆盖
        rule_data['conflicts_with'] = metadata.get('conflicts_with', [])
        rule_data['overrides'] = metadata.get('overrides', [])
        
        # 验证信息
        rule_data['validation'] = {
            'tools': metadata.get('validation_tools', metadata.get('tools', [])),
            'severity': metadata.get('severity', 'warning'),
            'auto_fix': metadata.get('auto_fix', False),
            'timeout': metadata.get('timeout', 30),
            'custom_config': metadata.get('custom_config', {})
        }
        
        # 元数据
        rule_data['active'] = metadata.get('active', True)
        rule_data['usage_count'] = metadata.get('usage_count', 0)
        rule_data['success_rate'] = metadata.get('success_rate', 0.0)
        
        # 新增：保留所有章节结构和完整正文
        rule_data['full_content'] = content.get('full_content', '')
        rule_data['sections'] = content.get('sections', [])
        
        return rule_data
    
    def _convert_rule_type(self, rule_type: str) -> RuleType:
        """转换规则类型"""
        type_mapping = {
            'style': RuleType.STYLE,
            'content': RuleType.CONTENT,
            'format': RuleType.FORMAT,
            'performance': RuleType.PERFORMANCE,
            'security': RuleType.SECURITY
        }
        return type_mapping.get(rule_type.lower(), RuleType.CONTENT)
    
    def _convert_task_types(self, task_types: List[str]) -> List[TaskType]:
        """转换任务类型"""
        type_mapping = {
            # 基础开发任务
            'data_analysis': TaskType.DATA_ANALYSIS,
            'visualization': TaskType.VISUALIZATION,
            'gui_development': TaskType.GUI_DEVELOPMENT,
            'http_service': TaskType.HTTP_SERVICE,
            'llm_mcp': TaskType.LLM_MCP,
            'numerical_computation': TaskType.NUMERICAL_COMPUTATION,
            'paper_writing': TaskType.PAPER_WRITING,
            'grant_application': TaskType.GRANT_APPLICATION,
            'software_design': TaskType.SOFTWARE_DESIGN,
            'code_generation': TaskType.CODE_GENERATION,
            'testing': TaskType.TESTING,
            'documentation': TaskType.DOCUMENTATION,
            'refactoring': TaskType.REFACTORING,
            'debugging': TaskType.DEBUGGING,
            'optimization': TaskType.OPTIMIZATION,
            'code_review': TaskType.CODE_REVIEW,
            
            # 专业文档编写任务
            'academic_writing': TaskType.ACADEMIC_WRITING,
            'academic_papers': TaskType.ACADEMIC_WRITING,
            'technical_reports': TaskType.TECHNICAL_REPORTS,
            'project_proposals': TaskType.PROJECT_PROPOSALS,
            'peer_review': TaskType.PEER_REVIEW,
            'review_guidelines': TaskType.PEER_REVIEW,
            'translation_services': TaskType.TRANSLATION_SERVICES,
            'translation': TaskType.TRANSLATION_SERVICES,
            'review_response': TaskType.REVIEW_RESPONSE,
            'scientific_writing': TaskType.SCIENTIFIC_WRITING,
            
            # 专业开发任务
            'scientific_computing': TaskType.SCIENTIFIC_COMPUTING,
            'hpc_computing': TaskType.HPC_COMPUTING,
            'machine_learning': TaskType.MACHINE_LEARNING,
            'database_storage': TaskType.DATABASE_STORAGE,
            'mcp_services': TaskType.MCP_SERVICES,
            
            # 科学研究任务
            'research_methodology': TaskType.RESEARCH_METHODOLOGY,
            'experimental_design': TaskType.EXPERIMENTAL_DESIGN,
            'statistical_analysis': TaskType.STATISTICAL_ANALYSIS,
            'data_validation': TaskType.DATA_VALIDATION
        }
        
        result = []
        for task_type in task_types:
            mapped_type = type_mapping.get(task_type.lower())
            if mapped_type and mapped_type not in result:
                result.append(mapped_type)
        
        return result or [TaskType.SOFTWARE_DESIGN]
    
    def _convert_content_types(self, content_types: List[str]) -> List[ContentType]:
        """转换内容类型"""
        type_mapping = {
            # 基础内容类型
            'code': ContentType.CODE,
            'documentation': ContentType.DOCUMENTATION,
            'data': ContentType.DATA,
            'algorithm': ContentType.ALGORITHM,
            'configuration': ContentType.CONFIGURATION,
            'data_interface': ContentType.DATA_INTERFACE,
            
            # 专业文档内容类型
            'academic_paper': ContentType.ACADEMIC_PAPER,
            'academic_papers': ContentType.ACADEMIC_PAPER,
            'technical_report': ContentType.TECHNICAL_REPORT,
            'technical_reports': ContentType.TECHNICAL_REPORT,
            'project_proposal': ContentType.PROJECT_PROPOSAL,
            'project_proposals': ContentType.PROJECT_PROPOSAL,
            'review_document': ContentType.REVIEW_DOCUMENT,
            'review_guidelines': ContentType.REVIEW_DOCUMENT,
            'peer_review': ContentType.REVIEW_DOCUMENT,
            'translation': ContentType.TRANSLATION,
            'translation_services': ContentType.TRANSLATION,
            'scientific_manuscript': ContentType.SCIENTIFIC_MANUSCRIPT,
            'scientific_writing': ContentType.SCIENTIFIC_MANUSCRIPT,
            
            # 专业领域内容
            'atmospheric_data': ContentType.ATMOSPHERIC_DATA,
            'atmospheric_science': ContentType.ATMOSPHERIC_DATA,
            'ionospheric_model': ContentType.IONOSPHERIC_MODEL,
            'ionospheric_physics': ContentType.IONOSPHERIC_MODEL,
            'geodetic_computation': ContentType.GEODETIC_COMPUTATION,
            'geodesy_surveying': ContentType.GEODETIC_COMPUTATION,
            'oceanographic_analysis': ContentType.OCEANOGRAPHIC_ANALYSIS,
            'oceanography': ContentType.OCEANOGRAPHIC_ANALYSIS,
            'geophysical_model': ContentType.GEOPHYSICAL_MODEL,
            'geophysics': ContentType.GEOPHYSICAL_MODEL,
            'climate_model': ContentType.CLIMATE_MODEL,
            'climate_science': ContentType.CLIMATE_MODEL,
            'space_science_data': ContentType.SPACE_SCIENCE_DATA,
            'space_science': ContentType.SPACE_SCIENCE_DATA,
            
            # 研究方法内容
            'statistical_model': ContentType.STATISTICAL_MODEL,
            'statistical_analysis': ContentType.STATISTICAL_MODEL,
            'experimental_protocol': ContentType.EXPERIMENTAL_PROTOCOL,
            'experimental_design': ContentType.EXPERIMENTAL_PROTOCOL,
            'validation_framework': ContentType.VALIDATION_FRAMEWORK,
            'data_validation': ContentType.VALIDATION_FRAMEWORK
        }
        
        result = []
        for content_type in content_types:
            mapped_type = type_mapping.get(content_type.lower())
            if mapped_type and mapped_type not in result:
                result.append(mapped_type)
        
        return result or [ContentType.CODE]
    
    def _create_cursor_rule(self, rule_data: Dict[str, Any]) -> CursorRule:
        """创建CursorRule对象"""
        # 转换规则条件
        rules = []
        for rule_item in rule_data['rules']:
            rules.append(RuleCondition(**rule_item))
        
        # 转换应用范围
        applies_to = RuleApplication(**rule_data['applies_to'])
        
        # 转换验证信息
        validation_data = rule_data['validation'].copy()
        validation_data['severity'] = self._convert_validation_severity(validation_data['severity'])
        validation = RuleValidation(**validation_data)
        
        # 创建CursorRule
        rule_data['rules'] = rules
        rule_data['applies_to'] = applies_to
        rule_data['validation'] = validation
        
        return CursorRule(**rule_data)
    
    def _convert_validation_severity(self, severity: str) -> ValidationSeverity:
        """转换验证严重程度"""
        severity_mapping = {
            'error': ValidationSeverity.ERROR,
            'warning': ValidationSeverity.WARNING,
            'info': ValidationSeverity.INFO
        }
        return severity_mapping.get(severity.lower(), ValidationSeverity.WARNING)


class YamlRuleParser(RuleParser):
    """YAML格式规则解析器"""
    
    def __init__(self, db: RuleDatabase):
        """
        初始化YAML规则解析器
        
        Args:
            db: 规则数据库实例
        """
        super().__init__(db)
        
    def can_parse(self, file_path: Path) -> bool:
        """检查是否为YAML文件"""
        return file_path.suffix.lower() in ['.yaml', '.yml']
    
    def parse(self, file_path: Path) -> List[CursorRule]:
        """解析YAML文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                raise ValueError(f"YAML文件为空: {file_path}")
            
            # 检查是否包含 [...] 类型的截断标记
            truncation_markers = [
                '[... 其余内容 ...]',
                '[...其余内容...]',
                '[... 内容省略以保持简洁 ...]',
                '[...内容省略以保持简洁...]',
                '[...省略...]',
                '[省略]',
                '[...]'
            ]
            
            def check_truncation(text: str) -> bool:
                if isinstance(text, str):
                    for marker in truncation_markers:
                        if marker in text:
                            return True
                return False
            
            def find_truncation_in_dict(d: dict) -> Optional[str]:
                for key, value in d.items():
                    if isinstance(value, str) and check_truncation(value):
                        return f"在字段 '{key}' 中发现内容截断标记"
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            if isinstance(item, dict):
                                result = find_truncation_in_dict(item)
                                if result:
                                    return f"在列表索引 {i} 的 {result}"
                            elif check_truncation(item):
                                return f"在列表索引 {i} 中发现内容截断标记"
                    elif isinstance(value, dict):
                        result = find_truncation_in_dict(value)
                        if result:
                            return f"在嵌套字典的 {result}"
                return None

            # 检查是否存在截断标记
            truncation_location = find_truncation_in_dict(data)
            if truncation_location:
                raise ValueError(f"发现内容截断 ({truncation_location})。请使用分批导入:\n"
                                 "1. 设置 append_mode=True\n"
                                 "2. 分多次导入完整内容\n"
                                 "3. 最后一次导入时设置 append_mode=False 表示导入完成")

            # 支持单个规则和规则列表
            if isinstance(data, dict):
                rule = self._create_rule_from_yaml(data, file_path)
                return [rule]
            elif isinstance(data, list):
                return [self._create_rule_from_yaml(item, file_path) for item in data]
            else:
                raise ValueError(f"无效的YAML格式: {file_path}")
                
        except Exception as e:
            logger.error(f"解析YAML文件失败 {file_path}: {e}")
            raise
    
    def _create_rule_from_yaml(self, data: Dict[str, Any], file_path: Path) -> CursorRule:
        """从YAML数据创建CursorRule"""
        # 验证必需字段
        if 'rule_id' not in data:
            raise ValueError(f"YAML规则缺少rule_id字段: {file_path}")
        
        if 'name' not in data:
            raise ValueError(f"YAML规则缺少name字段: {file_path}")
        
        # 使用MarkdownRuleParser的转换逻辑
        markdown_parser = MarkdownRuleParser(self.db)
        
        # 处理规则条件
        if 'rules' not in data and ('guideline' in data or 'condition' in data):
            # 简化格式，将顶级字段转换为rules数组
            rule_condition = {
                'condition': data.get('condition', 'main_rule'),
                'guideline': data.get('guideline', ''),
                'priority': data.get('priority', 8),
                'examples': data.get('examples', []),
                'pattern': data.get('pattern')
            }
            data['rules'] = [rule_condition]
        
        # 设置默认值
        data.setdefault('version', '1.0.0')
        data.setdefault('author', 'Unknown')
        data.setdefault('created_at', datetime.now(timezone.utc))
        data.setdefault('updated_at', datetime.now(timezone.utc))
        data.setdefault('rule_type', 'content')
        data.setdefault('languages', [])
        data.setdefault('domains', [])
        data.setdefault('task_types', [])
        data.setdefault('content_types', ['code'])
        data.setdefault('tags', [])
        data.setdefault('applies_to', {})
        data.setdefault('conflicts_with', [])
        data.setdefault('overrides', [])
        data.setdefault('validation', {})
        data.setdefault('active', True)
        data.setdefault('usage_count', 0)
        data.setdefault('success_rate', 0.0)
        
        # 转换类型
        data['rule_type'] = markdown_parser._convert_rule_type(data['rule_type'])
        data['task_types'] = markdown_parser._convert_task_types(data['task_types'])
        data['content_types'] = markdown_parser._convert_content_types(data['content_types'])
        
        # 转换规则条件
        rules = []
        for rule_item in data['rules']:
            rules.append(RuleCondition(**rule_item))
        data['rules'] = rules
        
        # 转换应用范围
        data['applies_to'] = RuleApplication(**data['applies_to'])
        
        # 转换验证信息
        validation_data = data['validation']
        if 'severity' in validation_data:
            validation_data['severity'] = markdown_parser._convert_validation_severity(validation_data['severity'])
        else:
            validation_data['severity'] = ValidationSeverity.WARNING
        data['validation'] = RuleValidation(**validation_data)
        
        return CursorRule(**data)

    def is_valid_url(self, url: str) -> bool:
        """
        检查是否为有效的HTTPS URL
        """
        try:
            result = urlparse(url)
            return all([
                result.scheme == 'https',  # 仅允许HTTPS
                result.netloc,  # 必须有域名
                any(url.endswith(ext) for ext in ['.yaml', '.yml'])  # 仅允许YAML文件
            ])
        except:
            return False

    def import_content(self, content: str, merge: bool = False, append_mode: bool = False) -> List[CursorRule]:
        """
        从YAML内容字符串导入规则
        
        Args:
            content: YAML格式的规则内容
            merge: 是否合并已存在的规则
            append_mode: 是否为追加模式，用于分批导入大内容
            
        Returns:
            导入的规则列表
            
        Raises:
            RuleImportError: 导入失败时抛出
        """
        try:
            data = yaml.safe_load(content)
            
            if not data:
                raise RuleImportError("内容为空或格式错误")

            # 检查是否包含 [...] 类型的截断标记
            truncation_markers = [
                '[... 其余内容 ...]',
                '[...其余内容...]',
                '[... 内容省略以保持简洁 ...]',
                '[...内容省略以保持简洁...]',
                '[...省略...]',
                '[省略]',
                '[...]'
            ]
            
            def check_truncation(text: str) -> bool:
                if isinstance(text, str):
                    for marker in truncation_markers:
                        if marker in text:
                            return True
                return False
            
            def find_truncation_in_dict(d: dict) -> Optional[str]:
                for key, value in d.items():
                    if isinstance(value, str) and check_truncation(value):
                        return f"在字段 '{key}' 中发现内容截断标记"
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            if isinstance(item, dict):
                                result = find_truncation_in_dict(item)
                                if result:
                                    return f"在列表索引 {i} 的 {result}"
                            elif check_truncation(item):
                                return f"在列表索引 {i} 中发现内容截断标记"
                    elif isinstance(value, dict):
                        result = find_truncation_in_dict(value)
                        if result:
                            return f"在嵌套字典的 {result}"
                return None

            # 检查是否存在截断标记
            truncation_location = find_truncation_in_dict(data)
            if truncation_location and not append_mode:
                raise RuleImportError(
                    f"发现内容截断 ({truncation_location})。请使用分批导入:\n"
                    "1. 设置 append_mode=True\n"
                    "2. 分多次导入完整内容\n"
                    "3. 最后一次导入时设置 append_mode=False 表示导入完成"
                )

            # 在追加模式下，检查规则是否已存在
            if append_mode:
                rule_id = data.get('rule_id')
                if not rule_id:
                    raise RuleImportError("追加模式下必须提供 rule_id")
                
                existing_rule = self.db.get_rule_by_id(rule_id)
                if not existing_rule:
                    if not merge:
                        raise RuleImportError(f"追加模式下找不到规则 {rule_id}，请先导入基础规则或使用 merge=True")
                else:
                    # 合并规则内容
                    self._merge_rule_content(existing_rule, data)
                    return [existing_rule]

            # 支持单个规则和规则列表
            if isinstance(data, dict):
                rule = self._create_rule_from_yaml(data, "<content>")  # 使用特殊标记表示内容导入
                return [rule]
            elif isinstance(data, list):
                return [self._create_rule_from_yaml(item, "<content>") for item in data]
            else:
                raise RuleImportError("无效的YAML格式")

        except yaml.YAMLError as e:
            raise RuleImportError(f"YAML解析错误: {e}")
        except Exception as e:
            raise RuleImportError(f"导入规则失败: {e}")

    def import_rule(self, file_path: str, merge: bool = False, is_http_api: bool = False) -> List[CursorRule]:
        """
        从YAML文件或URL导入规则
        
        Args:
            file_path: YAML文件路径或HTTPS URL
            merge: 是否合并已存在的规则
            is_http_api: 是否通过HTTP/JSONRPC API调用
            
        Returns:
            导入的规则列表
        """
        try:
            # 检查是否为URL
            is_url = self.is_valid_url(file_path)
            
            # 如果是HTTP API调用，只允许URL导入
            if is_http_api and not is_url:
                raise RuleImportError(
                    "通过HTTP/JSONRPC API只能导入HTTPS URL，不支持本地文件导入。"
                    "请提供有效的HTTPS URL，例如: https://example.com/rules/my_rule.yaml"
                )

            # 读取文件内容
            if is_url:
                try:
                    response = requests.get(file_path, timeout=30, verify=True)
                    response.raise_for_status()
                    content = response.text
                except requests.exceptions.RequestException as e:
                    raise RuleImportError(f"从URL获取规则文件失败: {e}")
            else:
                # 本地文件读取
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    raise RuleImportError(f"读取本地文件失败: {e}")

            # 文件导入不支持追加模式，append_mode 固定为 False
            return self.import_content(content, merge, append_mode=False)

        except Exception as e:
            raise RuleImportError(f"导入规则失败: {e}")


class JsonRuleParser(RuleParser):
    """JSON格式规则解析器"""
    
    def __init__(self, db: RuleDatabase):
        """
        初始化JSON规则解析器
        
        Args:
            db: 规则数据库实例
        """
        super().__init__(db)
    
    def can_parse(self, file_path: Path) -> bool:
        """检查是否为JSON文件"""
        return file_path.suffix.lower() == '.json'
    
    def parse(self, file_path: Path) -> List[CursorRule]:
        """解析JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data:
                raise ValueError(f"JSON文件为空: {file_path}")
            
            # 使用YAML解析器的逻辑（JSON是YAML的子集）
            yaml_parser = YamlRuleParser(self.db)
            
            if isinstance(data, dict):
                rule = yaml_parser._create_rule_from_yaml(data, file_path)
                return [rule]
            elif isinstance(data, list):
                rules = []
                for item in data:
                    if isinstance(item, dict):
                        rule = yaml_parser._create_rule_from_yaml(item, file_path)
                        rules.append(rule)
                return rules
            else:
                raise ValueError(f"无效的JSON格式: {file_path}")
                
        except Exception as e:
            logger.error(f"解析JSON文件失败 {file_path}: {e}")
            raise


class UnifiedRuleImporter:
    """统一规则导入器"""
    
    def __init__(self, save_to_database: bool = True):
        """初始化导入器"""
        self.parsers = []  # 初始化为空，在需要时延迟创建
        self.import_log: List[Dict[str, Any]] = []
        self.save_to_database = save_to_database
        self.database = None
        self._parsers_initialized = False

    async def _ensure_parsers_initialized(self):
        """确保解析器已初始化"""
        if not self._parsers_initialized:
            await self.initialize_database()
            if self.database:
                self.parsers = [
                    MarkdownRuleParser(self.database),
                    YamlRuleParser(self.database),
                    JsonRuleParser(self.database)
                ]
                self._parsers_initialized = True

    async def initialize_database(self):
        """初始化数据库连接"""
        if self.save_to_database and self.database is None:
            from .database import get_rule_database
            self.database = get_rule_database()
            await self.database.initialize()

    async def import_rules_async(self, 
                               paths: List[Union[str, Path]], 
                               recursive: bool = False,
                               format_hint: Optional[str] = None,
                               merge: Optional[bool] = None,
                               interactive: bool = False) -> List[CursorRule]:
        """异步导入规则（支持数据库保存，支持merge/交互确认）"""
        await self._ensure_parsers_initialized()
        rules = await self.import_rules(paths, recursive, format_hint)
        
        # 保存到数据库
        if self.save_to_database and self.database:
            for rule in rules:
                # 初始化保存路径
                rule_filename = f"{rule.rule_id.lower().replace('-', '_')}.yaml"
                save_path = Path(self.database.data_dir) / "imported" / rule_filename
                
                try:
                    # 检查是否已存在
                    exists = rule.rule_id in self.database.rules
                    
                    if exists:
                        if merge is True:
                            # 允许覆盖
                            await self.database.add_rule(rule, save_path)
                            self._log_success(str(save_path), f"覆盖已存在规则: {rule.rule_id}")
                        elif interactive:
                            # 命令行交互
                            resp = input(f"⚠️ 检测到重复 rule_id: {rule.rule_id}，是否覆盖？[y/N]: ").strip().lower()
                            if resp == 'y':
                                await self.database.add_rule(rule, save_path)
                                self._log_success(str(save_path), f"用户确认覆盖已存在规则: {rule.rule_id}")
                            else:
                                self._log_error(str(save_path), f"检测到重复 rule_id: {rule.rule_id}，用户选择跳过")
                        else:
                            # 非交互/未指定merge，直接报错
                            self._log_error(str(save_path), f"检测到重复 rule_id: {rule.rule_id}，未指定 merge，已跳过。请设置 merge=True 以允许覆盖。")
                    else:
                        # 不存在，正常添加
                        await self.database.add_rule(rule, save_path)
                        self._log_success(str(save_path), f"成功导入规则: {rule.rule_id}")
                except Exception as e:
                    self._log_error(str(save_path), f"❌ 保存规则到数据库失败 {rule.rule_id}: {e}")
        return rules

    async def import_rules(self, 
                     paths: List[Union[str, Path]], 
                     recursive: bool = False,
                     format_hint: Optional[str] = None) -> List[CursorRule]:
        """导入规则
        
        Args:
            paths: 文件或目录路径列表
            recursive: 是否递归扫描目录
            format_hint: 格式提示 ('markdown', 'yaml', 'json', 'auto')
            
        Returns:
            导入的规则列表
        """
        await self._ensure_parsers_initialized()
        all_rules = []
        
        for path in paths:
            path = Path(path)
            
            if path.is_file():
                rules = await self._import_file(path, format_hint)
                all_rules.extend(rules)
            elif path.is_dir():
                rules = await self._import_directory(path, recursive, format_hint)
                all_rules.extend(rules)
            else:
                self._log_error(str(path), f"路径不存在: {path}")
        
        return all_rules
    
    async def _import_file(self, file_path: Path, format_hint: Optional[str] = None) -> List[CursorRule]:
        """导入单个文件"""
        try:
            # 检查文件是否存在
            if not file_path.exists():
                self._log_error(str(file_path), f"文件不存在: {file_path}")
                return []
                
            # 选择解析器
            parser = self._select_parser(file_path, format_hint)
            if not parser:
                self._log_error(str(file_path), f"不支持的文件格式: {file_path.suffix}")
                return []
            
            # 解析文件
            rules = parser.parse(file_path)
            
            for rule in rules:
                self._log_success(str(file_path), f"成功导入规则: {rule.rule_id}")
            
            return rules
            
        except Exception as e:
            self._log_error(str(file_path), f"导入失败: {e}")
            return []
    
    async def _import_directory(self, dir_path: Path, recursive: bool, format_hint: Optional[str] = None) -> List[CursorRule]:
        """导入目录中的文件"""
        all_rules = []
        
        # 支持的文件扩展名
        extensions = ['.md', '.markdown', '.yaml', '.yml', '.json']
        
        if format_hint:
            if format_hint.lower() == 'markdown':
                extensions = ['.md', '.markdown']
            elif format_hint.lower() == 'yaml':
                extensions = ['.yaml', '.yml']
            elif format_hint.lower() == 'json':
                extensions = ['.json']
        
        # 扫描文件
        pattern = '**/*' if recursive else '*'
        for file_path in dir_path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                rules = await self._import_file(file_path, format_hint)
                all_rules.extend(rules)
        
        return all_rules
    
    def _select_parser(self, file_path: Path, format_hint: Optional[str] = None) -> Optional[RuleParser]:
        """选择合适的解析器"""
        if format_hint and format_hint.lower() != 'auto':
            # 根据格式提示选择
            for parser in self.parsers:
                if (format_hint.lower() == 'markdown' and isinstance(parser, MarkdownRuleParser) or
                    format_hint.lower() == 'yaml' and isinstance(parser, YamlRuleParser) or
                    format_hint.lower() == 'json' and isinstance(parser, JsonRuleParser)):
                    return parser
        
        # 根据文件扩展名自动选择
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser
        
        return None
    
    def _log_success(self, file_path: str, message: str):
        """记录成功日志"""
        self.import_log.append({
            'file': file_path,
            'status': 'success',
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        logger.info(f"✅ {file_path}: {message}")
    
    def _log_error(self, file_path: str, message: str):
        """记录错误日志"""
        self.import_log.append({
            'file': file_path,
            'status': 'error',
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        logger.error(f"❌ {file_path}: {message}")
    
    def get_import_summary(self) -> Dict[str, Any]:
        """获取导入摘要"""
        total = len(self.import_log)
        success = len([log for log in self.import_log if log['status'] == 'success'])
        errors = total - success
        
        return {
            'total_files': total,
            'successful_imports': success,
            'failed_imports': errors,
            'success_rate': success / total if total > 0 else 0.0,
            'import_log': self.import_log
        }
    
    def save_import_log(self, output_path: Path):
        """保存导入日志"""
        summary = self.get_import_summary()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"导入日志已保存到: {output_path}")