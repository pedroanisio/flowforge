"""
Unit tests for ChainManager AI history recording.
"""
import pytest

from app.core.chain_manager import ChainManager
from app.models.chain import ChainDefinition, ChainNode, ChainNodeType


class TestChainManagerHistory:
    """Test suite for execution telemetry persistence into AI history."""

    @pytest.mark.asyncio
    async def test_records_node_telemetry_for_ai(self, plugin_manager, sample_text, tmp_path):
        """Node telemetry should be persisted as node durations and plugin mapping."""
        manager = ChainManager(plugin_manager, base_dir=str(tmp_path))
        chain = ChainDefinition(
            id="chain-test",
            name="Telemetry Chain",
            description="",
            nodes=[
                ChainNode(
                    id="node1",
                    type=ChainNodeType.PLUGIN,
                    plugin_id="text_stat",
                    position={"x": 0, "y": 0},
                    config={}
                )
            ],
            connections=[]
        )

        result = await manager.execute_chain_definition(chain, {"text": sample_text})
        assert result.success == True

        records = manager.history_manager.get_all_executions(limit=1)
        assert len(records) == 1

        record = records[0]
        assert record.node_plugins["node1"] == "text_stat"
        assert record.node_results["node1"] == "success"
        assert record.node_durations["node1"] >= 0.0
