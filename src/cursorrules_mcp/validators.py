#!/usr/bin/env python3
"""
CursorRules-MCP 验证器模块
集成各种代码和文档验证工具
"""

import asyncio
import subprocess
import tempfile
import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .models import ValidationIssue, ValidationSeverity, ValidationResult
from .config import ValidationToolConfig, get_config

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    execution_time: float


class BaseValidator(ABC):
    """验证器基类"""
    
    def __init__(self, config: ValidationToolConfig):
        """初始化验证器
        
        Args:
            config: 验证工具配置
        """
        self.config = config
        self.name = config.name
        self.enabled = config.enabled
    
    @abstractmethod
    async def validate(self, content: str, file_path: Optional[str] = None) -> List[ValidationIssue]:
        """执行验证
        
        Args:
            content: 要验证的内容
            file_path: 文件路径（可选）
            
        Returns:
            验证问题列表
        """
        pass
    
    async def _run_command(self, command: List[str], input_data: Optional[str] = None) -> ToolResult:
        """执行命令
        
        Args:
            command: 命令和参数列表
            input_data: 输入数据
            
        Returns:
            执行结果
        """
        import time
        start_time = time.time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=subprocess.PIPE if input_data else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input_data.encode() if input_data else None),
                timeout=self.config.timeout
            )
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                success=process.returncode == 0,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                return_code=process.returncode,
                execution_time=execution_time
            )
            
        except asyncio.TimeoutError:
            logger.warning(f"验证工具 {self.name} 执行超时")
            return ToolResult(
                success=False,
                stdout="",
                stderr="执行超时",
                return_code=-1,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"执行验证工具 {self.name} 时发生错误: {e}")
            return ToolResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                execution_time=time.time() - start_time
            )
    
    def _create_temp_file(self, content: str, suffix: str = ".tmp") -> str:
        """创建临时文件
        
        Args:
            content: 文件内容
            suffix: 文件后缀
            
        Returns:
            临时文件路径
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
            f.write(content)
            return f.name


class PythonFlake8Validator(BaseValidator):
    """Python Flake8 验证器"""
    
    async def validate(self, content: str, file_path: Optional[str] = None) -> List[ValidationIssue]:
        """使用Flake8验证Python代码"""
        if not self.enabled:
            return []
        
        issues = []
        temp_file = None
        
        try:
            # 创建临时文件
            temp_file = self._create_temp_file(content, ".py")
            
            # 构建命令
            command = [self.config.command] + self.config.args + [temp_file]
            
            # 执行验证
            result = await self._run_command(command)
            
            if not result.success and result.stdout:
                # 解析Flake8输出
                for line in result.stdout.strip().split('\n'):
                    if line:
                        issue = self._parse_flake8_line(line, temp_file)
                        if issue:
                            issues.append(issue)
            
        except Exception as e:
            logger.error(f"Flake8验证失败: {e}")
        finally:
            # 清理临时文件
            if temp_file and Path(temp_file).exists():
                Path(temp_file).unlink()
        
        return issues
    
    def _parse_flake8_line(self, line: str, temp_file: str) -> Optional[ValidationIssue]:
        """解析Flake8输出行"""
        # Flake8格式: filename:line:column: code message
        pattern = r'^([^:]+):(\d+):(\d+):\s*([A-Z]\d+)\s*(.+)$'
        match = re.match(pattern, line)
        
        if match:
            file_path, line_num, col_num, code, message = match.groups()
            
            # 确定严重程度
            severity = ValidationSeverity.WARNING
            if code.startswith('E'):  # Error codes
                severity = ValidationSeverity.ERROR
            elif code.startswith('W'):  # Warning codes
                severity = ValidationSeverity.WARNING
            elif code.startswith('F'):  # Fatal codes
                severity = ValidationSeverity.ERROR
            
            return ValidationIssue(
                line_number=int(line_num),
                column_number=int(col_num),
                message=f"{code}: {message}",
                severity=severity,
                rule_id=f"flake8.{code}",
                suggestion=self._get_flake8_suggestion(code)
            )
        
        return None
    
    def _get_flake8_suggestion(self, code: str) -> str:
        """获取Flake8错误的建议"""
        suggestions = {
            'E501': '将长行拆分为多行，使用括号或反斜杠',
            'E302': '在类和函数定义前添加2个空行',
            'E303': '删除多余的空行',
            'W292': '在文件末尾添加换行符',
            'E231': '在逗号后添加空格',
            'E225': '在操作符周围添加空格',
            'F401': '删除未使用的导入',
            'F841': '删除未使用的变量或在变量名前添加下划线'
        }
        return suggestions.get(code, '参考PEP8风格指南修复此问题')


class PythonPylintValidator(BaseValidator):
    """Python Pylint 验证器"""
    
    async def validate(self, content: str, file_path: Optional[str] = None) -> List[ValidationIssue]:
        """使用Pylint验证Python代码"""
        if not self.enabled:
            return []
        
        issues = []
        temp_file = None
        
        try:
            # 创建临时文件
            temp_file = self._create_temp_file(content, ".py")
            
            # 构建命令，输出JSON格式
            command = [self.config.command] + self.config.args + ['--output-format=json', temp_file]
            
            # 执行验证
            result = await self._run_command(command)
            
            # Pylint即使有问题也可能返回非0状态码
            if result.stdout:
                try:
                    pylint_output = json.loads(result.stdout)
                    for item in pylint_output:
                        issue = self._parse_pylint_item(item)
                        if issue:
                            issues.append(issue)
                except json.JSONDecodeError:
                    # 如果不是JSON格式，尝试解析文本输出
                    issues.extend(self._parse_pylint_text(result.stdout))
            
        except Exception as e:
            logger.error(f"Pylint验证失败: {e}")
        finally:
            # 清理临时文件
            if temp_file and Path(temp_file).exists():
                Path(temp_file).unlink()
        
        return issues
    
    def _parse_pylint_item(self, item: Dict[str, Any]) -> Optional[ValidationIssue]:
        """解析Pylint JSON输出项"""
        try:
            # 确定严重程度
            severity_map = {
                'error': ValidationSeverity.ERROR,
                'warning': ValidationSeverity.WARNING,
                'refactor': ValidationSeverity.INFO,
                'convention': ValidationSeverity.INFO,
                'info': ValidationSeverity.INFO
            }
            
            severity = severity_map.get(item.get('type', '').lower(), ValidationSeverity.WARNING)
            
            return ValidationIssue(
                line_number=item.get('line', 1),
                column_number=item.get('column', 0),
                message=f"{item.get('symbol', '')}: {item.get('message', '')}",
                severity=severity,
                rule_id=f"pylint.{item.get('message-id', '')}",
                suggestion=self._get_pylint_suggestion(item.get('symbol', ''))
            )
            
        except Exception as e:
            logger.error(f"解析Pylint输出项失败: {e}")
            return None
    
    def _parse_pylint_text(self, output: str) -> List[ValidationIssue]:
        """解析Pylint文本输出"""
        issues = []
        
        for line in output.strip().split('\n'):
            if ':' in line and any(level in line for level in ['ERROR', 'WARNING', 'INFO']):
                # 简单的文本解析
                parts = line.split(':')
                if len(parts) >= 3:
                    try:
                        line_num = int(parts[1])
                        message = ':'.join(parts[2:]).strip()
                        
                        severity = ValidationSeverity.WARNING
                        if 'ERROR' in line:
                            severity = ValidationSeverity.ERROR
                        elif 'INFO' in line:
                            severity = ValidationSeverity.INFO
                        
                        issues.append(ValidationIssue(
                            line_number=line_num,
                            column_number=0,
                            message=message,
                            severity=severity,
                            rule_id="pylint.text_parse"
                        ))
                    except ValueError:
                        continue
        
        return issues
    
    def _get_pylint_suggestion(self, symbol: str) -> str:
        """获取Pylint错误的建议"""
        suggestions = {
            'line-too-long': '将长行拆分为多行',
            'missing-docstring': '为函数、类或模块添加docstring',
            'unused-import': '删除未使用的导入',
            'unused-variable': '删除未使用的变量或在变量名前添加下划线',
            'invalid-name': '使用符合命名规范的变量名',
            'too-many-locals': '考虑将函数拆分为更小的函数',
            'too-many-branches': '简化条件逻辑或使用多态'
        }
        return suggestions.get(symbol, '参考Pylint文档修复此问题')


class PythonBlackValidator(BaseValidator):
    """Python Black 格式验证器"""
    
    async def validate(self, content: str, file_path: Optional[str] = None) -> List[ValidationIssue]:
        """使用Black检查Python代码格式"""
        if not self.enabled:
            return []
        
        issues = []
        temp_file = None
        
        try:
            # 创建临时文件
            temp_file = self._create_temp_file(content, ".py")
            
            # 构建命令
            command = [self.config.command] + self.config.args + [temp_file]
            
            # 执行验证
            result = await self._run_command(command)
            
            # Black返回非0表示需要格式化
            if not result.success:
                # 如果有diff输出，说明格式不符合Black标准
                if result.stdout.strip():
                    issues.append(ValidationIssue(
                        line_number=1,
                        column_number=0,
                        message="代码格式不符合Black标准",
                        severity=ValidationSeverity.WARNING,
                        rule_id="black.format",
                        suggestion="运行 'black filename.py' 自动格式化代码"
                    ))
            
        except Exception as e:
            logger.error(f"Black验证失败: {e}")
        finally:
            # 清理临时文件
            if temp_file and Path(temp_file).exists():
                Path(temp_file).unlink()
        
        return issues


class PythonMypyValidator(BaseValidator):
    """Python MyPy 类型检查器"""
    
    async def validate(self, content: str, file_path: Optional[str] = None) -> List[ValidationIssue]:
        """使用MyPy进行类型检查"""
        if not self.enabled:
            return []
        
        issues = []
        temp_file = None
        
        try:
            # 创建临时文件
            temp_file = self._create_temp_file(content, ".py")
            
            # 构建命令
            command = [self.config.command] + self.config.args + [temp_file]
            
            # 执行验证
            result = await self._run_command(command)
            
            if result.stdout:
                # 解析MyPy输出
                for line in result.stdout.strip().split('\n'):
                    if line and ':' in line:
                        issue = self._parse_mypy_line(line, temp_file)
                        if issue:
                            issues.append(issue)
            
        except Exception as e:
            logger.error(f"MyPy验证失败: {e}")
        finally:
            # 清理临时文件
            if temp_file and Path(temp_file).exists():
                Path(temp_file).unlink()
        
        return issues
    
    def _parse_mypy_line(self, line: str, temp_file: str) -> Optional[ValidationIssue]:
        """解析MyPy输出行"""
        # MyPy格式: filename:line: level: message
        pattern = r'^([^:]+):(\d+):\s*(error|warning|note):\s*(.+)$'
        match = re.match(pattern, line)
        
        if match:
            file_path, line_num, level, message = match.groups()
            
            severity_map = {
                'error': ValidationSeverity.ERROR,
                'warning': ValidationSeverity.WARNING,
                'note': ValidationSeverity.INFO
            }
            
            return ValidationIssue(
                line_number=int(line_num),
                column_number=0,
                message=message,
                severity=severity_map.get(level, ValidationSeverity.WARNING),
                rule_id="mypy.type_check",
                suggestion="添加正确的类型注解或修复类型错误"
            )
        
        return None


class JavaScriptESLintValidator(BaseValidator):
    """JavaScript ESLint 验证器"""
    
    async def validate(self, content: str, file_path: Optional[str] = None) -> List[ValidationIssue]:
        """使用ESLint验证JavaScript代码"""
        if not self.enabled:
            return []
        
        issues = []
        temp_file = None
        
        try:
            # 创建临时文件
            temp_file = self._create_temp_file(content, ".js")
            
            # 构建命令，输出JSON格式
            command = [self.config.command] + self.config.args + [temp_file]
            
            # 执行验证
            result = await self._run_command(command)
            
            if result.stdout:
                try:
                    eslint_output = json.loads(result.stdout)
                    if eslint_output and len(eslint_output) > 0:
                        for message in eslint_output[0].get('messages', []):
                            issue = self._parse_eslint_message(message)
                            if issue:
                                issues.append(issue)
                except json.JSONDecodeError:
                    logger.warning("ESLint输出不是有效的JSON格式")
            
        except Exception as e:
            logger.error(f"ESLint验证失败: {e}")
        finally:
            # 清理临时文件
            if temp_file and Path(temp_file).exists():
                Path(temp_file).unlink()
        
        return issues
    
    def _parse_eslint_message(self, message: Dict[str, Any]) -> Optional[ValidationIssue]:
        """解析ESLint消息"""
        try:
            severity_map = {
                1: ValidationSeverity.WARNING,
                2: ValidationSeverity.ERROR
            }
            
            severity = severity_map.get(message.get('severity', 1), ValidationSeverity.WARNING)
            rule_id = message.get('ruleId', 'eslint.unknown')
            
            return ValidationIssue(
                line_number=message.get('line', 1),
                column_number=message.get('column', 0),
                message=message.get('message', ''),
                severity=severity,
                rule_id=f"eslint.{rule_id}",
                suggestion=self._get_eslint_suggestion(rule_id)
            )
            
        except Exception as e:
            logger.error(f"解析ESLint消息失败: {e}")
            return None
    
    def _get_eslint_suggestion(self, rule_id: str) -> str:
        """获取ESLint规则的建议"""
        suggestions = {
            'no-unused-vars': '删除未使用的变量',
            'no-undef': '定义变量或添加适当的全局声明',
            'semi': '添加或删除分号以保持一致性',
            'quotes': '使用一致的引号类型',
            'indent': '修复缩进问题',
            'no-console': '移除console语句或添加eslint-disable注释'
        }
        return suggestions.get(rule_id, '参考ESLint文档修复此问题')


class MarkdownLintValidator(BaseValidator):
    """Markdown Lint 验证器"""
    
    async def validate(self, content: str, file_path: Optional[str] = None) -> List[ValidationIssue]:
        """使用markdownlint验证Markdown文档"""
        if not self.enabled:
            return []
        
        issues = []
        temp_file = None
        
        try:
            # 创建临时文件
            temp_file = self._create_temp_file(content, ".md")
            
            # 构建命令
            command = [self.config.command] + self.config.args + [temp_file]
            
            # 执行验证
            result = await self._run_command(command)
            
            if result.stdout:
                try:
                    # 尝试解析JSON输出
                    markdownlint_output = json.loads(result.stdout)
                    for file_issues in markdownlint_output.values():
                        for issue_data in file_issues:
                            issue = self._parse_markdownlint_issue(issue_data)
                            if issue:
                                issues.append(issue)
                except json.JSONDecodeError:
                    # 解析文本输出
                    issues.extend(self._parse_markdownlint_text(result.stdout))
            
        except Exception as e:
            logger.error(f"MarkdownLint验证失败: {e}")
        finally:
            # 清理临时文件
            if temp_file and Path(temp_file).exists():
                Path(temp_file).unlink()
        
        return issues
    
    def _parse_markdownlint_issue(self, issue_data: Dict[str, Any]) -> Optional[ValidationIssue]:
        """解析markdownlint问题"""
        try:
            return ValidationIssue(
                line_number=issue_data.get('lineNumber', 1),
                column_number=issue_data.get('columnNumber', 0),
                message=issue_data.get('ruleDescription', ''),
                severity=ValidationSeverity.WARNING,
                rule_id=f"markdownlint.{issue_data.get('ruleNames', [''])[0]}",
                suggestion=self._get_markdownlint_suggestion(issue_data.get('ruleNames', [''])[0])
            )
        except Exception as e:
            logger.error(f"解析markdownlint问题失败: {e}")
            return None
    
    def _parse_markdownlint_text(self, output: str) -> List[ValidationIssue]:
        """解析markdownlint文本输出"""
        issues = []
        
        for line in output.strip().split('\n'):
            if ':' in line:
                # 简单的文本解析
                parts = line.split(':')
                if len(parts) >= 3:
                    try:
                        line_num = int(parts[1])
                        message = ':'.join(parts[2:]).strip()
                        
                        issues.append(ValidationIssue(
                            line_number=line_num,
                            column_number=0,
                            message=message,
                            severity=ValidationSeverity.WARNING,
                            rule_id="markdownlint.text_parse"
                        ))
                    except ValueError:
                        continue
        
        return issues
    
    def _get_markdownlint_suggestion(self, rule_name: str) -> str:
        """获取markdownlint规则的建议"""
        suggestions = {
            'MD001': '标题级别应该递增，不要跳级',
            'MD003': '使用一致的标题样式',
            'MD009': '删除行尾空格',
            'MD010': '使用空格替代制表符',
            'MD012': '删除多余的空行',
            'MD013': '行长度应该限制在合理范围内',
            'MD022': '标题前后应该有空行',
            'MD025': '每个文档只能有一个顶级标题'
        }
        return suggestions.get(rule_name, '参考markdownlint文档修复此问题')


class ValidatorFactory:
    """验证器工厂类"""
    
    _validators = {
        'python': {
            'flake8': PythonFlake8Validator,
            'pylint': PythonPylintValidator,
            'black': PythonBlackValidator,
            'mypy': PythonMypyValidator
        },
        'javascript': {
            'eslint': JavaScriptESLintValidator
        },
        'markdown': {
            'markdownlint': MarkdownLintValidator
        }
    }
    
    @classmethod
    def create_validator(cls, language: str, tool_name: str, config: ValidationToolConfig) -> Optional[BaseValidator]:
        """创建验证器实例
        
        Args:
            language: 编程语言
            tool_name: 工具名称
            config: 工具配置
            
        Returns:
            验证器实例或None
        """
        if language in cls._validators and tool_name in cls._validators[language]:
            validator_class = cls._validators[language][tool_name]
            return validator_class(config)
        
        logger.warning(f"未找到验证器: {language}.{tool_name}")
        return None
    
    @classmethod
    def get_available_validators(cls) -> Dict[str, List[str]]:
        """获取所有可用的验证器
        
        Returns:
            按语言分组的验证器列表
        """
        return {lang: list(tools.keys()) for lang, tools in cls._validators.items()}


class ValidationManager:
    """验证管理器"""
    
    def __init__(self):
        """初始化验证管理器"""
        self.config = get_config()
        self.validators: Dict[str, Dict[str, BaseValidator]] = {}
        self._initialize_validators()
    
    def _initialize_validators(self):
        """初始化验证器"""
        validation_tools = self.config.validation.tools
        
        for language, tools in validation_tools.items():
            self.validators[language] = {}
            
            for tool_name, tool_config in tools.items():
                validator = ValidatorFactory.create_validator(language, tool_name, tool_config)
                if validator:
                    self.validators[language][tool_name] = validator
                    logger.info(f"初始化验证器: {language}.{tool_name}")
    
    async def validate_content(self, content: str, language: str, file_path: Optional[str] = None) -> ValidationResult:
        """验证内容
        
        Args:
            content: 要验证的内容
            language: 编程语言
            file_path: 文件路径（可选）
            
        Returns:
            验证结果
        """
        all_issues = []
        applied_tools = []
        
        if language in self.validators:
            # 获取该语言的所有验证器
            language_validators = self.validators[language]
            
            if self.config.validation.parallel_validation:
                # 并行执行验证
                tasks = []
                for tool_name, validator in language_validators.items():
                    if validator.enabled:
                        task = self._validate_with_tool(validator, content, file_path, tool_name)
                        tasks.append(task)
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for i, result in enumerate(results):
                        tool_name = list(language_validators.keys())[i]
                        if isinstance(result, list):
                            all_issues.extend(result)
                            applied_tools.append(f"{language}.{tool_name}")
                        elif isinstance(result, Exception):
                            logger.error(f"验证工具 {tool_name} 执行失败: {result}")
            else:
                # 串行执行验证
                for tool_name, validator in language_validators.items():
                    if validator.enabled:
                        try:
                            issues = await validator.validate(content, file_path)
                            all_issues.extend(issues)
                            applied_tools.append(f"{language}.{tool_name}")
                        except Exception as e:
                            logger.error(f"验证工具 {tool_name} 执行失败: {e}")
        
        # 计算分数
        score = self._calculate_score(all_issues)
        
        return ValidationResult(
            is_valid=len(all_issues) == 0,
            score=score,
            issues=all_issues,
            suggestions=self._generate_suggestions(all_issues),
            applied_rules=applied_tools,
            validation_time=None  # 将在调用处设置
        )
    
    async def _validate_with_tool(self, validator: BaseValidator, content: str, 
                                 file_path: Optional[str], tool_name: str) -> List[ValidationIssue]:
        """使用单个工具进行验证"""
        try:
            return await validator.validate(content, file_path)
        except Exception as e:
            logger.error(f"验证工具 {tool_name} 执行失败: {e}")
            return []
    
    def _calculate_score(self, issues: List[ValidationIssue]) -> float:
        """计算验证分数"""
        if not issues:
            return 100.0
        
        deduction = 0.0
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                deduction += 10.0
            elif issue.severity == ValidationSeverity.WARNING:
                deduction += 5.0
            elif issue.severity == ValidationSeverity.INFO:
                deduction += 1.0
        
        return max(0.0, 100.0 - deduction)
    
    def _generate_suggestions(self, issues: List[ValidationIssue]) -> List[str]:
        """生成改进建议"""
        suggestions = set()
        
        # 按工具分组问题
        tool_issues = {}
        for issue in issues:
            if issue.rule_id:
                tool = issue.rule_id.split('.')[0]
                if tool not in tool_issues:
                    tool_issues[tool] = []
                tool_issues[tool].append(issue)
        
        # 生成工具特定的建议
        for tool, tool_issues_list in tool_issues.items():
            if tool == 'flake8':
                suggestions.add("配置编辑器使用Flake8进行实时代码检查")
                if len(tool_issues_list) > 5:
                    suggestions.add("考虑使用black自动格式化代码以减少格式问题")
            elif tool == 'pylint':
                suggestions.add("考虑添加pylint配置文件以自定义规则")
                suggestions.add("为函数和类添加完整的docstring")
            elif tool == 'mypy':
                suggestions.add("逐步添加类型注解提高代码质量")
                suggestions.add("使用mypy配置文件忽略第三方库的类型检查")
            elif tool == 'eslint':
                suggestions.add("配置编辑器集成ESLint进行实时检查")
                suggestions.add("考虑使用Prettier自动格式化JavaScript代码")
            elif tool == 'markdownlint':
                suggestions.add("使用支持markdownlint的编辑器插件")
                suggestions.add("建立团队的Markdown写作规范")
        
        # 通用建议
        if len(issues) > 10:
            suggestions.add("问题较多，建议分批修复，优先处理错误级别的问题")
        
        return list(suggestions)
    
    def get_available_validators(self) -> Dict[str, List[str]]:
        """获取可用的验证器"""
        result = {}
        for language, validators in self.validators.items():
            result[language] = [
                tool_name for tool_name, validator in validators.items() 
                if validator.enabled
            ]
        return result
    
    def is_tool_available(self, language: str, tool_name: str) -> bool:
        """检查验证工具是否可用"""
        return (language in self.validators and 
                tool_name in self.validators[language] and
                self.validators[language][tool_name].enabled)


# 全局验证管理器实例
_validation_manager: Optional[ValidationManager] = None


def get_validation_manager() -> ValidationManager:
    """获取全局验证管理器实例"""
    global _validation_manager
    
    if _validation_manager is None:
        _validation_manager = ValidationManager()
    
    return _validation_manager


if __name__ == "__main__":
    # 测试验证器
    async def test_validators():
        manager = ValidationManager()
        
        # 测试Python代码
        python_code = """
def long_function_name_that_exceeds_the_line_length_limit():
    x=1+2
    print(x)
"""
        
        result = await manager.validate_content(python_code, "python")
        print(f"Python验证结果: 分数={result.score}, 问题数={len(result.issues)}")
        
        for issue in result.issues[:3]:  # 显示前3个问题
            print(f"  {issue.line_number}:{issue.column_number} {issue.severity.value} {issue.message}")
    
    asyncio.run(test_validators())