"""Dynamic Information Gathering System Demonstration.

This script demonstrates the complete STREAM 6 implementation showing how agents
can dynamically request additional information during execution and seamlessly
integrate findings back into their context.

Usage:
    python dynamic_information_gathering_demo.py
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockAgentRegistry:
    """Mock agent registry for demonstration."""
    
    def __init__(self):
        self.agents = {
            "backend-gateway-expert": {
                "capabilities": ["api_design", "authentication", "microservices"],
                "available": True
            },
            "security-validator": {
                "capabilities": ["security", "authentication", "vulnerability_assessment"],
                "available": True
            },
            "dependency-analyzer": {
                "capabilities": ["dependency_analysis", "package_management", "security_scanning"],
                "available": True
            },
            "performance-profiler": {
                "capabilities": ["performance", "optimization", "monitoring"],
                "available": True
            }
        }
    
    async def is_agent_available(self, agent_name: str) -> bool:
        return self.agents.get(agent_name, {}).get("available", False)
    
    async def get_agent_info(self, agent_name: str) -> Dict[str, Any]:
        return self.agents.get(agent_name, {})


class MockContextGenerator:
    """Mock context generator for demonstration."""
    
    async def generate_context_package(self, agent_name: str, workflow_id: str, 
                                     task_context: Dict[str, Any], 
                                     requirements: Dict[str, Any]) -> str:
        package_id = f"context-{agent_name}-{int(time.time())}"
        logger.info(f"Generated context package {package_id} for {agent_name}")
        return package_id


class MockOrchestrator:
    """Mock orchestrator for demonstration."""
    
    async def create_workflow(self, workflow_id: str, workflow_config: Dict[str, Any], 
                            background_tasks=None) -> Dict[str, Any]:
        logger.info(f"Created spawned workflow {workflow_id} for dynamic request")
        return {"workflow_id": workflow_id}


class MockWorkflowManager:
    """Mock workflow manager for demonstration."""
    
    def __init__(self):
        self.workflows = {}
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        # Simulate workflow completion with realistic results
        return {
            "status": "completed",
            "results": {
                "security-validator": {
                    "analysis": {
                        "security_score": 78,
                        "vulnerabilities_found": 2,
                        "risk_level": "medium"
                    },
                    "findings": [
                        "JWT tokens not properly validated",
                        "Session timeout too long (24 hours)",
                        "Rate limiting not implemented"
                    ],
                    "recommendations": [
                        "Implement proper JWT signature validation",
                        "Reduce session timeout to 2 hours",
                        "Add rate limiting middleware"
                    ],
                    "confidence": {"overall": 0.9}
                },
                "dependency-analyzer": {
                    "analysis": {
                        "total_dependencies": 45,
                        "outdated_packages": 7,
                        "security_vulnerabilities": 2
                    },
                    "findings": [
                        "Express.js version 4.16.4 has known vulnerabilities",
                        "jsonwebtoken package is 2 major versions behind",
                        "Several dev dependencies are outdated"
                    ],
                    "recommendations": [
                        "Update Express.js to latest stable version",
                        "Update jsonwebtoken to version 9.x",
                        "Run npm audit fix for automated updates"
                    ],
                    "confidence": {"overall": 0.95}
                },
                "performance-profiler": {
                    "analysis": {
                        "response_time_avg": 150,
                        "memory_usage": "85MB",
                        "cpu_usage": "12%"
                    },
                    "findings": [
                        "Database queries not optimized",
                        "No caching layer implemented",
                        "Large payload responses"
                    ],
                    "recommendations": [
                        "Add database query optimization",
                        "Implement Redis caching",
                        "Add response compression"
                    ],
                    "confidence": {"overall": 0.85}
                }
            }
        }
    
    async def get_workflow_context(self, workflow_id: str) -> Dict[str, Any]:
        return {
            "current_analysis": "API gateway authentication system",
            "technology_stack": "Node.js, Express, JWT, PostgreSQL"
        }


async def demonstrate_information_gap_detection():
    """Demonstrate information gap detection capabilities."""
    print("\n" + "="*60)
    print("DEMONSTRATION: Information Gap Detection")
    print("="*60)
    
    # Import after path setup
    from services.dynamic_request_handler import InformationGapDetector
    
    detector = InformationGapDetector()
    
    # Simulate an agent's execution log
    execution_log = [
        "Starting analysis of API gateway authentication system",
        "Found JWT implementation in auth middleware",
        "Need security validation of current JWT implementation", 
        "Performance implications of authentication flow unclear",
        "Missing context for dependency security analysis",
        "Requires domain expert knowledge of OAuth2 best practices"
    ]
    
    task_context = {
        "workflow_id": "api-gateway-analysis-123",
        "system_architecture": "microservices",
        "technology_stack": "Node.js, Express, JWT"
        # Missing: dependencies, security_requirements, performance_targets
    }
    
    current_findings = {
        "authentication_method": "JWT",
        "middleware_location": "/src/auth/middleware.js",
        "jwt_library": "jsonwebtoken"
    }
    
    print(f"Agent: backend-gateway-expert")
    print(f"Task Context: {json.dumps(task_context, indent=2)}")
    print(f"Execution Log: {len(execution_log)} entries")
    print("\nDetecting information gaps...")
    
    gaps = await detector.detect_gaps(
        agent_name="backend-gateway-expert",
        task_context=task_context,
        execution_log=execution_log,
        current_findings=current_findings
    )
    
    print(f"\nDetected {len(gaps)} information gaps:")
    for i, gap in enumerate(gaps, 1):
        print(f"\n{i}. Gap Type: {gap.gap_type}")
        print(f"   Severity: {gap.severity}")
        print(f"   Description: {gap.description}")
        print(f"   Priority Score: {gap.priority_score}")
        print(f"   Suggested Expertise: {gap.suggested_expertise}")
    
    return gaps


async def demonstrate_dynamic_agent_spawning(gaps: List):
    """Demonstrate dynamic agent spawning for information gaps."""
    print("\n" + "="*60)
    print("DEMONSTRATION: Dynamic Agent Spawning")
    print("="*60)
    
    # Import services
    from services.dynamic_request_handler import DynamicRequestHandler
    
    # Create mock services
    mock_services = {
        'agent_registry': MockAgentRegistry(),
        'context_generator': MockContextGenerator(),
        'orchestrator': MockOrchestrator(),
        'workflow_manager': MockWorkflowManager(),
        'redis_service': None
    }
    
    # Initialize request handler
    request_handler = DynamicRequestHandler(**mock_services)
    await request_handler.initialize()
    
    print("Initialized Dynamic Request Handler")
    print(f"Available agents: {list(mock_services['agent_registry'].agents.keys())}")
    
    # Auto-create requests for high-priority gaps
    high_priority_gaps = [gap for gap in gaps if gap.severity in ["high", "critical"]]
    
    print(f"\nCreating dynamic requests for {len(high_priority_gaps)} high-priority gaps...")
    
    request_ids = await request_handler.auto_create_requests_for_gaps(
        requesting_agent="backend-gateway-expert",
        workflow_id="api-gateway-analysis-123",
        information_gaps=high_priority_gaps
    )
    
    print(f"Created {len(request_ids)} dynamic agent requests:")
    
    for request_id in request_ids:
        request = request_handler.active_requests[request_id]
        print(f"\nRequest ID: {request_id}")
        print(f"  Type: {request.request_type}")
        print(f"  Urgency: {request.urgency}")
        print(f"  Description: {request.description}")
        print(f"  Status: {request.status}")
    
    # Simulate request processing
    print("\nProcessing dynamic requests...")
    
    for request_id in request_ids:
        request = request_handler.active_requests[request_id]
        print(f"\nProcessing request {request_id}...")
        
        # Process the request
        await request_handler._process_request(request)
        
        print(f"  Assigned Agent: {request.assigned_agent}")
        print(f"  Context Package: {request.context_package_id}")
        print(f"  Spawned Workflow: {request.spawned_workflow_id}")
        print(f"  Status: {request.status}")
        
        # Simulate workflow completion
        if request.spawned_workflow_id:
            print(f"  Simulating completion of spawned workflow...")
            await request_handler._check_completed_requests()
            
            if request.response_data:
                print(f"  ✓ Request completed successfully")
                print(f"  Confidence Score: {request.confidence_score}")
    
    return request_handler, request_ids


async def demonstrate_context_integration(request_handler, request_ids: List[str]):
    """Demonstrate context integration of dynamic findings."""
    print("\n" + "="*60)
    print("DEMONSTRATION: Context Integration")
    print("="*60)
    
    from services.context_integration_service import ContextIntegrationService
    
    # Initialize context integration service
    context_integration = ContextIntegrationService(
        context_generator=MockContextGenerator(),
        redis_service=None
    )
    await context_integration.initialize()
    
    # Original agent context
    original_context = {
        "authentication_method": "JWT",
        "middleware_location": "/src/auth/middleware.js",
        "jwt_library": "jsonwebtoken",
        "analysis_status": "preliminary_review_complete",
        "confidence_level": 0.6
    }
    
    print("Original Agent Context:")
    print(json.dumps(original_context, indent=2))
    
    # Integrate findings from each completed request
    integration_results = []
    
    for i, request_id in enumerate(request_ids):
        request = request_handler.active_requests[request_id]
        
        if request.response_data:
            print(f"\nIntegrating findings from {request.assigned_agent}...")
            
            integration_id = await context_integration.create_integration(
                requesting_agent="backend-gateway-expert",
                workflow_id="api-gateway-analysis-123",
                request_id=request_id,
                original_context=original_context,
                new_findings=request.response_data,
                integration_strategy="merge"
            )
            
            # Allow processing to complete
            await asyncio.sleep(0.2)
            
            results = await context_integration.get_integration_result(integration_id)
            
            if results:
                integration_results.append(results)
                
                print(f"  ✓ Integration completed")
                print(f"  Strategy Used: {results['integration_summary'].get('strategy_used', 'N/A')}")
                print(f"  Confidence Improvement: {results['confidence_improvement']:.2f}")
                print(f"  Fields Added: {len(results['integration_summary'].get('changes_made', {}).get('added', []))}")
                print(f"  Fields Updated: {len(results['integration_summary'].get('changes_made', {}).get('updated', []))}")
                
                # Update original context for next integration
                original_context = results["integrated_context"]
    
    # Show final integrated context
    print(f"\nFinal Integrated Context:")
    print(json.dumps(original_context, indent=2))
    
    return integration_results


async def demonstrate_system_metrics(request_handler, context_integration):
    """Demonstrate system metrics and performance monitoring."""
    print("\n" + "="*60)
    print("DEMONSTRATION: System Metrics")
    print("="*60)
    
    # Get request handler metrics
    request_metrics = await request_handler.get_metrics()
    print("Dynamic Request Handler Metrics:")
    print(f"  Total Requests: {request_metrics['total_requests']}")
    print(f"  Completed Requests: {request_metrics['completed_requests']}")
    print(f"  Success Rate: {request_metrics['success_rate']:.2%}")
    print(f"  Average Response Time: {request_metrics['avg_response_time']:.2f}s")
    print(f"  Active Requests: {request_metrics['active_requests']}")
    
    # Get context integration metrics
    integration_metrics = await context_integration.get_metrics()
    print("\nContext Integration Service Metrics:")
    print(f"  Total Integrations: {integration_metrics['total_integrations']}")
    print(f"  Successful Integrations: {integration_metrics['successful_integrations']}")
    print(f"  Success Rate: {integration_metrics['success_rate']:.2%}")
    print(f"  Average Integration Time: {integration_metrics['avg_integration_time']:.2f}s")
    print(f"  Average Confidence Improvement: {integration_metrics['avg_confidence_improvement']:.2f}")


async def demonstrate_api_endpoints():
    """Demonstrate API endpoint usage."""
    print("\n" + "="*60)
    print("DEMONSTRATION: API Endpoint Usage")
    print("="*60)
    
    print("The following REST API endpoints are available for dynamic information gathering:")
    print()
    
    endpoints = [
        ("POST", "/dynamic-requests/create", "Create a new dynamic agent request"),
        ("POST", "/dynamic-requests/detect-gaps", "Detect information gaps and auto-create requests"),
        ("GET", "/dynamic-requests/{request_id}/status", "Get request status"),
        ("GET", "/dynamic-requests/{request_id}/results", "Get request results"),
        ("GET", "/dynamic-requests/metrics", "Get system metrics"),
        ("POST", "/context-integration/create", "Create context integration"),
        ("GET", "/context-integration/{integration_id}/status", "Get integration status"),
        ("GET", "/context-integration/{integration_id}/results", "Get integration results"),
        ("GET", "/context-integration/metrics", "Get integration metrics")
    ]
    
    for method, endpoint, description in endpoints:
        print(f"{method:6} {endpoint:45} - {description}")
    
    print("\nExample API Usage:")
    print("""
# Create a dynamic request
curl -X POST http://localhost:8004/dynamic-requests/create \\
  -H "Content-Type: application/json" \\
  -d '{
    "requesting_agent": "backend-gateway-expert",
    "workflow_id": "analysis-123",
    "request_type": "security_audit",
    "urgency": "high",
    "description": "Need security validation of JWT implementation"
  }'

# Detect information gaps
curl -X POST http://localhost:8004/dynamic-requests/detect-gaps \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent_name": "backend-gateway-expert",
    "task_context": {"workflow_id": "analysis-123"},
    "execution_log": ["Need security validation", "Performance unclear"],
    "current_findings": {"auth_method": "JWT"}
  }'

# Create context integration
curl -X POST http://localhost:8004/context-integration/create \\
  -H "Content-Type: application/json" \\
  -d '{
    "requesting_agent": "backend-gateway-expert",
    "workflow_id": "analysis-123",
    "request_id": "req-456",
    "original_context": {"auth": "JWT"},
    "new_findings": {"security_score": 85},
    "integration_strategy": "merge"
  }'
""")


async def main():
    """Run the complete demonstration."""
    print("🚀 DYNAMIC INFORMATION GATHERING SYSTEM DEMONSTRATION")
    print("📡 STREAM 6: Intelligent Agent Request Protocols")
    print("🔄 Real-time Information Gap Detection & Context Integration")
    
    try:
        # Step 1: Demonstrate information gap detection
        gaps = await demonstrate_information_gap_detection()
        
        # Step 2: Demonstrate dynamic agent spawning
        request_handler, request_ids = await demonstrate_dynamic_agent_spawning(gaps)
        
        # Step 3: Demonstrate context integration
        integration_results = await demonstrate_context_integration(request_handler, request_ids)
        
        # Step 4: Show system metrics
        context_integration = None
        for result in integration_results:
            if hasattr(result, '__dict__'):
                context_integration = result
                break
        
        if not context_integration:
            from services.context_integration_service import ContextIntegrationService
            context_integration = ContextIntegrationService(
                context_generator=MockContextGenerator(),
                redis_service=None
            )
            await context_integration.initialize()
        
        await demonstrate_system_metrics(request_handler, context_integration)
        
        # Step 5: Show API endpoints
        await demonstrate_api_endpoints()
        
        print("\n" + "="*60)
        print("✅ DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*60)
        print()
        print("Key Features Demonstrated:")
        print("✓ ML-Enhanced Information Gap Detection")
        print("✓ Intelligent Agent Selection & Spawning")
        print("✓ Runtime Context Package Generation")
        print("✓ Automated Workflow Creation")
        print("✓ Seamless Context Integration")
        print("✓ Performance Metrics & Monitoring")
        print("✓ RESTful API Interface")
        print()
        print("The system successfully enables agents to dynamically request")
        print("additional information during execution, leading to more")
        print("comprehensive and accurate results through intelligent")
        print("orchestration and context integration.")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {str(e)}")
        raise


if __name__ == "__main__":
    # Add the services directory to Python path for imports
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    # Run the demonstration
    asyncio.run(main())