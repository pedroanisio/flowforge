import asyncio
import uuid
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict, deque

from ..models.chain import (
    ChainDefinition, ChainExecutionResult, ChainNode, ChainConnection, 
    ChainNodeType, ChainValidationResult
)
from ..models.plugin import PluginInput
from .plugin_manager import PluginManager


class ChainValidator:
    """Validates chain definitions for correctness"""
    
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
    
    def validate_chain(self, chain: ChainDefinition) -> ChainValidationResult:
        """Comprehensive chain validation"""
        errors = []
        warnings = []
        missing_plugins = []
        disconnected_nodes = []
        
        # Check for empty chain
        if not chain.nodes:
            errors.append("Chain must contain at least one node")
        
        # Validate nodes
        node_ids = {node.id for node in chain.nodes}
        plugin_nodes = [node for node in chain.nodes if node.type == ChainNodeType.PLUGIN]
        
        # Check plugin existence and compliance
        for node in plugin_nodes:
            if not node.plugin_id:
                errors.append(f"Plugin node {node.id} missing plugin_id")
                continue
                
            plugin = self.plugin_manager.get_plugin(node.plugin_id)
            if not plugin:
                missing_plugins.append(node.plugin_id)
                errors.append(f"Plugin '{node.plugin_id}' not found for node {node.id}")
                continue
            
            # Check plugin compliance
            if hasattr(plugin, 'compliance_status') and not plugin.compliance_status.get("compliant", False):
                warnings.append(f"Plugin '{node.plugin_id}' is not compliant: {plugin.compliance_status.get('error', 'Unknown error')}")
        
        # Validate connections
        connection_sources = set()
        connection_targets = set()
        
        for conn in chain.connections:
            # Check node references
            if conn.source_node_id not in node_ids:
                errors.append(f"Connection {conn.id} references non-existent source node {conn.source_node_id}")
            if conn.target_node_id not in node_ids:
                errors.append(f"Connection {conn.id} references non-existent target node {conn.target_node_id}")
            
            connection_sources.add(conn.source_node_id)
            connection_targets.add(conn.target_node_id)
        
        # Check for cycles
        cycle_detected = self._detect_cycles(chain)
        if cycle_detected:
            errors.append("Circular dependencies detected in chain")
        
        # Find disconnected nodes (except start nodes)
        all_connected = connection_sources | connection_targets
        for node in chain.nodes:
            if node.id not in all_connected and len(chain.nodes) > 1:
                disconnected_nodes.append(node.id)
                warnings.append(f"Node {node.id} is not connected to any other nodes")
        
        # Validate data mappings
        for conn in chain.connections:
            source_node = next((n for n in chain.nodes if n.id == conn.source_node_id), None)
            target_node = next((n for n in chain.nodes if n.id == conn.target_node_id), None)
            
            if source_node and target_node and source_node.type == ChainNodeType.PLUGIN and target_node.type == ChainNodeType.PLUGIN:
                # Check if plugin schemas are compatible
                self._validate_data_mappings(conn, source_node, target_node, warnings)
        
        is_valid = len(errors) == 0
        
        return ChainValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_plugins=missing_plugins,
            cycle_detected=cycle_detected,
            disconnected_nodes=disconnected_nodes
        )
    
    def _detect_cycles(self, chain: ChainDefinition) -> bool:
        """Detect circular dependencies using DFS"""
        # Build adjacency list
        graph = defaultdict(list)
        for conn in chain.connections:
            graph[conn.source_node_id].append(conn.target_node_id)
        
        # DFS cycle detection
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for neighbor in graph[node_id]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node in chain.nodes:
            if node.id not in visited:
                if dfs(node.id):
                    return True
        
        return False
    
    def _validate_data_mappings(self, connection: ChainConnection, 
                               source_node: ChainNode, target_node: ChainNode, 
                               warnings: List[str]):
        """Validate data field mappings between nodes"""
        try:
            # Get plugin schemas
            source_plugin = self.plugin_manager.get_plugin(source_node.plugin_id)
            target_plugin = self.plugin_manager.get_plugin(target_node.plugin_id)
            
            if not source_plugin or not target_plugin:
                return
            
            # Get plugin classes to access response models
            source_class = self.plugin_manager.loader.get_plugin_class(source_node.plugin_id)
            target_class = self.plugin_manager.loader.get_plugin_class(target_node.plugin_id)
            
            if source_class and target_class:
                source_model = source_class.get_response_model()
                target_inputs = target_plugin.inputs
                
                # Check if mappings are valid
                for mapping in connection.data_mappings:
                    # Check if source field exists in response model
                    source_fields = getattr(source_model, "model_fields", getattr(source_model, "__fields__", {}))
                    if mapping.source_field not in source_fields:
                        warnings.append(f"Source field '{mapping.source_field}' not found in {source_node.plugin_id} output schema")
                    
                    # Check if target field exists in input schema
                    target_field_names = [field.name for field in target_inputs]
                    if mapping.target_field not in target_field_names:
                        warnings.append(f"Target field '{mapping.target_field}' not found in {target_node.plugin_id} input schema")
                        
        except Exception:
            # Skip validation if we can't access schemas
            pass


class ChainExecutor:
    """Executes plugin chains with dependency resolution and error handling"""
    
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
        self.validator = ChainValidator(plugin_manager)
    
    async def execute_chain(self, chain: ChainDefinition, input_data: Dict[str, Any]) -> ChainExecutionResult:
        """Execute a complete plugin chain"""
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()
        node_results: Dict[str, Dict[str, Any]] = {}
        node_execution_stats: Dict[str, Dict[str, Any]] = {}
        
        try:
            # Validate chain first
            validation = self.validator.validate_chain(chain)
            if not validation.is_valid:
                raise ValueError(f"Chain validation failed: {'; '.join(validation.errors)}")
            
            # Build execution graph (topological sort)
            execution_graph = self._build_execution_graph(chain)
            
            # Execute nodes in dependency order
            execution_context = {
                "input": input_data, 
                "results": node_results,
                "chain": chain
            }
            
            # Execute in batches (parallel where possible)
            for node_batch in execution_graph:
                # Execute nodes in parallel within batch
                batch_tasks = []
                for node in node_batch:
                    task = self._execute_node_with_timing(node, execution_context)
                    batch_tasks.append(task)
                
                batch_results = await asyncio.gather(*batch_tasks)
                
                # Process batch results and handle errors
                for node, result in zip(node_batch, batch_results):
                    node_execution_stats[node.id] = result["telemetry"]
                    if not result["success"]:
                        raise Exception(result["error"] or f"Node {node.id} failed")
                    node_results[node.id] = result["data"]
            
            # Extract final output from last nodes
            final_output = self._extract_final_output(node_results, chain)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            return ChainExecutionResult(
                success=True,
                chain_id=chain.id,
                execution_id=execution_id,
                results=final_output,
                node_results=node_results,
                execution_time=execution_time,
                node_execution_stats=node_execution_stats,
                execution_graph=[[node.id for node in batch] for batch in execution_graph],
                started_at=start_time.isoformat(),
                completed_at=end_time.isoformat()
            )
            
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            return ChainExecutionResult(
                success=False,
                chain_id=chain.id,
                execution_id=execution_id,
                results={},
                node_results=node_results,
                execution_time=execution_time,
                error=str(e),
                node_execution_stats=node_execution_stats,
                started_at=start_time.isoformat(),
                completed_at=end_time.isoformat()
            )

    async def _execute_node_with_timing(self, node: ChainNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute node and capture telemetry regardless of success/failure."""
        node_start = datetime.now()
        try:
            node_data = await self._execute_node(node, context)
            success = True
            error = None
        except Exception as exc:
            node_data = {}
            success = False
            error = str(exc)
        node_end = datetime.now()

        telemetry = {
            "duration_seconds": (node_end - node_start).total_seconds(),
            "success": success,
            "error": error,
            "plugin_id": node.plugin_id,
            "node_type": node.type.value if hasattr(node.type, "value") else str(node.type),
        }

        return {
            "success": success,
            "error": error,
            "data": node_data,
            "telemetry": telemetry,
        }
    
    def _build_execution_graph(self, chain: ChainDefinition) -> List[List[ChainNode]]:
        """Build execution graph using topological sort for parallel execution"""
        
        # Build adjacency list and in-degree count
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        nodes_by_id = {node.id: node for node in chain.nodes}
        
        # Initialize in-degree for all nodes
        for node in chain.nodes:
            in_degree[node.id] = 0
        
        # Build graph from connections
        for conn in chain.connections:
            graph[conn.source_node_id].append(conn.target_node_id)
            in_degree[conn.target_node_id] += 1
        
        # Topological sort with level detection for parallel execution
        execution_batches = []
        queue = deque()
        
        # Find nodes with no dependencies (in-degree = 0)
        for node_id, degree in in_degree.items():
            if degree == 0:
                queue.append(node_id)
        
        while queue:
            # All nodes in current queue can execute in parallel
            current_batch = []
            batch_size = len(queue)
            
            for _ in range(batch_size):
                node_id = queue.popleft()
                current_batch.append(nodes_by_id[node_id])
                
                # Reduce in-degree for neighbors
                for neighbor_id in graph[node_id]:
                    in_degree[neighbor_id] -= 1
                    if in_degree[neighbor_id] == 0:
                        queue.append(neighbor_id)
            
            if current_batch:
                execution_batches.append(current_batch)
        
        return execution_batches
    
    async def _execute_node(self, node: ChainNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute individual chain node"""
        if node.type == ChainNodeType.PLUGIN:
            return await self._execute_plugin_node(node, context)
        elif node.type == ChainNodeType.CONDITION:
            return self._execute_condition_node(node, context)
        elif node.type == ChainNodeType.TRANSFORM:
            return self._execute_transform_node(node, context)
        elif node.type == ChainNodeType.MERGE:
            return self._execute_merge_node(node, context)
        elif node.type == ChainNodeType.SPLIT:
            return self._execute_split_node(node, context)
        else:
            raise ValueError(f"Unknown node type: {node.type}")
    
    async def _execute_plugin_node(self, node: ChainNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin node"""
        # Collect input data from previous nodes and initial input
        input_data = self._collect_node_input(node, context)
        
        # Execute plugin
        plugin_input = PluginInput(plugin_id=node.plugin_id, data=input_data)
        
        # Run plugin execution in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            self.plugin_manager.execute_plugin, 
            plugin_input
        )
        
        if not result.success:
            raise Exception(f"Plugin {node.plugin_id} failed: {result.error}")
        
        return result.data or result.file_data or {}
    
    def _execute_condition_node(self, node: ChainNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute conditional logic node with safe evaluation"""
        condition = node.config.get("condition", "true")

        # Safe condition evaluation using simpleeval
        try:
            from simpleeval import simple_eval

            # Create safe evaluation context
            eval_context = {
                "input": context["input"],
                "results": context["results"]
            }

            # Safe evaluation - prevents code injection
            result = simple_eval(condition, names=eval_context)

            return {
                "condition_result": bool(result),
                "condition": condition
            }
        except Exception as e:
            return {
                "condition_result": False,
                "condition": condition,
                "error": str(e)
            }
    
    def _execute_transform_node(self, node: ChainNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data transformation node"""
        transform_type = node.config.get("transform_type", "passthrough")
        
        # Collect input data
        input_data = self._collect_node_input(node, context)
        
        if transform_type == "passthrough":
            return input_data
        elif transform_type == "extract_field":
            field_name = node.config.get("field_name")
            if field_name and field_name in input_data:
                return {"extracted_value": input_data[field_name]}
            return {"extracted_value": None}
        elif transform_type == "rename_fields":
            field_mappings = node.config.get("field_mappings", {})
            transformed = {}
            for old_name, new_name in field_mappings.items():
                if old_name in input_data:
                    transformed[new_name] = input_data[old_name]
            return transformed
        else:
            return input_data
    
    def _execute_merge_node(self, node: ChainNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data merge node"""
        # Collect all inputs from connected nodes
        input_data = self._collect_node_input(node, context)
        
        merge_strategy = node.config.get("merge_strategy", "combine")
        
        if merge_strategy == "combine":
            # Combine all input data into a single dictionary
            merged = {}
            if isinstance(input_data, dict):
                merged.update(input_data)
            return merged
        elif merge_strategy == "array":
            # Collect inputs as an array
            return {"merged_results": [input_data] if not isinstance(input_data, list) else input_data}
        else:
            return input_data
    
    def _execute_split_node(self, node: ChainNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data split node"""
        input_data = self._collect_node_input(node, context)
        
        split_strategy = node.config.get("split_strategy", "passthrough")
        
        if split_strategy == "array_items":
            # Split array into individual items
            if isinstance(input_data, dict) and "array" in input_data:
                array_data = input_data["array"]
                if isinstance(array_data, list):
                    return {"split_items": array_data}
            return {"split_items": [input_data]}
        else:
            return input_data
    
    def _collect_node_input(self, node: ChainNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect input data for a node from connected sources"""
        chain = context["chain"]
        node_results = context["results"]
        
        # Find incoming connections
        incoming_connections = [
            conn for conn in chain.connections 
            if conn.target_node_id == node.id
        ]
        
        if not incoming_connections:
            # No incoming connections, use chain input
            return context["input"]
        
        # Merge data from all incoming connections
        collected_data = {}
        
        for conn in incoming_connections:
            source_result = node_results.get(conn.source_node_id, {})
            
            if conn.data_mappings:
                # Apply data mappings
                for mapping in conn.data_mappings:
                    if mapping.source_field in source_result:
                        value = source_result[mapping.source_field]
                        
                        # Apply transformation if specified
                        if mapping.transform:
                            value = self._apply_transform(value, mapping.transform)
                        
                        collected_data[mapping.target_field] = value
            else:
                # No mappings, merge all data
                if isinstance(source_result, dict):
                    collected_data.update(source_result)
        
        # Include original input data if no mappings override it
        for key, value in context["input"].items():
            if key not in collected_data:
                collected_data[key] = value
        
        return collected_data
    
    def _apply_transform(self, value: Any, transform: str) -> Any:
        """Apply simple data transformations"""
        if transform == "uppercase" and isinstance(value, str):
            return value.upper()
        elif transform == "lowercase" and isinstance(value, str):
            return value.lower()
        elif transform == "length":
            return len(value) if hasattr(value, '__len__') else 0
        elif transform == "str":
            return str(value)
        elif transform == "int":
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        elif transform == "float":
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        else:
            return value
    
    def _extract_final_output(self, node_results: Dict[str, Dict[str, Any]], 
                            chain: ChainDefinition) -> Dict[str, Any]:
        """Extract final output from chain execution"""
        
        # Find leaf nodes (nodes with no outgoing connections)
        outgoing_nodes = set()
        for conn in chain.connections:
            outgoing_nodes.add(conn.source_node_id)
        
        leaf_nodes = []
        for node in chain.nodes:
            if node.id not in outgoing_nodes:
                leaf_nodes.append(node.id)
        
        if not leaf_nodes:
            # No clear leaf nodes, return all results
            return {"all_results": node_results}
        
        if len(leaf_nodes) == 1:
            # Single leaf node, return its result
            return node_results.get(leaf_nodes[0], {})
        else:
            # Multiple leaf nodes, combine results
            final_result = {}
            for leaf_id in leaf_nodes:
                leaf_result = node_results.get(leaf_id, {})
                final_result[f"output_{leaf_id}"] = leaf_result
            return final_result 
