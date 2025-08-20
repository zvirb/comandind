"""Basic tests for the Coordination Service main application."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Mock the services to avoid actual initialization during imports
mock_orchestrator = AsyncMock()
mock_workflow_manager = AsyncMock()
mock_context_generator = AsyncMock()
mock_cognitive_handler = AsyncMock()
mock_agent_registry = AsyncMock()
mock_redis_service = AsyncMock()
mock_performance_monitor = AsyncMock()

with patch.multiple(
    'main',
    orchestrator=mock_orchestrator,
    workflow_manager=mock_workflow_manager,
    context_generator=mock_context_generator,
    cognitive_handler=mock_cognitive_handler,
    agent_registry=mock_agent_registry,
    redis_service=mock_redis_service,
    performance_monitor=mock_performance_monitor
):
    from main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check_success(self):
        """Test successful health check."""
        with patch('main.redis_service') as mock_redis, \
             patch('main.agent_registry') as mock_registry, \
             patch('main.workflow_manager') as mock_wf_manager, \
             patch('main.performance_monitor') as mock_perf_monitor:
            
            # Mock successful health checks
            mock_redis.health_check.return_value = True
            mock_registry.get_agent_count.return_value = 47
            mock_wf_manager.get_active_workflow_count.return_value = 5
            mock_perf_monitor.get_current_metrics.return_value = {"avg_response_time": 0.15}
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert data["service"] == "coordination-service"
            assert data["version"] == "1.0.0"
            assert "redis_connected" in data
            assert "agent_registry" in data
            assert "workflow_manager" in data
    
    def test_health_check_degraded(self):
        """Test health check with degraded status."""
        with patch('main.redis_service') as mock_redis, \
             patch('main.agent_registry') as mock_registry, \
             patch('main.workflow_manager') as mock_wf_manager, \
             patch('main.performance_monitor') as mock_perf_monitor:
            
            # Mock failed Redis connection
            mock_redis.health_check.return_value = False
            mock_registry.get_agent_count.return_value = 47
            mock_wf_manager.get_active_workflow_count.return_value = 5
            mock_perf_monitor.get_current_metrics.return_value = {}
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "degraded"
            assert data["redis_connected"] is False


class TestWorkflowEndpoints:
    """Test workflow management endpoints."""
    
    def test_create_workflow_success(self):
        """Test successful workflow creation."""
        with patch('main.orchestrator') as mock_orch, \
             patch('main.agent_registry') as mock_registry:
            
            # Mock successful validation and creation
            mock_registry.validate_agents.return_value = True
            mock_orch.create_workflow.return_value = {
                "workflow_id": "test-workflow-123",
                "status": "created",
                "assigned_agents": ["test-agent-1", "test-agent-2"],
                "estimated_completion": 1703876000.0
            }
            
            workflow_request = {
                "workflow_type": "new_feature",
                "name": "Test Workflow",
                "priority": "medium",
                "required_agents": ["test-agent-1", "test-agent-2"],
                "context": {"test": "data"},
                "timeout_minutes": 60
            }
            
            response = client.post("/workflow/create", json=workflow_request)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "workflow_id" in data
            assert data["status"] == "created"
            assert "assigned_agents" in data
    
    def test_create_workflow_missing_agents(self):
        """Test workflow creation with unavailable agents."""
        with patch('main.agent_registry') as mock_registry:
            
            # Mock agent validation failure
            mock_registry.validate_agents.return_value = False
            
            workflow_request = {
                "workflow_type": "new_feature",
                "name": "Test Workflow",
                "required_agents": ["nonexistent-agent"]
            }
            
            response = client.post("/workflow/create", json=workflow_request)
            
            assert response.status_code == 400
            assert "Required agents not available" in response.json()["detail"]
    
    def test_get_workflow_status_success(self):
        """Test successful workflow status retrieval."""
        with patch('main.workflow_manager') as mock_manager:
            
            mock_manager.get_workflow_status.return_value = {
                "workflow_id": "test-workflow-123",
                "current_state": "running",
                "progress_percentage": 50.0,
                "execution_time_seconds": 300.0
            }
            
            response = client.get("/workflow/test-workflow-123/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["workflow_id"] == "test-workflow-123"
            assert data["current_state"] == "running"
            assert data["progress_percentage"] == 50.0
    
    def test_get_workflow_status_not_found(self):
        """Test workflow status for non-existent workflow."""
        with patch('main.workflow_manager') as mock_manager:
            
            mock_manager.get_workflow_status.return_value = None
            
            response = client.get("/workflow/nonexistent/status")
            
            assert response.status_code == 404
            assert "Workflow not found" in response.json()["detail"]


class TestAgentEndpoints:
    """Test agent management endpoints."""
    
    def test_get_active_agents_success(self):
        """Test successful active agents retrieval."""
        with patch('main.agent_registry') as mock_registry:
            
            mock_registry.get_active_assignments.return_value = [
                {
                    "agent_name": "test-agent-1",
                    "category": "test",
                    "current_workload": 1,
                    "status": "busy"
                },
                {
                    "agent_name": "test-agent-2",
                    "category": "test",
                    "current_workload": 0,
                    "status": "available"
                }
            ]
            
            response = client.get("/agents/active")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_active"] == 2
            assert len(data["agents"]) == 2
            assert data["agents"][0]["agent_name"] == "test-agent-1"


class TestCognitiveEventEndpoints:
    """Test cognitive event endpoints."""
    
    def test_receive_cognitive_event_success(self):
        """Test successful cognitive event processing."""
        with patch('main.cognitive_handler') as mock_handler:
            
            mock_handler.process_cognitive_event.return_value = {
                "processed": True,
                "workflow_updates": ["test-workflow-123"]
            }
            
            event_request = {
                "event_type": "reasoning_complete",
                "source_service": "reasoning-service",
                "workflow_id": "test-workflow-123",
                "event_data": {
                    "confidence_score": 0.9,
                    "result": "test result"
                }
            }
            
            response = client.post("/cognitive-events/receive", json=event_request)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "event_id" in data
            assert data["processed"] is True
            assert data["workflow_updates"] == ["test-workflow-123"]


class TestPerformanceEndpoints:
    """Test performance and monitoring endpoints."""
    
    def test_get_performance_metrics_success(self):
        """Test successful performance metrics retrieval."""
        with patch('main.performance_monitor') as mock_monitor:
            
            mock_monitor.get_comprehensive_metrics.return_value = {
                "timestamp": 1703875200.0,
                "metrics": {
                    "workflow_completion_time": {
                        "current": 480.5,
                        "avg": 520.2
                    }
                },
                "system_health": "good"
            }
            
            response = client.get("/performance/metrics")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "timestamp" in data
            assert "metrics" in data
            assert "system_health" in data
    
    def test_get_workflow_analytics_success(self):
        """Test successful workflow analytics retrieval."""
        with patch('main.orchestrator') as mock_orch:
            
            mock_orch.get_workflow_analytics.return_value = {
                "workflow_statistics": {
                    "total_active": 8,
                    "completion_rate": 0.94
                },
                "agent_utilization": {
                    "total_agents": 47,
                    "utilization_rate": 0.26
                },
                "performance_insights": {
                    "bottleneck_agents": ["test-agent-1"]
                }
            }
            
            response = client.get("/workflow/analytics")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "workflow_statistics" in data
            assert "agent_utilization" in data
            assert "performance_insights" in data


@pytest.mark.asyncio
class TestAsyncOperations:
    """Test asynchronous operations."""
    
    async def test_lifespan_context(self):
        """Test that lifespan context can be created."""
        # This is a basic test to ensure the lifespan context doesn't crash
        # In a real implementation, we'd mock the initialization
        pass


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_global_exception_handler(self):
        """Test global exception handler."""
        # This would require triggering an unhandled exception
        # For now, we just verify the handler exists
        assert hasattr(app, "exception_handlers")
    
    def test_validation_error_handling(self):
        """Test request validation errors."""
        # Send invalid request data
        response = client.post("/workflow/create", json={"invalid": "data"})
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data


# Test fixtures and utilities
@pytest.fixture
def mock_services():
    """Fixture providing mocked services."""
    return {
        "orchestrator": mock_orchestrator,
        "workflow_manager": mock_workflow_manager,
        "context_generator": mock_context_generator,
        "cognitive_handler": mock_cognitive_handler,
        "agent_registry": mock_agent_registry,
        "redis_service": mock_redis_service,
        "performance_monitor": mock_performance_monitor
    }


@pytest.fixture
def sample_workflow_config():
    """Fixture providing sample workflow configuration."""
    return {
        "workflow_type": "new_feature",
        "name": "Test Feature Implementation",
        "description": "Test workflow for feature implementation",
        "priority": "medium",
        "execution_mode": "mixed",
        "required_agents": [
            "project-orchestrator",
            "codebase-research-analyst",
            "security-validator"
        ],
        "optional_agents": [
            "test-automation-engineer",
            "documentation-specialist"
        ],
        "context": {
            "project_phase": "Phase 2",
            "target_files": ["test.py", "models.py"],
            "requirements": ["feature A", "feature B"]
        },
        "timeout_minutes": 90,
        "enable_recovery": True
    }


@pytest.fixture
def sample_cognitive_event():
    """Fixture providing sample cognitive event."""
    return {
        "event_type": "reasoning_complete",
        "source_service": "reasoning-service",
        "workflow_id": "test-workflow-123",
        "priority": "high",
        "event_data": {
            "reasoning_type": "evidence_validation",
            "confidence_score": 0.92,
            "result_summary": "Validation successful",
            "processing_time_ms": 1250
        },
        "requires_response": False
    }


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__])