from typing import Dict, Any, List, Optional, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class ChainNodeType(str, Enum):
    PLUGIN = "plugin"
    CONDITION = "condition"
    TRANSFORM = "transform"
    MERGE = "merge"
    SPLIT = "split"


class DataMapping(BaseModel):
    """Maps output fields from source to input fields of target"""
    source_field: str = Field(..., description="Field name from source plugin output")
    target_field: str = Field(..., description="Field name for target plugin input")
    transform: Optional[str] = Field(None, description="Optional transformation function")


class ChainNode(BaseModel):
    """Individual node in a plugin chain"""
    id: str = Field(..., description="Unique node identifier")
    type: ChainNodeType = Field(..., description="Type of chain node")
    plugin_id: Optional[str] = Field(None, description="Plugin ID if type is PLUGIN")
    position: Dict[str, float] = Field(..., description="UI position {x, y}")
    config: Dict[str, Any] = Field(default_factory=dict, description="Node-specific configuration")
    label: Optional[str] = Field(None, description="Custom node label")
    
    class Config:
        extra = "allow"


class ChainConnection(BaseModel):
    """Connection between chain nodes"""
    id: str = Field(..., description="Unique connection identifier")
    source_node_id: str = Field(..., description="Source node ID")
    target_node_id: str = Field(..., description="Target node ID")
    data_mappings: List[DataMapping] = Field(default_factory=list, description="Field mappings")
    condition: Optional[str] = Field(None, description="Conditional execution logic")


class ChainDefinition(BaseModel):
    """Complete chain definition"""
    id: str = Field(..., description="Unique chain identifier")
    name: str = Field(..., description="Human-readable chain name")
    description: str = Field(..., description="Chain description")
    version: str = Field(default="1.0.0", description="Chain version")
    nodes: List[ChainNode] = Field(..., description="Chain nodes")
    connections: List[ChainConnection] = Field(..., description="Node connections")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="Expected input schema")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="Expected output schema")
    tags: List[str] = Field(default_factory=list, description="Chain tags for categorization")
    is_template: bool = Field(default=False, description="Is this a reusable template")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Creation timestamp")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Last update timestamp")
    author: Optional[str] = Field(None, description="Chain author")
    
    class Config:
        extra = "allow"


class ChainExecutionResult(BaseModel):
    """Result of chain execution"""
    success: bool = Field(..., description="Overall execution success")
    chain_id: str = Field(..., description="Executed chain ID")
    execution_id: str = Field(..., description="Unique execution ID")
    results: Dict[str, Any] = Field(..., description="Final chain output")
    node_results: Dict[str, Dict[str, Any]] = Field(..., description="Individual node results")
    execution_time: float = Field(..., description="Total execution time")
    error: Optional[str] = Field(None, description="Error message if failed")
    node_execution_stats: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Per-node execution telemetry (duration, status, error, plugin_id)"
    )
    execution_graph: List[List[str]] = Field(default_factory=list, description="Execution order by batches")
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Execution start time")
    completed_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Execution completion time")


class ChainTemplate(BaseModel):
    """Reusable chain template"""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    chain_definition: ChainDefinition = Field(..., description="Template chain definition")
    preview_image: Optional[str] = Field(None, description="Template preview image URL")
    difficulty_level: Literal["beginner", "intermediate", "advanced"] = Field("beginner", description="Template difficulty")
    estimated_time: int = Field(..., description="Estimated execution time in seconds")
    required_plugins: List[str] = Field(..., description="Required plugin IDs")


class ChainAnalytics(BaseModel):
    """Analytics data for a chain"""
    chain_id: str = Field(..., description="Chain ID")
    total_executions: int = Field(0, description="Total number of executions")
    successful_executions: int = Field(0, description="Number of successful executions")
    failed_executions: int = Field(0, description="Number of failed executions")
    average_execution_time: float = Field(0.0, description="Average execution time in seconds")
    last_execution: Optional[str] = Field(None, description="Last execution timestamp")
    success_rate: float = Field(0.0, description="Success rate percentage")
    most_common_errors: List[Dict[str, Any]] = Field(default_factory=list, description="Most common error types")
    performance_trend: List[Dict[str, Any]] = Field(default_factory=list, description="Performance over time")


class ChainValidationResult(BaseModel):
    """Result of chain validation"""
    is_valid: bool = Field(..., description="Whether the chain is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    missing_plugins: List[str] = Field(default_factory=list, description="Missing required plugins")
    cycle_detected: bool = Field(False, description="Whether circular dependencies were detected")
    disconnected_nodes: List[str] = Field(default_factory=list, description="Nodes not connected to the main flow") 
