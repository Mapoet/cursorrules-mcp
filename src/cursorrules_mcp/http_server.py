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
from typing import Dict, Any, Optional, AsyncGenerator, List
from pathlib import Path
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from pydantic import BaseModel, HttpUrl
from .engine import RuleEngine
from .models import (
    MCPContext, SearchFilter, ValidationSeverity, RuleType,
    ContentType, TaskType, CursorRule
)
from .rule_import import YamlRuleParser, RuleImportError
from pydantic import validator
from .database import get_rule_database

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImportRuleRequest(BaseModel):
    """规则导入请求"""
    url: Optional[HttpUrl] = None  # 可选的HTTPS URL
    content: Optional[str] = None  # 可选的YAML内容
    merge: bool = False
    append_mode: bool = False  # 仅用于内容导入

    @validator('content', 'url')
    def validate_import_source(cls, v, values):
        # 确保至少提供了一个导入源
        if not values.get('url') and not values.get('content'):
            raise ValueError("必须提供 url 或 content 中的一个")
        return v

    @validator('append_mode')
    def validate_append_mode(cls, v, values):
        # append_mode 只能用于内容导入
        if v and values.get('url'):
            raise ValueError("append_mode 只能用于内容导入，不支持URL导入")
        return v

class ImportRuleResponse(BaseModel):
    """规则导入响应"""
    success: bool
    message: str
    rules: List[dict] = []

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
        
        @self.app.post("/import_rule", response_model=ImportRuleResponse)
        async def import_rule(request: ImportRuleRequest):
            """
            导入规则
            
            支持两种导入方式：
            1. 从HTTPS URL导入（不支持追加模式）
            2. 直接导入YAML内容（支持追加模式）
            
            特性说明：
            - URL导入：仅支持HTTPS，不支持追加模式
            - 内容导入：支持分批导入和追加模式
            - 两种方式都支持合并已存在的规则
            """
            try:
                db = get_rule_database()
                parser = YamlRuleParser(db)
                
                if request.url:
                    # 从URL导入（不支持追加模式）
                    rules = parser.import_rule(
                        str(request.url),
                        merge=request.merge,
                        is_http_api=True
                    )
                else:
                    # 从内容导入（支持追加模式）
                    rules = parser.import_content(
                        request.content,
                        merge=request.merge,
                        append_mode=request.append_mode
                    )
                
                return ImportRuleResponse(
                    success=True,
                    message="规则导入成功",
                    rules=[rule.dict() for rule in rules]
                )
                
            except RuleImportError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")
    
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
            elif method == "validate_content":
                result = await self._validate_content(**params)
            elif method == "import_resource":
                result = await self._import_resource(**params)
            elif method == "get_statistics":
                result = await self._get_statistics(**params)
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
        """列出可用工具（详细说明每个工具的功能、参数、注意事项、用法示例）"""
        tools = [
            {
                "name": "search_rules",
                "description": (
                    "搜索适用的规则。\n"
                    "【功能】根据关键词、语言、领域、标签等条件检索规则库，支持多条件组合过滤。\n"
                    "【参数说明】所有参数均为可选，支持逗号分隔多值。\n"
                    "【注意事项】limit建议不超过50。"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词。"},
                        "languages": {"type": "string", "description": "编程语言列表（逗号分隔），如 python,cpp。"},
                        "domains": {"type": "string", "description": "应用领域列表（逗号分隔），如 meteorology,ionosphere。"},
                        "tags": {"type": "string", "description": "标签列表（逗号分隔），如 style,performance。"},
                        "content_types": {"type": "string", "description": "内容类型列表（逗号分隔），如 code,documentation。"},
                        "rule_types": {"type": "string", "description": "规则类型列表（逗号分隔），如 style,content。"},
                        "limit": {"type": "integer", "description": "返回结果数量限制，默认10，最大50。", "default": 10}
                    },
                    "examples": [
                        {"query": "python 命名规范", "languages": "python", "limit": 5}
                    ]
                }
            },
            {
                "name": "validate_content",
                "description": (
                    "校验内容合规性。\n"
                    "【功能】对给定内容进行规则合规性校验，返回详细问题和建议。\n"
                    "参数 output_mode 控制输出内容，支持：result_only, result_with_prompt, result_with_rules, result_with_template, full。"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "待校验内容（必填）。"},
                        "file_path": {"type": "string", "description": "文件路径，仅用于推断语言类型（可选）。"},
                        "languages": {"type": "string", "description": "语言，如python,markdown（可选）。"},
                        "content_types": {"type": "string", "description": "内容类型，如code,documentation（可选）。"},
                        "domains": {"type": "string", "description": "领域（可选）。"},
                        "output_mode": {
                            "type": "string",
                            "description": (
                                "输出模式，支持以下枚举值：\n"
                                "- result_only：仅返回校验结果（success, passed, problems）\n"
                                "- result_with_prompt：返回校验结果和 prompt\n"
                                "- result_with_rules：返回校验结果和规则详情\n"
                                "- result_with_template：返回校验结果和模板信息\n"
                                "- full：返回全部信息（校验结果、prompt、规则、模板信息）\n"
                                "默认值为 result_only。"
                            ),
                            "enum": ["result_only", "result_with_prompt", "result_with_rules", "result_with_template", "full"],
                            "default": "result_only"
                        }
                    },
                    "required": ["content"],
                    "examples": [
                        {"content": "def foo(): pass", "languages": "python", "output_mode": "result_only"},
                        {"content": "def foo(): pass", "languages": "python", "output_mode": "full"}
                    ]
                }
            },
            {
                "name": "enhance_prompt",
                "description": (
                    "基于规则增强提示。\n"
                    "【功能】根据上下文和规则库自动补全、优化LLM提示词。\n"
                    "【参数说明】base_prompt为必填，其他参数用于筛选相关规则。\n"
                    "【注意事项】max_rules建议不超过10。"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "base_prompt": {"type": "string", "description": "基础提示（必填）。"},
                        "languages": {"type": "string", "description": "编程语言列表（逗号分隔，可选）。"},
                        "domains": {"type": "string", "description": "应用领域列表（逗号分隔，可选）。"},
                        "tags": {"type": "string", "description": "标签列表（逗号分隔，可选）。"},
                        "max_rules": {"type": "integer", "description": "最大包含规则数量，默认5，建议不超过10。", "default": 5}
                    },
                    "required": ["base_prompt"],
                    "examples": [
                        {"base_prompt": "请优化以下Python函数命名风格...", "languages": "python"}
                    ]
                }
            },
            {
                "name": "get_statistics",
                "description": (
                    "获取规则与模板的统计信息。\n"
                    "参数 resource_type 控制统计对象，支持：rules, templates, all。\n"
                    "兼容原有过滤参数，模板统计时部分字段可忽略。"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "resource_type": {
                            "type": "string",
                            "description": "统计对象类型，支持：rules（规则）、templates（模板）、all（全部）。默认 rules。",
                            "enum": ["rules", "templates", "all"],
                            "default": "rules"
                        },
                        "languages": {"type": "string", "description": "语言过滤（可选）。"},
                        "domains": {"type": "string", "description": "领域过滤（可选）。"},
                        "rule_types": {"type": "string", "description": "规则类型过滤（可选，仅规则）。"},
                        "tags": {"type": "string", "description": "标签过滤（可选）。"}
                    },
                    "examples": [
                        {"resource_type": "rules", "languages": "python"},
                        {"resource_type": "templates", "languages": "python"},
                        {"resource_type": "all"}
                    ]
                }
            },
            {
                "name": "import_resource",
                "description": (
                    "导入规则或模板的实现（仅支持 content 参数）。\n"
                    "【功能】将规则或模板内容导入到规则库，支持Markdown、YAML、JSON等格式。\n"
                    "【本地CLI/MCP】可通过 file_path（支持绝对路径）或 content 上传规则或模板。\n"
                    "【远程HTTP/MCP/JSON-RPC】仅支持 content 字段上传规则或模板内容，file_path 参数会被忽略。\n"
                    "【注意】规则正文内容必须完整上传，不能有截断或格式损失。推荐优先使用 content 字段以保证兼容性。"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": (
                                "规则或模板内容（完整文本，推荐）。\n"
                                "【远程HTTP/MCP/JSON-RPC】必须使用此字段上传规则或模板内容。\n"
                                "【本地CLI/MCP】也可用此字段。"
                            )
                        },
                        "file_path": {
                            "type": "string",
                            "description": (
                                "规则或模板文件路径（仅本地CLI/MCP可用，支持绝对路径和相对路径）。\n"
                                "【远程HTTP/MCP/JSON-RPC】此参数会被忽略，仅为兼容占位。"
                            )
                        },
                        "format": {
                            "type": "string",
                            "description": (
                                "规则或模板格式类型。可选：auto（自动识别）、markdown、yaml、json。"
                            ),
                            "enum": ["auto", "markdown", "yaml", "json"],
                            "default": "auto"
                        },
                        "validate": {
                            "type": "boolean",
                            "description": "导入后是否校验规则或模板，默认True。",
                            "default": True
                        },
                        "merge": {
                            "type": "boolean",
                            "description": "是否合并重复规则或模板，默认False。",
                            "default": False
                        },
                        "type": {
                            "type": "string",
                            "description": "资源类型，可选：rules（规则）、templates（模板），默认auto（自动识别）。",
                            "enum": ["rules", "templates", "auto"],
                            "default": "auto"
                        }
                    },
                    "required": ["content"],
                    "examples": [
                        {"content": "# 规则内容...", "format": "markdown", "type": "rules"},
                        {"file_path": "/absolute/path/to/rule.yaml", "format": "yaml", "type": "rules"},
                        {"content": "# 模板内容...", "format": "markdown", "type": "templates"},
                        {"file_path": "/absolute/path/to/template.yaml", "format": "yaml", "type": "templates"}
                    ]
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
        elif tool_name == "import_resource":
            result = await self._import_resource(**arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # 保证text字段始终为字符串
        return {
            "content": [
                {
                    "type": "text",
                    "text": result if isinstance(result, str) else str(result)
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
    
    async def _validate_content(self, content: str, file_path: str = "", languages: str = "", content_types: str = "", domains: str = "", output_mode: str = "result_only") -> dict:
        """
        校验内容合规性，支持枚举型输出模式。
        Args:
            content (str): 待校验内容。
            file_path (str, optional): 文件路径。
            languages (str, optional): 语言。
            content_types (str, optional): 内容类型。
            domains (str, optional): 领域。
            output_mode (str): 输出模式，支持：result_only, result_with_prompt, result_with_rules, result_with_template, full。
        Returns:
            dict: 校验结果及所需附加信息。
        """
        from .engine import OutputMode
        from .models import MCPContext
        
        # 执行验证
        return await self.rule_engine.validate_content(
            content=content,
            file_path=file_path,
            languages=languages,
            content_types=content_types,
            domains=domains,
            output_mode=OutputMode(output_mode)
        )
    
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
    
    async def _get_statistics(self, resource_type: str = "rules", languages: str = "", domains: str = "", rule_types: str = "", tags: str = "") -> dict:
        """
        获取规则与模板的统计信息。
        Args:
            resource_type (str): 统计对象类型，rules/templates/all。
            languages, domains, rule_types, tags: 过滤参数。
        Returns:
            dict: 统计结果，结构如 {resource_type, rules_stats, templates_stats}
        """
        stats = {}
        if resource_type in ("rules", "all"):
            stats["rules_stats"] = self.rule_engine.get_rule_statistics(languages, domains, rule_types, tags)
        if resource_type in ("templates", "all"):
            stats["templates_stats"] = self.rule_engine.get_template_statistics(languages, domains, tags)
        stats["resource_type"] = resource_type
        return stats

    async def _import_resource(self, content: str = "", file_path: str = "",
                           format: str = "auto", validate: bool = True,
                           merge: bool = False, type: str = None) -> str:
        """导入规则或模板的实现（仅支持 content 参数）"""
        try:
            import tempfile
            import os
            if not content:
                return {
                    "success": False,
                    "message": "❌ 必须通过 content 上传资源内容，不支持 file_path 参数",
                    "imported": 0,
                    "resource_type": type or "auto"
                }
            # 自动识别类型
            resource_type = type or None
            if not resource_type:
                if format in ["markdown"] or content.startswith('---') or file_path.endswith('.md'):
                    resource_type = 'templates'
                elif format in ["yaml", "yml"] or file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    resource_type = 'templates'
                else:
                    resource_type = 'rules'
            if resource_type == 'templates':
                # 导入模板
                from .engine import RuleEngine
                engine = self.rule_engine
                # 创建临时文件
                ext = '.md' if format == 'markdown' else '.yaml'
                with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False, encoding='utf-8') as temp_file:
                    temp_file.write(content)
                    temp_path = temp_file.name
                try:
                    engine.load_prompt_templates([temp_path], mode='append')
                    return {
                        "success": True,
                        "message": f"✅ 成功导入模板文件 {file_path or temp_path}",
                        "imported": 1,
                        "resource_type": "templates"
                    }
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            else:
                # 导入规则
                from .rule_import import UnifiedRuleImporter
                ext = '.yaml' if format in ['yaml', 'yml'] else '.md' if format == 'markdown' else '.json'
                with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False, encoding='utf-8') as temp_file:
                    temp_file.write(content)
                    temp_path = temp_file.name
                try:
                    importer = UnifiedRuleImporter(save_to_database=True)
                    rules = await importer.import_rules_async([temp_path], merge=merge)
                    await self.rule_engine.reload()
                    
                    # 检查导入日志中的错误
                    import_log = importer.get_import_summary()
                    if import_log['failed_imports'] > 0:
                        error_logs = [log for log in import_log['import_log'] if log['status'] == 'error']
                        error_messages = []
                        for log in error_logs:
                            if "检测到重复 rule_id" in log['message']:
                                # 对于重复 ID 的错误，提供更友好的提示
                                rule_id = log['message'].split("rule_id:")[1].split(",")[0].strip()
                                error_messages.append(f"规则 {rule_id} 已存在。如果要覆盖现有规则，请设置 merge=true。")
                            else:
                                error_messages.append(log['message'])
                        
                        return {
                            "success": False,
                            "message": "❌ 导入规则时出现问题：\n" + "\n".join(error_messages),
                            "imported": len(rules),
                            "resource_type": "rules",
                            "details": {
                                "total_files": import_log['total_files'],
                                "successful_imports": import_log['successful_imports'],
                                "failed_imports": import_log['failed_imports']
                            }
                        }
                    
                    return {
                        "success": True,
                        "message": f"✅ 成功导入 {len(rules)} 条规则到数据库",
                        "imported": len(rules),
                        "resource_type": "rules",
                        "details": {
                            "total_files": import_log['total_files'],
                            "successful_imports": import_log['successful_imports'],
                            "failed_imports": import_log['failed_imports']
                        }
                    }
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 导入资源失败: {e}",
                "imported": 0,
                "resource_type": type or "auto"
            }
    
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
