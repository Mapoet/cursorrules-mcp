#!/usr/bin/env python3
"""
CursorRules-MCP HTTP服务器实现
支持MCP JSON-RPC协议通过HTTP/SSE传输

Author: Mapoet
Institution: NUS/STAR
Date: 2025-01-23
License: MIT
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from pathlib import Path
import uuid
from datetime import datetime

# HTTP相关导入
try:
    from fastapi import FastAPI, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    import uvicorn
except ImportError:
    print("FastAPI未安装，请运行: pip install fastapi uvicorn")
    exit(1)

from .engine import RuleEngine
from .models import (
    MCPContext, SearchFilter, ValidationSeverity, RuleType,
    ContentType, TaskType
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPHttpServer:
    """
    MCP HTTP服务器
    
    支持通过HTTP/SSE提供MCP服务
    """
    
    def __init__(self, rules_dir: str = "data/rules", host: str = "localhost", port: int = 8000, workers: int = 1):
        """初始化HTTP服务器
        
        Args:
            rules_dir: 规则目录路径
            host: 服务器主机地址
            port: 服务器端口
            workers: 工作进程数量，默认为1
        """
        self.app = FastAPI(
            title="CursorRules-MCP HTTP Server",
            description="MCP服务器 - 支持HTTP/SSE传输",
            version="1.0.0"
        )
        self.rule_engine = RuleEngine(rules_dir)
        self.host = host
        self.port = port
        self.workers = workers
        self._initialized = False
        self._active_connections: Dict[str, Dict] = {}
        
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """设置中间件"""
        # CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 生产环境中应该限制
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """设置路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查端点"""
            return {
                "status": "healthy",
                "service": "cursorrules-mcp",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/mcp/info")
        async def mcp_info():
            """MCP服务信息"""
            await self._ensure_initialized()
            stats = await self.rule_engine.get_statistics()
            return {
                "protocol": "mcp",
                "version": "2024-11-05",
                "transport": "http-sse",
                "capabilities": {
                    "tools": True,
                    "resources": True,
                    "prompts": False,
                    "logging": True
                },
                "server_info": {
                    "name": "cursorrules-mcp",
                    "version": "1.0.0"
                },
                "statistics": stats
            }
        
        @self.app.post("/mcp/connect")
        async def connect():
            """建立MCP连接"""
            connection_id = str(uuid.uuid4())
            self._active_connections[connection_id] = {
                "created_at": datetime.now(),
                "last_activity": datetime.now()
            }
            
            return {
                "connection_id": connection_id,
                "protocol": "mcp",
                "version": "2024-11-05",
                "server_info": {
                    "name": "cursorrules-mcp",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": True,
                    "resources": True
                }
            }
        
        @self.app.post("/mcp/jsonrpc")
        async def handle_jsonrpc(request: Request):
            """处理MCP JSON-RPC请求"""
            try:
                # 确保初始化
                await self._ensure_initialized()
                
                # 解析JSON-RPC请求
                body = await request.json()
                
                # 验证JSON-RPC格式
                if not self._validate_jsonrpc(body):
                    return self._error_response(-32600, "Invalid Request")
                
                # 处理请求
                response = await self._handle_mcp_request(body)
                return response
                
            except json.JSONDecodeError:
                return self._error_response(-32700, "Parse error")
            except Exception as e:
                logger.error(f"处理JSON-RPC请求时出错: {e}")
                return self._error_response(-32603, f"Internal error: {str(e)}")
        
        @self.app.get("/mcp/sse")
        async def sse_endpoint(request: Request, connection_id: Optional[str] = None):
            """SSE端点，用于实时通信"""
            
            async def event_stream():
                """生成SSE事件流"""
                try:
                    # 发送初始连接事件
                    yield self._create_sse_event("connection", {
                        "status": "connected",
                        "connection_id": connection_id or "anonymous",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 保持连接活跃
                    while True:
                        # 发送心跳
                        yield self._create_sse_event("heartbeat", {
                            "timestamp": datetime.now().isoformat()
                        })
                        await asyncio.sleep(30)  # 30秒心跳
                        
                except asyncio.CancelledError:
                    logger.info("SSE连接已断开")
                except Exception as e:
                    logger.error(f"SSE流错误: {e}")
                    yield self._create_sse_event("error", {
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
            
            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )
    
    def _validate_jsonrpc(self, data: Dict[str, Any]) -> bool:
        """验证JSON-RPC请求格式"""
        required_fields = ["jsonrpc", "method", "id"]
        return all(field in data for field in required_fields) and data["jsonrpc"] == "2.0"
    
    async def _handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理MCP请求"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            # 路由到对应的处理方法
            if method == "tools/list":
                result = await self._list_tools()
            elif method == "tools/call":
                result = await self._call_tool(params)
            elif method == "resources/list":
                result = await self._list_resources()
            elif method == "resources/read":
                result = await self._read_resource(params)
            elif method == "initialize":
                result = await self._initialize(params)
            else:
                return self._error_response(-32601, f"Method not found: {method}", request_id)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"处理MCP方法 {method} 时出错: {e}")
            return self._error_response(-32603, f"Internal error: {str(e)}", request_id)
    
    async def _initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始化请求"""
        await self._ensure_initialized()
        
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "logging": {}
            },
            "serverInfo": {
                "name": "cursorrules-mcp",
                "version": "1.0.0"
            }
        }
    
    async def _list_tools(self) -> Dict[str, Any]:
        """列出可用工具"""
        tools = [
            {
                "name": "search_rules",
                "description": "搜索适用的规则",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"},
                        "languages": {"type": "string", "description": "编程语言列表（逗号分隔）"},
                        "domains": {"type": "string", "description": "应用领域列表（逗号分隔）"},
                        "tags": {"type": "string", "description": "标签列表（逗号分隔）"},
                        "content_types": {"type": "string", "description": "内容类型列表（逗号分隔）"},
                        "rule_types": {"type": "string", "description": "规则类型列表（逗号分隔）"},
                        "limit": {"type": "integer", "description": "返回结果数量限制", "default": 10}
                    }
                }
            },
            {
                "name": "validate_content",
                "description": "验证内容是否符合规则",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "要验证的内容"},
                        "file_path": {"type": "string", "description": "文件路径（可选）"},
                        "languages": {"type": "string", "description": "编程语言（逗号分隔）"},
                        "domains": {"type": "string", "description": "应用领域（逗号分隔）"},
                        "content_types": {"type": "string", "description": "内容类型（逗号分隔）"},
                        "project_context": {"type": "string", "description": "项目上下文信息"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "enhance_prompt",
                "description": "基于规则增强提示",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "base_prompt": {"type": "string", "description": "基础提示"},
                        "languages": {"type": "string", "description": "编程语言列表"},
                        "domains": {"type": "string", "description": "应用领域列表"},
                        "tags": {"type": "string", "description": "标签列表"},
                        "max_rules": {"type": "integer", "description": "最大规则数量", "default": 5}
                    },
                    "required": ["base_prompt"]
                }
            },
            {
                "name": "get_statistics",
                "description": "获取规则库统计信息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "languages": {"type": "string", "description": "过滤的编程语言（逗号分隔）"},
                        "domains": {"type": "string", "description": "过滤的应用领域（逗号分隔）"},
                        "rule_types": {"type": "string", "description": "过滤的规则类型（逗号分隔）"},
                        "tags": {"type": "string", "description": "过滤的标签（逗号分隔）"}
                    }
                }
            },
            {
                "name": "import_rules",
                "description": "导入规则（支持多种格式）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "规则内容（如果提供了content，则忽略file_path）"},
                        "file_path": {"type": "string", "description": "规则文件路径"},
                        "format": {"type": "string", "description": "格式类型", "enum": ["auto", "markdown", "yaml", "json"], "default": "auto"},
                        "validate": {"type": "boolean", "description": "是否验证规则", "default": True},
                        "merge": {"type": "boolean", "description": "是否合并重复规则", "default": False}
                    }
                }
            }
        ]
        
        return {"tools": tools}
    
    async def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "search_rules":
            result = await self._search_rules(**arguments)
        elif tool_name == "validate_content":
            result = await self._validate_content(**arguments)
        elif tool_name == "enhance_prompt":
            result = await self._enhance_prompt(**arguments)
        elif tool_name == "get_statistics":
            result = await self._get_statistics(**arguments)
        elif tool_name == "import_rules":
            result = await self._import_rules(**arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": result
                }
            ]
        }
    
    async def _list_resources(self) -> Dict[str, Any]:
        """列出可用资源"""
        resources = [
            {
                "uri": "cursorrules://rules/list",
                "name": "规则列表",
                "description": "列出所有可用规则的摘要",
                "mimeType": "text/plain"
            }
        ]
        
        return {"resources": resources}
    
    async def _read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """读取资源"""
        uri = params.get("uri")
        
        if uri == "cursorrules://rules/list":
            content = await self._list_all_rules()
        elif uri and uri.startswith("cursorrules://rules/"):
            # 提取规则ID
            rule_id = uri.split("/")[-1]
            content = await self._get_rule_detail(rule_id)
        else:
            raise ValueError(f"Unknown resource: {uri}")
        
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": content
                }
            ]
        }
    
    # 工具实现方法（重用现有逻辑）
    async def _search_rules(self, query: str = "", languages: str = "", domains: str = "", 
                          tags: str = "", content_types: str = "", rule_types: str = "", limit: int = 10) -> str:
        """搜索规则的实现"""
        try:
            # 解析参数
            search_filter = SearchFilter(
                query=query.strip() if query else None,
                languages=self._parse_list_param(languages),
                domains=self._parse_list_param(domains),
                tags=self._parse_list_param(tags),
                content_types=self._parse_list_param(content_types),
                rule_types=[RuleType(rt.strip()) for rt in rule_types.split(',') if rt.strip()] if rule_types else None,
                limit=max(1, min(50, limit))
            )
            
            # 执行搜索
            applicable_rules = await self.rule_engine.search_rules(search_filter)
            
            if not applicable_rules:
                return "❌ 未找到匹配的规则。请尝试调整搜索条件。"
            
            # 格式化结果
            result_text = f"""🔍 **搜索摘要**: 
- 查询: "{query}" (如果有)
- 找到 {len(applicable_rules)} 条匹配规则

---
"""
            
            for i, applicable_rule in enumerate(applicable_rules, 1):
                rule = applicable_rule.rule
                result_text += f"""
## {i}. {rule.name}
**ID**: `{rule.rule_id}` | **版本**: {rule.version} | **相关度**: {applicable_rule.relevance_score:.2f}

**描述**: {rule.description}

**分类信息**:
- 🏷️ **类型**: {rule.rule_type.value}
- 💻 **语言**: {', '.join(rule.languages) if rule.languages else '通用'}
- 🌍 **领域**: {', '.join(rule.domains) if rule.domains else '通用'}
- 🏪 **标签**: {', '.join(rule.tags)}

---
"""
            
            return result_text
            
        except Exception as e:
            logger.error(f"搜索规则时发生错误: {e}")
            return f"❌ 搜索失败: {str(e)}"
    
    async def _validate_content(self, content: str, file_path: str = "", 
                              languages: str = "", domains: str = "", 
                              content_types: str = "", project_context: str = "") -> str:
        """验证内容的实现"""
        try:
            # 构建MCP上下文
            context = MCPContext(
                user_query="Content validation request",
                file_path=file_path,
                languages=self._parse_list_param(languages) or self._infer_languages_from_path(file_path),
                domains=self._parse_list_param(domains),
                content_types=self._parse_list_param(content_types) or self._infer_content_types(content, file_path),
                project_context=project_context
            )
            
            # 执行验证
            validation_result = await self.rule_engine.validate_content(content, context)
            
            # 格式化验证结果
            if validation_result.is_valid:
                result_text = f"✅ **验证通过**\n\n"
            else:
                result_text = f"❌ **验证失败** ({len(validation_result.violations)} 个问题)\n\n"
            
            # 添加详细信息
            if validation_result.violations:
                result_text += "**发现的问题**:\n"
                for violation in validation_result.violations:
                    result_text += f"- {violation.severity.value}: {violation.message}\n"
                    if violation.suggestion:
                        result_text += f"  💡 建议: {violation.suggestion}\n"
            
            if validation_result.suggestions:
                result_text += "\n**改进建议**:\n"
                for suggestion in validation_result.suggestions:
                    result_text += f"- {suggestion}\n"
            
            return result_text
            
        except Exception as e:
            logger.error(f"验证内容时发生错误: {e}")
            return f"❌ 验证失败: {str(e)}"
    
    async def _enhance_prompt(self, base_prompt: str, languages: str = "", 
                            domains: str = "", tags: str = "", max_rules: int = 5) -> str:
        """增强提示的实现"""
        try:
            # 构建搜索过滤器
            search_filter = SearchFilter(
                languages=self._parse_list_param(languages),
                domains=self._parse_list_param(domains),
                tags=self._parse_list_param(tags),
                limit=max_rules
            )
            
            # 获取相关规则
            applicable_rules = await self.rule_engine.search_rules(search_filter)
            
            enhanced_prompt = f"{base_prompt}\n\n"
            
            if applicable_rules:
                enhanced_prompt += "**相关编程规则**:\n"
                for rule in applicable_rules[:max_rules]:
                    enhanced_prompt += f"- {rule.rule.name}: {rule.rule.description}\n"
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"增强提示时发生错误: {e}")
            return f"❌ 增强失败: {str(e)}"
    
    async def _get_statistics(self, languages: str = "", domains: str = "", 
                           rule_types: str = "", tags: str = "") -> str:
        """获取统计信息的实现（支持过滤参数）"""
        try:
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

**按类型分布**:
"""
            # 添加详细分布信息
            for rule_type, count in stats.get('rules_by_type', {}).items():
                if count > 0:
                    result_text += f"- {rule_type}: {count} 条\n"
            
            result_text += f"""
**按语言分布**:
"""
            for lang, count in stats.get('rules_by_language', {}).items():
                if count > 0:
                    result_text += f"- {lang}: {count} 条\n"
            
            result_text += f"""
**按领域分布**:
"""
            for domain, count in stats.get('rules_by_domain', {}).items():
                if count > 0:
                    result_text += f"- {domain}: {count} 条\n"
            
            # 添加版本分布
            if 'version_distribution' in stats and stats['version_distribution']:
                result_text += f"""
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
            
            result_text += f"""
**HTTP服务状态**:
- 活跃连接: {len(self._active_connections)}
- 服务器运行时间: {datetime.now().isoformat()}
"""
            
            return result_text
            
        except Exception as e:
            logger.error(f"获取统计信息时发生错误: {e}")
            return f"❌ 获取统计信息失败: {str(e)}"

    async def _import_rules(self, content: str = "", file_path: str = "",
                           format: str = "auto", validate: bool = True,
                           merge: bool = False) -> str:
        """导入规则的实现"""
        try:
            # 导入规则导入器
            from .rule_import import UnifiedRuleImporter
            
            # 创建导入器
            importer = UnifiedRuleImporter(
                output_dir="data/rules/imported",
                validate=validate,
                merge=merge
            )
            
            # 执行导入
            if content:
                # 直接从内容导入
                if format == "auto":
                    # 尝试自动检测格式
                    if content.startswith('---'):
                        format = "markdown"
                    elif content.strip().startswith('{'):
                        format = "json"
                    else:
                        format = "yaml"
                
                result = importer.import_from_content(content, format)
            else:
                # 从文件路径导入
                if not file_path:
                    return "❌ 必须提供 content 或 file_path 之一"
                
                result = importer.import_from_file(file_path, format)
            
            # 格式化结果
            if result['success']:
                result_text = f"""
✅ **规则导入成功**

**导入统计**:
- 处理文件: {result.get('processed_files', 1)}
- 导入规则: {result.get('imported_rules', 0)}
- 跳过规则: {result.get('skipped_rules', 0)}
- 格式: {result.get('detected_format', format)}

"""
                if result.get('imported_rule_ids'):
                    result_text += "**已导入的规则ID**:\n"
                    for rule_id in result['imported_rule_ids']:
                        result_text += f"- {rule_id}\n"
                
                if result.get('warnings'):
                    result_text += "\n**警告**:\n"
                    for warning in result['warnings']:
                        result_text += f"⚠️ {warning}\n"
            else:
                result_text = f"""
❌ **规则导入失败**

**错误信息**: {result.get('error', '未知错误')}

"""
                if result.get('details'):
                    result_text += f"**详细信息**: {result['details']}\n"
            
            # 重新加载规则引擎
            await self.rule_engine.reload()
            
            return result_text
            
        except Exception as e:
            logger.error(f"导入规则时发生错误: {e}")
            return f"❌ 导入失败: {str(e)}"
    
    async def _list_all_rules(self) -> str:
        """列出所有规则"""
        try:
            # 获取所有规则
            all_rules = await self.rule_engine.search_rules(SearchFilter(limit=1000))
            
            if not all_rules:
                return "📋 **规则库为空**\n\n当前没有可用的规则。"
            
            result_text = f"📋 **CursorRules 规则库** ({len(all_rules)} 条规则)\n\n"
            
            for i, applicable_rule in enumerate(all_rules, 1):
                rule = applicable_rule.rule
                result_text += f"{i}. **{rule.name}** (`{rule.rule_id}`)\n"
                result_text += f"   {rule.description}\n"
                result_text += f"   🏷️ {rule.rule_type.value} | 💻 {', '.join(rule.languages[:2]) if rule.languages else '通用'}\n\n"
            
            return result_text
            
        except Exception as e:
            logger.error(f"列出规则时发生错误: {e}")
            return f"❌ 列出规则失败: {str(e)}"
    
    async def _get_rule_detail(self, rule_id: str) -> str:
        """获取规则详情"""
        try:
            rule = await self.rule_engine.get_rule_by_id(rule_id)
            
            if not rule:
                return f"❌ 未找到规则: {rule_id}"
            
            # 格式化规则详情（这里可以重用现有逻辑）
            # ... 实现详细格式化
            
            return f"📋 **规则详情**: {rule.name}\n\n{rule.description}"
            
        except Exception as e:
            logger.error(f"获取规则详情时发生错误: {e}")
            return f"❌ 获取规则详情失败: {str(e)}"
    
    # 辅助方法
    def _parse_list_param(self, param: str) -> Optional[list]:
        """解析列表参数"""
        if not param or not param.strip():
            return None
        return [item.strip() for item in param.split(',') if item.strip()]
    
    def _infer_languages_from_path(self, file_path: str) -> list:
        """从文件路径推断编程语言"""
        if not file_path:
            return []
        
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.cpp': 'cpp',
            '.hpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.cu': 'cuda',
            '.cuh': 'cuda',
            '.cu++': 'cuda',
            '.cu++h': 'cuda',
            '.cu++h++': 'cuda',
            '.f': 'fortran',
            '.f90': 'fortran',
            '.f95': 'fortran',
            '.f03': 'fortran',
            '.f08': 'fortran',
            '.f18': 'fortran',
            '.f20': 'fortran',
            '.f23': 'fortran',
            '.sh': 'shell',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.sql': 'sql',
            '.md': 'markdown',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.conf': 'conf',
            '.cfg': 'conf',
            '.config': 'conf',
            '.settings': 'conf',
            '.properties': 'conf',
            '.env': 'conf',
            '.html': 'html',
            '.css': 'css'
        }
        
        ext = Path(file_path).suffix.lower()
        return [extension_map[ext]] if ext in extension_map else []
    
    def _infer_content_types(self, content: str, file_path: str) -> list:
        """推断内容类型"""
        content_types = []
        
        # 基于文件扩展名
        if file_path:
            ext = Path(file_path).suffix.lower()
            if ext in ['.py', '.js', '.cpp','.hpp','.h','.c', '.java', '.go', '.rs', '.cu', '.cuh', '.cu++', '.cu++h', '.cu++h++']:
                content_types.append('code')
            elif ext in ['.md', '.txt', '.rst']:
                content_types.append('documentation')
            elif ext in ['.yaml', '.yml', '.json', '.xml', '.toml', '.ini', '.conf', '.cfg', '.config', '.settings', '.properties', '.env']:
                content_types.append('configuration')
        
        # 基于内容特征
        if 'def ' in content or 'function ' in content or 'class ' in content:
            content_types.append('code')
        if '# ' in content or '## ' in content or '### ' in content:
            content_types.append('documentation')
        
        return content_types or ['code']  # 默认为代码
    
    def _create_sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """创建SSE事件"""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    def _error_response(self, code: int, message: str, request_id: Any = None) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": request_id
        }
    
    async def _ensure_initialized(self):
        """确保服务器已初始化"""
        if not self._initialized:
            logger.info("正在初始化规则引擎...")
            await self.rule_engine.initialize()
            self._initialized = True
            logger.info("✅ 规则引擎初始化完成")
    
    def run(self):
        """运行HTTP服务器"""
        logger.info(f"🚀 启动CursorRules-MCP HTTP服务器: http://{self.host}:{self.port}")
        if self.workers > 1:
            logger.info(f"👥 使用 {self.workers} 个工作进程")
            # 多进程模式需要使用导入字符串
            uvicorn.run(
                "src.cursorrules_mcp.http_server:create_app",
                host=self.host,
                port=self.port,
                log_level="info",
                workers=self.workers,
                factory=True
            )
        else:
            # 单进程模式可以直接传递app对象
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )


def create_app():
    """
    应用程序工厂函数，用于多进程模式
    从环境变量读取配置
    
    Returns:
        FastAPI应用实例
    """
    import os
    
    rules_dir = os.getenv("CURSORRULES_RULES_DIR", "data/rules")
    host = os.getenv("CURSORRULES_HOST", "localhost")
    port = int(os.getenv("CURSORRULES_PORT", "8000"))
    workers = int(os.getenv("CURSORRULES_WORKERS", "1"))
    
    server = MCPHttpServer(rules_dir=rules_dir, host=host, port=port, workers=workers)
    return server.app
