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

try:
    import frontmatter
except ImportError:
    frontmatter = None
    logging.warning("python-frontmatter not installed. Markdown frontmatter parsing will be limited.")

from .models import (
    CursorRule, RuleType, ContentType, TaskType, ValidationSeverity,
    RuleCondition, RuleApplication, RuleValidation
)

logger = logging.getLogger(__name__)


class RuleParser(ABC):
    """规则解析器抽象基类"""
    
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
        """解析Markdown内容部分"""
        sections = {}
        
        # 提取不同的章节
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
            
            # 查找好的和坏的示例
            good_examples = re.findall(r'(?:好的|Good|正确).*?\n```(\w+)?\n(.*?)```', examples_text, re.DOTALL | re.IGNORECASE)
            bad_examples = re.findall(r'(?:坏的|Bad|错误).*?\n```(\w+)?\n(.*?)```', examples_text, re.DOTALL | re.IGNORECASE)
            
            if good_examples:
                for lang, code in good_examples:
                    examples.append({
                        'good': code.strip(),
                        'explanation': '良好的代码示例'
                    })
            
            if bad_examples:
                for i, (lang, code) in enumerate(bad_examples):
                    if i < len(examples):
                        examples[i]['bad'] = code.strip()
                    else:
                        examples.append({
                            'bad': code.strip(),
                            'explanation': '错误的代码示例'
                        })
        
        sections['parsed_examples'] = examples
        return sections
    
    def _build_rule_data(self, metadata: Dict[str, Any], content: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """构建规则数据字典"""
        # 基本信息
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
        condition = metadata.get('condition', 'main_rule')
        guideline = content.get('guideline', metadata.get('guideline', ''))
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
            'development': TaskType.DEVELOPMENT,
            'documentation': TaskType.DOCUMENTATION,
            'testing': TaskType.TESTING,
            'refactoring': TaskType.REFACTORING,
            'debugging': TaskType.DEBUGGING,
            'optimization': TaskType.OPTIMIZATION,
            'code_review': TaskType.CODE_REVIEW
        }
        
        result = []
        for task_type in task_types:
            mapped_type = type_mapping.get(task_type.lower())
            if mapped_type and mapped_type not in result:
                result.append(mapped_type)
        
        return result or [TaskType.DEVELOPMENT]
    
    def _convert_content_types(self, content_types: List[str]) -> List[ContentType]:
        """转换内容类型"""
        type_mapping = {
            'code': ContentType.CODE,
            'documentation': ContentType.DOCUMENTATION,
            'data': ContentType.DATA,
            'algorithm': ContentType.ALGORITHM,
            'configuration': ContentType.CONFIGURATION
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
            
            # 支持单个规则和规则列表
            if isinstance(data, dict):
                # 单个规则
                rule = self._create_rule_from_yaml(data, file_path)
                return [rule]
            elif isinstance(data, list):
                # 规则列表
                rules = []
                for item in data:
                    if isinstance(item, dict):
                        rule = self._create_rule_from_yaml(item, file_path)
                        rules.append(rule)
                return rules
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
        markdown_parser = MarkdownRuleParser()
        
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


class JsonRuleParser(RuleParser):
    """JSON格式规则解析器"""
    
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
            yaml_parser = YamlRuleParser()
            
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
    
    def __init__(self):
        """初始化导入器"""
        self.parsers = [
            MarkdownRuleParser(),
            YamlRuleParser(),
            JsonRuleParser()
        ]
        self.import_log: List[Dict[str, Any]] = []
    
    def import_rules(self, 
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
        all_rules = []
        
        for path in paths:
            path = Path(path)
            
            if path.is_file():
                rules = self._import_file(path, format_hint)
                all_rules.extend(rules)
            elif path.is_dir():
                rules = self._import_directory(path, recursive, format_hint)
                all_rules.extend(rules)
            else:
                self._log_error(str(path), f"路径不存在: {path}")
        
        return all_rules
    
    def _import_file(self, file_path: Path, format_hint: Optional[str] = None) -> List[CursorRule]:
        """导入单个文件"""
        try:
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
    
    def _import_directory(self, dir_path: Path, recursive: bool, format_hint: Optional[str] = None) -> List[CursorRule]:
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
                rules = self._import_file(file_path, format_hint)
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