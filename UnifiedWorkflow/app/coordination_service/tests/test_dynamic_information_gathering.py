"""Comprehensive test suite for dynamic information gathering system.

This test suite validates the complete STREAM 6 implementation including:
- Dynamic agent request protocols
- Information gap detection
- Agent spawning and runtime creation
- Context integration and result merging
"""

import asyncio
import pytest
import time
import uuid
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Import the components we're testing
from services.dynamic_request_handler import (
    DynamicRequestHandler,
    InformationGapDetector,
    AgentSelector,
    RequestType,
    RequestUrgency,
    RequestStatus,
    DynamicAgentRequest,
    InformationGap
)
from services.context_integration_service import (
    ContextIntegrationService,
    ContextAnalyzer,
    ContextIntegrator,
    IntegrationStrategy,
    IntegrationStatus,
    ContextIntegration
)


class TestInformationGapDetection:
    """Test suite for information gap detection capabilities."""
    
    @pytest.fixture
    async def gap_detector(self):
        """Create a gap detector for testing."""
        detector = InformationGapDetector()
        return detector
    
    @pytest.mark.asyncio
    async def test_pattern_based_gap_detection(self, gap_detector):
        """Test pattern-based gap detection."""
        execution_log = [
            "Starting analysis of the authentication system",
            "Need information about the current OAuth configuration",
            "Security validation needed for proposed changes",
            "Missing context for database schema design",
            "Performance implications are unclear"
        ]
        
        gaps = await gap_detector.detect_gaps(
            agent_name="test-agent",
            task_context={"workflow_id": "test-workflow"},
            execution_log=execution_log,
            current_findings={}
        )
        
        assert len(gaps) >= 4  # Should detect multiple gaps
        
        # Check for specific gap types
        gap_types = [gap.gap_type for gap in gaps]
        assert "missing_dependency" in gap_types
        assert "security_concern" in gap_types
        assert "missing_context" in gap_types
        assert "performance_impact" in gap_types
    
    @pytest.mark.asyncio
    async def test_context_gap_detection(self, gap_detector):
        """Test context-based gap detection."""
        task_context = {
            "system_architecture": "microservices",
            # Missing other required contexts
        }
        current_findings = {
            "api_endpoints": ["auth", "users", "data"]
        }
        
        gaps = await gap_detector._detect_context_gaps(task_context, current_findings)
        
        # Should detect missing required contexts
        assert len(gaps) >= 3
        
        missing_contexts = [gap.description for gap in gaps if "Missing" in gap.description]
        assert any("dependencies" in desc for desc in missing_contexts)
        assert any("security_requirements" in desc for desc in missing_contexts)
        assert any("performance_targets" in desc for desc in missing_contexts)
    
    @pytest.mark.asyncio
    async def test_gap_prioritization(self, gap_detector):
        """Test gap prioritization based on severity."""
        execution_log = [
            "Critical security vulnerability detected",
            "Need additional context for minor feature",
            "High priority performance bottleneck found"
        ]
        
        gaps = await gap_detector.detect_gaps(
            agent_name="test-agent", 
            task_context={},
            execution_log=execution_log,
            current_findings={}
        )
        
        # Sort by priority to verify ordering
        gaps.sort(key=lambda g: g.priority_score, reverse=True)
        
        # Critical/high priority gaps should be first
        assert gaps[0].priority_score > gaps[-1].priority_score


class TestAgentSelection:
    """Test suite for intelligent agent selection."""
    
    @pytest.fixture
    def mock_agent_registry(self):
        """Create mock agent registry."""
        registry = Mock()
        registry.get_agent_info = AsyncMock()
        registry.is_agent_available = AsyncMock(return_value=True)
        return registry
    
    @pytest.fixture
    async def agent_selector(self, mock_agent_registry):
        """Create agent selector for testing."""
        selector = AgentSelector(mock_agent_registry)
        return selector
    
    @pytest.mark.asyncio
    async def test_agent_selection_by_request_type(self, agent_selector, mock_agent_registry):
        """Test agent selection based on request type."""
        # Test research request
        request = DynamicAgentRequest(
            request_id="test-request",
            requesting_agent="test-agent",
            workflow_id="test-workflow",
            request_type=RequestType.RESEARCH,
            urgency=RequestUrgency.MEDIUM,
            description="Need research on authentication systems"
        )
        
        selected_agent = await agent_selector.select_agent(request)
        
        # Should select from research-capable agents
        assert selected_agent in ["codebase-research-analyst", "smart-search-agent", "dependency-analyzer"]
    
    @pytest.mark.asyncio
    async def test_agent_selection_with_specific_expertise(self, agent_selector, mock_agent_registry):
        """Test agent selection with specific expertise requirements."""
        # Mock agent info with capabilities
        mock_agent_registry.get_agent_info.return_value = {
            "capabilities": ["security", "authentication", "validation"]
        }
        
        request = DynamicAgentRequest(
            request_id="test-request",
            requesting_agent="test-agent", 
            workflow_id="test-workflow",
            request_type=RequestType.SECURITY_AUDIT,
            urgency=RequestUrgency.HIGH,
            description="Security audit needed",
            specific_expertise_needed=["authentication", "security"]
        )
        
        selected_agent = await agent_selector.select_agent(request)
        
        # Should have called get_agent_info to check capabilities
        assert mock_agent_registry.get_agent_info.called
        assert selected_agent is not None
    
    @pytest.mark.asyncio
    async def test_agent_unavailable_handling(self, agent_selector, mock_agent_registry):
        """Test handling when no agents are available."""
        mock_agent_registry.is_agent_available.return_value = False
        
        request = DynamicAgentRequest(
            request_id="test-request",
            requesting_agent="test-agent",
            workflow_id="test-workflow", 
            request_type=RequestType.VALIDATION,
            urgency=RequestUrgency.CRITICAL,
            description="Urgent validation needed"
        )
        
        selected_agent = await agent_selector.select_agent(request)
        
        # Should return None when no agents available
        assert selected_agent is None


class TestDynamicRequestHandler:
    """Test suite for dynamic request handler."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        services = {
            'agent_registry': Mock(),
            'context_generator': Mock(),
            'orchestrator': Mock(),
            'workflow_manager': Mock(),
            'redis_service': Mock()
        }
        
        # Configure mocks
        services['agent_registry'].is_agent_available = AsyncMock(return_value=True)
        services['agent_registry'].get_agent_info = AsyncMock(return_value={"capabilities": ["test"]})
        services['context_generator'].generate_context_package = AsyncMock(return_value="context-package-123")
        services['orchestrator'].create_workflow = AsyncMock(return_value={"workflow_id": "spawned-workflow-123"})
        services['workflow_manager'].get_workflow_status = AsyncMock(return_value={"status": "completed", "results": {}})
        services['workflow_manager'].get_workflow_context = AsyncMock(return_value={"test": "context"})
        
        return services
    
    @pytest.fixture
    async def request_handler(self, mock_services):
        """Create request handler for testing."""
        handler = DynamicRequestHandler(**mock_services)
        await handler.initialize()
        return handler
    
    @pytest.mark.asyncio
    async def test_create_agent_request(self, request_handler):
        """Test creating a dynamic agent request."""
        request_id = await request_handler.create_agent_request(
            requesting_agent="test-agent",
            workflow_id="test-workflow",
            request_type=RequestType.RESEARCH,
            description="Need information about system architecture",
            urgency=RequestUrgency.HIGH
        )
        
        assert request_id is not None
        assert request_id in request_handler.active_requests
        
        request = request_handler.active_requests[request_id]
        assert request.requesting_agent == "test-agent"
        assert request.workflow_id == "test-workflow"
        assert request.request_type == RequestType.RESEARCH
        assert request.urgency == RequestUrgency.HIGH
        assert request.status == RequestStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_auto_create_requests_for_gaps(self, request_handler):
        """Test automatic request creation for information gaps."""
        gaps = [
            InformationGap(
                gap_id="gap-1",
                gap_type="security_concern",
                description="Security validation needed",
                severity="high",
                detected_by="test-agent",
                suggested_expertise=["security-validator"]
            ),
            InformationGap(
                gap_id="gap-2", 
                gap_type="missing_dependency",
                description="Dependency analysis required",
                severity="medium",
                detected_by="test-agent",
                suggested_expertise=["dependency-analyzer"]
            )
        ]
        
        request_ids = await request_handler.auto_create_requests_for_gaps(
            requesting_agent="test-agent",
            workflow_id="test-workflow",
            information_gaps=gaps
        )
        
        assert len(request_ids) == 2
        
        # Verify requests were created with appropriate types
        for request_id in request_ids:
            request = request_handler.active_requests[request_id]
            assert request.requesting_agent == "test-agent"
            assert request.workflow_id == "test-workflow"
            assert len(request.information_gaps) == 1  # Each request has one gap
    
    @pytest.mark.asyncio
    async def test_request_processing_lifecycle(self, request_handler, mock_services):
        """Test complete request processing lifecycle."""
        # Create request
        request_id = await request_handler.create_agent_request(
            requesting_agent="test-agent",
            workflow_id="test-workflow",
            request_type=RequestType.ANALYSIS,
            description="Performance analysis needed"
        )
        
        request = request_handler.active_requests[request_id]
        
        # Simulate request processing
        await request_handler._process_request(request)
        
        # Verify progression through states
        assert request.status == RequestStatus.EXECUTING
        assert request.assigned_agent is not None
        assert request.context_package_id is not None
        assert request.spawned_workflow_id is not None
        
        # Verify services were called
        assert mock_services['context_generator'].generate_context_package.called
        assert mock_services['orchestrator'].create_workflow.called
    
    @pytest.mark.asyncio
    async def test_request_timeout_handling(self, request_handler):
        """Test request timeout handling."""
        # Create request with short timeout
        request_id = await request_handler.create_agent_request(
            requesting_agent="test-agent",
            workflow_id="test-workflow",
            request_type=RequestType.VALIDATION,
            description="Urgent validation",
            urgency=RequestUrgency.CRITICAL
        )
        
        request = request_handler.active_requests[request_id]
        request.timeout_minutes = 0  # Immediate timeout for testing
        request.created_at = time.time() - 10  # Set to past time
        
        # Process timeouts
        await request_handler._handle_timeouts()
        
        # Verify request was timed out
        assert request.status == RequestStatus.FAILED
        assert "timed out" in request.error_message.lower()


class TestContextIntegration:
    """Test suite for context integration service."""
    
    @pytest.fixture
    async def context_analyzer(self):
        """Create context analyzer for testing."""
        analyzer = ContextAnalyzer()
        return analyzer
    
    @pytest.fixture
    async def context_integrator(self):
        """Create context integrator for testing."""
        integrator = ContextIntegrator()
        return integrator
    
    @pytest.mark.asyncio
    async def test_context_compatibility_analysis(self, context_analyzer):
        """Test context compatibility analysis."""
        original_context = {
            "authentication": "OAuth2",
            "database": "PostgreSQL",
            "api_version": "v1",
            "security_level": "high"
        }
        
        new_findings = {
            "authentication": "OAuth2 with PKCE extension",  # Supplement
            "caching": "Redis",  # New information
            "api_version": "v2",  # Potential conflict
            "security_audit": "completed"  # New information
        }
        
        analysis = await context_analyzer.analyze_context_compatibility(
            original_context, new_findings
        )
        
        assert analysis["compatibility_score"] > 0
        assert len(analysis["supplements"]) >= 1  # Should detect supplements
        assert len(analysis["conflicts"]) >= 0  # May detect conflicts
        assert analysis["recommended_strategy"] in [strategy.value for strategy in IntegrationStrategy]
    
    @pytest.mark.asyncio
    async def test_merge_integration_strategy(self, context_integrator):
        """Test merge integration strategy."""
        original = {
            "service_a": {"status": "running", "port": 8080},
            "service_b": {"status": "stopped"},
            "global_config": {"env": "production"}
        }
        
        new_findings = {
            "service_a": {"port": 8080, "health": "ok"},  # Supplement
            "service_c": {"status": "running", "port": 9090},  # New
            "global_config": {"debug": False}  # Addition
        }
        
        analysis = {"conflicts": [], "supplements": [], "overlaps": []}
        
        integrated, summary = await context_integrator._merge_strategy(
            original, new_findings, analysis
        )
        
        # Verify merge results
        assert "service_a" in integrated
        assert "service_b" in integrated
        assert "service_c" in integrated
        assert integrated["service_a"]["health"] == "ok"  # New field added
        assert integrated["global_config"]["env"] == "production"  # Original preserved
        assert integrated["global_config"]["debug"] is False  # New field added
        
        assert summary["strategy_used"] == "merge"
        assert len(summary["changes_made"]["added"]) >= 1
    
    @pytest.mark.asyncio
    async def test_selective_integration_strategy(self, context_integrator):
        """Test selective integration with conflict avoidance."""
        original = {
            "database_url": "postgres://localhost:5432/prod",
            "cache_enabled": True,
            "api_timeout": 30
        }
        
        new_findings = {
            "database_url": "postgres://localhost:5432/dev",  # Conflict
            "cache_enabled": False,  # Conflict
            "monitoring_enabled": True,  # Safe addition
            "rate_limiting": {"enabled": True, "requests_per_minute": 1000}  # Safe addition
        }
        
        analysis = {
            "conflicts": [
                {"field": "database_url", "conflict_type": "direct_contradiction"},
                {"field": "cache_enabled", "conflict_type": "direct_contradiction"}
            ],
            "supplements": [],
            "overlaps": []
        }
        
        integrated, summary = await context_integrator._selective_strategy(
            original, new_findings, analysis
        )
        
        # Verify selective integration
        assert integrated["database_url"] == "postgres://localhost:5432/prod"  # Original preserved
        assert integrated["cache_enabled"] is True  # Original preserved
        assert integrated["monitoring_enabled"] is True  # New field added
        assert "rate_limiting" in integrated  # New field added
        
        # Conflicts should be stored for review
        assert "_conflict_review" in integrated
        assert "database_url" in integrated["_conflict_review"]
        
        assert summary["strategy_used"] == "selective"
        assert len(summary["changes_made"]["avoided_conflicts"]) == 2


class TestContextIntegrationService:
    """Test suite for complete context integration service."""
    
    @pytest.fixture
    def mock_context_generator(self):
        """Create mock context generator."""
        generator = Mock()
        generator.generate_context_package = AsyncMock(return_value="updated-context-123")
        return generator
    
    @pytest.fixture
    async def integration_service(self, mock_context_generator):
        """Create context integration service for testing."""
        service = ContextIntegrationService(
            context_generator=mock_context_generator,
            redis_service=Mock()
        )
        await service.initialize()
        return service
    
    @pytest.mark.asyncio
    async def test_create_integration(self, integration_service):
        """Test creating a context integration operation."""
        original_context = {
            "current_status": "authentication system analysis",
            "findings": ["OAuth2 implemented", "Session management present"]
        }
        
        new_findings = {
            "security_audit": "completed",
            "vulnerabilities": [],
            "recommendations": ["Enable 2FA", "Update session timeout"]
        }
        
        integration_id = await integration_service.create_integration(
            requesting_agent="security-validator",
            workflow_id="security-workflow-123",
            request_id="request-456",
            original_context=original_context,
            new_findings=new_findings,
            integration_strategy="merge"
        )
        
        assert integration_id is not None
        assert integration_id in integration_service.active_integrations
        
        # Allow processing to complete
        await asyncio.sleep(0.1)
        
        integration = integration_service.active_integrations[integration_id]
        assert integration.status == IntegrationStatus.COMPLETED
        assert integration.integrated_context is not None
        assert integration.confidence_improvement >= 0.0
    
    @pytest.mark.asyncio
    async def test_integration_status_tracking(self, integration_service):
        """Test integration status tracking."""
        integration_id = await integration_service.create_integration(
            requesting_agent="test-agent",
            workflow_id="test-workflow",
            request_id="test-request",
            original_context={"test": "context"},
            new_findings={"new": "findings"}
        )
        
        # Check status
        status = await integration_service.get_integration_status(integration_id)
        
        assert status is not None
        assert status["integration_id"] == integration_id
        assert status["requesting_agent"] == "test-agent"
        assert status["workflow_id"] == "test-workflow"
        assert "status" in status
        assert "is_complete" in status
    
    @pytest.mark.asyncio
    async def test_integration_results_retrieval(self, integration_service):
        """Test retrieving integration results."""
        integration_id = await integration_service.create_integration(
            requesting_agent="test-agent",
            workflow_id="test-workflow", 
            request_id="test-request",
            original_context={"original": "data"},
            new_findings={"supplemental": "data"}
        )
        
        # Allow processing to complete
        await asyncio.sleep(0.1)
        
        results = await integration_service.get_integration_result(integration_id)
        
        assert results is not None
        assert results["integration_id"] == integration_id
        assert results["status"] == IntegrationStatus.COMPLETED
        assert "integrated_context" in results
        assert "integration_summary" in results
        assert "confidence_improvement" in results


class TestEndToEndDynamicInformationGathering:
    """End-to-end tests for the complete dynamic information gathering system."""
    
    @pytest.fixture
    async def complete_system(self):
        """Set up complete system for end-to-end testing."""
        # Mock all external dependencies
        mock_services = {
            'agent_registry': Mock(),
            'context_generator': Mock(),
            'orchestrator': Mock(),
            'workflow_manager': Mock(),
            'redis_service': Mock()
        }
        
        # Configure mocks for realistic behavior
        mock_services['agent_registry'].is_agent_available = AsyncMock(return_value=True)
        mock_services['agent_registry'].get_agent_info = AsyncMock(return_value={
            "capabilities": ["security", "analysis", "validation"]
        })
        mock_services['context_generator'].generate_context_package = AsyncMock(
            return_value="context-package-123"
        )
        mock_services['orchestrator'].create_workflow = AsyncMock(return_value={
            "workflow_id": "spawned-workflow-123"
        })
        mock_services['workflow_manager'].get_workflow_status = AsyncMock(return_value={
            "status": "completed",
            "results": {
                "security-validator": {
                    "analysis": {"security_score": 85},
                    "findings": ["2FA not enabled", "Session timeout too long"],
                    "recommendations": ["Enable 2FA", "Reduce session timeout"],
                    "confidence": {"overall": 0.9}
                }
            }
        })
        mock_services['workflow_manager'].get_workflow_context = AsyncMock(return_value={
            "current_analysis": "authentication system"
        })
        
        # Initialize services
        request_handler = DynamicRequestHandler(**mock_services)
        await request_handler.initialize()
        
        context_integration = ContextIntegrationService(
            context_generator=mock_services['context_generator'],
            redis_service=mock_services['redis_service']
        )
        await context_integration.initialize()
        
        return {
            'request_handler': request_handler,
            'context_integration': context_integration,
            'mocks': mock_services
        }
    
    @pytest.mark.asyncio
    async def test_complete_dynamic_information_flow(self, complete_system):
        """Test complete flow from gap detection to context integration."""
        request_handler = complete_system['request_handler']
        context_integration = complete_system['context_integration']
        
        # Step 1: Detect information gaps
        execution_log = [
            "Analyzing authentication system",
            "Need security validation for proposed changes",
            "Performance implications unknown"
        ]
        
        gaps = await request_handler.detect_information_gaps(
            agent_name="backend-gateway-expert",
            task_context={"workflow_id": "main-workflow-123"},
            execution_log=execution_log,
            current_findings={"auth_method": "OAuth2"}
        )
        
        assert len(gaps) > 0
        
        # Step 2: Auto-create requests for critical gaps
        critical_gaps = [gap for gap in gaps if gap.severity in ["high", "critical"]]
        if critical_gaps:
            request_ids = await request_handler.auto_create_requests_for_gaps(
                requesting_agent="backend-gateway-expert",
                workflow_id="main-workflow-123",
                information_gaps=critical_gaps
            )
            
            assert len(request_ids) > 0
            
            # Step 3: Process requests (simulate completion)
            for request_id in request_ids:
                request = request_handler.active_requests[request_id]
                await request_handler._process_request(request)
                
                # Simulate workflow completion
                request.status = RequestStatus.EXECUTING
                await request_handler._check_completed_requests()
            
            # Step 4: Integrate results back to requesting agent
            if request_ids:
                first_request = request_handler.active_requests[request_ids[0]]
                if first_request.response_data:
                    original_context = {
                        "auth_method": "OAuth2",
                        "current_analysis": "authentication system"
                    }
                    
                    integration_id = await context_integration.create_integration(
                        requesting_agent="backend-gateway-expert",
                        workflow_id="main-workflow-123",
                        request_id=request_ids[0],
                        original_context=original_context,
                        new_findings=first_request.response_data
                    )
                    
                    # Allow integration to complete
                    await asyncio.sleep(0.1)
                    
                    results = await context_integration.get_integration_result(integration_id)
                    
                    assert results is not None
                    assert results["status"] == IntegrationStatus.COMPLETED
                    assert "integrated_context" in results
                    assert results["confidence_improvement"] > 0
    
    @pytest.mark.asyncio
    async def test_system_performance_metrics(self, complete_system):
        """Test system performance metrics collection."""
        request_handler = complete_system['request_handler']
        context_integration = complete_system['context_integration']
        
        # Create and process several requests
        for i in range(3):
            request_id = await request_handler.create_agent_request(
                requesting_agent=f"test-agent-{i}",
                workflow_id=f"test-workflow-{i}",
                request_type=RequestType.ANALYSIS,
                description=f"Test analysis {i}"
            )
            
            # Simulate completion
            request = request_handler.active_requests[request_id]
            request.status = RequestStatus.COMPLETED
            request.completed_at = time.time()
            request.confidence_score = 0.8 + (i * 0.1)
        
        # Create several integrations
        for i in range(2):
            integration_id = await context_integration.create_integration(
                requesting_agent=f"test-agent-{i}",
                workflow_id=f"test-workflow-{i}",
                request_id=f"test-request-{i}",
                original_context={"test": f"original-{i}"},
                new_findings={"test": f"new-{i}"}
            )
        
        # Get metrics
        request_metrics = await request_handler.get_metrics()
        integration_metrics = await context_integration.get_metrics()
        
        # Verify metrics
        assert request_metrics["total_requests"] >= 3
        assert request_metrics["completed_requests"] >= 3
        assert request_metrics["success_rate"] > 0
        
        assert integration_metrics["total_integrations"] >= 2
        assert integration_metrics["successful_integrations"] >= 0


if __name__ == "__main__":
    """Run tests directly for development."""
    pytest.main([__file__, "-v"])