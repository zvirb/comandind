"""
Learning Service Main API Tests
==============================

Test the main FastAPI application endpoints and functionality.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from ..main import app
from ..models.learning_requests import OutcomeLearningRequest, OutcomeType


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test the health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_learn_outcome_endpoint():
    """Test the learn from outcome endpoint."""
    # Mock the learning engine
    with patch("app.learning_service.main.learning_engine") as mock_engine:
        mock_engine.learn_from_outcome = AsyncMock(return_value=([], {"insights": []}))
        
        request_data = {
            "outcome_type": "reasoning_success",
            "service_name": "reasoning-service",
            "context": {"test": "context"},
            "input_data": {"test": "input"},
            "output_data": {"test": "output"}
        }
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/learn/outcome", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "patterns_learned" in data


@pytest.mark.asyncio
async def test_search_patterns_endpoint():
    """Test the pattern search endpoint."""
    with patch("app.learning_service.main.pattern_engine") as mock_engine:
        mock_engine.search_patterns = AsyncMock(return_value=[])
        
        request_data = {
            "context": {"test": "context"},
            "search_scope": "global",
            "max_results": 10
        }
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/patterns/search", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "matches" in data


if __name__ == "__main__":
    pytest.main([__file__])