#!/usr/bin/env python3
"""
Memory Service Integration Demonstration

Shows how the memory service integration would work with actual MCP functions
and orchestration agents. This demonstrates the complete workflow.

Usage:
    python demo_integration.py
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Mock MCP functions for demonstration
class MockMCPFunctions:
    """Mock MCP functions for demonstration purposes."""
    
    def __init__(self):
        self.memory_store = {}
        self.entity_counter = 0
    
    async def mcp__memory__create_entities(self, entities: list) -> dict:
        """Mock entity creation."""
        created_entities = []
        
        for entity in entities:
            self.entity_counter += 1
            entity_id = f"entity_{self.entity_counter}"
            
            # Store entity
            self.memory_store[entity["name"]] = {
                "id": entity_id,
                "name": entity["name"],
                "entityType": entity["entityType"],
                "observations": entity["observations"],
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            
            created_entities.append(entity["name"])
            logger.info(f"Created entity: {entity['name']} ({entity['entityType']})")
        
        return {"created": created_entities}
    
    async def mcp__memory__search_nodes(self, query: str) -> dict:
        """Mock entity search."""
        results = []
        
        query_lower = query.lower()
        for name, entity in self.memory_store.items():
            # Simple search by name and observations
            match_score = 0
            
            if query_lower in name.lower():
                match_score += 10
            
            for obs in entity["observations"]:
                if query_lower in obs.lower():
                    match_score += 5
            
            if match_score > 0:
                results.append((match_score, entity))
        
        # Sort by match score
        results.sort(key=lambda x: x[0], reverse=True)
        
        return {
            "entities": [entity for _, entity in results[:10]]
        }
    
    async def mcp__memory__add_observations(self, observations: list) -> dict:
        """Mock add observations."""
        updated = []
        
        for obs_data in observations:
            entity_name = obs_data["entityName"]
            contents = obs_data["contents"]
            
            if entity_name in self.memory_store:
                self.memory_store[entity_name]["observations"].extend(contents)
                updated.append(entity_name)
                logger.info(f"Added observations to: {entity_name}")
        
        return {"updated": updated}
    
    async def mcp__memory__open_nodes(self, names: list) -> dict:
        """Mock open specific entities."""
        entities = []
        
        for name in names:
            if name in self.memory_store:
                entities.append(self.memory_store[name])
        
        return {"entities": entities}


async def demonstrate_memory_integration():
    """Demonstrate the complete memory service integration workflow."""
    
    print("=== Memory Service Integration Demonstration ===\n")
    
    # Initialize mock MCP functions
    mock_mcp = MockMCPFunctions()
    mcp_functions = {
        "mcp__memory__create_entities": mock_mcp.mcp__memory__create_entities,
        "mcp__memory__search_nodes": mock_mcp.mcp__memory__search_nodes,
        "mcp__memory__add_observations": mock_mcp.mcp__memory__add_observations,
        "mcp__memory__open_nodes": mock_mcp.mcp__memory__open_nodes
    }
    
    # Import and initialize memory integration
    try:
        from . import initialize_orchestration_wrapper, agent_memory, set_agent_context
        from . import store_analysis, store_validation_evidence, search_knowledge
        
        # Initialize the integration
        await initialize_orchestration_wrapper(mcp_functions)
        print("✓ Memory integration initialized successfully\n")
        
    except ImportError:
        print("Note: This is a demonstration with mock functions")
        print("In actual usage, the memory integration would be imported and used\n")
        return
    
    # Demonstrate agent usage patterns
    
    # 1. Security validator storing analysis
    print("1. Security Validator Example:")
    set_agent_context("security-validator", "validation")
    
    security_analysis = {
        "scan_timestamp": datetime.utcnow().isoformat(),
        "vulnerabilities_found": 1,
        "severity": "high",
        "details": {
            "authentication_bypass": {
                "component": "jwt_validation",
                "risk_level": "high",
                "remediation": "Implement strict signature validation"
            }
        },
        "compliance_status": "non_compliant"
    }
    
    security_entity = await store_analysis(
        analysis_name="jwt_security_scan",
        content=security_analysis,
        agent_name="security-validator",
        analysis_type="security"
    )
    print(f"   Stored security analysis: {security_entity}")
    
    # 2. Infrastructure monitoring storing findings
    print("\n2. Infrastructure Monitoring Example:")
    set_agent_context("monitoring-analyst", "infrastructure")
    
    validation_evidence = {
        "validation_type": "endpoint_accessibility",
        "endpoints_tested": 8,
        "successful_responses": 8,
        "evidence": {
            "curl_outputs": ["HTTP/1.1 200 OK"] * 8,
            "response_times": ["180ms", "165ms", "192ms", "158ms"]
        },
        "overall_status": "healthy"
    }
    
    validation_entity = await store_validation_evidence(
        validation_name="production_endpoint_validation",
        evidence=validation_evidence,
        success=True,
        agent_name="monitoring-analyst"
    )
    print(f"   Stored validation evidence: {validation_entity}")
    
    # 3. Research analyst storing findings
    print("\n3. Research Analyst Example:")
    set_agent_context("codebase-research-analyst", "research")
    
    research_findings = {
        "analysis_type": "service_discovery",
        "services_found": {
            "voice_interaction_service": "configured_not_deployed",
            "chat_service": "configured_not_deployed",
            "memory_service": "deployed_functional"
        },
        "deployment_gaps": [
            "Voice service container ready but not in docker-compose",
            "Chat service has Dockerfile but missing service definition"
        ],
        "recommendations": [
            "Add voice service to docker-compose.yml on port 8006",
            "Add chat service to docker-compose.yml on port 8007",
            "Update service mesh configuration"
        ]
    }
    
    research_entity = await store_analysis(
        analysis_name="service_deployment_analysis",
        content=research_findings,
        agent_name="codebase-research-analyst",
        analysis_type="research"
    )
    print(f"   Stored research findings: {research_entity}")
    
    # 4. Demonstrate search functionality
    print("\n4. Knowledge Search Example:")
    
    # Search for security-related knowledge
    security_results = await search_knowledge(
        query="security vulnerability authentication",
        limit=5
    )
    print(f"   Found {len(security_results)} security knowledge items")
    
    # Search for validation evidence
    validation_results = await search_knowledge(
        query="validation evidence endpoint",
        limit=5
    )
    print(f"   Found {len(validation_results)} validation evidence items")
    
    # Search for service deployment information
    deployment_results = await search_knowledge(
        query="service deployment voice chat",
        limit=5
    )
    print(f"   Found {len(deployment_results)} deployment knowledge items")
    
    # 5. Demonstrate agent memory interface
    print("\n5. Agent Memory Interface Example:")
    
    # Store implementation report
    impl_entity = await agent_memory.store_implementation_report(
        component="circuit_breaker_auth",
        implementation_details={
            "pattern": "Circuit Breaker Authentication",
            "files_modified": 15,
            "lines_added": 792,
            "validation_success_rate": "90%"
        },
        status="completed",
        agent_name="backend-gateway-expert"
    )
    print(f"   Stored implementation report: {impl_entity}")
    
    # Get context for task
    auth_context = await agent_memory.get_context_for_task(
        task_type="authentication_improvement",
        specific_area="circuit_breaker",
        limit=3
    )
    print(f"   Retrieved {len(auth_context)} context items for authentication task")
    
    # 6. Show memory store contents
    print("\n6. Memory Store Contents:")
    print(f"   Total entities stored: {len(mock_mcp.memory_store)}")
    for name, entity in mock_mcp.memory_store.items():
        print(f"   - {name} ({entity['entityType']})")
    
    # 7. Demonstrate markdown prevention
    print("\n7. Markdown Prevention Example:")
    print("   Instead of: Write('/path/ANALYSIS.md', content)")
    print("   System automatically redirects to: store_analysis()")
    print("   Result: Structured knowledge in memory service ✓")
    
    print("\n=== Demonstration Complete ===")
    print("\nKey Benefits:")
    print("✓ No markdown files cluttering project root")
    print("✓ Structured, searchable knowledge storage")
    print("✓ Automatic categorization and tagging")
    print("✓ Agent-friendly storage and retrieval APIs")
    print("✓ Cross-session knowledge persistence")
    print("✓ Evidence-based validation with proof")
    
    return mock_mcp.memory_store


async def demonstrate_markdown_prevention():
    """Demonstrate how markdown file creation is prevented and redirected."""
    
    print("\n=== Markdown Prevention Demonstration ===\n")
    
    # Mock Write function that would normally create files
    class MockWriteFunction:
        def __init__(self):
            self.calls = []
        
        async def __call__(self, file_path: str, content: str, **kwargs):
            self.calls.append((file_path, content, kwargs))
            print(f"[MOCK] Write called: {file_path}")
            return {"status": "written", "path": file_path}
    
    # Create mock MCP and wrap Write function
    mock_mcp = MockMCPFunctions()
    mcp_functions = {
        "mcp__memory__create_entities": mock_mcp.mcp__memory__create_entities,
        "mcp__memory__search_nodes": mock_mcp.mcp__memory__search_nodes,
        "mcp__memory__add_observations": mock_mcp.mcp__memory__add_observations,
        "mcp__memory__open_nodes": mock_mcp.mcp__memory__open_nodes
    }
    
    original_write = MockWriteFunction()
    
    try:
        from .orchestration_wrapper import MemoryServiceWrite, initialize_orchestration_wrapper
        
        # Initialize memory integration
        await initialize_orchestration_wrapper(mcp_functions)
        
        # Create wrapped Write function
        wrapped_write = MemoryServiceWrite(original_write)
        
        # Test cases
        test_cases = [
            ("/path/SECURITY_ANALYSIS.md", "# Security Analysis\n\nFound vulnerabilities..."),
            ("/path/VALIDATION_REPORT.md", "# Validation Report\n\nAll tests passed..."),
            ("/path/PERFORMANCE_METRICS.md", "# Performance Metrics\n\nResponse time: 180ms..."),
            ("/path/config.yaml", "# YAML Config\nkey: value"),  # Non-markdown, should pass through
            ("/path/ERROR_PATTERNS.md", "# Error Patterns\n\nRedis connectivity issues...")
        ]
        
        print("Testing Write function with various file types:\n")
        
        for file_path, content in test_cases:
            print(f"Attempting to write: {file_path}")
            
            result = await wrapped_write(file_path, content)
            
            if isinstance(result, dict) and result.get("status") == "redirected_to_memory":
                print(f"  ✓ Redirected to memory: {result['entity_name']}")
                print(f"    Message: {result['message']}")
            else:
                print(f"  → Passed through to original Write: {result}")
            
            print()
        
        # Show what was stored in memory vs what went to files
        print("Results Summary:")
        print(f"  Entities in memory: {len(mock_mcp.memory_store)}")
        print(f"  Calls to original Write: {len(original_write.calls)}")
        
        print("\nMemory entities created:")
        for name, entity in mock_mcp.memory_store.items():
            print(f"  - {name} ({entity['entityType']})")
        
        print("\nOriginal Write calls (non-markdown files):")
        for file_path, content, kwargs in original_write.calls:
            print(f"  - {file_path}")
        
    except ImportError:
        print("This would require the actual memory integration modules")
        print("Demonstration shows the structure and benefits")


async def main():
    """Main demonstration function."""
    try:
        # Run memory integration demonstration
        await demonstrate_memory_integration()
        
        # Run markdown prevention demonstration
        await demonstrate_markdown_prevention()
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())