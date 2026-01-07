"""Configuration management for searchgoat-hex.

Supports two patterns:
1. Hex pattern: Credentials passed explicitly as constructor parameters
2. Local pattern: Credentials read from environment variables
"""

import os
from dataclasses import dataclass
from typing import Optional

from searchgoat_hex.exceptions import ConfigurationError


@dataclass
class CriblConfig:
    """
    Cribl Search API configuration.
    
    Attributes:
        client_id: OAuth2 client ID from Cribl.Cloud
        client_secret: OAuth2 client secret
        org_id: Cribl organization identifier
        workspace: Cribl workspace name
    """
    client_id: str
    client_secret: str
    org_id: str
    workspace: str
    
    @property
    def auth_url(self) -> str:
        """OAuth2 token endpoint."""
        return "https://login.cribl.cloud/oauth/token"
    
    @property
    def api_base_url(self) -> str:
        """Construct the API base URL from workspace and org_id."""
        return f"https://{self.workspace}-{self.org_id}.cribl.cloud/api/v1/m/default_search"


def load_config(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    org_id: Optional[str] = None,
    workspace: Optional[str] = None,
) -> CriblConfig:
    """
    Load configuration from parameters or environment.
    
    If any parameter is None, attempts to load from environment variable.
    
    Args:
        client_id: Cribl Client ID (or CRIBL_CLIENT_ID env var)
        client_secret: Cribl Client Secret (or CRIBL_CLIENT_SECRET env var)
        org_id: Cribl Org ID (or CRIBL_ORG_ID env var)
        workspace: Cribl Workspace (or CRIBL_WORKSPACE env var)
        
    Returns:
        CriblConfig with all credentials populated
        
    Raises:
        ConfigurationError: If any required credential is missing
    """
    # Try to load dotenv if available (for local development)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not installed, skip
    
    # Resolve each credential
    resolved = {
        "client_id": client_id or os.getenv("CRIBL_CLIENT_ID"),
        "client_secret": client_secret or os.getenv("CRIBL_CLIENT_SECRET"),
        "org_id": org_id or os.getenv("CRIBL_ORG_ID"),
        "workspace": workspace or os.getenv("CRIBL_WORKSPACE"),
    }
    
    # Check for missing credentials
    missing = [key for key, value in resolved.items() if not value]
    
    if missing:
        env_vars = {
            "client_id": "CRIBL_CLIENT_ID",
            "client_secret": "CRIBL_CLIENT_SECRET",
            "org_id": "CRIBL_ORG_ID",
            "workspace": "CRIBL_WORKSPACE",
        }
        missing_env = [env_vars[k] for k in missing]
        raise ConfigurationError(
            f"Missing required credentials: {missing}\n"
            f"Either pass them as parameters or set environment variables: {missing_env}"
        )
    
    return CriblConfig(
        client_id=resolved["client_id"],
        client_secret=resolved["client_secret"],
        org_id=resolved["org_id"],
        workspace=resolved["workspace"],
    )
