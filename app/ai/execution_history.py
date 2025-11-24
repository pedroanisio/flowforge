"""
Execution History Storage and Analysis

Stores and analyzes chain execution history for ML training and optimization.
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field


class ExecutionRecord(BaseModel):
    """Record of a single chain execution"""
    id: str
    chain_id: str
    timestamp: datetime
    duration_seconds: float
    success: bool
    input_size_bytes: Optional[int] = None
    node_durations: Dict[str, float] = Field(default_factory=dict)
    node_results: Dict[str, str] = Field(default_factory=dict)  # node_id -> "success" | "failed"
    plugins_used: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionHistoryManager:
    """Manages storage and retrieval of execution history"""

    def __init__(self, data_dir: str = "app/data/execution_history"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "executions.jsonl"
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Ensure history file exists"""
        if not self.history_file.exists():
            self.history_file.touch()

    def record_execution(self, record: ExecutionRecord):
        """Record a chain execution"""
        with open(self.history_file, 'a') as f:
            f.write(record.model_dump_json() + '\n')

    def get_all_executions(self, limit: Optional[int] = None) -> List[ExecutionRecord]:
        """Get all execution records"""
        records = []

        if not self.history_file.exists():
            return records

        with open(self.history_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(ExecutionRecord(**json.loads(line)))
                    except Exception:
                        continue  # Skip malformed records

        # Return most recent first
        records.reverse()

        if limit:
            return records[:limit]
        return records

    def get_executions_for_chain(self, chain_id: str, limit: Optional[int] = None) -> List[ExecutionRecord]:
        """Get execution history for a specific chain"""
        all_records = self.get_all_executions()
        chain_records = [r for r in all_records if r.chain_id == chain_id]

        if limit:
            return chain_records[:limit]
        return chain_records

    def get_executions_for_plugin(self, plugin_id: str, limit: Optional[int] = None) -> List[ExecutionRecord]:
        """Get executions that used a specific plugin"""
        all_records = self.get_all_executions()
        plugin_records = [r for r in all_records if plugin_id in r.plugins_used]

        if limit:
            return plugin_records[:limit]
        return plugin_records

    def get_successful_executions(self, limit: Optional[int] = None) -> List[ExecutionRecord]:
        """Get only successful executions"""
        all_records = self.get_all_executions()
        successful = [r for r in all_records if r.success]

        if limit:
            return successful[:limit]
        return successful

    def get_average_duration(self, chain_id: Optional[str] = None) -> float:
        """Get average execution duration"""
        if chain_id:
            records = self.get_executions_for_chain(chain_id)
        else:
            records = self.get_successful_executions()

        if not records:
            return 0.0

        total_duration = sum(r.duration_seconds for r in records)
        return total_duration / len(records)

    def get_plugin_performance(self, plugin_id: str) -> Dict[str, Any]:
        """Get performance statistics for a plugin"""
        records = self.get_executions_for_plugin(plugin_id)

        if not records:
            return {
                "plugin_id": plugin_id,
                "total_executions": 0,
                "average_duration": 0.0,
                "success_rate": 0.0
            }

        successful = [r for r in records if r.success and plugin_id in r.node_durations]
        durations = [r.node_durations[plugin_id] for r in successful if plugin_id in r.node_durations]

        return {
            "plugin_id": plugin_id,
            "total_executions": len(records),
            "successful_executions": len(successful),
            "average_duration": sum(durations) / len(durations) if durations else 0.0,
            "success_rate": len(successful) / len(records) if records else 0.0,
            "min_duration": min(durations) if durations else 0.0,
            "max_duration": max(durations) if durations else 0.0
        }

    def get_chain_patterns(self) -> Dict[str, List[str]]:
        """Identify common plugin sequences"""
        successful = self.get_successful_executions()
        patterns = {}

        for record in successful:
            # Convert plugin sequence to pattern key
            pattern_key = " -> ".join(record.plugins_used)
            if pattern_key not in patterns:
                patterns[pattern_key] = []
            patterns[pattern_key].append(record.chain_id)

        # Sort by frequency
        sorted_patterns = dict(sorted(patterns.items(), key=lambda x: len(x[1]), reverse=True))
        return sorted_patterns

    def clear_history(self):
        """Clear all execution history (use with caution!)"""
        if self.history_file.exists():
            self.history_file.unlink()
        self._ensure_file_exists()
