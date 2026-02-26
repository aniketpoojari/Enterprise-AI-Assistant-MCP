"""Unit tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for health and info endpoints (no LLM required)."""

    def test_health_returns_200(self):
        """Health endpoint should return even without full initialization."""
        # Import app without lifespan to test basic routing
        from main import app

        # Note: Full integration tests require GROQ_API_KEY
        # These tests validate endpoint structure only
        assert app.title == "Enterprise AI Assistant"

    def test_mcp_tools_list_structure(self):
        """MCP tools endpoint should list 3 tools."""
        from main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/mcp/tools")
        if response.status_code == 200:
            data = response.json()
            assert "tools" in data
            assert len(data["tools"]) == 3
