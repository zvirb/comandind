#!/usr/bin/env python3
"""
Bug Report Subtask Generation Service

This service generates specific, actionable subtasks for bug reports
that include detailed information from the user's bug report to help
admin/developers understand and resolve the issues efficiently.
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from worker.services.ollama_service import invoke_llm_with_tokens
from shared.database.models import User

logger = logging.getLogger(__name__)

BUG_REPORT_SUBTASK_PROMPT = """You are a software engineering expert specializing in bug report triage and resolution. Your task is to create specific, actionable subtasks for resolving bug reports that include detailed information from the user's report.

**Your Role:**
- Create subtasks that preserve and reference specific details from the bug report
- Include enough context so developers can understand the issue without re-reading the full report
- Generate actionable steps that lead to systematic bug resolution
- Ensure subtasks contain specific information rather than generic placeholders

**Bug Report Information:**
- **Title:** {bug_title}
- **Description:** {bug_description}
- **Reporter:** {reporter_email}
- **Priority:** {bug_priority}
- **Category:** {bug_category}
- **Assignment Context:** {assignment_context}

**Instructions:**
Create 4-7 specific subtasks for resolving this bug report. Each subtask should:

1. **Include specific details** from the bug report (error messages, steps to reproduce, expected behavior, etc.)
2. **Reference the reporter** when appropriate for follow-up questions
3. **Be actionable** with clear deliverables
4. **Follow a logical workflow** from investigation to resolution
5. **Include time estimates** based on the complexity described

**Example Structure:**
For a bug report about "Login fails with 'Invalid credentials' error even with correct password":

```json
{{
  "subtasks": [
    {{
      "title": "Investigate 'Invalid credentials' error reported by {reporter_email}",
      "description": "Reproduce the login failure described by the user. Check server logs for authentication errors occurring around the time of the report. Look for any recent changes to the authentication system that might cause valid credentials to be rejected.",
      "estimated_hours": 1.5,
      "priority": "high",
      "category": "investigation"
    }},
    {{
      "title": "Verify database integrity for user authentication data",
      "description": "Check if the user's password hash is properly stored and if there are any database corruption issues. Verify that the password hashing algorithm hasn't changed unexpectedly.",
      "estimated_hours": 1.0,
      "priority": "high",
      "category": "analysis"
    }}
  ]
}}
```

**Generate subtasks for this specific bug report:**
Title: "{bug_title}"
Description: "{bug_description}"

Create subtasks that reference specific details from this report and provide clear, actionable steps for resolution. Make sure developers will understand the context without needing to re-read the full bug report.

Respond with JSON in this exact format:
{{
  "subtasks": [
    {{
      "title": "Specific task title with context from bug report",
      "description": "Detailed description including specific information from the user's report and clear actionable steps",
      "estimated_hours": 2.0,
      "priority": "high/medium/low",
      "category": "investigation/analysis/implementation/testing/deployment/communication"
    }}
  ],
  "analysis": {{
    "bug_type": "authentication/ui/performance/data/integration/etc",
    "complexity_level": "low/medium/high",
    "total_estimated_hours": 8.5,
    "reporter_followup_needed": true/false,
    "potential_impact": "description of potential user impact"
  }}
}}
"""

async def generate_bug_report_subtasks(
    bug_title: str,
    bug_description: str,
    reporter_email: str,
    bug_priority: str = "high",
    bug_category: str = "bug_report",
    assignment_context: str = "",
    admin_user: Optional[User] = None
) -> List[Dict[str, Any]]:
    """
    Generate specific, contextual subtasks for bug reports that include detailed information
    from the user's bug report to help admin/developers understand and resolve issues.
    """
    logger.info(f"🐛 Generating specialized subtasks for bug report: {bug_title}")
    logger.info(f"📧 Reporter: {reporter_email}, Priority: {bug_priority}, Category: {bug_category}")
    
    try:
        # Format the comprehensive prompt with all bug report details
        formatted_prompt = BUG_REPORT_SUBTASK_PROMPT.format(
            bug_title=bug_title,
            bug_description=bug_description,
            reporter_email=reporter_email,
            bug_priority=bug_priority,
            bug_category=bug_category,
            assignment_context=assignment_context or f"Assigned to admin for resolution"
        )
        
        logger.info(f"🤖 Invoking LLM for bug report subtask generation...")
        logger.debug(f"📏 Prompt length: {len(formatted_prompt)} characters")
        
        # Use LLM to generate bug-specific subtasks
        response, token_info = await invoke_llm_with_tokens(
            messages=[
                {"role": "system", "content": "You are a software engineering expert who creates specific, actionable subtasks for bug resolution. Always respond with valid JSON only."},
                {"role": "user", "content": formatted_prompt}
            ],
            model_name="llama3.2:3b",  # Use efficient model for faster response
            category="bug_report_subtask_generation"
        )
        
        logger.info(f"🤖 LLM response received - length: {len(response)} characters")
        logger.debug(f"🤖 Full LLM response: {response}")
        
        # Parse JSON response
        logger.info("📊 Parsing JSON from LLM response...")
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start != -1 and json_end != -1:
            json_str = response[json_start:json_end]
            logger.debug(f"📊 Extracted JSON: {json_str[:300]}...")
            
            try:
                parsed_data = json.loads(json_str)
                subtasks_data = parsed_data.get("subtasks", [])
                analysis = parsed_data.get("analysis", {})
                
                logger.info(f"✅ Successfully parsed {len(subtasks_data)} bug report subtasks")
                logger.info(f"📊 Bug type: {analysis.get('bug_type', 'unknown')}")
                logger.info(f"📊 Complexity: {analysis.get('complexity_level', 'unknown')}")
                logger.info(f"📊 Total estimated hours: {analysis.get('total_estimated_hours', 'unknown')}")
                logger.info(f"📊 Followup needed: {analysis.get('reporter_followup_needed', 'unknown')}")
                
                # Convert to required format with UUIDs
                formatted_subtasks = []
                for i, subtask_data in enumerate(subtasks_data):
                    formatted_subtask = {
                        "id": str(uuid.uuid4()),
                        "title": subtask_data.get("title", f"Bug Resolution Step {i+1}"),
                        "description": subtask_data.get("description", ""),
                        "completed": False,
                        "estimated_hours": subtask_data.get("estimated_hours", 2.0),
                        "priority": subtask_data.get("priority", "high"),
                        "category": subtask_data.get("category", "investigation"),
                        # Add bug-specific metadata
                        "bug_report_metadata": {
                            "reporter_email": reporter_email,
                            "original_bug_title": bug_title,
                            "bug_priority": bug_priority,
                            "bug_category": bug_category,
                            "followup_needed": analysis.get('reporter_followup_needed', False)
                        }
                    }
                    formatted_subtasks.append(formatted_subtask)
                    logger.debug(f"🐛 Subtask {i+1}: {formatted_subtask['title']} ({formatted_subtask['estimated_hours']}h)")
                
                if not formatted_subtasks:
                    logger.warning("❌ No subtasks generated by LLM, using fallback")
                    return _generate_fallback_bug_subtasks(bug_title, bug_description, reporter_email, bug_priority)
                
                logger.info(f"🎉 Generated {len(formatted_subtasks)} specialized bug report subtasks")
                return formatted_subtasks
                
            except json.JSONDecodeError as json_error:
                logger.error(f"❌ JSON parsing failed: {json_error}")
                logger.error(f"❌ Problematic JSON: {json_str}")
                return _generate_fallback_bug_subtasks(bug_title, bug_description, reporter_email, bug_priority)
        else:
            logger.error("❌ No JSON found in LLM response")
            logger.error(f"❌ Response preview: {response[:500]}...")
            return _generate_fallback_bug_subtasks(bug_title, bug_description, reporter_email, bug_priority)
            
    except Exception as e:
        logger.error(f"💥 Error in bug report subtask generation: {e}", exc_info=True)
        logger.warning("🔄 Falling back to manual bug report subtasks...")
        return _generate_fallback_bug_subtasks(bug_title, bug_description, reporter_email, bug_priority)

def _generate_fallback_bug_subtasks(
    bug_title: str, 
    bug_description: str, 
    reporter_email: str, 
    bug_priority: str
) -> List[Dict[str, Any]]:
    """
    Generate fallback subtasks for bug reports that still include specific context
    from the user's report when LLM generation fails.
    """
    logger.info(f"🔄 Generating fallback bug report subtasks for: {bug_title}")
    
    # Extract key information from the bug description for more specific subtasks
    description_lower = bug_description.lower()
    
    # Determine bug category from description keywords
    if any(keyword in description_lower for keyword in ["login", "password", "authentication", "auth", "credentials"]):
        bug_type = "authentication"
    elif any(keyword in description_lower for keyword in ["slow", "performance", "loading", "timeout", "lag"]):
        bug_type = "performance"
    elif any(keyword in description_lower for keyword in ["ui", "interface", "button", "display", "layout", "css"]):
        bug_type = "ui"
    elif any(keyword in description_lower for keyword in ["error", "exception", "crash", "fail", "broken"]):
        bug_type = "error"
    elif any(keyword in description_lower for keyword in ["data", "database", "save", "load", "sync"]):
        bug_type = "data"
    else:
        bug_type = "general"
    
    # Create contextual subtasks based on bug type and include specific details
    base_subtasks = [
        {
            "id": str(uuid.uuid4()),
            "title": f"Investigate bug report: '{bug_title}' from {reporter_email}",
            "description": f"Review the detailed bug report from {reporter_email}. Key details to investigate: {bug_description[:200]}{'...' if len(bug_description) > 200 else ''}. Attempt to reproduce the issue and document initial findings.",
            "completed": False,
            "estimated_hours": 1.5,
            "priority": bug_priority,
            "category": "investigation"
        },
        {
            "id": str(uuid.uuid4()),
            "title": f"Analyze root cause of {bug_type} issue reported in '{bug_title}'",
            "description": f"Based on the bug report from {reporter_email}, perform detailed analysis to identify the root cause. Focus on {bug_type}-related components and check recent code changes that might have introduced this issue.",
            "estimated_hours": 2.0,
            "priority": bug_priority,
            "category": "analysis",
            "completed": False
        }
    ]
    
    # Add type-specific subtasks with context
    if bug_type == "authentication":
        base_subtasks.append({
            "id": str(uuid.uuid4()),
            "title": f"Fix authentication issue described in '{bug_title}'",
            "description": f"Implement fix for the authentication problem reported by {reporter_email}. Ensure the specific scenario described in their report is resolved and test with similar user credentials.",
            "estimated_hours": 2.5,
            "priority": bug_priority,
            "category": "implementation",
            "completed": False
        })
    elif bug_type == "performance":
        base_subtasks.append({
            "id": str(uuid.uuid4()),
            "title": f"Optimize performance issue in '{bug_title}'",
            "description": f"Address the performance problem reported by {reporter_email}. Profile the specific functionality mentioned in their report and implement optimizations to resolve the slowness they experienced.",
            "estimated_hours": 3.0,
            "priority": bug_priority,
            "category": "implementation",
            "completed": False
        })
    elif bug_type == "ui":
        base_subtasks.append({
            "id": str(uuid.uuid4()),
            "title": f"Fix UI/UX issue described in '{bug_title}'",
            "description": f"Resolve the user interface problem reported by {reporter_email}. Focus on the specific UI elements and behaviors they described to ensure the visual and interaction issues are fully addressed.",
            "estimated_hours": 2.0,
            "priority": bug_priority,
            "category": "implementation",
            "completed": False
        })
    else:
        base_subtasks.append({
            "id": str(uuid.uuid4()),
            "title": f"Implement fix for '{bug_title}'",
            "description": f"Develop and implement solution for the issue reported by {reporter_email}. Address the specific problems and scenarios described in their detailed bug report.",
            "estimated_hours": 2.5,
            "priority": bug_priority,
            "category": "implementation",
            "completed": False
        })
    
    # Add testing and communication subtasks with specific context
    base_subtasks.extend([
        {
            "id": str(uuid.uuid4()),
            "title": f"Test fix for bug report '{bug_title}' with reporter's scenario",
            "description": f"Thoroughly test the implemented fix using the exact steps and scenario described by {reporter_email}. Verify that their specific use case now works correctly and no regressions were introduced.",
            "estimated_hours": 1.5,
            "priority": "medium",
            "category": "testing",
            "completed": False
        },
        {
            "id": str(uuid.uuid4()),
            "title": f"Follow up with {reporter_email} about bug resolution",
            "description": f"Contact {reporter_email} to inform them that the bug '{bug_title}' has been resolved. Provide details about the fix and ask them to verify the solution works in their environment.",
            "estimated_hours": 0.5,
            "priority": "low",
            "category": "communication",
            "completed": False
        }
    ])
    
    # Add bug-specific metadata to all subtasks
    for subtask in base_subtasks:
        subtask["bug_report_metadata"] = {
            "reporter_email": reporter_email,
            "original_bug_title": bug_title,
            "bug_priority": bug_priority,
            "bug_type": bug_type,
            "description_preview": bug_description[:100]
        }
    
    logger.info(f"🔄 Generated {len(base_subtasks)} fallback bug report subtasks ({bug_type} type)")
    return base_subtasks

# Global service instance for easy access
bug_report_subtask_service = {
    "generate_bug_report_subtasks": generate_bug_report_subtasks
}