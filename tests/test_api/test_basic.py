"""Basic API tests to verify the structure works."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import create_app


def test_api_creation():
    """Test that we can create the API app."""
    app = create_app()
    assert app is not None
    assert app.title == "NFL Analysis Engine"


def test_basic_endpoints():
    """Test basic endpoints without database."""
    app = create_app()
    
    # Override database dependency to avoid database connection
    def mock_db():
        pass
    
    with TestClient(app) as client:
        # Test root endpoint redirects to web interface
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/web/"
        
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "NFL Analysis Engine"