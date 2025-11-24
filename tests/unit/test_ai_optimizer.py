"""
Unit tests for AI Optimizer
"""
import pytest
from datetime import datetime
from app.ai.chain_optimizer import ChainOptimizer
from app.ai.execution_history import ExecutionHistoryManager, ExecutionRecord
from app.models.chain import ChainDefinition, ChainNode, ChainConnection, ChainNodeType


class TestChainOptimizer:
    """Test suite for ChainOptimizer"""

    def test_optimizer_initialization(self):
        """Test optimizer can be initialized"""
        optimizer = ChainOptimizer()
        assert optimizer is not None
        assert optimizer.history_manager is not None
        assert optimizer.plugin_recommender is not None
        assert optimizer.execution_predictor is not None

    def test_suggest_starter_plugins(self):
        """Test suggesting starter plugins"""
        optimizer = ChainOptimizer()

        # Initially should work even with no history
        suggestions = optimizer.suggest_starter_plugins(top_k=5)
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5

    def test_predict_execution_empty_chain(self):
        """Test prediction on empty chain"""
        optimizer = ChainOptimizer()
        chain = ChainDefinition(
            id="test-chain",
            name="Empty Chain",
            nodes=[],
            connections=[]
        )

        prediction = optimizer.predict_execution(chain)

        assert prediction["predicted_duration_seconds"] == 0.0
        assert prediction["confidence"] == 0.0

    def test_predict_execution_with_nodes(self):
        """Test prediction with actual nodes"""
        optimizer = ChainOptimizer()
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

        prediction = optimizer.predict_execution(chain)

        assert isinstance(prediction["predicted_duration_seconds"], float)
        assert "confidence" in prediction
        assert "node_predictions" in prediction

    def test_optimize_chain(self):
        """Test chain optimization"""
        optimizer = ChainOptimizer()
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

        result = optimizer.optimize_chain(chain, [])

        assert "original_prediction" in result
        assert "optimized_chain" in result
        assert "optimized_prediction" in result
        assert "improvements" in result
        assert "expected_speedup" in result

    def test_suggest_next_plugins_empty_chain(self):
        """Test plugin suggestions for empty chain"""
        optimizer = ChainOptimizer()
        chain = ChainDefinition(
            id="test-chain",
            name="Empty Chain",
            nodes=[],
            connections=[]
        )

        suggestions = optimizer.suggest_next_plugins(chain, [], top_k=3)

        assert isinstance(suggestions, list)
        assert len(suggestions) <= 3

    def test_recommend_strategy(self):
        """Test strategy recommendation"""
        optimizer = ChainOptimizer()

        # Test with small file
        recommendation = optimizer.recommend_strategy(
            plugin_id="pandoc_converter",
            input_size_bytes=1024 * 1024  # 1MB
        )

        assert "recommended_strategy" in recommendation
        assert "confidence" in recommendation
        assert "reason" in recommendation

    def test_get_system_insights_no_history(self):
        """Test system insights with no execution history"""
        optimizer = ChainOptimizer()
        insights = optimizer.get_system_insights()

        assert "total_executions" in insights
        assert insights["total_executions"] == 0

    def test_find_similar_chains_empty_list(self):
        """Test finding similar chains with empty list"""
        optimizer = ChainOptimizer()
        chain = ChainDefinition(
            id="test-chain",
            name="Test Chain",
            nodes=[],
            connections=[]
        )

        similar = optimizer.find_similar_chains(chain, [], top_k=5)

        assert isinstance(similar, list)
        assert len(similar) == 0


class TestExecutionHistory:
    """Test suite for ExecutionHistoryManager"""

    def test_history_manager_initialization(self, tmp_path):
        """Test history manager can be initialized"""
        manager = ExecutionHistoryManager(data_dir=str(tmp_path))
        assert manager is not None
        assert manager.history_file.exists()

    def test_record_and_retrieve_execution(self, tmp_path):
        """Test recording and retrieving execution"""
        manager = ExecutionHistoryManager(data_dir=str(tmp_path))

        record = ExecutionRecord(
            id="test-exec-1",
            chain_id="test-chain",
            timestamp=datetime.now(),
            duration_seconds=1.5,
            success=True,
            plugins_used=["text_stat"],
            node_durations={"node1": 1.5},
            node_results={"node1": "success"}
        )

        manager.record_execution(record)

        # Retrieve all executions
        executions = manager.get_all_executions()
        assert len(executions) == 1
        assert executions[0].id == "test-exec-1"

    def test_get_executions_for_chain(self, tmp_path):
        """Test filtering executions by chain"""
        manager = ExecutionHistoryManager(data_dir=str(tmp_path))

        # Record for chain A
        record1 = ExecutionRecord(
            id="exec-1",
            chain_id="chain-a",
            timestamp=datetime.now(),
            duration_seconds=1.0,
            success=True,
            plugins_used=["text_stat"]
        )

        # Record for chain B
        record2 = ExecutionRecord(
            id="exec-2",
            chain_id="chain-b",
            timestamp=datetime.now(),
            duration_seconds=2.0,
            success=True,
            plugins_used=["pandoc_converter"]
        )

        manager.record_execution(record1)
        manager.record_execution(record2)

        # Get executions for chain A
        chain_a_execs = manager.get_executions_for_chain("chain-a")
        assert len(chain_a_execs) == 1
        assert chain_a_execs[0].chain_id == "chain-a"

    def test_get_plugin_performance(self, tmp_path):
        """Test getting plugin performance stats"""
        manager = ExecutionHistoryManager(data_dir=str(tmp_path))

        # Record execution with plugin
        record = ExecutionRecord(
            id="exec-1",
            chain_id="test-chain",
            timestamp=datetime.now(),
            duration_seconds=2.5,
            success=True,
            plugins_used=["text_stat"],
            node_durations={"node1": 2.5}
        )

        manager.record_execution(record)

        # Get performance
        perf = manager.get_plugin_performance("text_stat")

        assert perf["total_executions"] == 1
        assert perf["success_rate"] == 1.0

    def test_get_average_duration(self, tmp_path):
        """Test calculating average duration"""
        manager = ExecutionHistoryManager(data_dir=str(tmp_path))

        # Record multiple executions
        for i in range(3):
            record = ExecutionRecord(
                id=f"exec-{i}",
                chain_id="test-chain",
                timestamp=datetime.now(),
                duration_seconds=float(i + 1),
                success=True,
                plugins_used=["text_stat"]
            )
            manager.record_execution(record)

        avg = manager.get_average_duration()
        assert avg == 2.0  # (1 + 2 + 3) / 3
