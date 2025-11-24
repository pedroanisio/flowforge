"""
Execution Time Prediction

Predicts chain execution duration based on historical data and chain characteristics.
"""
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import timedelta

from ..models.chain import ChainDefinition
from .execution_history import ExecutionHistoryManager


class ExecutionPredictor:
    """Predicts chain execution time and identifies bottlenecks"""

    def __init__(self, history_manager: Optional[ExecutionHistoryManager] = None):
        self.history_manager = history_manager or ExecutionHistoryManager()
        self.plugin_baselines = {}
        self._build_baselines()

    def _build_baselines(self):
        """Build baseline performance metrics for each plugin"""
        executions = self.history_manager.get_successful_executions(limit=1000)

        plugin_durations = {}

        for execution in executions:
            for plugin_id, duration in execution.node_durations.items():
                if plugin_id not in plugin_durations:
                    plugin_durations[plugin_id] = []
                plugin_durations[plugin_id].append(duration)

        # Calculate baseline statistics
        for plugin_id, durations in plugin_durations.items():
            self.plugin_baselines[plugin_id] = {
                "mean": np.mean(durations),
                "std": np.std(durations),
                "min": np.min(durations),
                "max": np.max(durations),
                "p50": np.percentile(durations, 50),
                "p95": np.percentile(durations, 95),
                "sample_count": len(durations)
            }

    def predict_execution_time(
        self,
        chain: ChainDefinition,
        input_size_bytes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Predict chain execution time

        Returns:
            {
                "predicted_duration_seconds": float,
                "confidence_interval": (float, float),
                "node_predictions": {node_id: duration},
                "bottlenecks": [node_ids],
                "confidence": float
            }
        """
        # Get plugin sequence
        plugins = [node.plugin_id for node in chain.nodes if node.plugin_id]

        if not plugins:
            return {
                "predicted_duration_seconds": 0.0,
                "confidence_interval": (0.0, 0.0),
                "node_predictions": {},
                "bottlenecks": [],
                "confidence": 0.0
            }

        # Predict each node duration
        node_predictions = {}
        total_duration = 0.0
        variance_sum = 0.0

        for node in chain.nodes:
            if not node.plugin_id:
                continue

            # Get baseline for plugin
            if node.plugin_id in self.plugin_baselines:
                baseline = self.plugin_baselines[node.plugin_id]

                # Adjust prediction based on input size if available
                predicted = baseline["mean"]

                if input_size_bytes:
                    # Scale prediction based on file size
                    # Assume linear relationship (simple model)
                    size_factor = max(1.0, input_size_bytes / (1024 * 1024))  # MB
                    predicted *= min(size_factor, 10.0)  # Cap at 10x

                node_predictions[node.id] = predicted
                total_duration += predicted
                variance_sum += baseline["std"] ** 2
            else:
                # No baseline, use default estimate
                node_predictions[node.id] = 1.0
                total_duration += 1.0
                variance_sum += 0.5 ** 2

        # Calculate confidence interval
        std_dev = np.sqrt(variance_sum)
        confidence_interval = (
            max(0, total_duration - 1.96 * std_dev),
            total_duration + 1.96 * std_dev
        )

        # Identify bottlenecks (nodes taking >20% of total time)
        bottlenecks = []
        if total_duration > 0:
            for node_id, duration in node_predictions.items():
                if duration / total_duration > 0.2:
                    bottlenecks.append(node_id)

        # Calculate overall confidence based on sample counts
        sample_counts = [
            self.plugin_baselines.get(node.plugin_id, {}).get("sample_count", 0)
            for node in chain.nodes if node.plugin_id
        ]
        avg_samples = np.mean(sample_counts) if sample_counts else 0
        confidence = min(avg_samples / 10.0, 1.0)  # Max confidence at 10+ samples

        return {
            "predicted_duration_seconds": round(total_duration, 2),
            "predicted_duration_human": str(timedelta(seconds=int(total_duration))),
            "confidence_interval": (
                round(confidence_interval[0], 2),
                round(confidence_interval[1], 2)
            ),
            "node_predictions": {
                node_id: round(duration, 2)
                for node_id, duration in node_predictions.items()
            },
            "bottlenecks": bottlenecks,
            "confidence": round(confidence, 2),
            "based_on_executions": int(avg_samples)
        }

    def predict_chain_comparison(
        self,
        chain1: ChainDefinition,
        chain2: ChainDefinition
    ) -> Dict[str, Any]:
        """Compare predicted performance of two chains"""
        pred1 = self.predict_execution_time(chain1)
        pred2 = self.predict_execution_time(chain2)

        speedup = 1.0
        if pred2["predicted_duration_seconds"] > 0:
            speedup = pred1["predicted_duration_seconds"] / pred2["predicted_duration_seconds"]

        return {
            "chain1_duration": pred1["predicted_duration_seconds"],
            "chain2_duration": pred2["predicted_duration_seconds"],
            "speedup": round(speedup, 2),
            "faster_chain": "chain2" if speedup > 1.0 else "chain1",
            "time_saved_seconds": abs(pred1["predicted_duration_seconds"] - pred2["predicted_duration_seconds"]),
            "recommendation": "Use chain2" if speedup > 1.1 else "Use chain1" if speedup < 0.9 else "Similar performance"
        }

    def identify_slow_plugins(self, threshold_percentile: float = 75) -> List[Dict[str, Any]]:
        """Identify plugins that are typically slow"""
        slow_plugins = []

        for plugin_id, baseline in self.plugin_baselines.items():
            if baseline["p95"] > np.percentile(
                [b["p95"] for b in self.plugin_baselines.values()],
                threshold_percentile
            ):
                slow_plugins.append({
                    "plugin_id": plugin_id,
                    "average_duration": round(baseline["mean"], 2),
                    "p95_duration": round(baseline["p95"], 2),
                    "variability": round(baseline["std"] / baseline["mean"], 2) if baseline["mean"] > 0 else 0
                })

        slow_plugins.sort(key=lambda x: x["p95_duration"], reverse=True)
        return slow_plugins

    def suggest_performance_improvements(
        self,
        chain: ChainDefinition
    ) -> List[Dict[str, Any]]:
        """Suggest ways to improve chain performance"""
        suggestions = []

        prediction = self.predict_execution_time(chain)

        # Identify bottlenecks
        if prediction["bottlenecks"]:
            for bottleneck_node_id in prediction["bottlenecks"]:
                node = next((n for n in chain.nodes if n.id == bottleneck_node_id), None)
                if node and node.plugin_id:
                    duration = prediction["node_predictions"].get(bottleneck_node_id, 0)
                    percentage = (duration / prediction["predicted_duration_seconds"] * 100) if prediction["predicted_duration_seconds"] > 0 else 0

                    suggestions.append({
                        "type": "bottleneck",
                        "node_id": bottleneck_node_id,
                        "plugin_id": node.plugin_id,
                        "message": f"Node '{bottleneck_node_id}' using {node.plugin_id} is a bottleneck ({int(percentage)}% of total time)",
                        "recommendation": "Consider using chunked strategy or caching results",
                        "impact": "high"
                    })

        # Check for parallelization opportunities
        serial_nodes = []
        for i, node in enumerate(chain.nodes[:-1]):
            next_node = chain.nodes[i + 1]

            # Check if nodes have no dependency
            has_dependency = any(
                conn.source_node_id == node.id and conn.target_node_id == next_node.id
                for conn in chain.connections
            )

            if not has_dependency and node.plugin_id and next_node.plugin_id:
                serial_nodes.append((node, next_node))

        if serial_nodes:
            suggestions.append({
                "type": "parallelization",
                "message": f"Found {len(serial_nodes)} nodes that could run in parallel",
                "recommendation": "Restructure chain to enable parallel execution",
                "impact": "medium",
                "potential_speedup": "2x"
            })

        # Check for redundant plugins
        plugin_counts = {}
        for node in chain.nodes:
            if node.plugin_id:
                plugin_counts[node.plugin_id] = plugin_counts.get(node.plugin_id, 0) + 1

        for plugin_id, count in plugin_counts.items():
            if count > 1:
                suggestions.append({
                    "type": "redundancy",
                    "plugin_id": plugin_id,
                    "message": f"Plugin '{plugin_id}' is used {count} times",
                    "recommendation": "Consider caching results or restructuring chain",
                    "impact": "medium"
                })

        return suggestions
