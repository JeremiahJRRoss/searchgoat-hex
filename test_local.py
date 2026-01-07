#!/usr/bin/env python3
"""
searchgoat-hex Local Test Script

This script tests searchgoat-hex locally before deploying to Hex.
It simulates both the local workflow (env vars) and Hex workflow (explicit params).

Usage:
    # With .env file:
    python test_local.py

    # With explicit credentials:
    python test_local.py --client-id YOUR_ID --client-secret YOUR_SECRET \
                         --org-id YOUR_ORG --workspace YOUR_WORKSPACE

    # Dry run (no actual API calls):
    python test_local.py --dry-run
"""

import argparse
import sys
import os
from pathlib import Path

# =============================================================================
# Test Configuration
# =============================================================================

# Default test query - modify to match a dataset in your Cribl instance
TEST_DATASET = "cribl_logs"  # Change this to your dataset
TEST_QUERY = f'cribl dataset="{TEST_DATASET}" | limit 5'
TEST_TIMERANGE = "-1h"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_success(text: str) -> None:
    print(f"✓ {text}")


def print_error(text: str) -> None:
    print(f"✗ {text}")


def print_info(text: str) -> None:
    print(f"→ {text}")


# =============================================================================
# Test: Import Module
# =============================================================================

def test_import():
    """Test that searchgoat_hex imports correctly."""
    print_header("Test 1: Import Module")
    
    try:
        from searchgoat_hex import CriblSearchHex, __version__
        print_success(f"searchgoat-hex v{__version__} imported successfully")
        return True
    except ImportError as e:
        print_error(f"Import failed: {e}")
        print_info("Make sure you've installed the package: pip install -e .")
        return False


# =============================================================================
# Test: Configuration Loading
# =============================================================================

def test_config_from_env():
    """Test that config loads from environment variables."""
    print_header("Test 2a: Config from Environment Variables")
    
    from searchgoat_hex import CriblSearchHex
    
    required_vars = [
        "CRIBL_CLIENT_ID",
        "CRIBL_CLIENT_SECRET", 
        "CRIBL_ORG_ID",
        "CRIBL_WORKSPACE"
    ]
    
    missing = [v for v in required_vars if not os.getenv(v)]
    
    if missing:
        print_error(f"Missing environment variables: {missing}")
        print_info("Set these in your .env file or environment")
        return False
    
    try:
        client = CriblSearchHex()
        print_success("CriblSearchHex() initialized from environment")
        print_info(f"Org ID: {client.org_id}")
        print_info(f"Workspace: {client.workspace}")
        return True
    except Exception as e:
        print_error(f"Failed to initialize: {e}")
        return False


def test_config_explicit(client_id, client_secret, org_id, workspace):
    """Test that config works with explicit parameters (Hex pattern)."""
    print_header("Test 2b: Config with Explicit Parameters (Hex Pattern)")
    
    from searchgoat_hex import CriblSearchHex
    
    try:
        client = CriblSearchHex(
            client_id=client_id,
            client_secret=client_secret,
            org_id=org_id,
            workspace=workspace
        )
        print_success("CriblSearchHex() initialized with explicit parameters")
        print_info(f"Org ID: {client.org_id}")
        print_info(f"Workspace: {client.workspace}")
        return client
    except Exception as e:
        print_error(f"Failed to initialize: {e}")
        return None


# =============================================================================
# Test: Authentication
# =============================================================================

def test_authentication(client):
    """Test that authentication works."""
    print_header("Test 3: Authentication")
    
    try:
        # This should trigger OAuth token fetch
        token = client._get_auth_token()
        print_success("OAuth2 authentication successful")
        print_info(f"Token: {token[:20]}..." if len(token) > 20 else f"Token: {token}")
        return True
    except Exception as e:
        print_error(f"Authentication failed: {e}")
        print_info("Check your client_id and client_secret")
        return False


# =============================================================================
# Test: Query Execution
# =============================================================================

def test_query(client, query: str, earliest: str):
    """Test that queries execute and return DataFrames."""
    print_header("Test 4: Query Execution")
    
    print_info(f"Query: {query}")
    print_info(f"Time range: {earliest}")
    
    try:
        df = client.query(query, earliest=earliest)
        print_success(f"Query returned {len(df)} records")
        print_success(f"Columns: {list(df.columns)[:5]}{'...' if len(df.columns) > 5 else ''}")
        
        if len(df) > 0:
            print_info("\nFirst row preview:")
            print(df.head(1).to_string())
        
        return df
    except Exception as e:
        print_error(f"Query failed: {e}")
        return None


# =============================================================================
# Test: DataFrame Output
# =============================================================================

def test_dataframe_output(df):
    """Test that output is a proper pandas DataFrame."""
    print_header("Test 5: DataFrame Validation")
    
    import pandas as pd
    
    if not isinstance(df, pd.DataFrame):
        print_error(f"Output is not a DataFrame: {type(df)}")
        return False
    
    print_success(f"Output is pandas DataFrame")
    print_success(f"Shape: {df.shape}")
    print_success(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024:.2f} KB")
    print_info(f"Data types:\n{df.dtypes}")
    
    return True


# =============================================================================
# Dry Run Mode
# =============================================================================

def test_dry_run():
    """Run tests without making actual API calls."""
    print_header("Dry Run Mode")
    
    print_info("Testing module structure without API calls")
    
    # Test imports
    try:
        from searchgoat_hex import CriblSearchHex, __version__
        from searchgoat_hex import CriblSearchError, AuthenticationError, QueryError
        print_success("All imports successful")
    except ImportError as e:
        print_error(f"Import failed: {e}")
        return False
    
    # Test class instantiation (will fail without creds, but shows structure)
    print_info("\nExpected API:")
    print("""
    # Initialize (Hex pattern - explicit credentials):
    client = CriblSearchHex(
        client_id="...",
        client_secret="...",
        org_id="...",
        workspace="..."
    )
    
    # Initialize (Local pattern - from environment):
    client = CriblSearchHex()
    
    # Test connection:
    client.test_connection()
    
    # List datasets:
    datasets = client.list_datasets()
    
    # Execute query:
    df = client.query(
        'cribl dataset="logs" | limit 100',
        earliest="-1h",
        latest="now"
    )
    
    # DataFrame is ready for use:
    print(df.head())
    """)
    
    print_success("Dry run complete - module structure looks correct")
    return True


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Test searchgoat-hex locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Test with .env file:
    python test_local.py
    
    # Test with explicit credentials:
    python test_local.py --client-id ID --client-secret SECRET --org-id ORG --workspace WS
    
    # Just check imports and structure:
    python test_local.py --dry-run
    
    # Custom query:
    python test_local.py --query 'cribl dataset="mydata" | stats count()' --earliest "-24h"
        """
    )
    
    parser.add_argument("--client-id", help="Cribl Client ID")
    parser.add_argument("--client-secret", help="Cribl Client Secret")
    parser.add_argument("--org-id", help="Cribl Organization ID")
    parser.add_argument("--workspace", help="Cribl Workspace")
    parser.add_argument("--query", default=TEST_QUERY, help="Test query to execute")
    parser.add_argument("--earliest", default=TEST_TIMERANGE, help="Time range start")
    parser.add_argument("--dry-run", action="store_true", help="Test without API calls")
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("  searchgoat-hex Local Test Suite")
    print("="*60)
    
    # Dry run mode
    if args.dry_run:
        success = test_dry_run()
        sys.exit(0 if success else 1)
    
    # Test imports
    if not test_import():
        sys.exit(1)
    
    # Determine credential source
    if args.client_id and args.client_secret and args.org_id and args.workspace:
        # Explicit credentials (simulating Hex pattern)
        client = test_config_explicit(
            args.client_id,
            args.client_secret,
            args.org_id,
            args.workspace
        )
    else:
        # Environment variables (local pattern)
        if not test_config_from_env():
            print_info("\nTip: Create a .env file or pass --client-id, --client-secret, --org-id, --workspace")
            sys.exit(1)
        
        from searchgoat_hex import CriblSearchHex
        client = CriblSearchHex()
    
    if client is None:
        sys.exit(1)
    
    # Test authentication
    if not test_authentication(client):
        sys.exit(1)
    
    # Test query
    df = test_query(client, args.query, args.earliest)
    if df is None:
        sys.exit(1)
    
    # Validate DataFrame
    if not test_dataframe_output(df):
        sys.exit(1)
    
    # Summary
    print_header("All Tests Passed! ✓")
    print("Your searchgoat-hex installation is working correctly.")
    print("You can now use this module in Hex notebooks.")


if __name__ == "__main__":
    main()
