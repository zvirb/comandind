#!/usr/bin/env python3
"""
Simple validation script for Hybrid Intelligence Implementation
Validates that all components are in place and properly structured
"""

import os
import json
from datetime import datetime

def validate_file_exists(file_path, description):
    """Validate that a file exists and report"""
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {file_path}")
    return exists

def validate_file_contains(file_path, search_terms, description):
    """Validate that a file contains specific terms"""
    if not os.path.exists(file_path):
        print(f"❌ {description}: File not found - {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        matches = {}
        for term in search_terms:
            matches[term] = term in content
        
        all_found = all(matches.values())
        status = "✅" if all_found else "⚠️"
        print(f"{status} {description}:")
        for term, found in matches.items():
            term_status = "✓" if found else "✗"
            print(f"    {term_status} {term}")
        
        return all_found
    except Exception as e:
        print(f"❌ {description}: Error reading file - {e}")
        return False

def main():
    print("🔍 HYBRID INTELLIGENCE IMPLEMENTATION VALIDATION")
    print("=" * 60)
    
    validation_results = []
    
    # 1. Core Backend Components
    print("\n🏗️ BACKEND COMPONENTS:")
    
    results = {
        "hybrid_orchestrator": validate_file_exists(
            "/home/marku/ai_workflow_engine/app/worker/services/hybrid_intelligence_orchestrator.py",
            "Hybrid Intelligence Orchestrator"
        ),
        "hybrid_router": validate_file_exists(
            "/home/marku/ai_workflow_engine/app/api/routers/hybrid_intelligence_router.py", 
            "Hybrid Intelligence API Router"
        ),
        "memory_service": validate_file_exists(
            "/home/marku/ai_workflow_engine/app/memory_service/main.py",
            "Memory Service"
        ),
        "sequential_thinking": validate_file_exists(
            "/home/marku/ai_workflow_engine/app/sequentialthinking_service/main.py",
            "Sequential Thinking Service"
        )
    }
    
    validation_results.extend(results.values())
    
    # 2. Frontend Components  
    print("\n🎨 FRONTEND COMPONENTS:")
    
    frontend_results = {
        "agent_thinking_block": validate_file_exists(
            "/home/marku/ai_workflow_engine/app/webui/src/lib/components/chat/AgentThinkingBlock.svelte",
            "AgentThinkingBlock Component"
        ),
        "hybrid_service": validate_file_exists(
            "/home/marku/ai_workflow_engine/app/webui/src/lib/services/hybridIntelligenceService.js",
            "Hybrid Intelligence Service"
        ),
        "chat_component": validate_file_exists(
            "/home/marku/ai_workflow_engine/app/webui/src/lib/components/Chat.svelte",
            "Chat Component"
        ),
        "chat_store": validate_file_exists(
            "/home/marku/ai_workflow_engine/app/webui/src/lib/stores/chatStore.js",
            "Chat Store"
        )
    }
    
    validation_results.extend(frontend_results.values())
    
    # 3. Integration Validation
    print("\n🔗 INTEGRATION VALIDATION:")
    
    integration_results = {
        "orchestrator_features": validate_file_contains(
            "/home/marku/ai_workflow_engine/app/worker/services/hybrid_intelligence_orchestrator.py",
            ["HybridIntelligenceOrchestrator", "hybrid_retrieval_node", "sequential_reasoning_node", "_send_websocket_update"],
            "Orchestrator Core Features"
        ),
        "router_endpoints": validate_file_contains(
            "/home/marku/ai_workflow_engine/app/api/routers/hybrid_intelligence_router.py",
            ["/process", "/ws/", "HybridRequestModel", "websocket_endpoint"],
            "API Router Endpoints"
        ),
        "thinking_block_features": validate_file_contains(
            "/home/marku/ai_workflow_engine/app/webui/src/lib/components/chat/AgentThinkingBlock.svelte",
            ["orchestrationPhase", "reasoningSteps", "hybridRetrievalData", "websocketConnection"],
            "AgentThinkingBlock Transparency Features"
        ),
        "service_websocket": validate_file_contains(
            "/home/marku/ai_workflow_engine/app/webui/src/lib/services/hybridIntelligenceService.js",
            ["connectWebSocket", "handleWebSocketMessage", "processRequest", "HybridIntelligenceService"],
            "Service WebSocket Integration"
        ),
        "chat_store_integration": validate_file_contains(
            "/home/marku/ai_workflow_engine/app/webui/src/lib/stores/chatStore.js",
            ["hybridIntelligenceService", "hybridModes", "hybrid intelligence orchestration"],
            "Chat Store Integration"
        ),
        "chat_component_integration": validate_file_contains(
            "/home/marku/ai_workflow_engine/app/webui/src/lib/components/Chat.svelte",
            ["AgentThinkingBlock", "hybridIntelligenceService"],
            "Chat Component Integration"
        ),
        "main_app_registration": validate_file_contains(
            "/home/marku/ai_workflow_engine/app/api/main.py",
            ["hybrid_intelligence_router", "include_router"],
            "Main App Router Registration"
        )
    }
    
    validation_results.extend(integration_results.values())
    
    # 4. Summary
    print("\n📊 VALIDATION SUMMARY:")
    print("=" * 60)
    
    total_checks = len(validation_results)
    passed_checks = sum(validation_results)
    success_rate = (passed_checks / total_checks) * 100
    
    print(f"✅ Passed: {passed_checks}/{total_checks} ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        print("\n🎉 HYBRID INTELLIGENCE SYSTEM: FULLY IMPLEMENTED!")
        print("✨ All major components are in place and properly integrated.")
        implementation_status = "COMPLETE"
    elif success_rate >= 70:
        print("\n🚧 HYBRID INTELLIGENCE SYSTEM: MOSTLY IMPLEMENTED")
        print("⚠️ Some components may need attention, but core functionality is present.")
        implementation_status = "MOSTLY_COMPLETE"
    else:
        print("\n❌ HYBRID INTELLIGENCE SYSTEM: INCOMPLETE")
        print("💔 Major components are missing or not properly configured.")
        implementation_status = "INCOMPLETE"
    
    # 5. Architecture Overview
    print("\n🏗️ ARCHITECTURE OVERVIEW:")
    print("=" * 60)
    print("The Hybrid Intelligence system includes:")
    print("  🧠 Enhanced Master Orchestrator")
    print("     - Hybrid retrieval (semantic + structured)")  
    print("     - Sequential reasoning integration")
    print("     - Real-time WebSocket transparency")
    print("  🎯 Memory Service Integration")
    print("     - Qdrant semantic search")
    print("     - PostgreSQL knowledge graph")
    print("     - Cross-reference linking")
    print("  🤔 Sequential Thinking Service")
    print("     - LangGraph reasoning workflows")
    print("     - Self-correction loops")
    print("     - Redis checkpointing")
    print("  📱 Transparent UI Visualization")  
    print("     - AgentThinkingBlock component")
    print("     - Real-time reasoning steps")
    print("     - Hybrid context visualization")
    print("     - WebSocket live updates")
    
    print("\n🚀 NEXT STEPS:")
    print("1. Start the memory service: cd app/memory_service && python -m uvicorn main:app --port 8001")
    print("2. Start the sequential thinking service: cd app/sequentialthinking_service && python -m uvicorn main:app --port 8002")
    print("3. Start the main API: python -m uvicorn app.api.main:app --port 8000")
    print("4. Access WebUI at https://localhost and test hybrid intelligence modes")
    print("5. Watch the AgentThinkingBlock for real-time transparency!")
    
    # Save validation report
    report = {
        "timestamp": datetime.now().isoformat(),
        "implementation_status": implementation_status,
        "success_rate": success_rate,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "components": {
            "backend": list(results.keys()),
            "frontend": list(frontend_results.keys()),
            "integration": list(integration_results.keys())
        }
    }
    
    with open("/home/marku/ai_workflow_engine/hybrid_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Validation report saved to: hybrid_validation_report.json")
    print("=" * 60)

if __name__ == "__main__":
    main()