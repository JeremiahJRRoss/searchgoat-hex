"""CriblSearchHex - Query Cribl Search from Hex notebooks."""

import time
from typing import Optional

import pandas as pd
import requests

from searchgoat_hex.config import CriblConfig, load_config
from searchgoat_hex.exceptions import (
    AuthenticationError,
    QueryError,
    TimeoutError,
)


class CriblSearchHex:
    """
    Query Cribl Search and return pandas DataFrames.
    
    Works in both Hex notebooks (explicit credentials) and locally (env vars).
    
    Hex Usage (credentials from secrets):
        client = CriblSearchHex(
            client_id=cribl_client_id,
            client_secret=cribl_client_secret,
            org_id=cribl_org_id,
            workspace=cribl_workspace
        )
        df = client.query('cribl dataset="logs" | limit 100', earliest="-1h")
        
    Local Usage (credentials from environment):
        client = CriblSearchHex()
        df = client.query('cribl dataset="logs" | limit 100', earliest="-1h")
        
    Attributes:
        org_id: The Cribl organization ID
        workspace: The Cribl workspace name
    """
    
    # Job polling configuration
    _POLL_INTERVAL = 2.0  # seconds between status checks
    _TOKEN_REFRESH_BUFFER = 300  # refresh token 5 min before expiry
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        org_id: Optional[str] = None,
        workspace: Optional[str] = None,
        timeout: float = 300.0,
    ):
        """
        Initialize Cribl Search client.
        
        If credentials are not provided, reads from environment variables:
        - CRIBL_CLIENT_ID
        - CRIBL_CLIENT_SECRET
        - CRIBL_ORG_ID
        - CRIBL_WORKSPACE
        
        Args:
            client_id: Cribl OAuth2 Client ID
            client_secret: Cribl OAuth2 Client Secret
            org_id: Cribl Organization ID
            workspace: Cribl Workspace name
            timeout: Default query timeout in seconds (default: 300)
            
        Raises:
            ConfigurationError: If required credentials are missing
        """
        self._config = load_config(client_id, client_secret, org_id, workspace)
        self._default_timeout = timeout
        
        # Token management
        self._token: Optional[str] = None
        self._token_expires_at: float = 0
        
        # HTTP session for connection reuse
        self._session = requests.Session()
    
    @property
    def org_id(self) -> str:
        """The Cribl organization ID."""
        return self._config.org_id
    
    @property
    def workspace(self) -> str:
        """The Cribl workspace name."""
        return self._config.workspace
    
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    
    def test_connection(self) -> bool:
        """
        Test the connection to Cribl Search.
        
        Verifies that:
        1. Credentials are valid (OAuth2 authentication succeeds)
        2. API endpoint is reachable
        
        Returns:
            True if connection is successful
            
        Raises:
            AuthenticationError: If credentials are invalid
            CriblSearchError: If API is unreachable
        """
        # Force token refresh to verify credentials
        self._token = None
        self._token_expires_at = 0
        
        try:
            self._get_auth_token()
            return True
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Connection test failed: {e}") from e
    
    def list_datasets(self) -> list[str]:
        """
        List available datasets in Cribl Search.
        
        Returns:
            List of dataset names that can be used in queries
            
        Raises:
            AuthenticationError: If credentials are invalid
            QueryError: If the request fails
            
        Example:
            datasets = client.list_datasets()
            print(datasets)  # ['cribl_logs', 'firewall', 'main', ...]
        """
        headers = self._get_headers()
        url = f"{self._config.api_base_url}/datasets"
        
        try:
            response = self._session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Authentication failed") from e
            raise QueryError(f"Failed to list datasets: {e}") from e
        except requests.exceptions.RequestException as e:
            raise QueryError(f"Failed to list datasets: {e}") from e
        
        data = response.json()
        
        # Extract dataset names from response
        # The API returns {"items": [{"id": "name", ...}, ...]}
        items = data.get("items", [])
        return [item.get("id") or item.get("name", "") for item in items]
    
    def query(
        self,
        query: str,
        earliest: str = "-1h",
        latest: str = "now",
        timeout: Optional[float] = None,
    ) -> pd.DataFrame:
        """
        Execute a Cribl Search query and return results as a DataFrame.
        
        Args:
            query: Cribl Search query (must start with 'cribl dataset="..."')
            earliest: Start of time range (default: "-1h")
            latest: End of time range (default: "now")
            timeout: Query timeout in seconds (default: instance timeout)
            
        Returns:
            pandas DataFrame containing query results
            
        Raises:
            AuthenticationError: If credentials are invalid
            QueryError: If query syntax is invalid or execution fails
            TimeoutError: If query exceeds timeout
            
        Example:
            df = client.query(
                'cribl dataset="logs" | where level="ERROR" | limit 100',
                earliest="-24h"
            )
            print(df.head())
        """
        timeout = timeout or self._default_timeout
        
        # Submit job
        job_id = self._submit_job(query, earliest, latest)
        
        # Wait for completion
        self._wait_for_job(job_id, timeout)
        
        # Retrieve results
        return self._get_results(job_id)
    
    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------
    
    def _get_auth_token(self) -> str:
        """Get a valid auth token, refreshing if necessary."""
        if self._token and time.time() < (self._token_expires_at - self._TOKEN_REFRESH_BUFFER):
            return self._token
        
        self._authenticate()
        return self._token  # type: ignore
    
    def _authenticate(self) -> None:
        """Perform OAuth2 client_credentials flow."""
        payload = {
            "grant_type": "client_credentials",
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "audience": "https://api.cribl.cloud",
        }
        
        try:
            response = self._session.post(
                self._config.auth_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise AuthenticationError(
                f"Authentication failed: {e.response.status_code} - {e.response.text}"
            ) from e
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Authentication request failed: {e}") from e
        
        data = response.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 86400)
    
    def _get_headers(self) -> dict:
        """Get request headers with valid auth token."""
        token = self._get_auth_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    
    # -------------------------------------------------------------------------
    # Job Management
    # -------------------------------------------------------------------------
    
    def _submit_job(self, query: str, earliest: str, latest: str) -> str:
        """Submit a search job and return the job ID."""
        headers = self._get_headers()
        url = f"{self._config.api_base_url}/search/jobs"
        
        payload = {
            "query": query,
            "earliest": earliest,
            "latest": latest,
            "sampleRate": 1,
        }
        
        try:
            response = self._session.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 400:
                raise QueryError(f"Invalid query syntax: {response.text}")
            
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Authentication failed") from e
            raise QueryError(f"Job submission failed: {e}") from e
        except requests.exceptions.RequestException as e:
            raise QueryError(f"Job submission failed: {e}") from e
        
        data = response.json()
        return data["items"][0]["id"]
    
    def _wait_for_job(self, job_id: str, timeout: float) -> None:
        """Poll job status until completion or timeout."""
        headers = self._get_headers()
        url = f"{self._config.api_base_url}/search/jobs/{job_id}/status"
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Query did not complete within {timeout} seconds. "
                    f"Try narrowing the time range or adding '| limit N' to your query."
                )
            
            try:
                response = self._session.get(url, headers=headers, timeout=30)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise QueryError(f"Failed to check job status: {e}") from e
            
            data = response.json()
            status = data["items"][0]["status"]
            
            if status == "completed":
                return
            
            if status == "failed":
                error_msg = data["items"][0].get("error", "Unknown error")
                raise QueryError(f"Query failed: {error_msg}", job_id=job_id)
            
            if status == "canceled":
                raise QueryError("Query was canceled", job_id=job_id)
            
            # Still running/queued, wait and poll again
            time.sleep(self._POLL_INTERVAL)
    
    def _get_results(self, job_id: str) -> pd.DataFrame:
        """Retrieve results and convert to DataFrame."""
        headers = self._get_headers()
        headers["Accept"] = "application/x-ndjson"
        url = f"{self._config.api_base_url}/search/jobs/{job_id}/results"
        
        all_records = []
        offset = 0
        page_size = 1000
        total_count = None
        
        while True:
            params = {"limit": page_size, "offset": offset}
            
            try:
                response = self._session.get(url, params=params, headers=headers, timeout=60)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise QueryError(f"Failed to retrieve results: {e}") from e
            
            lines = response.text.strip().split("\n")
            if not lines:
                break
            
            # First line is metadata
            import json
            metadata = json.loads(lines[0])
            total_count = metadata.get("totalEventCount", 0)
            
            # Remaining lines are events
            for line in lines[1:]:
                if line.strip():
                    all_records.append(json.loads(line))
            
            offset += page_size
            if total_count is None or offset >= total_count:
                break
        
        # Convert to DataFrame
        df = pd.DataFrame(all_records)
        
        # Parse _time column if present
        if "_time" in df.columns and len(df) > 0:
            df["_time"] = pd.to_datetime(df["_time"], unit="s", utc=True)
        
        return df
