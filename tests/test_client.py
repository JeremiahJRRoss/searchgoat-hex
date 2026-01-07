"""Tests for searchgoat_hex.client module."""

import json
import pytest
import responses
from responses import matchers

from searchgoat_hex import CriblSearchHex
from searchgoat_hex.config import CriblConfig, load_config
from searchgoat_hex.exceptions import (
    AuthenticationError,
    QueryError,
    TimeoutError,
    ConfigurationError,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_config():
    """Return test configuration."""
    return CriblConfig(
        client_id="test-client-id",
        client_secret="test-client-secret",
        org_id="test-org",
        workspace="test-workspace",
    )


@pytest.fixture
def base_url():
    """Base URL for mocked API."""
    return "https://test-workspace-test-org.cribl.cloud/api/v1/m/default_search"


@pytest.fixture
def mock_auth():
    """Set up mock OAuth2 authentication."""
    responses.add(
        responses.POST,
        "https://login.cribl.cloud/oauth/token",
        json={
            "access_token": "mock-token-12345",
            "expires_in": 86400,
            "token_type": "Bearer",
        },
        status=200,
    )


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfiguration:
    """Tests for configuration loading."""
    
    def test_load_config_from_explicit_values(self):
        """Config loads from explicit parameters."""
        config = load_config(
            client_id="my-id",
            client_secret="my-secret",
            org_id="my-org",
            workspace="my-ws",
        )
        
        assert config.client_id == "my-id"
        assert config.client_secret == "my-secret"
        assert config.org_id == "my-org"
        assert config.workspace == "my-ws"
    
    def test_load_config_from_env(self, monkeypatch):
        """Config loads from environment variables."""
        monkeypatch.setenv("CRIBL_CLIENT_ID", "env-id")
        monkeypatch.setenv("CRIBL_CLIENT_SECRET", "env-secret")
        monkeypatch.setenv("CRIBL_ORG_ID", "env-org")
        monkeypatch.setenv("CRIBL_WORKSPACE", "env-ws")
        
        config = load_config()
        
        assert config.client_id == "env-id"
        assert config.org_id == "env-org"
    
    def test_load_config_explicit_overrides_env(self, monkeypatch):
        """Explicit parameters override environment variables."""
        monkeypatch.setenv("CRIBL_CLIENT_ID", "env-id")
        monkeypatch.setenv("CRIBL_CLIENT_SECRET", "env-secret")
        monkeypatch.setenv("CRIBL_ORG_ID", "env-org")
        monkeypatch.setenv("CRIBL_WORKSPACE", "env-ws")
        
        config = load_config(client_id="explicit-id")
        
        assert config.client_id == "explicit-id"
        assert config.org_id == "env-org"  # Still from env
    
    def test_load_config_missing_raises_error(self, monkeypatch):
        """Missing credentials raise ConfigurationError."""
        monkeypatch.delenv("CRIBL_CLIENT_ID", raising=False)
        monkeypatch.delenv("CRIBL_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("CRIBL_ORG_ID", raising=False)
        monkeypatch.delenv("CRIBL_WORKSPACE", raising=False)
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config()
        
        assert "Missing required credentials" in str(exc_info.value)
    
    def test_api_base_url_construction(self, mock_config):
        """api_base_url is correctly constructed."""
        expected = "https://test-workspace-test-org.cribl.cloud/api/v1/m/default_search"
        assert mock_config.api_base_url == expected


# =============================================================================
# Client Initialization Tests
# =============================================================================

class TestClientInit:
    """Tests for CriblSearchHex initialization."""
    
    def test_init_with_explicit_credentials(self):
        """Client initializes with explicit credentials."""
        client = CriblSearchHex(
            client_id="my-id",
            client_secret="my-secret",
            org_id="my-org",
            workspace="my-ws",
        )
        
        assert client.org_id == "my-org"
        assert client.workspace == "my-ws"
    
    def test_init_from_env(self, monkeypatch):
        """Client initializes from environment variables."""
        monkeypatch.setenv("CRIBL_CLIENT_ID", "env-id")
        monkeypatch.setenv("CRIBL_CLIENT_SECRET", "env-secret")
        monkeypatch.setenv("CRIBL_ORG_ID", "env-org")
        monkeypatch.setenv("CRIBL_WORKSPACE", "env-ws")
        
        client = CriblSearchHex()
        
        assert client.org_id == "env-org"
        assert client.workspace == "env-ws"


# =============================================================================
# Authentication Tests
# =============================================================================

class TestAuthentication:
    """Tests for OAuth2 authentication."""
    
    @responses.activate
    def test_authentication_success(self):
        """Successful authentication returns token."""
        responses.add(
            responses.POST,
            "https://login.cribl.cloud/oauth/token",
            json={"access_token": "test-token", "expires_in": 86400},
            status=200,
        )
        
        client = CriblSearchHex(
            client_id="id",
            client_secret="secret",
            org_id="org",
            workspace="ws",
        )
        
        token = client._get_auth_token()
        assert token == "test-token"
    
    @responses.activate
    def test_authentication_failure_401(self):
        """401 response raises AuthenticationError."""
        responses.add(
            responses.POST,
            "https://login.cribl.cloud/oauth/token",
            json={"error": "invalid_client"},
            status=401,
        )
        
        client = CriblSearchHex(
            client_id="bad-id",
            client_secret="bad-secret",
            org_id="org",
            workspace="ws",
        )
        
        with pytest.raises(AuthenticationError):
            client._get_auth_token()
    
    @responses.activate
    def test_token_caching(self):
        """Token is cached and reused."""
        responses.add(
            responses.POST,
            "https://login.cribl.cloud/oauth/token",
            json={"access_token": "cached-token", "expires_in": 86400},
            status=200,
        )
        
        client = CriblSearchHex(
            client_id="id",
            client_secret="secret",
            org_id="org",
            workspace="ws",
        )
        
        token1 = client._get_auth_token()
        token2 = client._get_auth_token()
        
        assert token1 == token2
        assert len(responses.calls) == 1  # Only one auth call


# =============================================================================
# Test Connection Tests
# =============================================================================

class TestTestConnection:
    """Tests for test_connection method."""
    
    @responses.activate
    def test_connection_success(self):
        """test_connection returns True on success."""
        responses.add(
            responses.POST,
            "https://login.cribl.cloud/oauth/token",
            json={"access_token": "token", "expires_in": 86400},
            status=200,
        )
        
        client = CriblSearchHex(
            client_id="id",
            client_secret="secret",
            org_id="org",
            workspace="ws",
        )
        
        assert client.test_connection() is True
    
    @responses.activate
    def test_connection_failure(self):
        """test_connection raises AuthenticationError on failure."""
        responses.add(
            responses.POST,
            "https://login.cribl.cloud/oauth/token",
            json={"error": "invalid_client"},
            status=401,
        )
        
        client = CriblSearchHex(
            client_id="bad-id",
            client_secret="bad-secret",
            org_id="org",
            workspace="ws",
        )
        
        with pytest.raises(AuthenticationError):
            client.test_connection()


# =============================================================================
# List Datasets Tests
# =============================================================================

class TestListDatasets:
    """Tests for list_datasets method."""
    
    @responses.activate
    def test_list_datasets_success(self, base_url, mock_auth):
        """list_datasets returns list of dataset names."""
        responses.add(
            responses.GET,
            f"{base_url}/datasets",
            json={
                "items": [
                    {"id": "cribl_logs"},
                    {"id": "firewall"},
                    {"id": "main"},
                ]
            },
            status=200,
        )
        
        client = CriblSearchHex(
            client_id="id",
            client_secret="secret",
            org_id="test-org",
            workspace="test-workspace",
        )
        
        datasets = client.list_datasets()
        
        assert datasets == ["cribl_logs", "firewall", "main"]
    
    @responses.activate
    def test_list_datasets_empty(self, base_url, mock_auth):
        """list_datasets returns empty list when no datasets."""
        responses.add(
            responses.GET,
            f"{base_url}/datasets",
            json={"items": []},
            status=200,
        )
        
        client = CriblSearchHex(
            client_id="id",
            client_secret="secret",
            org_id="test-org",
            workspace="test-workspace",
        )
        
        datasets = client.list_datasets()
        
        assert datasets == []


# =============================================================================
# Query Tests
# =============================================================================

class TestQuery:
    """Tests for query method."""
    
    @responses.activate
    def test_query_success(self, base_url, mock_auth):
        """query returns DataFrame with results."""
        # Mock job submission
        responses.add(
            responses.POST,
            f"{base_url}/search/jobs",
            json={"items": [{"id": "job-123"}]},
            status=200,
        )
        
        # Mock job status (completed)
        responses.add(
            responses.GET,
            f"{base_url}/search/jobs/job-123/status",
            json={"items": [{"status": "completed", "numEvents": 2}]},
            status=200,
        )
        
        # Mock results (NDJSON)
        ndjson = (
            '{"isFinished":true,"totalEventCount":2,"offset":0}\n'
            '{"_time":1704067200,"message":"log1"}\n'
            '{"_time":1704067201,"message":"log2"}\n'
        )
        responses.add(
            responses.GET,
            f"{base_url}/search/jobs/job-123/results",
            body=ndjson,
            status=200,
        )
        
        client = CriblSearchHex(
            client_id="id",
            client_secret="secret",
            org_id="test-org",
            workspace="test-workspace",
        )
        
        df = client.query('cribl dataset="logs" | limit 2', earliest="-1h")
        
        assert len(df) == 2
        assert "message" in df.columns
        assert df["message"].tolist() == ["log1", "log2"]
    
    @responses.activate
    def test_query_invalid_syntax(self, base_url, mock_auth):
        """query raises QueryError on invalid syntax."""
        responses.add(
            responses.POST,
            f"{base_url}/search/jobs",
            body="Invalid query syntax",
            status=400,
        )
        
        client = CriblSearchHex(
            client_id="id",
            client_secret="secret",
            org_id="test-org",
            workspace="test-workspace",
        )
        
        with pytest.raises(QueryError) as exc_info:
            client.query("bad query", earliest="-1h")
        
        assert "Invalid query syntax" in str(exc_info.value)
    
    @responses.activate
    def test_query_job_failed(self, base_url, mock_auth):
        """query raises QueryError when job fails."""
        responses.add(
            responses.POST,
            f"{base_url}/search/jobs",
            json={"items": [{"id": "job-fail"}]},
            status=200,
        )
        
        responses.add(
            responses.GET,
            f"{base_url}/search/jobs/job-fail/status",
            json={"items": [{"status": "failed", "error": "Dataset not found"}]},
            status=200,
        )
        
        client = CriblSearchHex(
            client_id="id",
            client_secret="secret",
            org_id="test-org",
            workspace="test-workspace",
        )
        
        with pytest.raises(QueryError) as exc_info:
            client.query('cribl dataset="nonexistent"', earliest="-1h")
        
        assert "Dataset not found" in str(exc_info.value)
