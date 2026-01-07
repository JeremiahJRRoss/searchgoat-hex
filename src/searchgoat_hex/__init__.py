"""
searchgoat-hex - Query Cribl Search from Hex notebooks. Get DataFrames.

Quick Start (Hex)
-----------------
    from searchgoat_hex import CriblSearchHex

    client = CriblSearchHex(
        client_id=cribl_client_id,        # Hex secret
        client_secret=cribl_client_secret, # Hex secret
        org_id=cribl_org_id,              # Hex secret
        workspace=cribl_workspace          # Hex secret
    )
    
    df = client.query('cribl dataset="logs" | limit 100', earliest="-1h")

Quick Start (Local)
-------------------
    from searchgoat_hex import CriblSearchHex

    client = CriblSearchHex()  # Reads CRIBL_* env vars
    df = client.query('cribl dataset="logs" | limit 100', earliest="-1h")

Additional Methods
------------------
    # Test connection
    client.test_connection()
    
    # List available datasets
    datasets = client.list_datasets()

Full Documentation
------------------
    https://github.com/hackish-pub/searchgoat-hex#readme

Part of the hackish.pub project family.
"""

__version__ = "0.5.0"

from searchgoat_hex.client import CriblSearchHex
from searchgoat_hex.exceptions import (
    CriblSearchError,
    AuthenticationError,
    QueryError,
    TimeoutError,
    ConfigurationError,
)

__all__ = [
    "CriblSearchHex",
    "CriblSearchError",
    "AuthenticationError",
    "QueryError",
    "TimeoutError",
    "ConfigurationError",
    "__version__",
]
