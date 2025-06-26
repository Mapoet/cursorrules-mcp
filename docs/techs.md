# CursorRules-MCP 技术架构报告

**版本**: v1.4.0  
**日期**: 2025-01-23  
**作者**: Mapoet  
**机构**: NUS/STAR  

---

## 📋 技术概览

CursorRules-MCP是一个基于Model Context Protocol (MCP)的智能编程规则与提示模板管理系统。项目采用现代Python技术栈，实现了多协议服务架构，为LLM应用提供标准化的代码质量控制与内容验证服务。

### 🎯 项目定位

| 维度 | 描述 |
|------|------|
| **目标用户** | LLM开发者、代码审查团队、软件工程师、技术写作者 |
| **应用场景** | 代码生成质量控制、文档标准化、规则库管理、内容合规性校验 |
| **技术特色** | 多协议支持、异步处理、智能匹配、可扩展架构 |
| **集成方式** | MCP客户端、HTTP API、命令行工具、Python库 |

---

## 🏗️ 整体架构设计

### 系统架构图

```mermaid
graph TB
    subgraph "客户端层 (Client Layer)"
        MCP[MCP客户端]
        HTTP[HTTP客户端]
        CLI[命令行工具]
        PY[Python库调用]
    end
    
    subgraph "接口层 (Interface Layer)"
        MCPS[MCP服务器<br/>server.py]
        HTTPS[HTTP服务器<br/>http_server.py]
        CLIS[CLI服务<br/>cursorrules_cli.py]
    end
    
    subgraph "业务逻辑层 (Business Logic Layer)"
        ENGINE[规则引擎<br/>RuleEngine]
        VALIDATOR[验证管理器<br/>ValidationManager]
        IMPORTER[规则导入器<br/>UnifiedRuleImporter]
        GENERATOR[规则生成器<br/>RuleGenerator]
    end
    
    subgraph "数据层 (Data Layer)"
        DB[(规则数据库<br/>RuleDatabase)]
        CACHE[(缓存系统)]
        FILES[文件系统<br/>规则文件/模板]
    end
    
    subgraph "工具层 (Tool Layer)"
        FLAKE8[Flake8]
        PYLINT[Pylint]
        BLACK[Black]
        ESLINT[ESLint]
        CUSTOM[自定义验证器]
    end
    
    MCP --> MCPS
    HTTP --> HTTPS  
    CLI --> CLIS
    PY --> ENGINE
    
    MCPS --> ENGINE
    HTTPS --> ENGINE
    CLIS --> ENGINE
    
    ENGINE --> DB
    ENGINE --> CACHE
    ENGINE --> VALIDATOR
    ENGINE --> IMPORTER
    ENGINE --> GENERATOR
    
    VALIDATOR --> FLAKE8
    VALIDATOR --> PYLINT
    VALIDATOR --> BLACK
    VALIDATOR --> ESLINT
    VALIDATOR --> CUSTOM
    
    IMPORTER --> DB
    IMPORTER --> FILES
    GENERATOR --> DB
```

### 核心组件关系

```mermaid
classDiagram
    class RuleEngine {
        +rules: Dict[str, CursorRule]
        +database: RuleDatabase
        +validation_tools: ValidationManager
        +prompt_templates: List[PromptTemplate]
        +initialize() async
        +search_rules(filter: SearchFilter) async
        +validate_content(content: str, context: MCPContext) async
        +enhance_prompt(prompt: str, context: MCPContext) async
        +get_statistics() dict
    }
    
    class MCPHttpServer {
        +app: FastAPI
        +rule_engine: RuleEngine
        +_setup_routes()
        +_handle_mcp_request(request: dict) async
        +run()
    }
    
    class CursorRulesMCPServer {
        +mcp: FastMCP
        +rule_engine: RuleEngine
        +setup_handlers()
        +run()
    }
    
    class RuleDatabase {
        +rules: Dict[str, CursorRule]
        +data_dir: str
        +save_rule(rule: CursorRule) async
        +load_rules() async
        +get_rule(rule_id: str) CursorRule
        +delete_rule(rule_id: str) async
    }
    
    class UnifiedRuleImporter {
        +parsers: Dict[str, RuleParser]
        +database: RuleDatabase
        +import_rules_async(files: List[str]) async
        +import_content(content: str) async
    }
    
    class ValidationManager {
        +validators: Dict[str, BaseValidator]
        +validate_async(content: str, language: str) async
        +get_validator(language: str) BaseValidator
    }
    
    RuleEngine --> RuleDatabase
    RuleEngine --> ValidationManager
    RuleEngine --> UnifiedRuleImporter
    MCPHttpServer --> RuleEngine
    CursorRulesMCPServer --> RuleEngine
    UnifiedRuleImporter --> RuleDatabase
```

---

## 🔧 技术路线图

### 发展阶段

```mermaid
timeline
    title CursorRules-MCP 技术演进路线
    
    section 基础阶段 (v1.0.x)
        MCP协议集成 : 实现基础MCP服务器
                   : 规则搜索功能
                   : CLI工具开发
    
    section 扩展阶段 (v1.1.x-v1.2.x)
        多协议支持 : HTTP/REST API服务器
                   : 规则验证系统
                   : 统计分析功能
                   : 多格式导入支持
    
    section 完善阶段 (v1.3.x-v1.4.x)
        架构优化 : 异步处理架构
                 : 错误处理完善
                 : 输出模式控制
                 : 性能优化
    
    section 未来规划 (v2.0.x+)
        智能化增强 : AI驱动规则推荐
                   : 自适应学习系统
                   : 分布式部署支持
                   : 实时协作功能
```

### 技术选型决策

| 技术领域 | 选型 | 理由 | 替代方案 |
|----------|------|------|----------|
| **Web框架** | FastAPI | 高性能、自动文档生成、类型安全 | Flask, Django |
| **异步框架** | asyncio | 原生支持、生态成熟 | Twisted, Tornado |
| **数据模型** | Pydantic | 类型验证、序列化支持 | dataclasses, attrs |
| **数据存储** | SQLite/PostgreSQL | 轻量级开发、生产级扩展 | MongoDB, Redis |
| **MCP实现** | FastMCP | 标准协议支持、易于集成 | 自研实现 |
| **命令行** | Click/Typer | 功能丰富、用户友好 | argparse, fire |

---

## 📊 数据流分析

### 规则搜索数据流

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as API层
    participant Engine as 规则引擎
    participant DB as 数据库
    participant Cache as 缓存
    
    Client->>API: 搜索请求 (SearchFilter)
    API->>Engine: search_rules(filter)
    
    Engine->>Cache: 检查缓存
    alt 缓存命中
        Cache-->>Engine: 返回缓存结果
    else 缓存未命中
        Engine->>DB: 查询规则数据
        DB-->>Engine: 返回规则列表
        Engine->>Engine: 计算相关度评分
        Engine->>Cache: 更新缓存
    end
    
    Engine-->>API: 返回ApplicableRule列表
    API-->>Client: 格式化响应
```

### 内容验证数据流

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as API层
    participant Engine as 规则引擎
    participant Validator as 验证器
    participant Tools as 外部工具
    
    Client->>API: 验证请求 (content, context)
    API->>Engine: validate_content()
    
    Engine->>Engine: 搜索适用规则
    Engine->>Validator: 创建验证任务
    
    par 并行验证
        Validator->>Tools: Flake8检查
        Tools-->>Validator: 结果1
    and
        Validator->>Tools: Pylint检查  
        Tools-->>Validator: 结果2
    and
        Validator->>Tools: 自定义检查
        Tools-->>Validator: 结果3
    end
    
    Validator->>Validator: 聚合验证结果
    Validator-->>Engine: ValidationResult
    Engine-->>API: 格式化结果
    API-->>Client: 返回验证报告
```

### 规则导入数据流

```mermaid
flowchart TD
    A[导入请求] --> B{资源类型}
    
    B -->|规则| C[UnifiedRuleImporter]
    B -->|模板| D[RuleEngine.load_prompt_templates]
    
    C --> E[解析文件格式]
    D --> F[解析模板文件]
    
    E --> G{格式类型}
    F --> H{格式类型}
    
    G -->|Markdown| I[MarkdownRuleParser]
    G -->|YAML| J[YamlRuleParser]
    G -->|JSON| K[JsonRuleParser]
    
    H -->|Markdown| L[解析Markdown模板]
    H -->|YAML| M[解析YAML模板]
    
    I --> N[解析规则结构]
    J --> N
    K --> N
    
    L --> O[创建PromptTemplate]
    M --> O
    
    N --> P[验证规则完整性]
    O --> Q[验证模板完整性]
    
    P --> R{验证通过?}
    Q --> S{验证通过?}
    
    R -->|是| T[检查规则ID冲突]
    S -->|是| U[检查模板ID冲突]
    
    R -->|否| V[返回错误信息]
    S -->|否| V
    
    T --> W{ID冲突?}
    U --> X{ID冲突?}
    
    W -->|是,merge=true| Y[合并规则]
    W -->|是,merge=false| V
    W -->|否| Z[保存到数据库]
    
    X -->|是,mode=append| AA[追加模板]
    X -->|是,mode=replace| BB[替换模板]
    X -->|否| CC[添加新模板]
    
    Y --> Z
    AA --> DD[更新模板索引]
    BB --> DD
    CC --> DD
    
    Z --> EE[更新规则索引]
    DD --> FF[返回成功结果]
    EE --> FF
```

### 提示增强数据流

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as API层
    participant Engine as 规则引擎
    participant DB as 规则数据库
    participant Template as 模板系统
    
    Client->>API: 增强请求 (base_prompt, context)
    API->>Engine: enhance_prompt()
    
    par 规则搜索
        Engine->>DB: 搜索相关规则
        DB-->>Engine: 返回规则列表
    and 模板匹配
        Engine->>Template: 获取适用模板
        Template-->>Engine: 返回模板列表
    end
    
    Engine->>Engine: 规则排序与筛选
    Engine->>Engine: 规则注入处理
    Engine->>Template: 应用模板渲染
    Template-->>Engine: 返回增强结果
    
    Engine-->>API: 返回增强后的提示
    API-->>Client: 格式化响应
```

### 统计分析数据流

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as API层
    participant Engine as 规则引擎
    participant DB as 规则数据库
    participant Cache as 缓存系统
    
    Client->>API: 统计请求 (resource_type, filters)
    API->>Engine: get_statistics()
    
    Engine->>Cache: 检查统计缓存
    
    alt 缓存命中
        Cache-->>Engine: 返回缓存结果
    else 缓存未命中
        Engine->>DB: 查询规则数据
        DB-->>Engine: 返回规则集合
        
        par 多维度统计
            Engine->>Engine: 语言分布统计
            Engine->>Engine: 领域分布统计
            Engine->>Engine: 标签使用统计
            Engine->>Engine: 使用情况分析
        end
        
        Engine->>Engine: 合并统计结果
        Engine->>Cache: 更新统计缓存
    end
    
    Engine-->>API: 返回统计报告
    API-->>Client: 格式化响应
```

---

## 🏛️ 类设计框架

### 核心模型设计

```mermaid
classDiagram
    class CursorRule {
        +rule_id: str
        +name: str
        +version: str
        +description: str
        +rule_type: RuleType
        +languages: List[str]
        +domains: List[str]
        +content_types: List[ContentType]
        +task_types: List[TaskType]
        +tags: List[str]
        +rules: List[RuleCondition]
        +validation: RuleValidation
        +application: RuleApplication
        +author: str
        +created_at: datetime
        +active: bool
        +usage_count: int
        +success_rate: float
    }
    
    class PromptTemplate {
        +template_id: str
        +name: str
        +template: str
        +domains: List[str]
        +languages: List[str]
        +content_types: List[str]
        +description: str
        +priority: int
        +source: str
        +render(rules: str, content: str): str
    }
    
    class RuleCondition {
        +condition: str
        +guideline: str
        +priority: int
        +enforcement: bool
        +examples: List[dict]
        +pattern: Optional[str]
        +anti_pattern: Optional[str]
    }
    
    class RuleValidation {
        +tools: List[str]
        +severity: ValidationSeverity
        +auto_fix: bool
        +timeout: int
        +custom_script: Optional[str]
    }
    
    class MCPContext {
        +user_query: str
        +current_file: Optional[str]
        +project_path: Optional[str]
        +primary_language: Optional[str]
        +domain: Optional[str]
        +task_type: Optional[TaskType]
        +intent_tags: List[str]
        +complexity_level: str
        +target_audience: str
    }
    
    class ValidationResult {
        +is_valid: bool
        +score: float
        +issues: List[ValidationIssue]
        +suggestions: List[str]
        +applied_rules: List[str]
        +execution_time: float
        +context: MCPContext
    }
    
    class ValidationIssue {
        +rule_id: str
        +condition: str
        +severity: ValidationSeverity
        +message: str
        +line_number: Optional[int]
        +column: Optional[int]
        +suggestion: Optional[str]
        +auto_fixable: bool
    }
    
    CursorRule --> RuleCondition
    CursorRule --> RuleValidation
    ValidationResult --> ValidationIssue
    ValidationResult --> MCPContext
```

### 服务器架构模式

#### MCP服务器 (server.py) 设计模式

CursorRulesMCPServer采用**装饰器模式**实现MCP工具注册，通过FastMCP框架提供标准化的MCP协议支持。核心设计原则：

1. **工具导向设计** - 每个功能作为独立的MCP工具暴露
2. **异步优先** - 所有IO操作使用async/await模式
3. **类型安全** - 完整的类型注解与验证
4. **错误容错** - 完善的异常处理与日志记录

```python
# 设计模式示例
@self.mcp.tool()
async def search_rules(query: str = "", languages: str = "", ...) -> str:
    """工具函数通过装饰器自动注册到MCP协议"""
    try:
        await self._ensure_initialized()
        # 业务逻辑处理
        return formatted_result
    except Exception as e:
        logger.error(f"搜索规则时发生错误: {e}")
        return f"❌ 搜索失败: {str(e)}"
```

#### HTTP服务器 (http_server.py) 设计模式

MCPHttpServer采用**组合模式**构建REST API，通过FastAPI提供HTTP/JSON-RPC双协议支持。核心设计原则：

1. **协议桥接** - MCP协议与HTTP协议之间的适配层
2. **请求路由** - 统一的请求处理与分发机制
3. **响应标准化** - 统一的响应格式与错误处理
4. **性能优化** - 支持多进程部署与负载均衡

### 数据访问层设计

```mermaid
classDiagram
    class RuleEngine {
        +rules_dir: str
        +templates_dir: str
        +rules: Dict[str, CursorRule]
        +prompt_templates: Dict[str, PromptTemplate]
        +database: RuleDatabase
        +validation_tools: Dict[str, List[str]]
        
        +initialize() async
        +load_rules() async
        +load_prompt_templates(files: List[str], mode: str)
        +search_rules(filter: SearchFilter) async
        +validate_content(content: str, context: MCPContext) async
        +enhance_prompt(prompt: str, context: MCPContext) async
        +get_statistics(resource_type: str) dict
    }
    
    class RuleDatabase {
        +data_dir: str
        +rules: Dict[str, CursorRule]
        +version_manager: RuleVersionManager
        +conflict_detector: RuleConflictDetector
        
        +save_rule(rule: CursorRule) async
        +load_rules() async
        +get_rule(rule_id: str) CursorRule
        +delete_rule(rule_id: str) async
        +get_database_stats() dict
        +search_by_criteria(criteria: dict) List[CursorRule]
    }
    
    class RuleVersionManager {
        +manage_versions(rule: CursorRule) bool
        +get_latest_version(rule_id: str) str
        +get_version_history(rule_id: str) List[str]
        +compare_versions(v1: str, v2: str) int
    }
    
    class RuleConflictDetector {
        +detect_conflicts(new_rule: CursorRule) List[str]
        +resolve_conflicts(conflicts: List[str], strategy: str) bool
        +merge_rules(base: CursorRule, incoming: CursorRule) CursorRule
    }
    
    RuleEngine --> RuleDatabase
    RuleDatabase --> RuleVersionManager
    RuleDatabase --> RuleConflictDetector
```

---

## 🔧 工具与验证器系统

### 验证器架构

```mermaid
classDiagram
    class BaseValidator {
        <<abstract>>
        +name: str
        +language: str
        +command: str
        +timeout: int
        +validate_async(content: str) ToolResult*
        +_parse_output(output: str) List[ValidationIssue]*
    }
    
    class PythonFlake8Validator {
        +validate_async(content: str) ToolResult
        +_parse_output(output: str) List[ValidationIssue]
        +_create_temp_file(content: str) str
    }
    
    class PythonPylintValidator {
        +validate_async(content: str) ToolResult
        +_parse_json_output(output: str) List[ValidationIssue]
    }
    
    class JavaScriptESLintValidator {
        +validate_async(content: str) ToolResult
        +_parse_eslint_output(output: str) List[ValidationIssue]
    }
    
    class ValidationManager {
        +validators: Dict[str, BaseValidator]
        +register_validator(validator: BaseValidator)
        +get_validator(language: str) BaseValidator
        +validate_async(content: str, language: str) ToolResult
        +validate_parallel(content: str, languages: List[str]) List[ToolResult]
    }
    
    BaseValidator <|-- PythonFlake8Validator
    BaseValidator <|-- PythonPylintValidator  
    BaseValidator <|-- JavaScriptESLintValidator
    ValidationManager --> BaseValidator
```

### 支持的验证工具

| 语言 | 工具 | 检查类型 | 配置参数 |
|------|------|----------|----------|
| **Python** | Flake8 | 代码风格、语法错误 | `--max-line-length=88` |
| **Python** | Pylint | 代码质量、复杂度 | `--disable=C0103,C0114` |
| **Python** | Black | 代码格式化检查 | `--check --diff` |
| **Python** | Mypy | 类型检查 | `--ignore-missing-imports` |
| **JavaScript** | ESLint | 语法、风格、最佳实践 | `--format=json` |
| **TypeScript** | TSLint | TypeScript特定检查 | `--format=json` |
| **C++** | Clang-tidy | 静态分析、现代化建议 | `-checks=*` |
| **Markdown** | Markdownlint | 文档格式、结构 | `--json` |

---

## 📚 技术细节补充

### MCP协议实现细节

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_rules",
    "arguments": {
      "query": "python naming conventions",
      "languages": "python",
      "limit": 10
    }
  },
  "id": "request-123"
}
```

### HTTP API规范

```yaml
openapi: 3.0.0
info:
  title: CursorRules-MCP API
  version: 1.4.0
paths:
  /mcp/jsonrpc:
    post:
      summary: MCP JSON-RPC接口
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/JsonRpcRequest'
  /import_rule:
    post:
      summary: 规则导入接口
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ImportRuleRequest'
```

### 配置管理

配置系统采用分层设计，支持环境变量覆盖和动态重载：

```python
# 配置优先级: 环境变量 > 配置文件 > 默认值
@dataclass
class CursorRulesConfig:
    rules_dir: str = field(default="data/rules")
    server_host: str = field(default="localhost") 
    server_port: int = field(default=8000)
    
    def __post_init__(self):
        # 环境变量覆盖
        self.rules_dir = os.getenv("CURSORRULES_RULES_DIR", self.rules_dir)
        self.server_port = int(os.getenv("CURSORRULES_PORT", self.server_port))
```

---

## ✅ 总结

CursorRules-MCP通过现代化的架构设计和技术选型，实现了一个高性能、可扩展的智能规则管理系统。项目在以下方面具有显著优势：

### 🎯 核心优势

1. **多协议支持** - MCP、HTTP、CLI三位一体的接口设计
2. **异步优先** - 全链路异步处理提升并发性能
3. **智能匹配** - 多维度评分算法确保规则匹配准确性
4. **扩展性强** - 插件化验证器与模块化设计
5. **运维友好** - 完善的监控、日志与配置管理

### 🔧 技术亮点

- **现代Python栈**: FastAPI + Pydantic + SQLAlchemy的最佳实践组合
- **协议桥接**: MCP与HTTP协议的无缝适配
- **并发处理**: 多进程+异步IO的高并发架构
- **缓存策略**: 多级缓存提升系统响应速度
- **类型安全**: 完整的类型注解与运行时验证

项目为LLM应用生态提供了强大的代码质量控制基础设施，在规则管理、内容验证、提示增强等方面建立了行业标准，具有广阔的应用前景和技术价值。

---

**文档版本**: v1.4.0  
**最后更新**: 2025-06-23  
**维护团队**: Mapoet