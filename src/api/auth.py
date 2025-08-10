"""Authentication middleware and utilities for NFL Analysis API."""

import os
import hashlib
import secrets
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED

# Security scheme
security = HTTPBearer(auto_error=False)

def get_api_key_hash() -> Optional[str]:
    """Get API key hash from environment variable."""
    return os.getenv('NFL_API_KEY_HASH')

def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()

def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)

def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> bool:
    """
    Verify API key authentication.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        bool: True if authenticated
        
    Raises:
        HTTPException: 401 if authentication fails
    """
    # Allow access if no API key is configured (for development)
    expected_hash = get_api_key_hash()
    if not expected_hash:
        return True
    
    # Check if credentials provided
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key required. Use Authorization: Bearer YOUR_API_KEY",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify API key
    provided_hash = hash_api_key(credentials.credentials)
    if provided_hash != expected_hash:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True

# Dependency for protecting API endpoints
def authenticated(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> bool:
    """FastAPI dependency for API authentication."""
    return verify_api_key(credentials)

# Generate API key utility (for setup)
if __name__ == "__main__":
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    
    print("=== NFL Analysis Engine API Key Setup ===")
    print(f"API Key: {api_key}")
    print(f"API Key Hash: {api_key_hash}")
    print(f"\nTo enable authentication, set environment variable:")
    print(f"NFL_API_KEY_HASH={api_key_hash}")
    print(f"\nTo make authenticated requests, use:")
    print(f"Authorization: Bearer {api_key}")