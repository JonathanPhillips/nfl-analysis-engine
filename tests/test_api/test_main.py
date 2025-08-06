"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient


class TestMainApplication:
    """Test main FastAPI application endpoints."""
    
    def test_root_endpoint(self, test_client):
        """Test the root endpoint returns HTML."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "NFL Analysis Engine API" in response.text
        assert "/api/docs" in response.text
    
    def test_health_check_endpoint(self, test_client):
        """Test the health check endpoint."""
        response = test_client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "NFL Analysis Engine"
        assert data["version"] == "1.0.0"
        assert "database" in data
    
    def test_openapi_docs(self, test_client):
        """Test that OpenAPI documentation is available."""
        response = test_client.get("/api/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_docs(self, test_client):
        """Test that ReDoc documentation is available."""
        response = test_client.get("/api/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_openapi_schema(self, test_client):
        """Test that OpenAPI schema is available."""
        response = test_client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "NFL Analysis Engine"
        assert schema["info"]["version"] == "1.0.0"
        
        # Check that our endpoints are documented
        paths = schema["paths"]
        assert "/api/v1/teams/" in paths
        assert "/api/v1/players/" in paths
        assert "/api/v1/games/" in paths
        assert "/api/v1/plays/" in paths
        assert "/api/v1/data/status" in paths
    
    def test_cors_headers(self, test_client):
        """Test CORS headers are present."""
        response = test_client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # FastAPI/Starlette handles OPTIONS automatically
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly handled
        
        # Test actual request with origin
        response = test_client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        # CORS middleware should add these headers
        assert "access-control-allow-origin" in response.headers
    
    def test_process_time_header(self, test_client):
        """Test that process time header is added by middleware."""
        response = test_client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert "x-process-time" in response.headers
        
        # Should be a valid float
        process_time = float(response.headers["x-process-time"])
        assert process_time >= 0
        assert process_time < 10  # Should complete quickly
    
    def test_404_endpoint(self, test_client):
        """Test 404 response for non-existent endpoint."""
        response = test_client.get("/nonexistent/endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data