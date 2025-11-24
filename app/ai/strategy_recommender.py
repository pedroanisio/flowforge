"""
Strategy Recommendation System

Recommends optimal processing strategies based on input characteristics and historical performance.
"""
from typing import Dict, Any, Optional, List
from enum import Enum

from .execution_history import ExecutionHistoryManager


class ProcessingStrategy(str, Enum):
    """Available processing strategies"""
    SINGLE_FILE = "single_file"
    CHUNKED = "chunked"
    STREAMING = "streaming"
    TEXT_EXTRACTION = "text_extraction"
    MEMORY_MAPPED = "memory_mapped"


class StrategyRecommender:
    """Recommends processing strategies for plugins"""

    def __init__(self, history_manager: Optional[ExecutionHistoryManager] = None):
        self.history_manager = history_manager or ExecutionHistoryManager()

        # Define strategy rules (simple rule-based system)
        # In production, this would use ML models trained on historical data
        self.strategy_rules = {
            "pandoc_converter": {
                "rules": [
                    {"max_size_mb": 5, "strategy": ProcessingStrategy.SINGLE_FILE},
                    {"max_size_mb": 50, "strategy": ProcessingStrategy.CHUNKED},
                    {"max_size_mb": float('inf'), "strategy": ProcessingStrategy.TEXT_EXTRACTION}
                ]
            },
            "pdf2html": {
                "rules": [
                    {"max_size_mb": 10, "strategy": ProcessingStrategy.SINGLE_FILE},
                    {"max_size_mb": float('inf'), "strategy": ProcessingStrategy.CHUNKED}
                ]
            }
        }

    def recommend_strategy(
        self,
        plugin_id: str,
        input_size_bytes: Optional[int] = None,
        input_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend processing strategy for a plugin

        Returns:
            {
                "recommended_strategy": str,
                "confidence": float,
                "reason": str,
                "alternatives": [{"strategy": str, "reason": str}]
            }
        """
        # Convert bytes to MB
        input_size_mb = (input_size_bytes / (1024 * 1024)) if input_size_bytes else 0

        # Check if we have rules for this plugin
        if plugin_id in self.strategy_rules:
            rules = self.strategy_rules[plugin_id]["rules"]

            for rule in rules:
                if input_size_mb <= rule["max_size_mb"]:
                    recommended = rule["strategy"]
                    break
            else:
                recommended = rules[-1]["strategy"]

            # Generate reason
            if recommended == ProcessingStrategy.SINGLE_FILE:
                reason = "File size is small enough for direct processing"
                confidence = 0.9
            elif recommended == ProcessingStrategy.CHUNKED:
                reason = "File size requires chunked processing for memory efficiency"
                confidence = 0.85
            elif recommended == ProcessingStrategy.TEXT_EXTRACTION:
                reason = "Large file size - text extraction recommended for best performance"
                confidence = 0.8
            else:
                reason = "Default strategy"
                confidence = 0.5

            # Generate alternatives
            alternatives = []
            for rule in rules:
                if rule["strategy"] != recommended:
                    alt_reason = self._get_strategy_description(rule["strategy"])
                    alternatives.append({
                        "strategy": rule["strategy"],
                        "reason": alt_reason
                    })

            return {
                "recommended_strategy": recommended,
                "confidence": confidence,
                "reason": reason,
                "alternatives": alternatives[:2]  # Top 2 alternatives
            }

        # No specific rules, use heuristics
        if input_size_mb == 0:
            return {
                "recommended_strategy": ProcessingStrategy.SINGLE_FILE,
                "confidence": 0.6,
                "reason": "Unknown file size, defaulting to standard processing",
                "alternatives": []
            }

        if input_size_mb < 10:
            recommended = ProcessingStrategy.SINGLE_FILE
            reason = "Small file size suitable for direct processing"
            confidence = 0.7
        elif input_size_mb < 100:
            recommended = ProcessingStrategy.CHUNKED
            reason = "Medium file size benefits from chunked processing"
            confidence = 0.7
        else:
            recommended = ProcessingStrategy.STREAMING
            reason = "Large file size requires streaming for memory efficiency"
            confidence = 0.7

        return {
            "recommended_strategy": recommended,
            "confidence": confidence,
            "reason": reason,
            "alternatives": [
                {
                    "strategy": ProcessingStrategy.CHUNKED,
                    "reason": "Balance between memory and performance"
                }
            ]
        }

    def _get_strategy_description(self, strategy: ProcessingStrategy) -> str:
        """Get human-readable description of strategy"""
        descriptions = {
            ProcessingStrategy.SINGLE_FILE: "Process entire file at once (fastest, high memory)",
            ProcessingStrategy.CHUNKED: "Process in chunks (balanced memory and speed)",
            ProcessingStrategy.STREAMING: "Stream processing (lowest memory, slower)",
            ProcessingStrategy.TEXT_EXTRACTION: "Extract text only (fast, reduced features)",
            ProcessingStrategy.MEMORY_MAPPED: "Memory-mapped processing (efficient for large files)"
        }
        return descriptions.get(strategy, "Unknown strategy")

    def analyze_strategy_performance(
        self,
        plugin_id: str
    ) -> Dict[str, Any]:
        """Analyze historical performance of different strategies"""
        executions = self.history_manager.get_executions_for_plugin(plugin_id, limit=1000)

        strategy_stats = {}

        for execution in executions:
            # Extract strategy from metadata (if available)
            strategy = execution.metadata.get("strategy", "unknown")

            if strategy not in strategy_stats:
                strategy_stats[strategy] = {
                    "count": 0,
                    "successful": 0,
                    "total_duration": 0.0,
                    "durations": []
                }

            stats = strategy_stats[strategy]
            stats["count"] += 1

            if execution.success:
                stats["successful"] += 1
                if plugin_id in execution.node_durations:
                    duration = execution.node_durations[plugin_id]
                    stats["total_duration"] += duration
                    stats["durations"].append(duration)

        # Calculate statistics
        results = {}
        for strategy, stats in strategy_stats.items():
            if stats["count"] > 0:
                results[strategy] = {
                    "executions": stats["count"],
                    "success_rate": stats["successful"] / stats["count"],
                    "average_duration": stats["total_duration"] / stats["successful"] if stats["successful"] > 0 else 0,
                    "min_duration": min(stats["durations"]) if stats["durations"] else 0,
                    "max_duration": max(stats["durations"]) if stats["durations"] else 0
                }

        return {
            "plugin_id": plugin_id,
            "strategies_analyzed": len(results),
            "strategy_performance": results,
            "recommendation": max(
                results.items(),
                key=lambda x: x[1]["success_rate"],
                default=(None, None)
            )[0] if results else None
        }

    def get_memory_estimate(
        self,
        plugin_id: str,
        strategy: ProcessingStrategy,
        input_size_bytes: Optional[int] = None
    ) -> Dict[str, Any]:
        """Estimate memory requirements for a strategy"""
        input_size_mb = (input_size_bytes / (1024 * 1024)) if input_size_bytes else 10

        # Simple heuristic-based estimates
        if strategy == ProcessingStrategy.SINGLE_FILE:
            estimated_memory_mb = input_size_mb * 3  # 3x input size
            peak_memory_mb = input_size_mb * 4
        elif strategy == ProcessingStrategy.CHUNKED:
            estimated_memory_mb = min(input_size_mb * 0.5, 100)  # Cap at 100MB
            peak_memory_mb = min(input_size_mb * 0.8, 200)
        elif strategy == ProcessingStrategy.STREAMING:
            estimated_memory_mb = 50  # Constant low memory
            peak_memory_mb = 80
        elif strategy == ProcessingStrategy.TEXT_EXTRACTION:
            estimated_memory_mb = input_size_mb * 0.3
            peak_memory_mb = input_size_mb * 0.5
        else:
            estimated_memory_mb = input_size_mb * 2
            peak_memory_mb = input_size_mb * 3

        return {
            "plugin_id": plugin_id,
            "strategy": strategy,
            "input_size_mb": round(input_size_mb, 2),
            "estimated_memory_mb": round(estimated_memory_mb, 2),
            "peak_memory_mb": round(peak_memory_mb, 2),
            "recommendation": "safe" if peak_memory_mb < 500 else "caution" if peak_memory_mb < 1000 else "risky"
        }
