"""
Core data models for CursorRules-MCP system.

This module defines the fundamental data structures used throughout the system,
including rules, knowledge items, contexts, and validation results.

Author: Mapoet
Institution: NUS/STAR
Date: 2025-01-23
License: MIT
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, validator
import uuid


class RuleType(str, Enum):
    """Types of cursor rules."""
    STYLE = "style"
    CONTENT = "content"
    SEMANTIC = "semantic"
    FORMAT = "format"
    PERFORMANCE = "performance"
    SECURITY = "security"


class ContentType(str, Enum):
    """Types of content that rules can apply to."""
    CODE = "code"
    DOCUMENTATION = "documentation"
    DATA_INTERFACE = "data_interface"
    DATA = "data"
    ALGORITHM = "algorithm"
    CONFIGURATION = "configuration"


class TaskType(str, Enum):
    """Types of tasks."""
    DATA_ANALYSIS = "data_analysis"
    VISUALIZATION = "visualization"
    GUI_DEVELOPMENT = "gui_development"
    HTTP_SERVICE = "http_service"
    LLM_MCP = "llm_mcp"
    NUMERICAL_COMPUTATION = "numerical_computation"
    PAPER_WRITING = "paper_writing"
    GRANT_APPLICATION = "grant_application"
    SOFTWARE_DESIGN = "software_design"
    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"
    CODE_REVIEW = "code_review"


class ValidationSeverity(str, Enum):
    """Severity levels for validation results."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RuleCondition(BaseModel):
    """Represents a conditional rule application."""
    condition: str = Field(..., description="When this rule applies")
    guideline: str = Field(..., description="What the rule specifies")
    priority: int = Field(default=5, ge=1, le=10, description="Rule priority (1-10)")
    examples: List[Any] = Field(default_factory=list, description="Usage examples")
    pattern: Optional[str] = Field(default=None, description="Regex pattern for validation")



class RuleApplication(BaseModel):
    """Defines where and how a rule applies."""
    file_patterns: List[str] = Field(default_factory=list, description="File patterns")
    project_types: List[str] = Field(default_factory=list, description="Project types")
    contexts: List[str] = Field(default_factory=list, description="Application contexts")


class RuleValidation(BaseModel):
    """Validation configuration for a rule."""
    tools: List[str] = Field(default_factory=list, description="Validation tools")
    severity: ValidationSeverity = Field(default=ValidationSeverity.WARNING, description="Validation severity")
    auto_fix: bool = Field(default=False, description="Whether auto-fix is enabled")
    timeout: int = Field(default=30, description="Validation timeout in seconds")
    custom_config: Dict[str, Any] = Field(default_factory=dict, description="Custom configuration")
    
    # Legacy fields for backward compatibility
    code_style: Optional[str] = Field(None, description="Code style standard")
    documentation: Optional[str] = Field(None, description="Documentation standard")
    testing: Optional[str] = Field(None, description="Testing requirements")
    custom_validators: List[str] = Field(default_factory=list, description="Custom validation functions")


class CursorRule(BaseModel):
    """
    Core cursor rule model with comprehensive metadata and validation.
    
    Represents a single rule that can be applied to guide LLM behavior
    in specific contexts and domains.
    """
    # Identification
    rule_id: str = Field(..., description="Unique identifier for the rule")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Detailed description of the rule")
    version: str = Field(default="1.0.0", description="Rule version")
    author: str = Field(..., description="Rule creator")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Classification
    rule_type: RuleType = Field(..., description="Type of rule")
    languages: List[str] = Field(default_factory=list, description="Programming languages")
    domains: List[str] = Field(default_factory=list, description="Application domains")
    task_types: List[TaskType] = Field(default_factory=list, description="Task types")
    content_types: List[ContentType] = Field(default_factory=list, description="Content types")
    
    # Tagging system
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    
    # Rule definition
    rules: List[RuleCondition] = Field(..., description="Rule conditions and guidelines")
    
    # Application scope
    applies_to: RuleApplication = Field(default_factory=RuleApplication)
    
    # Conflict handling
    conflicts_with: List[str] = Field(default_factory=list, description="Conflicting rule IDs")
    overrides: List[str] = Field(default_factory=list, description="Overridden rule IDs")
    
    # Validation
    validation: RuleValidation = Field(default_factory=RuleValidation)
    
    # Metadata
    active: bool = Field(default=True, description="Whether rule is active")
    usage_count: int = Field(default=0, description="Times rule has been used")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Success rate")

    @validator('rule_id')
    def validate_rule_id(cls, v):
        """Validate rule ID format."""
        if not v.startswith('CR-'):
            raise ValueError('Rule ID must start with "CR-"')
        return v

    @validator('tags')
    def validate_tags(cls, v):
        """Ensure tags are lowercase and cleaned."""
        return [tag.lower().strip() for tag in v if tag.strip()]

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class KnowledgeType(str, Enum):
    """Types of knowledge items."""
    ALGORITHM = "algorithm"
    DATA_INTERFACE = "data_interface"
    RESEARCH_PAPER = "research_paper"
    CODE_SNIPPET = "code_snippet"
    DOCUMENTATION = "documentation"
    BEST_PRACTICE = "best_practice"


class KnowledgeContent(BaseModel):
    """Content structure for knowledge items."""
    abstract: str = Field(..., description="Brief description")
    full_text: Optional[str] = Field(None, description="Complete content")
    file_path: Optional[str] = Field(None, description="Path to content file")
    code_examples: List[str] = Field(default_factory=list, description="Code examples")
    references: List[str] = Field(default_factory=list, description="Related references")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class KnowledgeItem(BaseModel):
    """
    Knowledge base item for professional domain information.
    
    Represents structured knowledge that can be retrieved and used
    to enhance LLM context with domain-specific information.
    """
    # Identification
    knowledge_id: str = Field(..., description="Unique knowledge identifier")
    title: str = Field(..., description="Knowledge item title")
    knowledge_type: KnowledgeType = Field(..., description="Type of knowledge")
    
    # Classification
    domains: List[str] = Field(default_factory=list, description="Applicable domains")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    
    # Content
    content: KnowledgeContent = Field(..., description="Knowledge content")
    
    # Semantic search
    embedding_vector: Optional[List[float]] = Field(None, description="Semantic embedding")
    
    # Metadata
    source: Optional[str] = Field(None, description="Content source")
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Quality rating")
    last_indexed: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(default=0, description="Access frequency")
    
    @validator('tags')
    def validate_knowledge_tags(cls, v):
        """Ensure tags are lowercase and cleaned."""
        return [tag.lower().strip() for tag in v if tag.strip()]


class MCPContext(BaseModel):
    """
    Context information for MCP requests.
    
    Captures the current state and requirements for rule retrieval
    and application in LLM interactions.
    """
    # Request identification
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Current context
    current_file: Optional[str] = Field(None, description="Active file path")
    file_type: Optional[str] = Field(None, description="File type/extension")
    selected_text: Optional[str] = Field(None, description="Selected text content")
    cursor_position: Optional[Dict[str, int]] = Field(None, description="Cursor position")
    
    # Project context
    project_path: Optional[str] = Field(None, description="Project root path")
    project_type: Optional[str] = Field(None, description="Project type")
    project_tags: List[str] = Field(default_factory=list, description="Project tags")
    
    # User intent
    user_query: Optional[str] = Field(None, description="User's request or query")
    task_type: Optional[TaskType] = Field(None, description="Detected task type")
    intent_tags: List[str] = Field(default_factory=list, description="Intent-derived tags")
    
    # Language and domain
    primary_language: Optional[str] = Field(None, description="Primary programming language")
    domain: Optional[str] = Field(None, description="Primary domain")
    
    # Previous context
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list, description="Previous exchanges")
    applied_rules: List[str] = Field(default_factory=list, description="Previously applied rule IDs")
    
    # Preferences
    style_preferences: Dict[str, Any] = Field(default_factory=dict, description="User style preferences")
    consistency_level: str = Field(default="medium", description="Desired consistency level")


class ValidationIssue(BaseModel):
    """Represents a validation issue found in LLM output."""
    severity: ValidationSeverity = Field(..., description="Issue severity")
    message: str = Field(..., description="Issue description")
    line_number: Optional[int] = Field(None, description="Line number if applicable")
    column_number: Optional[int] = Field(None, description="Column number if applicable")
    rule_id: Optional[str] = Field(None, description="Associated rule ID")
    suggestion: Optional[str] = Field(None, description="Suggested fix")


class ValidationResult(BaseModel):
    """Result of validating content against rules."""
    is_valid: bool = Field(..., description="Whether content passes validation")
    score: float = Field(default=0.0, ge=0.0, description="Overall validation score")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Validation issues")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    applied_rules: List[str] = Field(default_factory=list, description="Rules that were applied")
    validation_time: Optional[datetime] = Field(default=None, description="When validation was performed")



class ApplicableRule(BaseModel):
    """A rule that applies to a specific context with relevance scoring."""
    rule: CursorRule = Field(..., description="The applicable rule")
    relevance_score: float = Field(default=0.0, ge=0.0, description="Context relevance")
    matched_conditions: List[str] = Field(default_factory=list, description="Matched conditions")
    application_context: Dict[str, Any] = Field(default_factory=dict, description="Application context")
    match_reasons: List[str] = Field(default_factory=list, description="Why this rule matched")
    priority_weight: float = Field(default=1.0, description="Priority weighting")



class EnhancedPrompt(BaseModel):
    """Enhanced prompt with injected rules and context."""
    original_prompt: str = Field(..., description="Original user prompt")
    enhanced_prompt: str = Field(..., description="Enhanced prompt with rules")
    injected_rules: List[str] = Field(default_factory=list, description="Injected rule IDs")
    context_summary: str = Field(default="", description="Context summary")
    priority_strategy: str = Field(default="weighted", description="Priority application strategy")


class SearchFilter(BaseModel):
    """Filter criteria for searching rules and knowledge."""
    query: Optional[str] = Field(None, description="Search query text")
    domains: Optional[List[str]] = Field(None, description="Domain filters")
    languages: Optional[List[str]] = Field(None, description="Language filters")
    task_types: Optional[List[TaskType]] = Field(None, description="Task type filters")
    content_types: Optional[List[str]] = Field(None, description="Content type filters")
    rule_types: Optional[List[RuleType]] = Field(None, description="Rule type filters")
    tags: Optional[List[str]] = Field(None, description="Tag filters")
    date_range: Optional[Dict[str, datetime]] = Field(None, description="Date range filter")
    quality_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum quality score")
    limit: int = Field(default=50, ge=1, le=1000, description="Result limit")
 