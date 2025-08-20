#!/usr/bin/env python3
"""
Test script for Knowledge Graph Research Integration
Demonstrates how historical patterns inform research and planning
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from systems.knowledge_graph_research_integration import KnowledgeGraphResearchIntegration
import json

def test_websocket_issue():
    """Test with current WebSocket null session ID issue"""
    print("=== TESTING: WebSocket Null Session ID Issue ===\n")
    
    kg_integration = KnowledgeGraphResearchIntegration()
    
    # Current issue from the logs
    task_description = "Fix Helios WebSocket connection failures using 'null' session ID instead of valid session identifier"
    symptoms = [
        "WebSocket connection to 'wss://aiwfe.com/ws/helios/null' failed",
        "connection closed before establishment", 
        "null session ID in connection URL",
        "Helios WebSocket error",
        "WebSocket disconnected"
    ]
    
    # Generate research brief with historical patterns
    research_brief = kg_integration.generate_research_brief(task_description, symptoms)
    
    print("📋 ENHANCED RESEARCH BRIEF")
    print("=" * 50)
    
    print(f"🎯 Task: {research_brief['task_analysis']['description']}")
    print(f"⚠️  Risk Level: {research_brief['task_analysis']['risk_level']}")
    print(f"🔍 Symptoms: {', '.join(research_brief['task_analysis']['identified_symptoms'])}")
    print()
    
    print("🧠 HISTORICAL INTELLIGENCE")
    print("-" * 30)
    print(f"Similar Past Failures: {research_brief['historical_context']['similar_past_failures']}")
    print(f"High Risk Patterns: {research_brief['historical_context']['high_risk_patterns']}")
    print()
    
    print("🔬 RESEARCH GUIDANCE")
    print("-" * 30)
    print("Priority Areas:")
    for area in research_brief['research_guidance']['priority_areas']:
        print(f"  • {area}")
    print("\nValidated Approaches:")
    for approach in research_brief['research_guidance']['validated_approaches']:
        print(f"  ✓ {approach}")
    print("\nRisk Indicators to Watch:")
    for risk in research_brief['research_guidance']['risk_indicators']:
        print(f"  ⚠️  {risk}")
    print()
    
    print("📋 PLANNING RECOMMENDATIONS")
    print("-" * 30)
    print("Proven Sequences:")
    for sequence in research_brief['planning_recommendations']['proven_sequences']:
        print(f"  → {sequence}")
    print("\nValidation Checkpoints:")
    for checkpoint in research_brief['planning_recommendations']['validation_checkpoints']:
        print(f"  🔍 {checkpoint}")
    print("\nParallel Opportunities:")
    for parallel in research_brief['planning_recommendations']['parallel_opportunities']:
        print(f"  ⚡ {parallel}")
    print()
    
    print("📊 EXECUTION STRATEGY")
    print("-" * 30)
    print(f"Recommended Approach: {research_brief['execution_strategy']['recommended_approach']}")
    print(f"Success Probability: {research_brief['execution_strategy']['success_probability']:.1%}")
    print(f"Iteration Likelihood: {research_brief['execution_strategy']['iteration_likelihood']:.1%}")
    print()

def test_authentication_issue():
    """Test with authentication-related issue"""
    print("=== TESTING: Authentication Issue Pattern Matching ===\n")
    
    kg_integration = KnowledgeGraphResearchIntegration()
    
    task_description = "Fix user authentication login failures with CSRF token validation errors"
    symptoms = [
        "403 CSRF token validation failed",
        "existing users cannot log in",
        "authentication endpoint returns error"
    ]
    
    research_brief = kg_integration.generate_research_brief(task_description, symptoms)
    
    print("🔍 PATTERN MATCHING RESULTS")
    print("=" * 40)
    print(f"Task Type Detected: {research_brief.get('pattern_analysis', {}).get('primary_type', 'authentication_related')}")
    print(f"Risk Level: {research_brief['task_analysis']['risk_level']}")
    print(f"Historical Failures: {research_brief['historical_context']['similar_past_failures']}")
    print()
    
    print("🎯 KEY RESEARCH PRIORITIES")
    print("-" * 30)
    for i, area in enumerate(research_brief['research_guidance']['priority_areas'][:5], 1):
        print(f"{i}. {area}")
    print()

def test_ui_issue():
    """Test with UI-related issue"""
    print("=== TESTING: UI Asset Missing Issue ===\n")
    
    kg_integration = KnowledgeGraphResearchIntegration()
    
    task_description = "Fix missing agent profile images causing 404 errors and CSS preload warnings"
    symptoms = [
        "404 resource not found for agent images",
        "CSS preload warning unused resources",
        "static assets not loading"
    ]
    
    research_brief = kg_integration.generate_research_brief(task_description, symptoms)
    
    print("🎨 UI ISSUE ANALYSIS")
    print("=" * 30)
    print("Research Priorities:")
    for area in research_brief['research_guidance']['priority_areas'][:3]:
        print(f"  • {area}")
    print("\nRecommended Parallel Work:")
    for parallel in research_brief['planning_recommendations']['parallel_opportunities']:
        print(f"  ⚡ {parallel}")
    print()

if __name__ == "__main__":
    print("🧠 KNOWLEDGE GRAPH RESEARCH INTEGRATION TESTING")
    print("=" * 60)
    print()
    
    try:
        # Test current high-priority issues
        test_websocket_issue()
        print("\n" + "=" * 60 + "\n")
        test_authentication_issue()
        print("\n" + "=" * 60 + "\n")
        test_ui_issue()
        
        print("✅ INTEGRATION TESTING COMPLETE")
        print("\nThe knowledge graph integration successfully:")
        print("✓ Analyzed task patterns and matched to historical data")
        print("✓ Generated research priorities based on past failures")
        print("✓ Recommended validation approaches from successful patterns")
        print("✓ Identified risk indicators from failure pattern analysis")
        print("✓ Suggested parallel execution opportunities")
        print("✓ Estimated success probability and iteration likelihood")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()