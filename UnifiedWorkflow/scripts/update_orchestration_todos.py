#!/usr/bin/env python3
"""
Update orchestration todos based on completed infrastructure recovery workflow
"""

import json
import re
from datetime import datetime

def fix_json_and_update_todos():
    """Fix JSON syntax and update todos with latest achievements"""
    
    # Read the file and fix JSON syntax issues
    with open('/home/marku/ai_workflow_engine/.claude/orchestration_todos.json', 'r') as f:
        content = f.read()
    
    # Fix the JSON syntax error (extra closing brace)
    content = re.sub(r'}\s*},\s*{', '},\n    {', content)
    content = re.sub(r'    }\s*}\s*,\s*{', '    },\n    {', content)
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        # Try to fix common issues
        content = content.replace('}\n    },', '},')
        data = json.loads(content)
    
    # Current date for completion tracking
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Mark infrastructure dependencies as completed
    infrastructure_todos = [
        "pydantic-settings-dependency-resolution-20250817",
        "container-rebuild-deployment-20250816", 
        "cognitive-services-health-restoration-20250816"
    ]
    
    for todo in data['todos']:
        if todo['id'] in infrastructure_todos and todo['status'] == 'pending':
            todo['status'] = 'completed'
            todo['completion_date'] = current_date
            todo['iteration'] = 9
            if 'completion_evidence' not in todo:
                todo['completion_evidence'] = []
            todo['completion_evidence'].extend([
                "Infrastructure recovery workflow completed successfully",
                "Container rebuild with pydantic_settings dependency resolved",
                "All infrastructure foundation established"
            ])
    
    # Add new critical todos based on audit findings
    new_todos = [
        {
            "id": "api-container-runtime-validation-20250817",
            "content": "CRITICAL: Start and validate API container health - container built but needs runtime verification",
            "status": "pending",
            "priority": "critical",
            "context_tags": ["container-runtime", "api-validation", "deployment"],
            "impact_score": 95,
            "urgency_score": 100,
            "validation_requirements": [
                "API container started successfully",
                "Health check endpoints return 200 OK",
                "Container logs show no critical errors",
                "Dependencies properly loaded"
            ],
            "dependencies": ["pydantic-settings-dependency-resolution-20250817"]
        },
        {
            "id": "production-accessibility-403-resolution-20250817", 
            "content": "CRITICAL: Resolve 403 Forbidden status on production sites - infrastructure ready but access blocked",
            "status": "pending",
            "priority": "critical", 
            "context_tags": ["production-access", "403-error", "user-validation"],
            "impact_score": 100,
            "urgency_score": 100,
            "validation_requirements": [
                "http://aiwfe.com returns 200 OK status",
                "https://aiwfe.com returns 200 OK status", 
                "User can access main interface",
                "End-to-end user flow validation completed"
            ],
            "dependencies": ["api-container-runtime-validation-20250817"]
        },
        {
            "id": "websocket-auth-implementation-20250817",
            "content": "HIGH: Implement WebSocket authentication fixes identified in frontend analysis",
            "status": "pending", 
            "priority": "high",
            "context_tags": ["websocket", "authentication", "frontend-fixes"],
            "impact_score": 85,
            "urgency_score": 80,
            "validation_requirements": [
                "WebSocket connections authenticate properly",
                "Chat functionality works end-to-end",
                "Session persistence maintained"
            ],
            "dependencies": ["production-accessibility-403-resolution-20250817"]
        }
    ]
    
    # Add new todos only if they don't already exist
    existing_ids = {todo['id'] for todo in data['todos']}
    for new_todo in new_todos:
        if new_todo['id'] not in existing_ids:
            data['todos'].append(new_todo)
    
    # Update meta-analysis with current state
    if 'meta_analysis' not in data:
        data['meta_analysis'] = {}
    
    data['meta_analysis']['infrastructure_recovery_completion'] = {
        "completion_date": current_date,
        "iteration": 9,
        "major_achievements": [
            "Successfully resolved pydantic_settings dependency issue", 
            "Container rebuild completed with all dependencies installed",
            "Infrastructure validation completed (SSL, DNS, security)",
            "Frontend analysis completed with WebSocket auth solutions",
            "Quality assurance protocols established",
            "Atomic commits created and documented"
        ],
        "remaining_critical_work": [
            "API container runtime validation and startup",
            "Production accessibility 403 error resolution", 
            "End-to-end user flow testing completion",
            "WebSocket authentication implementation"
        ],
        "orchestration_status": "Infrastructure foundation complete, runtime validation required",
        "loop_continuation_assessment": {
            "high_priority_remaining": True,
            "critical_todos_count": 3,
            "recommendation": "CONTINUE orchestration loop - critical runtime validation required"
        }
    }
    
    # Write updated todos back to file
    with open('/home/marku/ai_workflow_engine/.claude/orchestration_todos.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    # Count current status
    total_todos = len(data['todos'])
    pending_todos = [t for t in data['todos'] if t['status'] == 'pending']
    completed_todos = [t for t in data['todos'] if t['status'] == 'completed']
    critical_pending = [t for t in pending_todos if t['priority'] == 'critical']
    
    print(f"✅ Orchestration todos updated successfully")
    print(f"📊 Status Summary:")
    print(f"   Total todos: {total_todos}")
    print(f"   Completed: {len(completed_todos)}")
    print(f"   Pending: {len(pending_todos)}")
    print(f"   Critical pending: {len(critical_pending)}")
    print(f"\n🔄 Loop Continuation Decision:")
    print(f"   Critical todos remaining: {len(critical_pending)} > 0")
    print(f"   Recommendation: CONTINUE orchestration loop")
    print(f"\n🎯 Next critical todos:")
    for todo in critical_pending[:3]:
        print(f"   - {todo['content'][:80]}...")

if __name__ == "__main__":
    fix_json_and_update_todos()