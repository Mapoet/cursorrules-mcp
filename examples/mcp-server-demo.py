#!/usr/bin/env python3
"""
cursorrules-mcp MCP服务器演示
实现基本的规则检索、验证和模板功能
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# MCP相关导入（示例实现）
from mcp.server import Server
from mcp.types import Tool, TextContent, Resource


@dataclass
class Rule:
    """规则数据模型"""
    rule_id: str
    name: str
    description: str
    category: str
    priority: int
    tags: List[str]
    applicable_to: Dict[str, List[str]]
    rule_content: Dict[str, Any]
    validation: Dict[str, Any]
    metadata: Dict[str, Any]


class RuleEngine:
    """规则引擎核心类"""
    
    def __init__(self, rules_path: str = "examples/sample-rules.json"):
        self.rules: List[Rule] = []
        self.rules_path = rules_path
        self._load_rules()
    
    def _load_rules(self):
        """加载规则文件"""
        try:
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
                self.rules = [Rule(**rule_data) for rule_data in rules_data]
            print(f"成功加载 {len(self.rules)} 条规则")
        except FileNotFoundError:
            print(f"规则文件 {self.rules_path} 未找到")
            self.rules = []
        except Exception as e:
            print(f"加载规则失败: {e}")
            self.rules = []
    
    async def search_rules(self, query: str = "", tags: List[str] = None, 
                          languages: List[str] = None, domains: List[str] = None) -> List[Rule]:
        """搜索匹配的规则"""
        if not self.rules:
            return []
        
        matched_rules = []
        
        for rule in self.rules:
            score = 0
            
            # 文本匹配
            if query:
                if (query.lower() in rule.name.lower() or 
                    query.lower() in rule.description.lower()):
                    score += 3
            
            # 标签匹配
            if tags:
                matching_tags = set(tags) & set(rule.tags)
                score += len(matching_tags) * 2
            
            # 语言匹配
            if languages:
                rule_languages = rule.applicable_to.get('languages', [])
                if any(lang in rule_languages for lang in languages):
                    score += 2
            
            # 领域匹配
            if domains:
                rule_domains = rule.applicable_to.get('domains', [])
                if any(domain in rule_domains for domain in domains) or 'all' in rule_domains:
                    score += 2
            
            # 如果没有搜索条件，返回所有规则
            if not any([query, tags, languages, domains]):
                score = 1
            
            if score > 0:
                matched_rules.append((rule, score))
        
        # 按分数和优先级排序
        matched_rules.sort(key=lambda x: (x[1], x[0].priority), reverse=True)
        
        return [rule for rule, _ in matched_rules[:10]]  # 最多返回10条
    
    async def validate_content(self, content: str, content_type: str = "code") -> Dict[str, Any]:
        """验证内容是否符合规则"""
        # 这里是简化的验证逻辑，实际应该更复杂
        validation_result = {
            "is_valid": True,
            "violations": [],
            "suggestions": [],
            "score": 100
        }
        
        # 检查Python代码行长度（示例）
        if content_type == "python" or "python" in content_type.lower():
            lines = content.split('\n')
            long_lines = []
            
            for i, line in enumerate(lines, 1):
                if len(line) > 79:
                    long_lines.append({
                        "line": i,
                        "length": len(line),
                        "content": line[:50] + "..." if len(line) > 50 else line,
                        "rule_violated": "CR-PY-STYLE-001"
                    })
            
            if long_lines:
                validation_result["is_valid"] = False
                validation_result["violations"].extend(long_lines)
                validation_result["suggestions"].append(
                    "建议将长行拆分为多行，每行不超过79个字符"
                )
                validation_result["score"] = max(60, 100 - len(long_lines) * 10)
        
        return validation_result
    
    async def get_templates(self, template_type: str, domain: str = None) -> List[Dict[str, str]]:
        """获取模板"""
        templates = []
        
        if template_type == "function_docstring":
            templates.append({
                "name": "Google Style Python Docstring",
                "content": '''def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """简短的函数描述。
    
    更详细的函数说明（可选）。
    
    Args:
        param1: 参数1的描述
        param2: 参数2的描述
    
    Returns:
        返回值的描述
    
    Raises:
        ExceptionType: 异常情况的描述
    """
    pass'''
            })
        
        elif template_type == "scientific_paper" and domain == "meteorology":
            templates.append({
                "name": "气象学研究论文模板",
                "content": '''# 论文标题：基于XXX方法的XXX分析研究

## 摘要
本研究针对...问题，采用...方法，分析了...数据，主要发现...，结论表明...

**关键词**：关键词1，关键词2，关键词3

## 1. 引言

### 1.1 研究背景
当前气象...领域面临的主要挑战...

### 1.2 文献综述
前人研究表明...

### 1.3 研究目标
本研究旨在...

## 2. 数据与方法

### 2.1 数据来源
本研究使用的数据包括...

### 2.2 研究方法
采用...分析方法...

## 3. 结果与分析

### 3.1 描述性统计
数据的基本特征...

### 3.2 主要发现
研究发现...

## 4. 讨论

### 4.1 结果解释
本研究结果表明...

### 4.2 局限性
本研究存在的局限性包括...

## 5. 结论
本研究的主要贡献...未来研究方向...

## 参考文献
[1] 作者. 论文标题. 期刊名, 年份, 卷(期): 页码.'''
            })
        
        return templates


class CursorRulesMCPServer:
    """cursorrules MCP服务器"""
    
    def __init__(self):
        self.server = Server("cursorrules-mcp")
        self.rule_engine = RuleEngine()
        self.setup_tools()
        self.setup_resources()
    
    def setup_tools(self):
        """注册MCP工具"""
        
        @self.server.tool("search_rules")
        async def search_rules(
            query: str = "",
            tags: str = "",
            languages: str = "",
            domains: str = ""
        ) -> List[TextContent]:
            """搜索适用的规则
            
            Args:
                query: 搜索关键词
                tags: 标签列表（逗号分隔）
                languages: 编程语言列表（逗号分隔）
                domains: 领域列表（逗号分隔）
            """
            # 解析参数
            tags_list = [t.strip() for t in tags.split(',') if t.strip()] if tags else None
            languages_list = [l.strip() for l in languages.split(',') if l.strip()] if languages else None
            domains_list = [d.strip() for d in domains.split(',') if d.strip()] if domains else None
            
            rules = await self.rule_engine.search_rules(query, tags_list, languages_list, domains_list)
            
            results = []
            for rule in rules:
                rule_text = f"""
**规则**: {rule.name} (ID: {rule.rule_id})
**描述**: {rule.description}
**类别**: {rule.category} | **优先级**: {rule.priority}/10
**标签**: {', '.join(rule.tags)}
**适用于**: 
- 语言: {', '.join(rule.applicable_to.get('languages', []))}
- 领域: {', '.join(rule.applicable_to.get('domains', []))}
- 内容类型: {', '.join(rule.applicable_to.get('content_types', []))}

**指导原则**: 
{rule.rule_content.get('guideline', '无')}

**示例**:
{rule.rule_content.get('examples', [{}])[0].get('good', '无示例') if rule.rule_content.get('examples') else '无示例'}

---
"""
                results.append(TextContent(text=rule_text))
            
            if not results:
                results.append(TextContent(text="未找到匹配的规则。请尝试其他搜索条件。"))
            
            return results
        
        @self.server.tool("validate_content")
        async def validate_content(content: str, content_type: str = "code") -> TextContent:
            """验证内容一致性
            
            Args:
                content: 要验证的内容
                content_type: 内容类型（如：python, cpp, markdown等）
            """
            result = await self.rule_engine.validate_content(content, content_type)
            
            report = f"""
## 验证结果

**状态**: {'✅ 通过' if result['is_valid'] else '❌ 存在问题'}
**评分**: {result['score']}/100

### 发现的问题
"""
            if result['violations']:
                for violation in result['violations']:
                    if isinstance(violation, dict) and 'line' in violation:
                        report += f"- 第{violation['line']}行: 长度{violation['length']}字符，超出限制\n"
                    else:
                        report += f"- {violation}\n"
            else:
                report += "无问题发现。\n"
            
            if result['suggestions']:
                report += "\n### 改进建议\n"
                for suggestion in result['suggestions']:
                    report += f"- {suggestion}\n"
            
            return TextContent(text=report)
        
        @self.server.tool("get_templates")
        async def get_templates(template_type: str, domain: str = "") -> List[TextContent]:
            """获取模板
            
            Args:
                template_type: 模板类型（如：function_docstring, scientific_paper等）
                domain: 领域（可选，如：meteorology, ionosphere等）
            """
            templates = await self.rule_engine.get_templates(template_type, domain or None)
            
            results = []
            for template in templates:
                template_text = f"""
**模板**: {template['name']}

```
{template['content']}
```
"""
                results.append(TextContent(text=template_text))
            
            if not results:
                results.append(TextContent(text=f"未找到类型为 '{template_type}' 的模板。"))
            
            return results
        
        @self.server.tool("list_available_tags")
        async def list_available_tags() -> TextContent:
            """列出所有可用的标签"""
            all_tags = set()
            for rule in self.rule_engine.rules:
                all_tags.update(rule.tags)
            
            tags_by_category = {
                "编程语言": [tag for tag in all_tags if tag in ['python', 'cpp', 'fortran', 'shell', 'javascript']],
                "领域": [tag for tag in all_tags if tag in ['meteorology', 'ionosphere', 'surveying', 'oceanography', 'geophysics']],
                "质量类型": [tag for tag in all_tags if tag in ['style', 'performance', 'security', 'readability']],
                "其他": [tag for tag in all_tags if tag not in ['python', 'cpp', 'fortran', 'shell', 'javascript', 'meteorology', 'ionosphere', 'surveying', 'oceanography', 'geophysics', 'style', 'performance', 'security', 'readability']]
            }
            
            result = "## 可用标签\n\n"
            for category, tags in tags_by_category.items():
                if tags:
                    result += f"**{category}**: {', '.join(sorted(tags))}\n\n"
            
            return TextContent(text=result)
    
    def setup_resources(self):
        """注册MCP资源"""
        
        @self.server.resource("cursorrules://rules/list")
        async def list_rules() -> Resource:
            """列出所有规则"""
            rules_list = []
            for rule in self.rule_engine.rules:
                rules_list.append({
                    "id": rule.rule_id,
                    "name": rule.name,
                    "category": rule.category,
                    "tags": rule.tags
                })
            
            return Resource(
                uri="cursorrules://rules/list",
                name="规则列表",
                mimeType="application/json",
                text=json.dumps(rules_list, ensure_ascii=False, indent=2)
            )
    
    async def run(self):
        """启动MCP服务器"""
        print("🚀 启动 cursorrules-mcp 服务器...")
        print(f"📋 已加载 {len(self.rule_engine.rules)} 条规则")
        print("🔧 可用工具:")
        print("  - search_rules: 搜索规则")
        print("  - validate_content: 验证内容")
        print("  - get_templates: 获取模板")
        print("  - list_available_tags: 列出可用标签")
        print("📚 可用资源:")
        print("  - cursorrules://rules/list: 规则列表")
        print("=" * 50)
        
        await self.server.run()


async def main():
    """主函数"""
    server = CursorRulesMCPServer()
    await server.run()


if __name__ == "__main__":
    # 简单的测试代码
    async def test_rule_engine():
        """测试规则引擎功能"""
        print("🧪 测试规则引擎...")
        
        engine = RuleEngine()
        
        # 测试搜索
        print("\n1. 测试搜索Python规则:")
        python_rules = await engine.search_rules(languages=["python"])
        for rule in python_rules[:2]:
            print(f"  - {rule.name} ({rule.rule_id})")
        
        # 测试验证
        print("\n2. 测试代码验证:")
        test_code = """def very_long_function_name_that_exceeds_the_pep8_line_length_limit():
    pass"""
        
        result = await engine.validate_content(test_code, "python")
        print(f"  验证结果: {'通过' if result['is_valid'] else '失败'}")
        print(f"  评分: {result['score']}/100")
        
        # 测试模板
        print("\n3. 测试获取模板:")
        templates = await engine.get_templates("function_docstring")
        if templates:
            print(f"  找到 {len(templates)} 个模板")
        
        print("✅ 测试完成")
    
    try:
        # 如果直接运行此文件，执行测试
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "test":
            asyncio.run(test_rule_engine())
        else:
            asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 错误: {e}") 