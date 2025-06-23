"""
规则数据库管理模块
提供规则的存储、版本管理、冲突检测等功能

Author: Mapoet
Institution: NUS/STAR
Date: 2025-01-23
License: MIT
"""

import json
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from packaging import version
import yaml

from .models import CursorRule, RuleType, ValidationSeverity
from .config import get_config

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
        self.version_history[rule_id].sort(
            key=lambda r: version.parse(r.version)
        )
        
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
    
    def detect_conflicts(self, rule: CursorRule, all_rules: List[CursorRule]) -> List[Dict[str, Any]]:
        """检测规则冲突"""
        conflicts = []
        
        for other_rule in all_rules:
            if other_rule.rule_id == rule.rule_id:
                continue
            
            # 检查显式冲突声明
            if other_rule.rule_id in rule.conflicts_with:
                conflicts.append({
                    "type": "explicit_conflict",
                    "rule_id": other_rule.rule_id,
                    "severity": "error",
                    "description": f"规则 {rule.rule_id} 显式声明与 {other_rule.rule_id} 冲突"
                })
            
            # 检查覆盖关系
            if other_rule.rule_id in rule.overrides:
                conflicts.append({
                    "type": "override",
                    "rule_id": other_rule.rule_id,
                    "severity": "warning",
                    "description": f"规则 {rule.rule_id} 覆盖了 {other_rule.rule_id}"
                })
            
            # 检查应用范围冲突
            scope_conflict = self._check_scope_conflict(rule, other_rule)
            if scope_conflict:
                conflicts.append(scope_conflict)
            
            # 检查验证工具冲突
            tool_conflict = self._check_validation_tool_conflict(rule, other_rule)
            if tool_conflict:
                conflicts.append(tool_conflict)
        
        return conflicts
    
    def _check_scope_conflict(self, rule1: CursorRule, rule2: CursorRule) -> Optional[Dict[str, Any]]:
        """检查应用范围冲突"""
        # 检查是否有相同的适用范围
        common_languages = set(rule1.languages) & set(rule2.languages)
        common_domains = set(rule1.domains) & set(rule2.domains)
        common_content_types = set(ct.value for ct in rule1.content_types) & \
                              set(ct.value for ct in rule2.content_types)
        
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
                        "common_content_types": list(common_content_types)
                    }
                }
        
        return None
    
    def _check_validation_tool_conflict(self, rule1: CursorRule, rule2: CursorRule) -> Optional[Dict[str, Any]]:
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
                        "severity2": rule2.validation.severity.value
                    }
                }
        
        return None


class RuleDatabase:
    """规则数据库管理器"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(get_config().rules_dir)
        self.version_manager = RuleVersionManager()
        self.conflict_detector = RuleConflictDetector()
        self.rules: Dict[str, CursorRule] = {}  # rule_id -> latest_rule
        self.rule_index: Dict[str, Set[str]] = {  # 索引
            "languages": {},
            "domains": {},
            "types": {},
            "tags": {}
        }
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化数据库"""
        if self._initialized:
            return
        
        await self._load_rules()
        await self._build_indexes()
        await self._detect_all_conflicts()
        self._initialized = True
        
        logger.info(f"规则数据库初始化完成，加载了 {len(self.rules)} 条规则")
    
    async def _load_rules(self) -> None:
        """从文件系统加载规则"""
        if not self.data_dir.exists():
            logger.warning(f"规则目录不存在: {self.data_dir}")
            return
        
        loaded_count = 0
        for file_path in self.data_dir.rglob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 支持单个规则或规则列表
                if isinstance(data, dict):
                    data = [data]
                
                for rule_data in data:
                    rule = CursorRule(**rule_data)
                    if self.version_manager.add_rule_version(rule):
                        loaded_count += 1
                        
            except Exception as e:
                logger.error(f"加载规则文件失败 {file_path}: {e}")
        
        # 加载YAML文件
        for file_path in self.data_dir.rglob("*.yaml"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if isinstance(data, dict):
                    data = [data]
                
                for rule_data in data:
                    rule = CursorRule(**rule_data)
                    if self.version_manager.add_rule_version(rule):
                        loaded_count += 1
                        
            except Exception as e:
                logger.error(f"加载规则文件失败 {file_path}: {e}")
        
        # 更新主规则字典
        for rule_id in self.version_manager.latest_versions:
            latest_rule = self.version_manager.get_latest_rule(rule_id)
            if latest_rule and latest_rule.active:
                self.rules[rule_id] = latest_rule
        
        logger.info(f"从文件系统加载了 {loaded_count} 条规则")
    
    async def _build_indexes(self) -> None:
        """构建搜索索引"""
        self.rule_index = {
            "languages": {},
            "domains": {},
            "types": {},
            "tags": {}
        }
        
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
    
    def get_rule(self, rule_id: str, version: Optional[str] = None) -> Optional[CursorRule]:
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
    
    async def add_rule(self, rule: CursorRule, file_path: Optional[Path] = None) -> bool:
        """添加新规则"""
        # 检测冲突
        conflicts = self.conflict_detector.detect_conflicts(rule, list(self.rules.values()))
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
            await self._save_rule_to_file(rule, file_path)
        
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
    
    async def _save_rule_to_file(self, rule: CursorRule, file_path: Path) -> None:
        """保存规则到文件"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.suffix == '.yaml':
                    yaml.dump(rule.dict(), f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(rule.dict(), f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"规则已保存到 {file_path}")
        except Exception as e:
            logger.error(f"保存规则到文件失败 {file_path}: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        total_versions = sum(len(versions) for versions in self.version_manager.version_history.values())
        
        return {
            "total_rules": len(self.rules),
            "total_versions": total_versions,
            "active_rules": len([r for r in self.rules.values() if r.active]),
            "languages": len(self.rule_index["languages"]),
            "domains": len(self.rule_index["domains"]),
            "rule_types": len(self.rule_index["types"]),
            "total_tags": len(self.rule_index["tags"]),
            "version_distribution": {
                rule_id: len(versions) 
                for rule_id, versions in self.version_manager.version_history.items()
            }
        }
    
    async def search_rules(self, query: str, languages: Optional[List[str]] = None, 
                          domains: Optional[List[str]] = None, rule_types: Optional[List[RuleType]] = None,
                          tags: Optional[List[str]] = None, limit: int = 50) -> List[CursorRule]:
        """搜索规则"""
        results = []
        
        # 如果没有任何过滤条件，进行文本搜索
        if not languages and not domains and not rule_types and not tags:
            for rule in self.rules.values():
                if (query.lower() in rule.name.lower() or 
                    query.lower() in rule.description.lower() or
                    any(query.lower() in tag.lower() for tag in rule.tags)):
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
                    type_ids.update(self.rule_index["types"].get(rule_type.value, set()))
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
                    if not query or (query.lower() in rule.name.lower() or 
                                   query.lower() in rule.description.lower()):
                        results.append(rule)
        
        # 限制结果数量
        return results[:limit]


# 全局数据库实例
_rule_database: Optional[RuleDatabase] = None


def get_rule_database() -> RuleDatabase:
    """获取规则数据库实例"""
    global _rule_database
    if _rule_database is None:
        _rule_database = RuleDatabase()
    return _rule_database


async def initialize_rule_database() -> RuleDatabase:
    """初始化规则数据库"""
    db = get_rule_database()
    await db.initialize()
    return db