"""
Unit tests for Authentication
"""
import pytest
from datetime import timedelta
from jose import jwt
from app.core.auth import (
    verify_password, get_password_hash, authenticate_user,
    create_access_token, get_user
)
from app.core.config import settings


class TestAuthentication:
    """Test suite for Authentication"""

    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed) == True
        assert verify_password("wrongpassword", hashed) == False

    def test_get_existing_user(self):
        """Test getting an existing user"""
        user = get_user("admin")

        assert user is not None
        assert user.username == "admin"
        assert user.email == "admin@example.com"

    def test_get_nonexistent_user(self):
        """Test getting a user that doesn't exist"""
        user = get_user("nonexistent_user")
        assert user is None

    def test_authenticate_valid_user(self):
        """Test authenticating with valid credentials"""
        user = authenticate_user("admin", "secret")

        assert user is not None
        assert user.username == "admin"

    def test_authenticate_invalid_password(self):
        """Test authenticating with invalid password"""
        user = authenticate_user("admin", "wrongpassword")
        assert user is None

    def test_authenticate_nonexistent_user(self):
        """Test authenticating a nonexistent user"""
        user = authenticate_user("nonexistent", "password")
        assert user is None

    def test_create_access_token(self):
        """Test creating a JWT access token"""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)

        # Decode and verify
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "testuser"
        assert "exp" in payload

    def test_create_access_token_with_expiry(self):
        """Test creating a token with custom expiry"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta)

        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "testuser"
