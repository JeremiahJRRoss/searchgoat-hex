# searchgoat-hex User Manual

**Query Cribl Search from Hex notebooks. Get DataFrames.**

searchgoat-hex is a minimal Python adapter for querying Cribl Search and returning pandas DataFrames. It works both locally (for development/testing) and in Hex notebooks (for production analytics).

## How not to use searchgoat (a very clear disclaimer) 
If you are querying someone else's data (e.g. an employer, client, customer) you should never do anything that violates their policies. 
 - There are legal compliance and governance requirements
 - There are security requirements
 - There are privacy requirements
 - Data that lives in Cribl Search may not be suitable for the platform you are pulling that data into. Think about it before you do it.

Use this tool with great discretion and always be mindful of your security posture. Don't just trust, verify!


---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Running Locally](#running-locally)
6. [Running in Hex](#running-in-hex)
7. [API Reference](#api-reference)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

**In Hex (secrets as variables):**
```python
# Cell 1: Install
!uv pip install searchgoat-hex

# Cell 2: Query
from searchgoat_hex import CriblSearchHex

client = CriblSearchHex(
    client_id=cribl_client_id,        # Hex secret
    client_secret=cribl_client_secret, # Hex secret
    org_id=cribl_org_id,              # Hex secret
    workspace=cribl_workspace          # Hex secret
)

df = client.query('cribl dataset="logs" | limit 100', earliest="-1h")
df.head()
```

**Locally (env vars):**
```python
from searchgoat_hex import CriblSearchHex

client = CriblSearchHex()  # Reads from CRIBL_* environment variables
df = client.query('cribl dataset="logs" | limit 100', earliest="-1h")
```

---

## Installation

### Local Development

```bash
# Clone or download the package
cd searchgoat-hex

# Install in development mode
pip install -e .

# Or install from wheel
pip install searchgoat_hex-0.5.0-py3-none-any.whl
```

### In Hex Notebooks

Add this as the first cell in your notebook:

```python
!uv pip install searchgoat-hex
```

> **Note:** Hex packages don't persist across kernel restarts. You'll need this install cell in every notebook that uses searchgoat-hex.

---

## Configuration

searchgoat-hex needs four credentials to connect to Cribl Search:

| Credential | Description | Where to Find |
|------------|-------------|---------------|
| `client_id` | OAuth2 Client ID | Cribl Cloud → ⚙️ → Organization Settings → API Credentials |
| `client_secret` | OAuth2 Client Secret | Generated when you create API credentials |
| `org_id` | Organization identifier | Your URL: `https://{workspace}-{org_id}.cribl.cloud` |
| `workspace` | Workspace name | Your URL: `https://{workspace}-{org_id}.cribl.cloud` |

### Finding Your Org ID and Workspace

Look at your Cribl Cloud URL:

```
https://main-abc123xyz.cribl.cloud
       ^^^^  ^^^^^^^^^^
       │     │
       │     └── org_id = "abc123xyz"
       └──────── workspace = "main"
```

### Creating API Credentials

1. Log into [Cribl Cloud](https://cribl.cloud)
2. Click **⚙️** (gear icon) → **Organization Settings**
3. Go to **Access Management** → **API Credentials**
4. Click **+ Add Credentials**
5. Name it (e.g., "hex-analytics")
6. Ensure it has **Search** permissions
7. Click **Create**
8. **Copy the Client Secret immediately** — you won't see it again

---

## Usage

### Basic Query

```python
from searchgoat_hex import CriblSearchHex

client = CriblSearchHex(...)

# Simple query
df = client.query('cribl dataset="logs" | limit 100', earliest="-1h")

# With time range
df = client.query(
    'cribl dataset="logs" | where level="ERROR"',
    earliest="-24h",
    latest="now"
)
```

### Query Syntax

Queries use Cribl Search syntax. They must start with `cribl dataset="..."`:

```python
# Filter
df = client.query('cribl dataset="logs" | where host="web01"', earliest="-1h")

# Aggregate
df = client.query('cribl dataset="logs" | stats count() by level', earliest="-1h")

# Multiple pipes
df = client.query('''
    cribl dataset="logs" 
    | where level="ERROR" 
    | stats count() by host 
    | sort -count
''', earliest="-24h")
```

### Working with Results

Results are standard pandas DataFrames:

```python
df = client.query('cribl dataset="logs" | limit 1000', earliest="-1h")

# Standard pandas operations
print(df.shape)
print(df.columns)
print(df.describe())

# Filter
errors = df[df['level'] == 'ERROR']

# Group
by_host = df.groupby('host').size()

# Plot (in Hex, use native chart cells)
df['count'].plot(kind='bar')
```

### Handling Large Results

For large result sets, use server-side limiting and pagination:

```python
# Limit on server (recommended)
df = client.query('cribl dataset="logs" | limit 10000', earliest="-24h")

# Aggregate on server to reduce data transfer
df = client.query('''
    cribl dataset="logs" 
    | stats count(), avg(duration) by host, level
''', earliest="-7d")
```

---

## Running Locally

Local development uses environment variables for credentials.

### Step 1: Create .env File

In your project directory, create a `.env` file:

```bash
# .env
CRIBL_CLIENT_ID=your-client-id
CRIBL_CLIENT_SECRET=your-client-secret
CRIBL_ORG_ID=your-org-id
CRIBL_WORKSPACE=your-workspace
```

### Step 2: Load Environment

Option A — Use python-dotenv:

```python
from dotenv import load_dotenv
load_dotenv()

from searchgoat_hex import CriblSearchHex
client = CriblSearchHex()  # Automatically reads CRIBL_* env vars
```

Option B — Export in shell:

```bash
export CRIBL_CLIENT_ID=your-client-id
export CRIBL_CLIENT_SECRET=your-client-secret
export CRIBL_ORG_ID=your-org-id
export CRIBL_WORKSPACE=your-workspace

python your_script.py
```

### Step 3: Run Test Script

Use the included test script to verify your setup:

```bash
# With .env file
python test_local.py

# With explicit credentials
python test_local.py \
    --client-id YOUR_ID \
    --client-secret YOUR_SECRET \
    --org-id YOUR_ORG \
    --workspace YOUR_WORKSPACE

# Dry run (no API calls)
python test_local.py --dry-run

# Custom query
python test_local.py --query 'cribl dataset="mydata" | limit 10' --earliest "-24h"
```

### Step 4: Develop and Iterate

```python
# local_dev.py
from dotenv import load_dotenv
load_dotenv()

from searchgoat_hex import CriblSearchHex

client = CriblSearchHex()

# Develop your queries
df = client.query('cribl dataset="logs" | stats count() by level', earliest="-1h")
print(df)

# Test aggregations
df = client.query('''
    cribl dataset="logs" 
    | where level="ERROR" 
    | stats count() by host
''', earliest="-24h")
print(df)
```

---

## Running in Hex

Hex injects secrets as Python variables, not environment variables. This is more secure and doesn't expose credentials in code.

### Step 1: Configure Secrets in Hex

**Project-level secrets** (single project):
1. Open your Hex project
2. Click the **Variables** tab in the left sidebar
3. Click **+ Add secret**
4. Create four secrets:
   - `cribl_client_id` → Your Client ID
   - `cribl_client_secret` → Your Client Secret
   - `cribl_org_id` → Your Org ID
   - `cribl_workspace` → Your Workspace

**Workspace-level secrets** (shared across projects, Admin only):
1. Go to **Settings** → **Workspace assets**
2. Select **Secrets**
3. Create the same four secrets
4. Optionally restrict to specific user groups

### Step 2: Create Install Cell

First cell in your notebook:

```python
# Cell 1: Install dependencies
!uv pip install searchgoat-hex
```

> **Why `uv pip`?** It's 10-100x faster than regular pip. Hex recommends it.

### Step 3: Initialize Client with Secrets

```python
# Cell 2: Initialize client
from searchgoat_hex import CriblSearchHex

client = CriblSearchHex(
    client_id=cribl_client_id,         # ← Hex injects this
    client_secret=cribl_client_secret, # ← Hex injects this
    org_id=cribl_org_id,               # ← Hex injects this
    workspace=cribl_workspace          # ← Hex injects this
)
```

Hex automatically redacts secret values in output — you'll see `[SECRET VALUE]` instead of actual credentials.

### Step 4: Query and Analyze

```python
# Cell 3: Run query
df = client.query(
    'cribl dataset="logs" | where level="ERROR" | limit 1000',
    earliest="-24h"
)

# Cell 4: Display
df
```

### Step 5: Use Hex Features

The returned DataFrame works with all Hex features:

**Chart cells:**
- Select your DataFrame
- Choose visualization type
- Hex auto-detects columns

**SQL cells:**
```sql
SELECT host, COUNT(*) as error_count
FROM df
WHERE level = 'ERROR'
GROUP BY host
ORDER BY error_count DESC
```

**Input parameters:**
```python
# Create an input cell for 'time_range' dropdown

df = client.query(
    f'cribl dataset="logs" | limit 1000',
    earliest=time_range  # ← Input parameter
)
```

### Complete Hex Notebook Template

```python
# ═══════════════════════════════════════════════════════════════
# Cell 1: Setup
# ═══════════════════════════════════════════════════════════════
!uv pip install searchgoat-hex

# ═══════════════════════════════════════════════════════════════
# Cell 2: Initialize Client
# ═══════════════════════════════════════════════════════════════
from searchgoat_hex import CriblSearchHex

client = CriblSearchHex(
    client_id=cribl_client_id,
    client_secret=cribl_client_secret,
    org_id=cribl_org_id,
    workspace=cribl_workspace
)
print("✓ Connected to Cribl Search")

# ═══════════════════════════════════════════════════════════════
# Cell 3: Define Query
# ═══════════════════════════════════════════════════════════════
QUERY = '''
cribl dataset="logs" 
| where level="ERROR" 
| stats count() by host, source
| sort -count
'''

# ═══════════════════════════════════════════════════════════════
# Cell 4: Execute Query
# ═══════════════════════════════════════════════════════════════
df = client.query(QUERY, earliest="-24h")
print(f"Retrieved {len(df)} records")

# ═══════════════════════════════════════════════════════════════
# Cell 5: Display Results
# ═══════════════════════════════════════════════════════════════
df
```

---

## API Reference

### CriblSearchHex

```python
class CriblSearchHex:
    def __init__(
        self,
        client_id: str = None,      # Cribl OAuth2 Client ID
        client_secret: str = None,  # Cribl OAuth2 Client Secret
        org_id: str = None,         # Cribl Organization ID
        workspace: str = None,      # Cribl Workspace name
        timeout: float = 300.0      # Query timeout in seconds
    ):
        """
        Initialize Cribl Search client.
        
        If credentials are not provided, reads from environment:
        - CRIBL_CLIENT_ID
        - CRIBL_CLIENT_SECRET
        - CRIBL_ORG_ID
        - CRIBL_WORKSPACE
        """
```

### test_connection()

```python
def test_connection(self) -> bool:
    """
    Test the connection to Cribl Search.
    
    Verifies that credentials are valid and API is reachable.
    
    Returns:
        True if connection is successful
        
    Raises:
        AuthenticationError: If credentials are invalid
    """
```

### list_datasets()

```python
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
```

### query()

```python
def query(
    self,
    query: str,              # Cribl Search query
    earliest: str = "-1h",   # Start time (e.g., "-24h", "-7d", "2024-01-01")
    latest: str = "now",     # End time
    timeout: float = None    # Override default timeout
) -> pd.DataFrame:
    """
    Execute a Cribl Search query and return results as a DataFrame.
    
    Raises:
        AuthenticationError: Invalid credentials
        QueryError: Query syntax error or execution failure
        TimeoutError: Query exceeded timeout
    """
```

### Exceptions

```python
from searchgoat_hex import (
    CriblSearchError,     # Base exception
    AuthenticationError,  # Credential issues
    QueryError,           # Query syntax or execution errors
    TimeoutError,         # Query timeout
    ConfigurationError    # Missing credentials
)
```

---

## Troubleshooting

### "Field required" / Missing credentials

**Cause:** Credentials not found in environment or not passed explicitly.

**Local fix:**
```bash
# Check your .env file exists and has all four values
cat .env

# Or export directly
export CRIBL_CLIENT_ID=...
```

**Hex fix:**
- Ensure all four secrets are created in the Variables tab
- Check spelling matches exactly: `cribl_client_id`, not `CRIBL_CLIENT_ID`

### "401 Unauthorized"

**Cause:** Invalid client_id or client_secret.

**Fix:**
1. Go to Cribl Cloud → API Credentials
2. Verify the credential exists and is not revoked
3. If unsure, delete and create a new credential
4. Copy the new secret immediately

### "Dataset not found"

**Cause:** The dataset name in your query doesn't exist.

**Fix:**
1. Go to Cribl Cloud → Search
2. Check the Datasets panel for available datasets
3. Use the exact name (case-sensitive)

### "Query timeout"

**Cause:** Query took longer than the timeout (default 300s).

**Fix:**
```python
# Option 1: Increase timeout
df = client.query(query, earliest="-24h", timeout=600)

# Option 2: Narrow the time range
df = client.query(query, earliest="-1h")  # Instead of -24h

# Option 3: Add server-side limits
df = client.query(query + " | limit 10000", earliest="-24h")
```

### Hex: "Module not found" after kernel restart

**Cause:** Hex doesn't persist pip packages across sessions.

**Fix:** Always include the install cell at the top:
```python
!uv pip install searchgoat-hex
```

### Hex: Secrets showing as undefined

**Cause:** Secret names don't match variable names in code.

**Fix:** 
- Secret name in Hex: `cribl_client_id`
- Variable in code: `cribl_client_id` (must match exactly)
- Note: Hex secrets are lowercase with underscores, not `CRIBL_CLIENT_ID`

---

## Version History

| Version | Changes |
|---------|---------|
| 0.5.0 | Initial public release, Apache 2.0 license |

---

## License

Apache 2.0

---

## Support

- **GitHub Issues:** [github.com/hackish-pub/searchgoat-hex/issues](https://github.com/hackish-pub/searchgoat-hex/issues)
- **Cribl Docs:** [docs.cribl.io](https://docs.cribl.io)
- **Hex Docs:** [learn.hex.tech](https://learn.hex.tech)

---

*Part of the hackish.pub project family. 🐐*
