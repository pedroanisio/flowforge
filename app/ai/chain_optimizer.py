"""
Chain Optimizer - Main AI Engine

Combines all AI features to provide intelligent chain optimization and recommendations.
"""
from typing import List, Dict, Any, Optional
import copy

from ..models.chain import ChainDefinition, ChainNode, ChainConnection
from .execution_history import ExecutionHistoryManager
from .plugin_recommender import PluginRecommender
from .execution_predictor import ExecutionPredictor
from .strategy_recommender import StrategyRecommender
from .embeddings import ChainEmbeddings


class ChainOptimizer:
    """
    Main AI-powered chain optimization engine

    Provides:
    - Chain optimization for performance
    - Plugin recommendations
    - Execution time prediction
    - Strategy recommendations
    - Pattern learning
    """

    def __init__(self):
        self.history_manager = ExecutionHistoryManager()
        self.plugin_recommender = PluginRecommender(self.history_manager)
        self.execution_predictor = ExecutionPredictor(self.history_manager)
        self.strategy_recommender = StrategyRecommender(self.history_manager)
        self.embeddings = ChainEmbeddings()

    def optimize_chain(
        self,
        chain: ChainDefinition,
        all_chains: Optional[List[ChainDefinition]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive chain optimization

        Returns:
            {
                "original_prediction": {...},
                "optimized_chain": ChainDefinition,
                "optimized_prediction": {...},
                "improvements": [...],
                "expected_speedup": float
            }
        """
        all_chains = all_chains or []

        # Get original prediction
        original_prediction = self.execution_predictor.predict_execution_time(chain)

        # Create optimized chain
        optimized_chain = copy.deepcopy(chain)
        improvements = []

        # Optimization 1: Remove redundant nodes
        redundant_removed = self._remove_redundant_nodes(optimized_chain)
        if redundant_removed:
            improvements.append({
                "type": "redundancy_removal",
                "description": f"Removed {redundant_removed} redundant nodes",
                "impact": "medium"
            })

        # Optimization 2: Reorder for better parallelization
        reordering_improvement = self._optimize_execution_order(optimized_chain)
        if reordering_improvement:
            improvements.append(reordering_improvement)

        # Optimization 3: Get performance suggestions
        perf_suggestions = self.execution_predictor.suggest_performance_improvements(optimized_chain)
        for suggestion in perf_suggestions:
            if suggestion["impact"] == "high":
                improvements.append({
                    "type": "performance",
                    "description": suggestion["message"],
                    "recommendation": suggestion["recommendation"],
                    "impact": suggestion["impact"]
                })

        # Get optimized prediction
        optimized_prediction = self.execution_predictor.predict_execution_time(optimized_chain)

        # Calculate speedup
        original_time = original_prediction["predicted_duration_seconds"]
        optimized_time = optimized_prediction["predicted_duration_seconds"]
        speedup = original_time / optimized_time if optimized_time > 0 else 1.0

        return {
            "original_prediction": original_prediction,
            "optimized_chain": optimized_chain,
            "optimized_prediction": optimized_prediction,
            "improvements": improvements,
            "expected_speedup": round(speedup, 2),
            "time_saved_seconds": round(original_time - optimized_time, 2),
            "confidence": optimized_prediction["confidence"]
        }

    def _remove_redundant_nodes(self, chain: ChainDefinition) -> int:
        """Remove redundant nodes from chain"""
        # Find nodes with same plugin_id that have no intermediate processing
        removed = 0

        plugin_nodes = {}
        for node in chain.nodes:
            if node.plugin_id:
                if node.plugin_id not in plugin_nodes:
                    plugin_nodes[node.plugin_id] = []
                plugin_nodes[node.plugin_id].append(node)

        # Remove duplicates (simple heuristic - could be more sophisticated)
        for plugin_id, nodes in plugin_nodes.items():
            if len(nodes) > 1:
                # Keep only first occurrence (simple strategy)
                nodes_to_remove = nodes[1:]
                for node in nodes_to_remove:
                    chain.nodes.remove(node)
                    removed += 1

                    # Update connections
                    chain.connections = [
                        conn for conn in chain.connections
                        if conn.source_node_id != node.id and conn.target_node_id != node.id
                    ]

        return removed

    def _optimize_execution_order(self, chain: ChainDefinition) -> Optional[Dict[str, Any]]:
        """Optimize node execution order for parallelization"""
        # Check if reordering would help
        # For now, this is a placeholder - real implementation would use
        # critical path analysis

        if len(chain.nodes) < 3:
            return None

        # Simple check: if nodes are in serial but could be parallel
        serial_nodes = 0
        for i in range(len(chain.nodes) - 1):
            current = chain.nodes[i]
            next_node = chain.nodes[i + 1]

            # Check if there's a direct dependency
            has_dep = any(
                conn.source_node_id == current.id and conn.target_node_id == next_node.id
                for conn in chain.connections
            )

            if not has_dep:
                serial_nodes += 1

        if serial_nodes > 0:
            return {
                "type": "parallelization",
                "description": f"Identified {serial_nodes} nodes that could run in parallel",
                "recommendation": "Nodes rearranged to enable parallel execution",
                "impact": "high",
                "potential_speedup": f"{serial_nodes}x"
            }

        return None

    def suggest_next_plugins(
        self,
        current_chain: ChainDefinition,
        all_chains: List[ChainDefinition],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Suggest next plugins to add to chain

        Returns list of suggestions with confidence scores
        """
        suggestions = self.plugin_recommender.suggest_next_plugin(
            current_chain, all_chains, top_k
        )

        # Format for API response
        formatted = []
        for plugin_id, confidence, reason in suggestions:
            formatted.append({
                "plugin_id": plugin_id,
                "confidence": round(confidence, 2),
                "reason": reason,
                "confidence_label": self._confidence_label(confidence)
            })

        return formatted

    def suggest_starter_plugins(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """Suggest plugins to start a new chain"""
        suggestions = self.plugin_recommender.suggest_starter_plugins(top_k)

        formatted = []
        for plugin_id, confidence, reason in suggestions:
            formatted.append({
                "plugin_id": plugin_id,
                "confidence": round(confidence, 2),
                "reason": reason,
                "confidence_label": self._confidence_label(confidence)
            })

        return formatted

    def predict_execution(
        self,
        chain: ChainDefinition,
        input_size_bytes: Optional[int] = None
    ) -> Dict[str, Any]:
        """Predict chain execution time and identify bottlenecks"""
        return self.execution_predictor.predict_execution_time(chain, input_size_bytes)

    def recommend_strategy(
        self,
        plugin_id: str,
        input_size_bytes: Optional[int] = None,
        input_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Recommend processing strategy for a plugin"""
        return self.strategy_recommender.recommend_strategy(
            plugin_id, input_size_bytes, input_type
        )

    def analyze_chain_patterns(self) -> Dict[str, Any]:
        """Analyze common patterns in successful chains"""
        patterns = self.history_manager.get_chain_patterns()

        # Get top 10 patterns
        top_patterns = list(patterns.items())[:10]

        formatted_patterns = []
        for pattern, chain_ids in top_patterns:
            formatted_patterns.append({
                "pattern": pattern,
                "frequency": len(chain_ids),
                "example_chains": chain_ids[:3]
            })

        return {
            "total_patterns": len(patterns),
            "top_patterns": formatted_patterns,
            "most_common": formatted_patterns[0] if formatted_patterns else None
        }

    def get_plugin_insights(self, plugin_id: str) -> Dict[str, Any]:
        """Get AI insights about a specific plugin"""
        # Get performance stats
        performance = self.history_manager.get_plugin_performance(plugin_id)

        # Get strategy analysis
        strategy_analysis = self.strategy_recommender.analyze_strategy_performance(plugin_id)

        # Get compatibility info
        compatible = self.plugin_recommender.suggest_compatible_plugins(
            plugin_id, [], top_k=5
        )

        formatted_compatible = []
        for other_plugin, confidence, reason in compatible:
            formatted_compatible.append({
                "plugin_id": other_plugin,
                "compatibility_score": round(confidence, 2),
                "reason": reason
            })

        return {
            "plugin_id": plugin_id,
            "performance": performance,
            "strategy_analysis": strategy_analysis,
            "compatible_plugins": formatted_compatible,
            "usage_rank": self._get_plugin_usage_rank(plugin_id)
        }

    def find_similar_chains(
        self,
        chain: ChainDefinition,
        all_chains: List[ChainDefinition],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Find chains similar to the given chain"""
        similar = self.embeddings.find_similar_chains(chain, all_chains, top_k)

        formatted = []
        for similar_chain, similarity in similar:
            # Get prediction for similar chain
            prediction = self.execution_predictor.predict_execution_time(similar_chain)

            formatted.append({
                "chain_id": similar_chain.id,
                "chain_name": similar_chain.name,
                "similarity_score": round(similarity, 2),
                "predicted_duration": prediction["predicted_duration_seconds"],
                "num_nodes": len(similar_chain.nodes),
                "tags": similar_chain.tags or []
            })

        return formatted

    def _confidence_label(self, confidence: float) -> str:
        """Convert confidence score to label"""
        if confidence >= 0.8:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        else:
            return "low"

    def _get_plugin_usage_rank(self, plugin_id: str) -> int:
        """Get usage rank of plugin (1 = most used)"""
        executions = self.history_manager.get_successful_executions(limit=1000)

        plugin_counts = {}
        for execution in executions:
            for pid in execution.plugins_used:
                plugin_counts[pid] = plugin_counts.get(pid, 0) + 1

        # Sort by count
        sorted_plugins = sorted(plugin_counts.items(), key=lambda x: x[1], reverse=True)

        for rank, (pid, count) in enumerate(sorted_plugins, 1):
            if pid == plugin_id:
                return rank

        return -1  # Not found

    def get_system_insights(self) -> Dict[str, Any]:
        """Get overall system insights"""
        executions = self.history_manager.get_successful_executions(limit=1000)

        if not executions:
            return {
                "total_executions": 0,
                "message": "No execution history available yet"
            }

        # Calculate statistics
        total_duration = sum(e.duration_seconds for e in executions)
        avg_duration = total_duration / len(executions)

        plugin_usage = {}
        for execution in executions:
            for plugin_id in execution.plugins_used:
                plugin_usage[plugin_id] = plugin_usage.get(plugin_id, 0) + 1

        most_used = sorted(plugin_usage.items(), key=lambda x: x[1], reverse=True)[:5]

        slow_plugins = self.execution_predictor.identify_slow_plugins()

        return {
            "total_executions": len(executions),
            "total_processing_time_hours": round(total_duration / 3600, 2),
            "average_execution_time_seconds": round(avg_duration, 2),
            "most_used_plugins": [{"plugin_id": pid, "usage_count": count} for pid, count in most_used],
            "slow_plugins": slow_plugins[:3],
            "patterns_identified": len(self.history_manager.get_chain_patterns())
        }
