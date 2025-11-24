"""
AI-Powered Optimization & Auto-Tuning Module

This module provides intelligent features for the plugin system:
- Chain optimization and recommendations
- Execution time prediction
- Strategy recommendation
- Pattern learning from historical data
"""

from .chain_optimizer import ChainOptimizer
from .plugin_recommender import PluginRecommender
from .execution_predictor import ExecutionPredictor
from .strategy_recommender import StrategyRecommender
from .embeddings import ChainEmbeddings

__all__ = [
    'ChainOptimizer',
    'PluginRecommender',
    'ExecutionPredictor',
    'StrategyRecommender',
    'ChainEmbeddings'
]
