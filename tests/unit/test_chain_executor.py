"""
Unit tests for Chain Executor
"""
import pytest
from app.core.chain_executor import ChainExecutor, ChainValidator
from app.models.chain import ChainDefinition, ChainNode, ChainConnection, ChainNodeType


class TestChainValidator:
    """Test suite for ChainValidator"""

    def test_validate_empty_chain(self, plugin_manager):
        """Test validating an empty chain"""
        validator = ChainValidator(plugin_manager)
        chain = ChainDefinition(
            id="test-chain",
            name="Test Chain",
            nodes=[],
            connections=[]
        )
        result = validator.validate_chain(chain)

        assert result.is_valid == False
        assert "at least one node" in " ".join(result.errors).lower()

    def test_validate_single_node_chain(self, plugin_manager):
        """Test validating a chain with a single node"""
        validator = ChainValidator(plugin_manager)
        chain = ChainDefinition(
            id="test-chain",
            name="Test Chain",
            nodes=[
                ChainNode(
                    id="node1",
                    type=ChainNodeType.PLUGIN,
                    plugin_id="text_stat",
                    config={}
                )
            ],
            connections=[]
        )
        result = validator.validate_chain(chain)

        assert result.is_valid == True
        assert len(result.errors) == 0

    def test_validate_chain_with_missing_plugin(self, plugin_manager):
        """Test validating a chain with a missing plugin"""
        validator = ChainValidator(plugin_manager)
        chain = ChainDefinition(
            id="test-chain",
            name="Test Chain",
            nodes=[
                ChainNode(
                    id="node1",
                    type=ChainNodeType.PLUGIN,
                    plugin_id="nonexistent_plugin",
                    config={}
                )
            ],
            connections=[]
        )
        result = validator.validate_chain(chain)

        assert result.is_valid == False
        assert "nonexistent_plugin" in " ".join(result.errors)
        assert len(result.missing_plugins) == 1

    def test_detect_circular_dependency(self, plugin_manager):
        """Test detecting circular dependencies in chains"""
        validator = ChainValidator(plugin_manager)
        chain = ChainDefinition(
            id="test-chain",
            name="Test Chain",
            nodes=[
                ChainNode(id="node1", type=ChainNodeType.PLUGIN, plugin_id="text_stat", config={}),
                ChainNode(id="node2", type=ChainNodeType.PLUGIN, plugin_id="text_stat", config={})
            ],
            connections=[
                ChainConnection(id="conn1", source_node_id="node1", target_node_id="node2"),
                ChainConnection(id="conn2", source_node_id="node2", target_node_id="node1")  # Creates cycle
            ]
        )
        result = validator.validate_chain(chain)

        assert result.is_valid == False
        assert result.cycle_detected == True
        assert "circular" in " ".join(result.errors).lower()


class TestChainExecutor:
    """Test suite for ChainExecutor"""

    @pytest.mark.asyncio
    async def test_execute_single_node_chain(self, plugin_manager, sample_text):
        """Test executing a chain with a single plugin node"""
        executor = ChainExecutor(plugin_manager)
        chain = ChainDefinition(
            id="test-chain",
            name="Test Chain",
            nodes=[
                ChainNode(
                    id="node1",
                    type=ChainNodeType.PLUGIN,
                    plugin_id="text_stat",
                    config={}
                )
            ],
            connections=[]
        )

        result = await executor.execute_chain(chain, {"text": sample_text})

        assert result.success == True
        assert result.error is None
        assert "word_count" in result.results

    @pytest.mark.asyncio
    async def test_execute_invalid_chain(self, plugin_manager):
        """Test executing an invalid chain"""
        executor = ChainExecutor(plugin_manager)
        chain = ChainDefinition(
            id="test-chain",
            name="Test Chain",
            nodes=[],
            connections=[]
        )

        result = await executor.execute_chain(chain, {})

        assert result.success == False
        assert result.error is not None
        assert "validation failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_build_execution_graph(self, plugin_manager):
        """Test building execution graph with topological sort"""
        executor = ChainExecutor(plugin_manager)
        chain = ChainDefinition(
            id="test-chain",
            name="Test Chain",
            nodes=[
                ChainNode(id="node1", type=ChainNodeType.PLUGIN, plugin_id="text_stat", config={}),
                ChainNode(id="node2", type=ChainNodeType.PLUGIN, plugin_id="text_stat", config={}),
                ChainNode(id="node3", type=ChainNodeType.PLUGIN, plugin_id="text_stat", config={})
            ],
            connections=[
                ChainConnection(id="conn1", source_node_id="node1", target_node_id="node2"),
                ChainConnection(id="conn2", source_node_id="node2", target_node_id="node3")
            ]
        )

        execution_graph = executor._build_execution_graph(chain)

        # Should have 3 batches (sequential execution)
        assert len(execution_graph) == 3
        assert execution_graph[0][0].id == "node1"
        assert execution_graph[1][0].id == "node2"
        assert execution_graph[2][0].id == "node3"
