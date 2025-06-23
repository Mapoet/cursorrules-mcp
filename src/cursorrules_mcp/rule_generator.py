"""
规则生成器
用于创建丰富的规则库内容
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any
import uuid

from .models import (
    CursorRule, RuleType, ContentType, TaskType, ValidationSeverity,
    RuleCondition, RuleApplication, RuleValidation
)


class RuleGenerator:
    """规则生成器"""
    
    def __init__(self):
        self.rule_templates = {
            "python": self._create_python_rules,
            "cpp": self._create_cpp_rules,
            "javascript": self._create_javascript_rules,
            "documentation": self._create_documentation_rules,
            "scientific": self._create_scientific_rules,
            "web": self._create_web_rules,
            "database": self._create_database_rules,
            "security": self._create_security_rules,
        }
    
    def generate_comprehensive_ruleset(self) -> List[CursorRule]:
        """生成完整的规则集"""
        all_rules = []
        
        for category, generator in self.rule_templates.items():
            try:
                rules = generator()
                all_rules.extend(rules)
                print(f"✅ 生成 {category} 类别规则: {len(rules)} 条")
            except Exception as e:
                print(f"❌ 生成 {category} 类别规则失败: {e}")
        
        print(f"🎉 总计生成规则: {len(all_rules)} 条")
        return all_rules
    
    def _create_base_rule(self, rule_id: str, name: str, description: str, 
                         rule_type: RuleType, author: str = "RuleGenerator") -> CursorRule:
        """创建基础规则模板"""
        return CursorRule(
            rule_id=rule_id,
            name=name,
            description=description,
            version="1.0.0",
            author=author,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            rule_type=rule_type,
            rules=[],
            applies_to=RuleApplication(),
            validation=RuleValidation(severity=ValidationSeverity.WARNING)
        )
    
    def _create_python_rules(self) -> List[CursorRule]:
        """创建Python规则"""
        rules = []
        
        # PEP8样式规则
        rule = self._create_base_rule(
            "CR-PY-STYLE-002", 
            "Python导入语句规范",
            "Python导入语句应遵循PEP8规范：标准库、第三方库、本地模块分组，按字母排序",
            RuleType.STYLE
        )
        rule.languages = ["python"]
        rule.domains = ["all"]
        rule.content_types = [ContentType.CODE]
        rule.tags = ["python", "pep8", "imports", "organization"]
        rule.rules = [
            RuleCondition(
                condition="import_organization",
                guideline="导入语句应分为三组：1)标准库 2)第三方库 3)本地模块，组间用空行分隔，组内按字母排序",
                priority=8,
                examples=[{
                    "good": "import os\nimport sys\n\nimport numpy as np\nimport pandas as pd\n\nfrom .models import CursorRule\nfrom .utils import helper_function",
                    "bad": "from .models import CursorRule\nimport numpy as np\nimport os\nfrom .utils import helper_function\nimport pandas as pd",
                    "explanation": "正确的导入顺序提高代码可读性和维护性"
                }]
            )
        ]
        rule.validation = RuleValidation(
            tools=["isort", "flake8"],
            severity=ValidationSeverity.WARNING
        )
        rules.append(rule)
        
        # 异常处理规则
        rule = self._create_base_rule(
            "CR-PY-ERROR-001",
            "Python异常处理最佳实践",
            "Python异常处理应具体化异常类型，避免裸露的except子句，提供有意义的错误信息",
            RuleType.CONTENT
        )
        rule.languages = ["python"]
        rule.domains = ["all"]
        rule.content_types = [ContentType.CODE]
        rule.tags = ["python", "exceptions", "error_handling", "best_practices"]
        rule.rules = [
            RuleCondition(
                condition="specific_exception_handling",
                guideline="使用具体的异常类型，避免裸露的except，为异常提供上下文信息",
                priority=9,
                examples=[{
                    "good": "try:\n    value = int(user_input)\nexcept ValueError as e:\n    logger.error(f'无法转换输入为整数: {user_input}, 错误: {e}')\n    raise ValueError(f'输入值无效: {user_input}') from e",
                    "bad": "try:\n    value = int(user_input)\nexcept:\n    pass",
                    "explanation": "具体的异常处理提供更好的错误信息和调试能力"
                }]
            )
        ]
        rule.validation = RuleValidation(
            tools=["pylint", "flake8"],
            severity=ValidationSeverity.ERROR
        )
        rules.append(rule)
        
        # 类型注解规则
        rule = self._create_base_rule(
            "CR-PY-TYPE-001",
            "Python类型注解标准",
            "Python函数和方法应包含完整的类型注解，包括参数和返回值类型",
            RuleType.STYLE
        )
        rule.languages = ["python"]
        rule.domains = ["all"]
        rule.content_types = [ContentType.CODE]
        rule.tags = ["python", "typing", "annotations", "mypy"]
        rule.rules = [
            RuleCondition(
                condition="type_annotations",
                guideline="所有公共函数必须包含类型注解，使用Union、Optional等类型提示",
                priority=7,
                examples=[{
                    "good": "from typing import List, Optional, Union\n\ndef process_data(data: List[str], threshold: Optional[float] = None) -> Union[List[str], None]:\n    \"\"\"处理数据\"\"\"\n    if threshold is None:\n        return data\n    return [item for item in data if len(item) >= threshold]",
                    "bad": "def process_data(data, threshold=None):\n    if threshold is None:\n        return data\n    return [item for item in data if len(item) >= threshold]",
                    "explanation": "类型注解提高代码可读性和IDE支持"
                }]
            )
        ]
        rule.validation = RuleValidation(
            tools=["mypy"],
            severity=ValidationSeverity.WARNING
        )
        rules.append(rule)
        
        return rules
    
    def _create_cpp_rules(self) -> List[CursorRule]:
        """创建C++规则"""
        rules = []
        
        # RAII规则
        rule = self._create_base_rule(
            "CR-CPP-RAII-001",
            "C++ RAII资源管理",
            "C++代码应使用RAII模式管理资源，优先使用智能指针而不是原始指针",
            RuleType.CONTENT
        )
        rule.languages = ["cpp"]
        rule.domains = ["all"]
        rule.content_types = [ContentType.CODE]
        rule.tags = ["cpp", "raii", "memory_management", "smart_pointers"]
        rule.rules = [
            RuleCondition(
                condition="raii_resource_management",
                guideline="使用std::unique_ptr、std::shared_ptr等智能指针管理动态内存，避免手动new/delete",
                priority=9,
                examples=[{
                    "good": "#include <memory>\n\nclass DataProcessor {\npublic:\n    DataProcessor() : data_(std::make_unique<std::vector<double>>()) {}\n    \nprivate:\n    std::unique_ptr<std::vector<double>> data_;\n};",
                    "bad": "class DataProcessor {\npublic:\n    DataProcessor() : data_(new std::vector<double>()) {}\n    ~DataProcessor() { delete data_; }\n    \nprivate:\n    std::vector<double>* data_;\n};",
                    "explanation": "智能指针自动管理内存，避免内存泄漏"
                }]
            )
        ]
        rule.validation = RuleValidation(
            tools=["clang-tidy", "cppcheck"],
            severity=ValidationSeverity.ERROR
        )
        rules.append(rule)
        
        # 现代C++特性规则
        rule = self._create_base_rule(
            "CR-CPP-MODERN-001",
            "现代C++特性使用",
            "优先使用C++11/14/17的现代特性，如auto、范围for循环、lambda表达式等",
            RuleType.STYLE
        )
        rule.languages = ["cpp"]
        rule.domains = ["all"]
        rule.content_types = [ContentType.CODE]
        rule.tags = ["cpp", "modern_cpp", "auto", "lambda", "range_for"]
        rule.rules = [
            RuleCondition(
                condition="modern_cpp_features",
                guideline="使用auto推导类型，范围for循环遍历容器，lambda表达式简化代码",
                priority=7,
                examples=[{
                    "good": "std::vector<int> numbers = {1, 2, 3, 4, 5};\n\n// 使用范围for循环\nfor (const auto& num : numbers) {\n    std::cout << num << std::endl;\n}\n\n// 使用lambda和算法\nauto is_even = [](int n) { return n % 2 == 0; };\nauto count = std::count_if(numbers.begin(), numbers.end(), is_even);",
                    "bad": "std::vector<int> numbers;\nnumbers.push_back(1);\nnumbers.push_back(2);\n\n// 传统for循环\nfor (std::vector<int>::iterator it = numbers.begin(); it != numbers.end(); ++it) {\n    std::cout << *it << std::endl;\n}",
                    "explanation": "现代C++特性使代码更简洁、安全和高效"
                }]
            )
        ]
        rules.append(rule)
        
        return rules
    
    def _create_javascript_rules(self) -> List[CursorRule]:
        """创建JavaScript规则"""
        rules = []
        
        # ES6+特性规则
        rule = self._create_base_rule(
            "CR-JS-ES6-001",
            "JavaScript ES6+特性使用",
            "优先使用ES6+特性：const/let、箭头函数、模板字符串、解构赋值等",
            RuleType.STYLE
        )
        rule.languages = ["javascript", "typescript"]
        rule.domains = ["web", "node"]
        rule.content_types = [ContentType.CODE]
        rule.tags = ["javascript", "es6", "arrow_functions", "destructuring", "const_let"]
        rule.rules = [
            RuleCondition(
                condition="modern_javascript",
                guideline="使用const/let替代var，箭头函数替代function，模板字符串替代字符串拼接",
                priority=8,
                examples=[{
                    "good": "const users = [\n  { id: 1, name: 'Alice', email: 'alice@example.com' },\n  { id: 2, name: 'Bob', email: 'bob@example.com' }\n];\n\nconst getActiveUsers = () => {\n  return users.filter(user => user.active);\n};\n\nconst formatUser = ({ name, email }) => {\n  return `${name} <${email}>`;\n};",
                    "bad": "var users = [\n  { id: 1, name: 'Alice', email: 'alice@example.com' },\n  { id: 2, name: 'Bob', email: 'bob@example.com' }\n];\n\nfunction getActiveUsers() {\n  return users.filter(function(user) {\n    return user.active;\n  });\n}\n\nfunction formatUser(user) {\n  return user.name + ' <' + user.email + '>';\n}",
                    "explanation": "现代JavaScript特性提高代码可读性和维护性"
                }]
            )
        ]
        rule.validation = RuleValidation(
            tools=["eslint"],
            severity=ValidationSeverity.WARNING
        )
        rules.append(rule)
        
        return rules
    
    def _create_documentation_rules(self) -> List[CursorRule]:
        """创建文档规则"""
        rules = []
        
        # API文档规则
        rule = self._create_base_rule(
            "CR-DOC-API-001",
            "API文档标准格式",
            "API文档应包含完整的端点描述、参数说明、响应格式和错误码",
            RuleType.FORMAT
        )
        rule.languages = ["markdown", "openapi"]
        rule.domains = ["api", "web"]
        rule.content_types = [ContentType.DOCUMENTATION]
        rule.tags = ["api", "documentation", "openapi", "rest"]
        rule.rules = [
            RuleCondition(
                condition="complete_api_documentation",
                guideline="每个API端点必须包含：描述、HTTP方法、URL路径、参数、响应示例、错误码",
                priority=9,
                examples=[{
                    "good": "## POST /api/users\n\n创建新用户\n\n### 参数\n- `name` (string, required): 用户姓名\n- `email` (string, required): 用户邮箱\n- `age` (integer, optional): 用户年龄\n\n### 响应\n\n**成功 (201)**\n```json\n{\n  \"id\": 123,\n  \"name\": \"张三\",\n  \"email\": \"zhangsan@example.com\",\n  \"created_at\": \"2024-01-01T00:00:00Z\"\n}\n```\n\n**错误 (400)**\n```json\n{\n  \"error\": \"邮箱格式无效\",\n  \"code\": \"INVALID_EMAIL\"\n}\n```",
                    "bad": "## 创建用户\n\n发送POST请求到/api/users创建用户",
                    "explanation": "完整的API文档帮助开发者正确使用接口"
                }]
            )
        ]
        rules.append(rule)
        
        return rules
    
    def _create_scientific_rules(self) -> List[CursorRule]:
        """创建科学计算规则"""
        rules = []
        
        # 数值精度规则
        rule = self._create_base_rule(
            "CR-SCI-PRECISION-001",
            "科学计算数值精度标准",
            "科学计算中必须明确指定数值精度，避免浮点误差，使用适当的数值类型",
            RuleType.CONTENT
        )
        rule.languages = ["python", "cpp", "fortran"]
        rule.domains = ["meteorology", "geophysics", "oceanography", "numerical_computation"]
        rule.content_types = [ContentType.CODE, ContentType.ALGORITHM]
        rule.tags = ["scientific", "numerical", "precision", "floating_point"]
        rule.rules = [
            RuleCondition(
                condition="numerical_precision",
                guideline="使用Decimal或高精度库处理精确计算，明确指定容差和收敛条件",
                priority=10,
                examples=[{
                    "good": "import numpy as np\nfrom decimal import Decimal, getcontext\n\n# 设置精度\ngetcontext().prec = 50\n\ndef calculate_atmospheric_pressure(altitude_m: float, tolerance: float = 1e-6) -> float:\n    \"\"\"\n    计算大气压力，使用标准大气模型\n    \n    Args:\n        altitude_m: 海拔高度（米）\n        tolerance: 计算容差\n    \n    Returns:\n        大气压力（帕斯卡）\n    \"\"\"\n    # 标准大气压\n    p0 = Decimal('101325.0')  # Pa\n    # 重力加速度\n    g = Decimal('9.80665')    # m/s²\n    # 气体常数\n    R = Decimal('287.05')     # J/(kg·K)\n    # 标准温度\n    T0 = Decimal('288.15')    # K\n    \n    h = Decimal(str(altitude_m))\n    pressure = p0 * (1 - g * h / (R * T0)) ** (g / R)\n    \n    return float(pressure)",
                    "bad": "def calculate_pressure(altitude):\n    return 101325 * (1 - 0.0065 * altitude / 288.15) ** 5.255",
                    "explanation": "明确的精度控制确保科学计算的准确性和可重复性"
                }]
            )
        ]
        rule.validation = RuleValidation(
            tools=["numerical_validator"],
            severity=ValidationSeverity.ERROR
        )
        rules.append(rule)
        
        return rules
    
    def _create_web_rules(self) -> List[CursorRule]:
        """创建Web开发规则"""
        rules = []
        
        # 响应式设计规则
        rule = self._create_base_rule(
            "CR-WEB-RESPONSIVE-001",
            "响应式设计标准",
            "Web界面必须支持响应式设计，适配移动设备和不同屏幕尺寸",
            RuleType.FORMAT
        )
        rule.languages = ["css", "html", "javascript"]
        rule.domains = ["web", "frontend"]
        rule.content_types = [ContentType.CODE]
        rule.tags = ["web", "responsive", "css", "mobile", "media_queries"]
        rule.rules = [
            RuleCondition(
                condition="responsive_design",
                guideline="使用媒体查询、flexbox/grid布局，确保在不同设备上的良好体验",
                priority=8,
                examples=[{
                    "good": "/* 移动优先设计 */\n.container {\n  display: flex;\n  flex-direction: column;\n  padding: 1rem;\n}\n\n.card {\n  width: 100%;\n  margin-bottom: 1rem;\n}\n\n/* 平板设备 */\n@media (min-width: 768px) {\n  .container {\n    flex-direction: row;\n    flex-wrap: wrap;\n    padding: 2rem;\n  }\n  \n  .card {\n    width: calc(50% - 1rem);\n    margin-right: 1rem;\n  }\n}\n\n/* 桌面设备 */\n@media (min-width: 1024px) {\n  .card {\n    width: calc(33.333% - 1rem);\n  }\n}",
                    "bad": ".container {\n  width: 1200px;\n  margin: 0 auto;\n}\n\n.card {\n  width: 300px;\n  float: left;\n}",
                    "explanation": "响应式设计确保网站在所有设备上都有良好的用户体验"
                }]
            )
        ]
        rules.append(rule)
        
        return rules
    
    def _create_database_rules(self) -> List[CursorRule]:
        """创建数据库规则"""
        rules = []
        
        # SQL优化规则
        rule = self._create_base_rule(
            "CR-DB-OPTIMIZE-001",
            "SQL查询优化标准",
            "SQL查询应使用适当的索引、避免N+1查询、合理使用JOIN和WHERE条件",
            RuleType.PERFORMANCE
        )
        rule.languages = ["sql", "python", "javascript"]
        rule.domains = ["database", "backend"]
        rule.content_types = [ContentType.CODE]
        rule.tags = ["sql", "database", "performance", "optimization", "indexing"]
        rule.rules = [
            RuleCondition(
                condition="sql_optimization",
                guideline="使用EXPLAIN分析查询计划，创建合适的索引，避免SELECT *",
                priority=9,
                examples=[{
                    "good": "-- 使用索引的高效查询\nSELECT u.id, u.name, u.email\nFROM users u\nINNER JOIN user_profiles p ON u.id = p.user_id\nWHERE u.active = true\n  AND u.created_at >= '2024-01-01'\n  AND p.department = 'engineering'\nORDER BY u.created_at DESC\nLIMIT 50;\n\n-- 创建支持查询的复合索引\nCREATE INDEX idx_users_active_created ON users(active, created_at);\nCREATE INDEX idx_profiles_department ON user_profiles(department);",
                    "bad": "-- 低效查询\nSELECT *\nFROM users u, user_profiles p\nWHERE u.id = p.user_id\nORDER BY u.created_at;",
                    "explanation": "优化的SQL查询提高数据库性能和响应速度"
                }]
            )
        ]
        rules.append(rule)
        
        return rules
    
    def _create_security_rules(self) -> List[CursorRule]:
        """创建安全规则"""
        rules = []
        
        # 输入验证规则
        rule = self._create_base_rule(
            "CR-SEC-INPUT-001",
            "输入验证安全标准",
            "所有用户输入必须进行验证和净化，防止注入攻击和XSS",
            RuleType.SECURITY
        )
        rule.languages = ["python", "javascript", "sql"]
        rule.domains = ["web", "api", "backend"]
        rule.content_types = [ContentType.CODE]
        rule.tags = ["security", "input_validation", "xss", "sql_injection", "sanitization"]
        rule.rules = [
            RuleCondition(
                condition="input_validation",
                guideline="使用参数化查询、输入净化库、类型验证，永远不信任用户输入",
                priority=10,
                examples=[{
                    "good": "from pydantic import BaseModel, validator\nimport bleach\nfrom sqlalchemy import text\n\nclass UserInput(BaseModel):\n    name: str\n    email: str\n    content: str\n    \n    @validator('name')\n    def validate_name(cls, v):\n        if not v or len(v.strip()) < 2:\n            raise ValueError('姓名至少2个字符')\n        return bleach.clean(v.strip())\n    \n    @validator('email')\n    def validate_email(cls, v):\n        # 使用正则验证邮箱格式\n        import re\n        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n        if not re.match(pattern, v):\n            raise ValueError('邮箱格式无效')\n        return v.lower().strip()\n\ndef get_user_by_email(db, email: str):\n    # 使用参数化查询防止SQL注入\n    query = text('SELECT * FROM users WHERE email = :email')\n    return db.execute(query, {'email': email}).fetchone()",
                    "bad": "def get_user_by_email(db, email):\n    # SQL注入漏洞\n    query = f\"SELECT * FROM users WHERE email = '{email}'\"\n    return db.execute(query).fetchone()\n\ndef process_user_input(data):\n    # 未验证的用户输入\n    return f\"<div>用户说: {data['content']}</div>\"",
                    "explanation": "严格的输入验证是防止安全漏洞的第一道防线"
                }]
            )
        ]
        rule.validation = RuleValidation(
            tools=["bandit", "safety", "security_linter"],
            severity=ValidationSeverity.ERROR
        )
        rules.append(rule)
        
        return rules
    
    def save_rules_to_database(self, rules: List[CursorRule], output_dir: Path) -> None:
        """保存规则到数据库目录"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 按类别分组保存
        rules_by_category = {}
        for rule in rules:
            category = rule.rule_type.value
            if category not in rules_by_category:
                rules_by_category[category] = []
            rules_by_category[category].append(rule)
        
        # 保存每个类别的规则
        for category, category_rules in rules_by_category.items():
            file_path = output_dir / f"{category}_rules.json"
            rules_data = [rule.dict() for rule in category_rules]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"✅ 保存 {category} 规则到 {file_path}")
        
        # 保存所有规则的索引
        index_file = output_dir / "rule_index.json"
        index_data = {
            "total_rules": len(rules),
            "categories": {
                category: len(category_rules) 
                for category, category_rules in rules_by_category.items()
            },
            "languages": list(set(lang for rule in rules for lang in rule.languages)),
            "domains": list(set(domain for rule in rules for domain in rule.domains)),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 保存规则索引到 {index_file}")


if __name__ == "__main__":
    # 测试规则生成器
    generator = RuleGenerator()
    rules = generator.generate_comprehensive_ruleset()
    
    output_dir = Path("data/rules/generated")
    generator.save_rules_to_database(rules, output_dir)
    
    print(f"\n🎉 规则生成完成！总计 {len(rules)} 条规则")