"""
规则数据库管理模块
提供规则的存储、版本管理、冲突检测等功能

Author: Mapoet
Institution: NUS/STAR
Date: 2025-01-23
License: MIT
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import os

import yaml
from packaging import version

from .config import get_config
from .models import CursorRule, RuleType, ValidationSeverity

logger = logging.getLogger(__name__)


class RuleVersionManager:
    """规则版本管理器"""

    def __init__(self):
        self.version_history: Dict[str, List[CursorRule]] = {}  # rule_id -> versions
        self.latest_versions: Dict[str, str] = {}  # rule_id -> latest_version

    def add_rule_version(self, rule: CursorRule) -> bool:
        """添加规则版本"""
        rule_id = rule.rule_id

        if rule_id not in self.version_history:
            self.version_history[rule_id] = []
            self.latest_versions[rule_id] = rule.version

        # 检查版本是否已存在
        existing_versions = [r.version for r in self.version_history[rule_id]]
        if rule.version in existing_versions:
            logger.warning(f"规则 {rule_id} 版本 {rule.version} 已存在")
            return False

        # 添加新版本
        self.version_history[rule_id].append(rule)

        # 更新最新版本
        if self._is_newer_version(rule.version, self.latest_versions[rule_id]):
            self.latest_versions[rule_id] = rule.version

        # 按版本排序
        self.version_history[rule_id].sort(key=lambda r: version.parse(r.version))

        return True

    def get_latest_rule(self, rule_id: str) -> Optional[CursorRule]:
        """获取规则的最新版本"""
        if rule_id not in self.version_history:
            return None

        latest_version = self.latest_versions[rule_id]
        for rule in self.version_history[rule_id]:
            if rule.version == latest_version:
                return rule
        return None

    def get_rule_version(self, rule_id: str, rule_version: str) -> Optional[CursorRule]:
        """获取规则的特定版本"""
        if rule_id not in self.version_history:
            return None

        for rule in self.version_history[rule_id]:
            if rule.version == rule_version:
                return rule
        return None

    def get_version_history(self, rule_id: str) -> List[CursorRule]:
        """获取规则的版本历史"""
        return self.version_history.get(rule_id, [])

    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """比较版本号"""
        try:
            return version.parse(version1) > version.parse(version2)
        except Exception:
            # 如果版本号格式不标准，按字符串比较
            return version1 > version2


class RuleConflictDetector:
    """规则冲突检测器"""

    def __init__(self):
        self.conflict_cache: Dict[str, Set[str]] = {}

    def detect_conflicts(
        self, rule: CursorRule, all_rules: List[CursorRule]
    ) -> List[Dict[str, Any]]:
        """检测规则冲突"""
        conflicts = []

        for other_rule in all_rules:
            if other_rule.rule_id == rule.rule_id:
                continue

            # 检查显式冲突声明
            if other_rule.rule_id in rule.conflicts_with:
                conflicts.append(
                    {
                        "type": "explicit_conflict",
                        "rule_id": other_rule.rule_id,
                        "severity": "error",
                        "description": f"规则 {rule.rule_id} 显式声明与 {other_rule.rule_id} 冲突",
                    }
                )

            # 检查覆盖关系
            if other_rule.rule_id in rule.overrides:
                conflicts.append(
                    {
                        "type": "override",
                        "rule_id": other_rule.rule_id,
                        "severity": "warning",
                        "description": f"规则 {rule.rule_id} 覆盖了 {other_rule.rule_id}",
                    }
                )

            # 检查应用范围冲突
            scope_conflict = self._check_scope_conflict(rule, other_rule)
            if scope_conflict:
                conflicts.append(scope_conflict)

            # 检查验证工具冲突
            tool_conflict = self._check_validation_tool_conflict(rule, other_rule)
            if tool_conflict:
                conflicts.append(tool_conflict)

        return conflicts

    def _check_scope_conflict(
        self, rule1: CursorRule, rule2: CursorRule
    ) -> Optional[Dict[str, Any]]:
        """检查应用范围冲突"""
        # 检查是否有相同的适用范围
        common_languages = set(rule1.languages) & set(rule2.languages)
        common_domains = set(rule1.domains) & set(rule2.domains)
        common_content_types = set(ct.value for ct in rule1.content_types) & set(
            ct.value for ct in rule2.content_types
        )

        if common_languages and common_domains and common_content_types:
            # 检查是否是相同类型的规则，如果是则可能冲突
            if rule1.rule_type == rule2.rule_type:
                return {
                    "type": "scope_overlap",
                    "rule_id": rule2.rule_id,
                    "severity": "warning",
                    "description": f"规则 {rule1.rule_id} 和 {rule2.rule_id} 在相同范围内有重叠",
                    "details": {
                        "common_languages": list(common_languages),
                        "common_domains": list(common_domains),
                        "common_content_types": list(common_content_types),
                    },
                }

        return None

    def _check_validation_tool_conflict(
        self, rule1: CursorRule, rule2: CursorRule
    ) -> Optional[Dict[str, Any]]:
        """检查验证工具冲突"""
        if not rule1.validation.tools or not rule2.validation.tools:
            return None

        common_tools = set(rule1.validation.tools) & set(rule2.validation.tools)
        if common_tools:
            # 如果使用相同的验证工具但严重程度不同，可能有冲突
            if rule1.validation.severity != rule2.validation.severity:
                return {
                    "type": "validation_tool_conflict",
                    "rule_id": rule2.rule_id,
                    "severity": "info",
                    "description": f"规则 {rule1.rule_id} 和 {rule2.rule_id} 使用相同验证工具但严重程度不同",
                    "details": {
                        "common_tools": list(common_tools),
                        "severity1": rule1.validation.severity.value,
                        "severity2": rule2.validation.severity.value,
                    },
                }

        return None


class RuleDatabase:
    """规则数据库管理器"""

    def __init__(self, data_dir: str = "data/rules"):
        """
        初始化规则数据库
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir
        self.logger = logging.getLogger(__name__)
        self.version_manager = RuleVersionManager()
        self.conflict_detector = RuleConflictDetector()
        self.rules: Dict[str, CursorRule] = {}
        self.rule_index: Dict[str, Set[str]] = {  # 索引
            "languages": {},
            "domains": {},
            "types": {},
            "tags": {},
        }
        self._initialized = False
        self.load_rules()

    def load_rules(self):
        """加载所有规则"""
        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 遍历所有规则文件
        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            rules_data = json.load(f)
                            if isinstance(rules_data, list):
                                for rule_data in rules_data:
                                    rule = CursorRule(**rule_data)
                                    self.rules[rule.rule_id] = rule
                            else:
                                rule = CursorRule(**rules_data)
                                self.rules[rule.rule_id] = rule
                    except Exception as e:
                        logger.error(f"加载规则文件 {file_path} 失败: {str(e)}")

    async def initialize(self) -> None:
        """初始化数据库"""
        if self._initialized:
            return

        await self._build_indexes()
        await self._detect_all_conflicts()
        self._initialized = True

        logger.info(f"规则数据库初始化完成，加载了 {len(self.rules)} 条规则")

    async def _build_indexes(self) -> None:
        """构建搜索索引"""
        self.rule_index = {"languages": {}, "domains": {}, "types": {}, "tags": {}}

        for rule_id, rule in self.rules.items():
            # 语言索引
            for lang in rule.languages:
                if lang not in self.rule_index["languages"]:
                    self.rule_index["languages"][lang] = set()
                self.rule_index["languages"][lang].add(rule_id)

            # 领域索引
            for domain in rule.domains:
                if domain not in self.rule_index["domains"]:
                    self.rule_index["domains"][domain] = set()
                self.rule_index["domains"][domain].add(rule_id)

            # 类型索引
            rule_type = rule.rule_type.value
            if rule_type not in self.rule_index["types"]:
                self.rule_index["types"][rule_type] = set()
            self.rule_index["types"][rule_type].add(rule_id)

            # 标签索引
            for tag in rule.tags:
                if tag not in self.rule_index["tags"]:
                    self.rule_index["tags"][tag] = set()
                self.rule_index["tags"][tag].add(rule_id)

    async def _detect_all_conflicts(self) -> None:
        """检测所有规则冲突"""
        all_rules = list(self.rules.values())

        for rule in all_rules:
            conflicts = self.conflict_detector.detect_conflicts(rule, all_rules)
            if conflicts:
                logger.info(f"规则 {rule.rule_id} 检测到 {len(conflicts)} 个冲突")
                for conflict in conflicts:
                    if conflict["severity"] == "error":
                        logger.error(f"冲突: {conflict['description']}")
                    else:
                        logger.warning(f"冲突: {conflict['description']}")

    def get_rule(
        self, rule_id: str, version: Optional[str] = None
    ) -> Optional[CursorRule]:
        """获取规则"""
        if version:
            return self.version_manager.get_rule_version(rule_id, version)
        else:
            return self.rules.get(rule_id)

    def get_rules_by_language(self, language: str) -> List[CursorRule]:
        """按语言获取规则"""
        rule_ids = self.rule_index["languages"].get(language, set())
        return [self.rules[rid] for rid in rule_ids if rid in self.rules]

    def get_rules_by_domain(self, domain: str) -> List[CursorRule]:
        """按领域获取规则"""
        rule_ids = self.rule_index["domains"].get(domain, set())
        return [self.rules[rid] for rid in rule_ids if rid in self.rules]

    def get_rules_by_type(self, rule_type: RuleType) -> List[CursorRule]:
        """按类型获取规则"""
        rule_ids = self.rule_index["types"].get(rule_type.value, set())
        return [self.rules[rid] for rid in rule_ids if rid in self.rules]

    def get_rules_by_tag(self, tag: str) -> List[CursorRule]:
        """按标签获取规则"""
        rule_ids = self.rule_index["tags"].get(tag, set())
        return [self.rules[rid] for rid in rule_ids if rid in self.rules]

    async def add_rule(
        self, rule: CursorRule, file_path: Optional[Path] = None
    ) -> bool:
        """添加新规则"""
        # 检测冲突
        conflicts = self.conflict_detector.detect_conflicts(
            rule, list(self.rules.values())
        )
        if any(c["severity"] == "error" for c in conflicts):
            logger.error(f"规则 {rule.rule_id} 有严重冲突，无法添加")
            return False

        # 添加到版本管理器
        if not self.version_manager.add_rule_version(rule):
            return False

        # 更新主规则字典
        if rule.active:
            self.rules[rule.rule_id] = rule

        # 重建索引
        await self._build_indexes()

        # 保存到文件
        if file_path:
            self.save_rule(rule, merge=False, append_mode=False)

        logger.info(f"成功添加规则 {rule.rule_id} v{rule.version}")
        return True

    async def update_rule(self, rule: CursorRule) -> bool:
        """更新规则"""
        # 增加版本号
        if rule.rule_id in self.version_manager.latest_versions:
            current_version = self.version_manager.latest_versions[rule.rule_id]
            try:
                parsed_version = version.parse(current_version)
                new_version = f"{parsed_version.major}.{parsed_version.minor}.{parsed_version.micro + 1}"
                rule.version = new_version
            except Exception:
                # 如果版本号解析失败，使用时间戳
                rule.version = f"{current_version}.{int(datetime.now().timestamp())}"

        rule.updated_at = datetime.now(timezone.utc)

        return await self.add_rule(rule)

    def save_rule(self, rule: CursorRule, merge: bool = False, append_mode: bool = False) -> None:
        """
        保存规则到文件系统
        
        Args:
            rule: 要保存的规则
            merge: 是否合并已存在的规则
            append_mode: 是否为追加模式，用于分批导入大文件
        """
        try:
            # 确定保存路径
            file_path = self._get_rule_file_path(rule)
            
            # 如果是追加模式，先读取现有内容
            existing_content = None
            if append_mode and file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_content = yaml.safe_load(f)

            # 转换规则为字典
            rule_dict = self._convert_rule_for_serialization(rule)

            # 在追加模式下合并内容
            if existing_content and append_mode:
                rule_dict = self._merge_rule_dicts(existing_content, rule_dict)
            
            def format_multiline_text(text: str) -> str:
                if not text or not isinstance(text, str):
                    return text
                if '\n' in text:
                    # 使用 | 标记来保持多行文本格式，保持原始缩进
                    lines = text.split('\n')
                    # 找到最小缩进
                    min_indent = float('inf')
                    for line in lines[1:]:  # 跳过第一行
                        if line.strip():  # 只考虑非空行
                            indent = len(line) - len(line.lstrip())
                            min_indent = min(min_indent, indent)
                    min_indent = 0 if min_indent == float('inf') else min_indent
                    
                    # 调整缩进，保持相对缩进关系
                    formatted_lines = []
                    formatted_lines.append('|')  # YAML 多行文本标记
                    for line in lines:
                        if line.strip():  # 非空行
                            # 保持相对缩进，但确保至少有2个空格
                            indent = len(line) - len(line.lstrip())
                            relative_indent = max(2, indent - min_indent + 2)
                            formatted_lines.append(' ' * relative_indent + line.lstrip())
                        else:  # 空行
                            formatted_lines.append('  ')  # 保持最小缩进
                    return '\n'.join(formatted_lines)
                return text

            # 递归处理所有字段
            def process_data(data):
                if isinstance(data, dict):
                    return {k: process_data(v) for k, v in data.items()}
                elif isinstance(data, list):
                    return [process_data(item) for item in data]
                elif isinstance(data, str):
                    return format_multiline_text(data)
                return data

            rule_dict = process_data(rule_dict)

            # 保存为YAML文件，设置更大的行宽以避免自动换行
            with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(
                    rule_dict,
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    width=10000,  # 设置非常大的宽度以避免自动换行
                    indent=2,
                    default_flow_style=False
                )

            self.logger.info(f"规则已保存到 {file_path}")
        except Exception as e:
            self.logger.error(f"保存规则到文件失败: {e}")
            raise

    def _merge_rule_dicts(self, existing: dict, new: dict) -> dict:
        """合并两个规则字典"""
        result = existing.copy()
        
        for key, value in new.items():
            if key == 'rules' and isinstance(value, list):
                # 特殊处理规则列表
                existing_rules = result.get('rules', [])
                for new_rule in value:
                    if isinstance(new_rule, dict):
                        condition = new_rule.get('condition')
                        if condition:
                            # 查找并更新已存在的条件
                            found = False
                            for existing_rule in existing_rules:
                                if existing_rule.get('condition') == condition:
                                    existing_rule.update(new_rule)
                                    found = True
                                    break
                            if not found:
                                existing_rules.append(new_rule)
                result['rules'] = existing_rules
            elif value is not None:  # 只更新非空值
                result[key] = value
                
        return result

    def _convert_rule_for_serialization(self, rule: CursorRule) -> Dict[str, Any]:
        """将规则转换为可序列化的字典格式"""
        rule_dict = rule.dict()

        # 转换枚举类型为字符串值
        if "rule_type" in rule_dict:
            rule_dict["rule_type"] = (
                rule_dict["rule_type"].value
                if hasattr(rule_dict["rule_type"], "value")
                else str(rule_dict["rule_type"])
            )

        if "task_types" in rule_dict:
            rule_dict["task_types"] = [
                task_type.value if hasattr(task_type, "value") else str(task_type)
                for task_type in rule_dict["task_types"]
            ]

        if "content_types" in rule_dict:
            rule_dict["content_types"] = [
                (
                    content_type.value
                    if hasattr(content_type, "value")
                    else str(content_type)
                )
                for content_type in rule_dict["content_types"]
            ]

        # 转换验证严重程度
        if "validation" in rule_dict and "severity" in rule_dict["validation"]:
            severity = rule_dict["validation"]["severity"]
            rule_dict["validation"]["severity"] = (
                severity.value if hasattr(severity, "value") else str(severity)
            )

        # 转换日期时间为字符串
        for date_field in ["created_at", "updated_at"]:
            if date_field in rule_dict and rule_dict[date_field]:
                rule_dict[date_field] = (
                    rule_dict[date_field].isoformat()
                    if hasattr(rule_dict[date_field], "isoformat")
                    else str(rule_dict[date_field])
                )

        return rule_dict

    def get_database_stats(
        self,
        languages: List[str] = None,
        domains: List[str] = None,
        rule_types: List[RuleType] = None,
        tags: List[str] = None,
    ) -> Dict[str, Any]:
        """获取数据库统计信息

        Args:
            languages: 过滤的编程语言列表
            domains: 过滤的应用领域列表
            rule_types: 过滤的规则类型列表
            tags: 过滤的标签列表

        Returns:
            统计信息字典
        """
        # 获取所有规则或过滤后的规则
        filtered_rules = list(self.rules.values())

        # 应用过滤条件
        if languages:
            filtered_rules = [
                r
                for r in filtered_rules
                if any(lang in r.languages for lang in languages)
            ]

        if domains:
            filtered_rules = [
                r
                for r in filtered_rules
                if any(domain in r.domains for domain in domains)
            ]

        if rule_types:
            filtered_rules = [r for r in filtered_rules if r.rule_type in rule_types]

        if tags:
            filtered_rules = [
                r for r in filtered_rules if any(tag in r.tags for tag in tags)
            ]

        # 计算基本统计
        active_rules = [r for r in filtered_rules if r.active]
        total_versions = sum(
            len(versions) for versions in self.version_manager.version_history.values()
        )

        # 统计分布
        rules_by_type = {}
        rules_by_language = {}
        rules_by_domain = {}

        for rule in filtered_rules:
            # 按类型统计
            rule_type = rule.rule_type.value
            rules_by_type[rule_type] = rules_by_type.get(rule_type, 0) + 1

            # 按语言统计
            for lang in rule.languages:
                rules_by_language[lang] = rules_by_language.get(lang, 0) + 1

            # 按领域统计
            for domain in rule.domains:
                rules_by_domain[domain] = rules_by_domain.get(domain, 0) + 1

        # 计算使用统计
        total_usage = sum(rule.usage_count for rule in filtered_rules)
        success_rates = [
            rule.success_rate for rule in filtered_rules if rule.usage_count > 0
        ]
        average_success_rate = (
            sum(success_rates) / len(success_rates) if success_rates else 0.0
        )

        # 找出最常用的规则
        most_used_rule = None
        if filtered_rules:
            most_used = max(filtered_rules, key=lambda r: r.usage_count)
            if most_used.usage_count > 0:
                most_used_rule = f"{most_used.name} ({most_used.usage_count} 次)"

        return {
            "total_rules": len(filtered_rules),
            "total_versions": total_versions,
            "active_rules": len(active_rules),
            "languages": len(
                set().union(*[r.languages for r in filtered_rules])
                if filtered_rules
                else set()
            ),
            "domains": len(
                set().union(*[r.domains for r in filtered_rules])
                if filtered_rules
                else set()
            ),
            "rule_types": len(set(r.rule_type for r in filtered_rules)),
            "total_tags": len(
                set().union(*[r.tags for r in filtered_rules])
                if filtered_rules
                else set()
            ),
            "version_distribution": {
                rule_id: len(versions)
                for rule_id, versions in self.version_manager.version_history.items()
                if rule_id in [r.rule_id for r in filtered_rules]
            },
            "rules_by_type": rules_by_type,
            "rules_by_language": rules_by_language,
            "rules_by_domain": rules_by_domain,
            "usage_stats": {
                "total_usage": total_usage,
                "average_success_rate": average_success_rate,
                "most_used_rule": most_used_rule or "无",
            },
        }

    async def search_rules(
        self,
        query: str,
        languages: Optional[List[str]] = None,
        domains: Optional[List[str]] = None,
        rule_types: Optional[List[RuleType]] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[CursorRule]:
        """搜索规则"""
        results = []

        # 如果没有任何过滤条件，进行文本搜索
        if not languages and not domains and not rule_types and not tags:
            for rule in self.rules.values():
                if (
                    query.lower() in rule.name.lower()
                    or query.lower() in rule.description.lower()
                    or any(query.lower() in tag.lower() for tag in rule.tags)
                ):
                    results.append(rule)
        else:
            # 基于索引的过滤搜索
            candidate_ids = set(self.rules.keys())

            # 按语言过滤
            if languages:
                lang_ids = set()
                for lang in languages:
                    lang_ids.update(self.rule_index["languages"].get(lang, set()))
                candidate_ids &= lang_ids

            # 按领域过滤
            if domains:
                domain_ids = set()
                for domain in domains:
                    domain_ids.update(self.rule_index["domains"].get(domain, set()))
                candidate_ids &= domain_ids

            # 按类型过滤
            if rule_types:
                type_ids = set()
                for rule_type in rule_types:
                    type_ids.update(
                        self.rule_index["types"].get(rule_type.value, set())
                    )
                candidate_ids &= type_ids

            # 按标签过滤
            if tags:
                tag_ids = set()
                for tag in tags:
                    tag_ids.update(self.rule_index["tags"].get(tag, set()))
                candidate_ids &= tag_ids

            # 收集结果
            for rule_id in candidate_ids:
                if rule_id in self.rules:
                    rule = self.rules[rule_id]
                    if not query or (
                        query.lower() in rule.name.lower()
                        or query.lower() in rule.description.lower()
                    ):
                        results.append(rule)

        # 限制结果数量
        return results[:limit]

    def _get_rule_file_path(self, rule: CursorRule) -> Path:
        """获取规则文件路径"""
        return Path(self.data_dir) / f"{rule.rule_id}.{rule.version.replace('.', '_')}.yaml"


# 全局数据库实例
_rule_database: Optional[RuleDatabase] = None


def get_rule_database() -> RuleDatabase:
    """获取规则数据库实例"""
    global _rule_database
    if _rule_database is None:
        _rule_database = RuleDatabase(get_config().rules_dir)
    return _rule_database


async def initialize_rule_database() -> RuleDatabase:
    """初始化规则数据库"""
    db = get_rule_database()
    await db.initialize()
    return db
