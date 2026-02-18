import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.chain import (
    ChainDefinition, ChainExecutionResult, ChainTemplate,
    ChainAnalytics, ChainValidationResult, ChainNode, ChainNodeType
)
from .chain_storage import ChainStorageManager
from .chain_executor import ChainExecutor
from .plugin_manager import PluginManager
from ..ai.execution_history import ExecutionHistoryManager, ExecutionRecord
from ..models.plugin import model_json_schema


class ChainManager:
    """Central manager for all chain operations"""

    def __init__(self, plugin_manager: PluginManager, base_dir: str = "app/data"):
        self.plugin_manager = plugin_manager
        self.storage = ChainStorageManager(base_dir)
        self.executor = ChainExecutor(plugin_manager)
        self.history_manager = ExecutionHistoryManager()

        # Initialize with sample templates
        self._ensure_sample_templates()
    
    # ========== Chain CRUD Operations ==========
    
    def create_chain(self, name: str, description: str = "", author: str = None) -> ChainDefinition:
        """Create a new empty chain"""
        chain = ChainDefinition(
            id=f"chain-{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            author=author,
            nodes=[],
            connections=[]
        )
        
        success = self.storage.save_chain(chain)
        if not success:
            raise RuntimeError(f"Failed to save chain {chain.id}")
        
        return chain
    
    def save_chain(self, chain: ChainDefinition) -> bool:
        """Save chain to storage"""
        return self.storage.save_chain(chain)
    
    def load_chain(self, chain_id: str) -> Optional[ChainDefinition]:
        """Load chain by ID"""
        return self.storage.load_chain(chain_id)
    
    def list_chains(self, tags: List[str] = None, template_only: bool = False) -> List[ChainDefinition]:
        """List all chains with optional filtering"""
        return self.storage.list_chains(tags=tags, template_only=template_only)
    
    def delete_chain(self, chain_id: str) -> bool:
        """Delete chain by ID"""
        return self.storage.delete_chain(chain_id)
    
    def search_chains(self, query: str = "", tags: List[str] = None) -> List[Dict[str, Any]]:
        """Search chains by query and tags"""
        return self.storage.search_chains(query=query, tags=tags)
    
    def duplicate_chain(self, chain_id: str, new_name: str = None) -> Optional[ChainDefinition]:
        """Duplicate an existing chain"""
        original = self.load_chain(chain_id)
        if not original:
            return None
        
        # Create new chain with duplicated data
        duplicate = ChainDefinition(
            id=f"chain-{uuid.uuid4().hex[:8]}",
            name=new_name or f"{original.name} (Copy)",
            description=f"Copy of {original.description}",
            version="1.0.0",
            nodes=original.nodes.copy(),
            connections=original.connections.copy(),
            input_schema=original.input_schema.copy(),
            output_schema=original.output_schema.copy(),
            tags=original.tags.copy(),
            author=original.author
        )
        
        success = self.save_chain(duplicate)
        return duplicate if success else None
    
    # ========== Chain Validation ==========
    
    def validate_chain(self, chain: ChainDefinition) -> ChainValidationResult:
        """Validate chain definition"""
        return self.executor.validator.validate_chain(chain)
    
    # ========== Chain Execution ==========
    
    async def execute_chain(self, chain_id: str, input_data: Dict[str, Any]) -> ChainExecutionResult:
        """Execute a chain by ID"""
        chain = self.load_chain(chain_id)
        if not chain:
            raise ValueError(f"Chain {chain_id} not found")

        # Execute chain
        result = await self.executor.execute_chain(chain, input_data)

        # Save execution result
        self.storage.save_execution_result(result)

        # Record for AI learning
        self._record_execution_for_ai(chain, result, input_data)

        return result
    
    async def execute_chain_definition(self, chain: ChainDefinition, input_data: Dict[str, Any]) -> ChainExecutionResult:
        """Execute a chain definition directly (without saving)"""
        result = await self.executor.execute_chain(chain, input_data)

        # Record for AI learning
        self._record_execution_for_ai(chain, result, input_data)

        return result

    def _record_execution_for_ai(
        self,
        chain: ChainDefinition,
        result: ChainExecutionResult,
        input_data: Dict[str, Any]
    ):
        """Record execution for AI analysis"""
        try:
            # Extract plugins used
            plugins_used = [node.plugin_id for node in chain.nodes if node.plugin_id]

            # Get input size if available
            input_size_bytes = None
            if "input_file" in input_data:
                file_data = input_data["input_file"]
                if isinstance(file_data, dict) and "size" in file_data:
                    input_size_bytes = file_data["size"]

            # Create execution record
            record = ExecutionRecord(
                id=result.execution_id,
                chain_id=chain.id,
                timestamp=datetime.fromisoformat(result.started_at),
                duration_seconds=result.execution_time,
                success=result.success,
                input_size_bytes=input_size_bytes,
                node_durations={},
                node_results={},
                plugins_used=plugins_used,
                error_message=result.error,
                metadata={}
            )

            # Record in history
            self.history_manager.record_execution(record)
        except Exception as e:
            # Don't fail the execution if history recording fails
            print(f"Failed to record execution for AI: {e}")
    
    # ========== Chain Analytics ==========
    
    def get_execution_history(self, chain_id: str, limit: int = 50) -> List[ChainExecutionResult]:
        """Get execution history for a chain"""
        return self.storage.get_execution_history(chain_id, limit)
    
    def get_chain_analytics(self, chain_id: str) -> Optional[ChainAnalytics]:
        """Get analytics for a specific chain"""
        return self.storage.get_chain_analytics(chain_id)
    
    def get_system_analytics(self) -> Dict[str, Any]:
        """Get system-wide analytics"""
        return self.storage.get_system_analytics()
    
    # ========== Template Management ==========
    
    def create_template_from_chain(self, chain_id: str, category: str = "custom", 
                                 difficulty_level: str = "intermediate") -> Optional[ChainTemplate]:
        """Convert a chain to a template"""
        chain = self.load_chain(chain_id)
        if not chain:
            return None
        
        # Extract required plugins
        required_plugins = list(set(
            node.plugin_id for node in chain.nodes 
            if node.type == ChainNodeType.PLUGIN and node.plugin_id
        ))
        
        template = ChainTemplate(
            id=f"template-{uuid.uuid4().hex[:8]}",
            name=f"{chain.name} Template",
            description=f"Template based on {chain.description}",
            category=category,
            chain_definition=chain,
            difficulty_level=difficulty_level,
            estimated_time=60,  # Default 1 minute
            required_plugins=required_plugins
        )
        
        success = self.storage.save_template(template)
        return template if success else None
    
    def list_templates(self, category: str = None) -> List[ChainTemplate]:
        """List all templates"""
        return self.storage.list_templates(category=category)
    
    def load_template(self, template_id: str) -> Optional[ChainTemplate]:
        """Load template by ID"""
        return self.storage.load_template(template_id)
    
    def create_chain_from_template(self, template_id: str, name: str, 
                                 author: str = None) -> Optional[ChainDefinition]:
        """Create a new chain from a template"""
        template = self.load_template(template_id)
        if not template:
            return None
        
        # Create new chain from template
        chain = ChainDefinition(
            id=f"chain-{uuid.uuid4().hex[:8]}",
            name=name,
            description=f"Based on template: {template.description}",
            version="1.0.0",
            nodes=template.chain_definition.nodes.copy(),
            connections=template.chain_definition.connections.copy(),
            input_schema=template.chain_definition.input_schema.copy(),
            output_schema=template.chain_definition.output_schema.copy(),
            tags=[template.category] + template.chain_definition.tags,
            author=author
        )
        
        success = self.save_chain(chain)
        return chain if success else None
    
    # ========== Chain Building Helpers ==========
    
    def add_plugin_node(self, chain: ChainDefinition, plugin_id: str, 
                       position: Dict[str, float], label: str = None) -> str:
        """Add a plugin node to a chain"""
        node_id = f"node-{uuid.uuid4().hex[:8]}"
        
        plugin = self.plugin_manager.get_plugin(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin {plugin_id} not found")
        
        node = ChainNode(
            id=node_id,
            type=ChainNodeType.PLUGIN,
            plugin_id=plugin_id,
            position=position,
            label=label or plugin.name
        )
        
        chain.nodes.append(node)
        return node_id
    
    def add_transform_node(self, chain: ChainDefinition, transform_type: str,
                         position: Dict[str, float], config: Dict[str, Any] = None) -> str:
        """Add a transform node to a chain"""
        node_id = f"node-{uuid.uuid4().hex[:8]}"
        
        node = ChainNode(
            id=node_id,
            type=ChainNodeType.TRANSFORM,
            position=position,
            config={"transform_type": transform_type, **(config or {})},
            label=f"Transform: {transform_type}"
        )
        
        chain.nodes.append(node)
        return node_id
    
    def connect_nodes(self, chain: ChainDefinition, source_node_id: str, 
                     target_node_id: str, data_mappings: List[Dict[str, str]] = None) -> str:
        """Connect two nodes in a chain"""
        from ..models.chain import ChainConnection, DataMapping
        
        connection_id = f"conn-{uuid.uuid4().hex[:8]}"
        
        # Validate nodes exist
        source_node = next((n for n in chain.nodes if n.id == source_node_id), None)
        target_node = next((n for n in chain.nodes if n.id == target_node_id), None)
        
        if not source_node:
            raise ValueError(f"Source node {source_node_id} not found")
        if not target_node:
            raise ValueError(f"Target node {target_node_id} not found")
        
        # Create data mappings
        mappings = []
        if data_mappings:
            for mapping in data_mappings:
                mappings.append(DataMapping(
                    source_field=mapping["source_field"],
                    target_field=mapping["target_field"],
                    transform=mapping.get("transform")
                ))
        
        connection = ChainConnection(
            id=connection_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            data_mappings=mappings
        )
        
        chain.connections.append(connection)
        return connection_id
    
    def get_plugin_schema(self, plugin_id: str) -> Dict[str, Any]:
        """Get plugin input/output schema for chain building"""
        plugin = self.plugin_manager.get_plugin(plugin_id)
        if not plugin:
            return {}
        
        # Get plugin class and response model
        plugin_class = self.plugin_manager.loader.get_plugin_class(plugin_id)
        if not plugin_class:
            return {}
        
        try:
            response_model = plugin_class.get_response_model()
            
            return {
                "input_schema": {
                    field.name: {
                        "type": field.field_type,
                        "required": field.required,
                        "description": field.label,
                        "options": field.options
                    } for field in plugin.inputs
                },
                "output_schema": model_json_schema(response_model) if response_model else {}
            }
        except Exception:
            return {
                "input_schema": {
                    field.name: {
                        "type": field.field_type,
                        "required": field.required,
                        "description": field.label
                    } for field in plugin.inputs
                },
                "output_schema": {}
            }
    
    def get_compatible_connections(self, chain: ChainDefinition, source_node_id: str) -> List[Dict[str, Any]]:
        """Get possible connections from a source node"""
        source_node = next((n for n in chain.nodes if n.id == source_node_id), None)
        if not source_node or source_node.type != ChainNodeType.PLUGIN:
            return []
        
        compatible = []
        
        for node in chain.nodes:
            if node.id == source_node_id or node.type != ChainNodeType.PLUGIN:
                continue
            
            # Check if already connected
            existing_connection = next((
                c for c in chain.connections 
                if c.source_node_id == source_node_id and c.target_node_id == node.id
            ), None)
            
            if not existing_connection:
                # Get schemas to suggest field mappings
                source_schema = self.get_plugin_schema(source_node.plugin_id)
                target_schema = self.get_plugin_schema(node.plugin_id)
                
                compatible.append({
                    "target_node_id": node.id,
                    "target_label": node.label or node.plugin_id,
                    "suggested_mappings": self._suggest_field_mappings(
                        source_schema.get("output_schema", {}),
                        target_schema.get("input_schema", {})
                    )
                })
        
        return compatible
    
    def _suggest_field_mappings(self, source_schema: Dict[str, Any], 
                               target_schema: Dict[str, Any]) -> List[Dict[str, str]]:
        """Suggest field mappings based on field names and types"""
        suggestions = []
        
        if not source_schema or not target_schema:
            return suggestions
        
        source_fields = source_schema.get("properties", {})
        
        for target_field, target_info in target_schema.items():
            # Look for exact name matches first
            if target_field in source_fields:
                suggestions.append({
                    "source_field": target_field,
                    "target_field": target_field,
                    "confidence": "high"
                })
                continue
            
            # Look for similar names
            for source_field in source_fields:
                if (source_field.lower() in target_field.lower() or 
                    target_field.lower() in source_field.lower()):
                    suggestions.append({
                        "source_field": source_field,
                        "target_field": target_field,
                        "confidence": "medium"
                    })
                    break
        
        return suggestions
    
    # ========== Sample Templates ==========
    
    def _ensure_sample_templates(self):
        """Create sample templates if they don't exist"""
        pass  # Will implement later 
