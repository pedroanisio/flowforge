"""
Integration tests for API endpoints
"""
import pytest


class TestAPIEndpoints:
    """Test suite for API endpoints"""

    def test_root_endpoint(self, client):
        """Test the root endpoint returns HTML"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_get_plugins(self, client):
        """Test getting all plugins"""
        response = client.get("/api/plugins")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] == True
        assert "plugins" in data
        assert len(data["plugins"]) == 10

    def test_get_specific_plugin(self, client):
        """Test getting a specific plugin"""
        response = client.get("/api/plugin/text_stat")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] == True
        assert data["plugin"]["id"] == "text_stat"

    def test_get_nonexistent_plugin(self, client):
        """Test getting a plugin that doesn't exist"""
        response = client.get("/api/plugin/nonexistent")
        assert response.status_code == 404

    def test_plugin_compliance_endpoint(self, client):
        """Test the plugin compliance check endpoint"""
        response = client.get("/api/plugin-compliance")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] == True
        assert "summary" in data
        assert data["summary"]["total_plugins"] == 10
        assert data["summary"]["compliance_percentage"] == 100.0

    def test_auth_status_endpoint(self, client):
        """Test the auth status endpoint"""
        response = client.get("/auth/status")
        assert response.status_code == 200

        data = response.json()
        assert "auth_enabled" in data
        assert "rate_limit_enabled" in data
        assert "max_upload_size_mb" in data

    def test_execute_text_stat_plugin(self, client):
        """Test executing the text_stat plugin via API"""
        response = client.post(
            "/api/plugin/text_stat/execute",
            data={"text": "This is a test sentence."}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] == True
        assert "data" in data
        assert data["data"]["word_count"] == 5

    def test_refresh_plugins(self, client):
        """Test refreshing plugins"""
        response = client.post("/api/refresh-plugins")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] == True
        assert data["count"] == 10

    def test_chains_list_endpoint(self, client):
        """Test listing chains"""
        response = client.get("/api/chains")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] == True
        assert "chains" in data


class TestAuthenticationEndpoints:
    """Test suite for authentication endpoints"""

    def test_login_with_valid_credentials(self, client):
        """Test login with valid credentials"""
        response = client.post(
            "/token",
            data={"username": "admin", "password": "secret"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_login_with_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post(
            "/token",
            data={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    def test_get_current_user_without_auth(self, client):
        """Test getting current user when auth is disabled"""
        response = client.get("/users/me")
        # Should work when auth is disabled (returns anonymous user)
        assert response.status_code == 200
