"""
Unit tests for Plugin Manager
"""
import pytest
from app.core.plugin_manager import PluginManager
from app.models.plugin import PluginInput


class TestPluginManager:
    """Test suite for PluginManager"""

    def test_plugin_discovery(self, plugin_manager):
        """Test that plugins are discovered correctly"""
        plugins = plugin_manager.get_all_plugins()
        assert len(plugins) > 0, "Should discover at least one plugin"
        assert len(plugins) == 10, "Should discover exactly 10 plugins"

    def test_plugin_compliance(self, plugin_manager):
        """Test that all plugins are compliant with response model rule"""
        non_compliant = plugin_manager.get_non_compliant_plugins()
        assert len(non_compliant) == 0, f"All plugins should be compliant, found non-compliant: {non_compliant}"

    def test_get_plugin_by_id(self, plugin_manager):
        """Test getting a specific plugin by ID"""
        plugin = plugin_manager.get_plugin("text_stat")
        assert plugin is not None, "text_stat plugin should exist"
        assert plugin.id == "text_stat"
        assert plugin.name == "Text Statistics"

    def test_get_nonexistent_plugin(self, plugin_manager):
        """Test getting a plugin that doesn't exist"""
        plugin = plugin_manager.get_plugin("nonexistent_plugin")
        assert plugin is None, "Should return None for nonexistent plugin"

    def test_plugin_has_manifest(self, plugin_manager):
        """Test that plugins have required manifest properties"""
        plugin = plugin_manager.get_plugin("text_stat")
        assert hasattr(plugin, 'id')
        assert hasattr(plugin, 'name')
        assert hasattr(plugin, 'description')
        assert hasattr(plugin, 'inputs')
        assert hasattr(plugin, 'outputs')

    def test_plugin_compliance_status(self, plugin_manager):
        """Test that plugins have compliance status"""
        plugin = plugin_manager.get_plugin("text_stat")
        assert hasattr(plugin, 'compliance_status')
        assert plugin.compliance_status.get('compliant') == True
        assert 'response_model' in plugin.compliance_status

    def test_execute_text_stat_plugin(self, plugin_manager, sample_text):
        """Test executing the text_stat plugin"""
        plugin_input = PluginInput(
            plugin_id="text_stat",
            data={"text": sample_text}
        )
        result = plugin_manager.execute_plugin(plugin_input)

        assert result.success == True
        assert result.error is None
        assert result.data is not None
        assert "word_count" in result.data
        assert "character_count" in result.data
        assert result.data["word_count"] > 0

    def test_execute_plugin_with_missing_input(self, plugin_manager):
        """Test executing plugin with missing required input"""
        plugin_input = PluginInput(
            plugin_id="text_stat",
            data={}  # Missing 'text' field
        )
        result = plugin_manager.execute_plugin(plugin_input)

        assert result.success == False or result.data["word_count"] == 0

    def test_execute_nonexistent_plugin(self, plugin_manager):
        """Test executing a plugin that doesn't exist"""
        plugin_input = PluginInput(
            plugin_id="nonexistent_plugin",
            data={"text": "test"}
        )
        result = plugin_manager.execute_plugin(plugin_input)

        assert result.success == False
        assert "not found" in result.error.lower()

    def test_plugin_dependency_checking(self, plugin_manager):
        """Test that plugin dependencies are checked"""
        plugin = plugin_manager.get_plugin("text_stat")
        assert hasattr(plugin, 'dependency_status')
        assert 'all_met' in plugin.dependency_status

    def test_refresh_plugins(self, plugin_manager):
        """Test refreshing the plugin list"""
        initial_count = len(plugin_manager.get_all_plugins())
        plugin_manager.refresh_plugins()
        refreshed_count = len(plugin_manager.get_all_plugins())

        assert refreshed_count == initial_count
        assert refreshed_count == 10
