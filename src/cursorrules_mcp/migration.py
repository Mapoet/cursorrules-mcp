"""
数据库迁移工具
将现有规则数据转换为新的数据库格式，并进行验证

Author: Mapoet
Institution: NUS/STAR
Date: 2025-01-23
License: MIT
"""

import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

from .models import (
    CursorRule, RuleType, ContentType, TaskType, ValidationSeverity,
    RuleCondition, RuleApplication, RuleValidation
)
from .database import RuleDatabase, get_rule_database
from .rule_generator import RuleGenerator


class RuleMigration:
    """规则迁移工具"""
    
    def __init__(self):
        self.migration_log: List[Dict[str, Any]] = []
    
    def migrate_legacy_rules(self, legacy_file: Path, output_dir: Path) -> List[CursorRule]:
        """迁移传统规则文件"""
        print(f"🔄 开始迁移规则文件: {legacy_file}")
        
        # 读取传统规则
        try:
            with open(legacy_file, 'r', encoding='utf-8') as f:
                legacy_data = json.load(f)
        except Exception as e:
            print(f"❌ 读取规则文件失败: {e}")
            return []
        
        if not isinstance(legacy_data, list):
            legacy_data = [legacy_data]
        
        migrated_rules = []
        for rule_data in legacy_data:
            try:
                migrated_rule = self._convert_legacy_rule(rule_data)
                migrated_rules.append(migrated_rule)
                self.migration_log.append({
                    "rule_id": migrated_rule.rule_id,
                    "status": "success",
                    "message": "成功迁移"
                })
            except Exception as e:
                self.migration_log.append({
                    "rule_id": rule_data.get("rule_id", "unknown"),
                    "status": "error",
                    "message": f"迁移失败: {e}"
                })
                print(f"⚠️ 迁移规则失败 {rule_data.get('rule_id', 'unknown')}: {e}")
        
        # 保存迁移的规则
        if migrated_rules:
            self._save_migrated_rules(migrated_rules, output_dir)
        
        print(f"✅ 迁移完成，成功迁移 {len(migrated_rules)} 条规则")
        return migrated_rules
    
    def _convert_legacy_rule(self, legacy_data: Dict[str, Any]) -> CursorRule:
        """转换传统规则格式"""
        # 基本信息
        rule_id = legacy_data["rule_id"]
        name = legacy_data["name"]
        description = legacy_data["description"]
        
        # 转换规则类型
        rule_type = self._convert_rule_type(legacy_data.get("category", "style"))
        
        # 转换内容类型
        content_types = self._convert_content_types(
            legacy_data.get("applicable_to", {}).get("content_types", ["code"])
        )
        
        # 转换任务类型（从标签推断）
        task_types = self._infer_task_types(legacy_data.get("tags", []))
        
        # 转换规则条件
        rules = self._convert_rule_conditions(legacy_data.get("rule_content", {}))
        
        # 转换应用范围
        applies_to = self._convert_application_scope(legacy_data.get("applicable_to", {}))
        
        # 转换验证信息
        validation = self._convert_validation(legacy_data.get("validation", {}))
        
        # 元数据处理
        metadata = legacy_data.get("metadata", {})
        version = metadata.get("version", "1.0.0")
        author = metadata.get("author", "Unknown")
        
        # 创建时间
        created_at = datetime.now(timezone.utc)
        if "created_at" in metadata:
            try:
                created_at = datetime.fromisoformat(metadata["created_at"].replace('Z', '+00:00'))
            except:
                pass
        
        # 更新时间
        updated_at = datetime.now(timezone.utc)
        if "updated_at" in metadata:
            try:
                updated_at = datetime.fromisoformat(metadata["updated_at"].replace('Z', '+00:00'))
            except:
                pass
        
        return CursorRule(
            rule_id=rule_id,
            name=name,
            description=description,
            version=version,
            author=author,
            created_at=created_at,
            updated_at=updated_at,
            rule_type=rule_type,
            languages=legacy_data.get("applicable_to", {}).get("languages", []),
            domains=legacy_data.get("applicable_to", {}).get("domains", []),
            task_types=task_types,
            content_types=content_types,
            tags=legacy_data.get("tags", []),
            rules=rules,
            applies_to=applies_to,
            validation=validation,
            active=True,
            usage_count=0,
            success_rate=0.0
        )
    
    def _convert_rule_type(self, category: str) -> RuleType:
        """转换规则类型"""
        type_mapping = {
            "style": RuleType.STYLE,
            "content": RuleType.CONTENT,
            "semantic": RuleType.CONTENT,
            "performance": RuleType.PERFORMANCE,
            "format": RuleType.FORMAT,
            "security": RuleType.SECURITY
        }
        return type_mapping.get(category.lower(), RuleType.STYLE)
    
    def _convert_content_types(self, legacy_types: List[str]) -> List[ContentType]:
        """转换内容类型"""
        type_mapping = {
            "code": ContentType.CODE,
            "documentation": ContentType.DOCUMENTATION,
            "data_interface": ContentType.DATA,
            "algorithm": ContentType.ALGORITHM,
            "configuration": ContentType.CONFIGURATION
        }
        
        result = []
        for legacy_type in legacy_types:
            content_type = type_mapping.get(legacy_type.lower())
            if content_type and content_type not in result:
                result.append(content_type)
        
        return result or [ContentType.CODE]
    
    def _infer_task_types(self, tags: List[str]) -> List[TaskType]:
        """从标签推断任务类型"""
        task_mapping = {
            "documentation": TaskType.DOCUMENTATION,
            "testing": TaskType.TESTING,
            "refactoring": TaskType.REFACTORING,
            "debugging": TaskType.DEBUGGING,
            "optimization": TaskType.OPTIMIZATION,
            "review": TaskType.CODE_REVIEW
        }
        
        result = []
        for tag in tags:
            task_type = task_mapping.get(tag.lower())
            if task_type and task_type not in result:
                result.append(task_type)
        
        return result
    
    def _convert_rule_conditions(self, rule_content: Dict[str, Any]) -> List[RuleCondition]:
        """转换规则条件"""
        conditions = []
        
        guideline = rule_content.get("guideline", "")
        examples = rule_content.get("examples", [])
        pattern = rule_content.get("pattern")
        
        # 创建主要条件
        main_condition = RuleCondition(
            condition=rule_content.get("condition", "main_rule"),
            guideline=guideline,
            priority=8,  # 默认优先级
            examples=examples,
            pattern=pattern
        )
        
        conditions.append(main_condition)
        
        return conditions
    
    def _convert_application_scope(self, applicable_to: Dict[str, Any]) -> RuleApplication:
        """转换应用范围"""
        return RuleApplication(
            file_patterns=applicable_to.get("file_patterns", []),
            exclude_patterns=applicable_to.get("exclude_patterns", []),
            min_file_size=applicable_to.get("min_file_size", 0),
            max_file_size=applicable_to.get("max_file_size", 1000000),
            requires_context=applicable_to.get("requires_context", False)
        )
    
    def _convert_validation(self, validation_data: Dict[str, Any]) -> RuleValidation:
        """转换验证信息"""
        # 转换严重程度
        severity_mapping = {
            "error": ValidationSeverity.ERROR,
            "warning": ValidationSeverity.WARNING,
            "info": ValidationSeverity.INFO
        }
        
        severity = severity_mapping.get(
            validation_data.get("severity", "warning").lower(),
            ValidationSeverity.WARNING
        )
        
        return RuleValidation(
            tools=validation_data.get("tools", []),
            severity=severity,
            auto_fix=validation_data.get("auto_fix", False),
            timeout=validation_data.get("timeout", 30),
            custom_config=validation_data.get("custom_config", {})
        )
    
    def _save_migrated_rules(self, rules: List[CursorRule], output_dir: Path) -> None:
        """保存迁移的规则"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存为YAML格式（更易读）
        migrated_file = output_dir / "migrated_rules.yaml"
        rules_data = [rule.dict() for rule in rules]
        
        with open(migrated_file, 'w', encoding='utf-8') as f:
            yaml.dump(rules_data, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ 迁移的规则已保存到 {migrated_file}")
        
        # 保存迁移日志
        log_file = output_dir / "migration_log.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                "migration_date": datetime.now(timezone.utc).isoformat(),
                "total_rules": len(rules),
                "migration_log": self.migration_log
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 迁移日志已保存到 {log_file}")


async def perform_database_migration():
    """执行完整的数据库迁移"""
    print("🚀 开始规则库数据化迁移...")
    
    # 1. 迁移现有规则
    migration = RuleMigration()
    legacy_file = Path("examples/sample-rules.json")
    output_dir = Path("data/rules/migrated")
    
    migrated_rules = []
    if legacy_file.exists():
        migrated_rules = migration.migrate_legacy_rules(legacy_file, output_dir)
    else:
        print(f"⚠️ 传统规则文件不存在: {legacy_file}")
    
    # 2. 生成扩展规则
    print("\n📚 生成扩展规则库...")
    generator = RuleGenerator()
    generated_rules = generator.generate_comprehensive_ruleset()
    
    # 保存生成的规则
    generated_dir = Path("data/rules/generated")
    generator.save_rules_to_database(generated_rules, generated_dir)
    
    # 3. 初始化数据库并加载所有规则
    print("\n🗄️ 初始化规则数据库...")
    database = get_rule_database()
    await database.initialize()
    
    # 添加新生成的规则到数据库
    for rule in generated_rules:
        try:
            await database.add_rule(rule)
        except Exception as e:
            print(f"⚠️ 添加规则失败 {rule.rule_id}: {e}")
    
    # 4. 生成数据库统计报告
    stats = database.get_database_stats()
    
    print("\n📊 数据库统计报告:")
    print(f"  总规则数: {stats['total_rules']}")
    print(f"  总版本数: {stats['total_versions']}")
    print(f"  活跃规则: {stats['active_rules']}")
    print(f"  支持语言: {stats['languages']} 种")
    print(f"  覆盖领域: {stats['domains']} 个")
    print(f"  规则类型: {stats['rule_types']} 种")
    print(f"  标签总数: {stats['total_tags']} 个")
    
    # 5. 保存统计报告
    report_file = Path("data/rules/database_report.json")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "migration_date": datetime.now(timezone.utc).isoformat(),
            "migrated_rules": len(migrated_rules),
            "generated_rules": len(generated_rules),
            "database_stats": stats
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 数据库迁移完成！报告已保存到 {report_file}")
    
    return database


if __name__ == "__main__":
    # 执行迁移
    asyncio.run(perform_database_migration())