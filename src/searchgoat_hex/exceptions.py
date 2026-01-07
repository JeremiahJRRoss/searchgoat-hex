"""Exception hierarchy for searchgoat-hex."""


class CriblSearchError(Exception):
    """Base exception for all searchgoat-hex errors."""
    pass


class AuthenticationError(CriblSearchError):
    """
    OAuth2 authentication failed.
    
    Common causes:
    - Invalid client_id or client_secret
    - Expired or revoked credentials
    - Network connectivity to login.cribl.cloud
    """
    pass


class QueryError(CriblSearchError):
    """
    Query execution failed.
    
    Common causes:
    - Invalid query syntax (must start with 'cribl dataset="..."')
    - Dataset does not exist
    - Insufficient permissions
    - Server-side execution error
    """
    
    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message)
        self.job_id = job_id


class TimeoutError(CriblSearchError):
    """
    Query did not complete within the timeout period.
    
    Consider:
    - Narrowing the time range (earliest/latest)
    - Adding filters to reduce data volume
    - Adding '| limit N' to the query
    - Increasing the timeout parameter
    """
    pass


class ConfigurationError(CriblSearchError):
    """
    Missing or invalid configuration.
    
    Ensure all required credentials are provided either:
    - As constructor parameters (Hex pattern)
    - As environment variables: CRIBL_CLIENT_ID, CRIBL_CLIENT_SECRET, 
      CRIBL_ORG_ID, CRIBL_WORKSPACE
    """
    pass
