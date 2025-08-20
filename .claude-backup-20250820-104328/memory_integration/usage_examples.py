#!/usr/bin/env python3
"""
Memory Service Integration Usage Examples

Demonstrates how to use the memory service integration instead of creating
markdown files. These examples show the correct patterns for agents.

BEFORE (Anti-pattern - creates markdown files):
    Write("/path/analysis.md", analysis_content)
    Write("/path/validation_report.md", validation_results)
    Write("/path/security_findings.md", security_data)

AFTER (Correct pattern - uses memory service):
    await store_analysis("redis_connectivity", analysis_content, "security-validator")
    await store_validation_evidence("endpoint_validation", evidence_data, True)
    await store_security_analysis("auth_vulnerabilities", security_data, "high")
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List

# Import memory integration components
from . import (
    initialize_orchestration_wrapper,
    store_analysis,
    store_validation_evidence,
    store_security_analysis,
    store_infrastructure_findings,
    store_performance_metrics,
    store_error_pattern,
    search_knowledge,
    agent_memory,
    set_agent_context
)


async def example_security_validator_usage():
    """
    Example: Security validator agent using memory service instead of markdown files.
    
    BEFORE (creates markdown files):
        Write("/path/SECURITY_VALIDATION_EVIDENCE.md", security_report)
        Write("/path/VULNERABILITY_ANALYSIS.md", vuln_data)
    
    AFTER (uses memory service):
        Uses store_security_analysis() and store_validation_evidence()
    """
    
    # Set agent context for proper attribution
    set_agent_context("security-validator", "validation")
    
    # Example security analysis data
    security_findings = {
        "scan_timestamp": datetime.utcnow().isoformat(),
        "vulnerabilities": [
            {
                "type": "authentication_bypass",
                "severity": "high",
                "component": "auth_service",
                "description": "JWT validation can be bypassed with null signature"
            }
        ],
        "recommendations": [
            "Implement strict JWT signature validation",
            "Add rate limiting to auth endpoints"
        ],
        "compliance_status": "non_compliant"
    }
    
    # Store security analysis (instead of creating markdown file)
    security_entity = await store_security_analysis(
        security_area="authentication_service",
        analysis=security_findings,
        severity="high",
        agent_name="security-validator"
    )
    
    # Example validation evidence
    validation_evidence = {
        "validation_type": "security_scan",
        "endpoints_tested": 15,
        "vulnerabilities_found": 1,
        "compliance_checks": {
            "owasp_top_10": "8/10 passed",
            "cis_controls": "12/15 passed"
        },
        "evidence_files": [
            "security_scan_output.json",
            "vulnerability_details.json"
        ]
    }
    
    # Store validation evidence (instead of creating validation report markdown)
    validation_entity = await store_validation_evidence(
        validation_name="security_compliance_scan",
        evidence=validation_evidence,
        success=False,  # Due to high severity vulnerability
        agent_name="security-validator"
    )
    
    print(f"Stored security analysis: {security_entity}")
    print(f"Stored validation evidence: {validation_entity}")
    
    return security_entity, validation_entity


async def example_infrastructure_monitoring_usage():
    """
    Example: Infrastructure monitoring agent using memory service.
    
    BEFORE (creates markdown files):
        Write("/path/INFRASTRUCTURE_STATUS_REPORT.md", infra_status)
        Write("/path/PERFORMANCE_METRICS.md", performance_data)
    
    AFTER (uses memory service):
        Uses store_infrastructure_findings() and store_performance_metrics()
    """
    
    # Set agent context
    set_agent_context("monitoring-analyst", "infrastructure")
    
    # Example infrastructure findings
    infrastructure_status = {
        "scan_timestamp": datetime.utcnow().isoformat(),
        "components": {
            "redis": {
                "status": "degraded",
                "connectivity": "partial",
                "memory_usage": "78%",
                "issues": ["Authentication failures", "Connection timeouts"]
            },
            "postgres": {
                "status": "healthy",
                "connectivity": "full",
                "performance": "optimal",
                "connections": "45/100 used"
            },
            "api_gateway": {
                "status": "healthy",
                "response_time": "180ms",
                "throughput": "1200 req/min"
            }
        },
        "overall_health": "degraded",
        "critical_issues": 1,
        "recommendations": ["Fix Redis authentication", "Monitor Redis closely"]
    }
    
    # Store infrastructure findings (instead of markdown report)
    infra_entity = await store_infrastructure_findings(
        component_name="system_infrastructure",
        findings=infrastructure_status,
        status="degraded",
        agent_name="monitoring-analyst"
    )
    
    # Example performance metrics
    performance_data = {
        "measurement_timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "api_response_time": {
                "average": 180,
                "p95": 350,
                "p99": 500,
                "unit": "ms"
            },
            "database_query_time": {
                "average": 45,
                "slowest_query": 120,
                "unit": "ms"
            },
            "memory_usage": {
                "total": "16GB",
                "used": "12.8GB",
                "percentage": 80
            },
            "cpu_usage": {
                "average": 35,
                "peak": 78,
                "unit": "percentage"
            }
        },
        "bottlenecks": ["Redis connectivity", "API response time"],
        "optimization_opportunities": [
            "Implement Redis connection pooling",
            "Add database query caching"
        ]
    }
    
    # Store performance metrics (instead of markdown report)
    perf_entity = await store_performance_metrics(
        metric_name="system_performance",
        metrics=performance_data,
        agent_name="monitoring-analyst"
    )
    
    print(f"Stored infrastructure findings: {infra_entity}")
    print(f"Stored performance metrics: {perf_entity}")
    
    return infra_entity, perf_entity


async def example_research_analyst_usage():
    """
    Example: Research analyst agent using memory service for findings.
    
    BEFORE (creates markdown files):
        Write("/path/CODEBASE_ANALYSIS.md", research_findings)
        Write("/path/DEPENDENCY_ANALYSIS.md", dependency_data)
    
    AFTER (uses memory service):
        Uses store_analysis() with appropriate categorization
    """
    
    # Set agent context
    set_agent_context("codebase-research-analyst", "research")
    
    # Example codebase research findings
    research_findings = {
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "codebase_structure": {
            "total_files": 1247,
            "languages": ["Python", "JavaScript", "SQL", "YAML", "Dockerfile"],
            "key_directories": [
                "app/api/", "app/worker/", "app/webui-next/", 
                "docker/", "config/", "scripts/"
            ]
        },
        "architecture_patterns": [
            "Microservices with Docker containers",
            "FastAPI for API services",
            "Celery for background tasks",
            "PostgreSQL + Redis for data storage",
            "Prometheus + Grafana for monitoring"
        ],
        "identified_services": {
            "api": "Main API service with authentication",
            "worker": "Background task processing with Celery",
            "memory_service": "Hybrid memory management with PostgreSQL + Qdrant",
            "chat_service": "AI chat functionality",
            "voice_interaction_service": "Voice processing capabilities"
        },
        "deployment_status": {
            "api": "deployed",
            "worker": "deployed",
            "memory_service": "deployed",
            "chat_service": "configured_not_deployed",
            "voice_interaction_service": "configured_not_deployed"
        },
        "key_insights": [
            "Voice and chat services are configured but not deployed",
            "Redis connectivity issues affecting system reliability",
            "Strong monitoring infrastructure already in place",
            "Authentication system uses JWT with circuit breaker pattern"
        ]
    }
    
    # Store research findings (instead of markdown file)
    research_entity = await store_analysis(
        analysis_name="codebase_architecture_analysis",
        content=research_findings,
        agent_name="codebase-research-analyst",
        analysis_type="research"
    )
    
    # Example dependency analysis
    dependency_analysis = {
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "python_dependencies": {
            "total_packages": 45,
            "key_frameworks": [
                "fastapi==0.104.1",
                "celery==5.3.4",
                "sqlalchemy==2.0.23",
                "redis==5.0.1",
                "prometheus-client==0.19.0"
            ],
            "security_concerns": [],
            "outdated_packages": ["requests==2.28.1"]
        },
        "javascript_dependencies": {
            "frontend_framework": "Vue.js",
            "build_tool": "Vite",
            "styling": "Tailwind CSS"
        },
        "system_dependencies": {
            "runtime": "Python 3.11",
            "database": "PostgreSQL 15",
            "cache": "Redis 7",
            "monitoring": "Prometheus + Grafana",
            "vector_db": "Qdrant"
        },
        "recommendations": [
            "Update requests package to latest version",
            "Consider upgrading to Python 3.12 for performance",
            "Evaluate Redis 7.2 for improved performance"
        ]
    }
    
    # Store dependency analysis (instead of markdown file)
    dependency_entity = await store_analysis(
        analysis_name="dependency_security_analysis",
        content=dependency_analysis,
        agent_name="codebase-research-analyst",
        analysis_type="dependency_analysis"
    )
    
    print(f"Stored research findings: {research_entity}")
    print(f"Stored dependency analysis: {dependency_entity}")
    
    return research_entity, dependency_entity


async def example_agent_memory_interface_usage():
    """
    Example: Using the high-level AgentMemoryInterface for simplified operations.
    
    The agent_memory interface provides specialized methods for common operations
    without needing to know specific storage function details.
    """
    
    # Set agent context
    set_agent_context("backend-gateway-expert", "implementation")
    
    # Store implementation report using high-level interface
    impl_entity = await agent_memory.store_implementation_report(
        component="jwt_circuit_breaker",
        implementation_details={
            "feature": "Circuit Breaker Authentication Pattern",
            "files_modified": [
                "app/api/auth.py",
                "app/webui-next/src/components/auth/SimplifiedAuthContext.jsx"
            ],
            "lines_of_code": 792,
            "tests_added": 15,
            "validation_success_rate": "90%"
        },
        status="completed"
    )
    
    # Store validation results using high-level interface
    validation_entity = await agent_memory.store_validation_results(
        validation_type="endpoint_accessibility",
        results={
            "endpoints_tested": 8,
            "successful_responses": 8,
            "average_response_time": "180ms"
        },
        success=True,
        evidence={
            "curl_outputs": ["HTTP/1.1 200 OK", "Content-Type: application/json"],
            "health_checks": "All services responding"
        }
    )
    
    # Search for previous work
    previous_auth_work = await agent_memory.search_previous_work(
        topic="authentication circuit breaker",
        agent_type="backend-gateway-expert",
        limit=5
    )
    
    # Get context for current task
    task_context = await agent_memory.get_context_for_task(
        task_type="authentication_improvement",
        specific_area="circuit_breaker",
        limit=3
    )
    
    print(f"Stored implementation report: {impl_entity}")
    print(f"Stored validation results: {validation_entity}")
    print(f"Found {len(previous_auth_work)} previous authentication work items")
    print(f"Retrieved {len(task_context)} context items for task")
    
    return impl_entity, validation_entity, previous_auth_work, task_context


async def example_search_and_retrieval():
    """
    Example: Searching and retrieving knowledge instead of reading markdown files.
    
    BEFORE (reads markdown files):
        Read("/path/SECURITY_ANALYSIS.md")
        Read("/path/PERFORMANCE_REPORT.md")
        Read("/path/VALIDATION_EVIDENCE.md")
    
    AFTER (searches memory service):
        Uses search_knowledge() with specific queries
    """
    
    # Search for security-related knowledge
    security_knowledge = await search_knowledge(
        query="security authentication vulnerability",
        limit=5
    )
    
    # Search for performance analysis
    performance_knowledge = await search_knowledge(
        query="performance metrics optimization",
        limit=5
    )
    
    # Search for validation evidence
    validation_knowledge = await search_knowledge(
        query="validation evidence endpoint",
        limit=5
    )
    
    # Search for error patterns and solutions
    error_patterns = await search_knowledge(
        query="redis connectivity authentication error",
        limit=3
    )
    
    print(f"Found {len(security_knowledge)} security knowledge items")
    print(f"Found {len(performance_knowledge)} performance knowledge items")
    print(f"Found {len(validation_knowledge)} validation knowledge items")
    print(f"Found {len(error_patterns)} error pattern items")
    
    # Example of processing search results
    for item in security_knowledge:
        print(f"Security Knowledge: {item['name']} ({item['entity_type']})")
        if item.get('metadata'):
            print(f"  Metadata: {json.dumps(item['metadata'], indent=2)}")
    
    return security_knowledge, performance_knowledge, validation_knowledge, error_patterns


async def example_error_handling_and_pattern_storage():
    """
    Example: Storing error patterns and solutions for future reference.
    
    When agents encounter errors, they should store the pattern and solution
    in memory for future agents to learn from.
    """
    
    # Set agent context
    set_agent_context("debugging-specialist", "debugging")
    
    # Example error pattern
    redis_error_pattern = {
        "error_type": "redis_authentication_failure",
        "symptoms": [
            "Connection timeouts to Redis",
            "Authentication errors in logs",
            "Service degradation"
        ],
        "root_cause": "Redis ACL configuration mismatch",
        "investigation_steps": [
            "Check Redis logs for auth failures",
            "Verify ACL user configuration",
            "Test connection with redis-cli"
        ],
        "affected_services": ["api", "worker", "memory_service"]
    }
    
    solution_steps = """
    1. Connect to Redis container: docker exec -it redis redis-cli
    2. Check ACL users: ACL LIST
    3. Verify user permissions: ACL GETUSER username
    4. Update ACL configuration if needed
    5. Restart affected services
    6. Verify connectivity restoration
    """
    
    # Store error pattern with solution
    error_entity = await store_error_pattern(
        error_name="redis_authentication_failure",
        error_data=redis_error_pattern,
        solution=solution_steps,
        agent_name="debugging-specialist"
    )
    
    print(f"Stored error pattern: {error_entity}")
    
    return error_entity


async def run_all_examples():
    """
    Run all usage examples to demonstrate memory service integration.
    
    Note: This assumes memory integration has been initialized with MCP functions.
    """
    
    print("=== Memory Service Integration Usage Examples ===\n")
    
    try:
        # Security validator example
        print("1. Security Validator Usage:")
        security_results = await example_security_validator_usage()
        print(f"   Results: {security_results}\n")
        
        # Infrastructure monitoring example
        print("2. Infrastructure Monitoring Usage:")
        infra_results = await example_infrastructure_monitoring_usage()
        print(f"   Results: {infra_results}\n")
        
        # Research analyst example
        print("3. Research Analyst Usage:")
        research_results = await example_research_analyst_usage()
        print(f"   Results: {research_results}\n")
        
        # Agent memory interface example
        print("4. Agent Memory Interface Usage:")
        interface_results = await example_agent_memory_interface_usage()
        print(f"   Results: {len(interface_results)} entities created\n")
        
        # Search and retrieval example
        print("5. Search and Retrieval:")
        search_results = await example_search_and_retrieval()
        print(f"   Results: {[len(r) for r in search_results]} items found\n")
        
        # Error handling example
        print("6. Error Pattern Storage:")
        error_result = await example_error_handling_and_pattern_storage()
        print(f"   Result: {error_result}\n")
        
        print("=== All examples completed successfully ===")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        raise


if __name__ == "__main__":
    # Note: This would need actual MCP function initialization in practice
    print("Memory Service Integration Usage Examples")
    print("These examples show how to use memory service instead of markdown files")
    print("For actual execution, initialize memory integration first:")
    print("  await initialize_orchestration_wrapper(mcp_functions)")