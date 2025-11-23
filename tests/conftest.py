"""
Pytest configuration and fixtures
"""
import pytest
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.plugin_manager import PluginManager
from app.core.chain_manager import ChainManager


@pytest.fixture
def client():
    """FastAPI test client"""
    # Disable auth for tests
    settings.enable_auth = False
    settings.rate_limit_enabled = False
    return TestClient(app)


@pytest.fixture
def plugin_manager():
    """Plugin manager instance"""
    return PluginManager()


@pytest.fixture
def chain_manager(plugin_manager):
    """Chain manager instance"""
    return ChainManager(plugin_manager)


@pytest.fixture
def sample_text():
    """Sample text for testing"""
    return "This is a test sentence. It has multiple sentences! And some punctuation?"


@pytest.fixture
def sample_plugin_data():
    """Sample plugin execution data"""
    return {
        "text": "Hello world! This is a test.",
    }
