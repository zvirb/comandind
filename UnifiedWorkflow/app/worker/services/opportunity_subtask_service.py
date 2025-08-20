#!/usr/bin/env python3
"""
Opportunity Subtask Generation Service

This service generates contextual, intelligent subtasks for opportunities
based on the opportunity title, user context, and supplementary information.
It replaces the generic "research, plan, execute" pattern with specific,
actionable steps tailored to each opportunity.
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from worker.services.ollama_service import invoke_llm_with_tokens
from shared.database.models import User, SystemPrompt
from shared.services.system_prompt_service import system_prompt_service
from shared.utils.database_setup import get_db

logger = logging.getLogger(__name__)

DEFAULT_SUBTASK_PROMPT = """You are an expert task breakdown specialist. When someone asks you "Can you please outline the steps I should take to accomplish this task?", you first evaluate if the task is suitable for step-by-step breakdown, then provide appropriate guidance.

**Step 1: Evaluate the Task Type**
Before generating steps, determine what type of task this is:

1. **Single Action** (doesn't need breakdown): "Send email to John", "Buy milk", "Call dentist"
2. **Vague/Abstract** (needs clarification): "Be happier", "Find purpose", "Improve life"  
3. **Personal/Subjective** (needs reflection): "Choose career", "Decide on relationship", "Find life partner"
4. **Context-Missing** (needs specifics): "Fix the bug", "Improve performance", "Optimize system"
5. **Extremely Complex** (needs project management): "Become a doctor", "Build billion-dollar company"
6. **Ongoing/Maintenance** (continuous process): "Stay healthy", "Maintain relationships"
7. **Perfect for Steps** (concrete, multi-step process): "Paint living room", "Learn Python", "Plan birthday party"

**Step 2: Provide Appropriate Response**

**For Single Actions:** Return JSON with guidance to not break down:
```json
{{
  "guidance_type": "single_action",
  "message": "This appears to be a single action that doesn't need to be broken down into subtasks. You can likely accomplish this in one step.",
  "subtasks": []
}}
```

**For Vague/Abstract Tasks:** Return JSON with clarification request:
```json
{{
  "guidance_type": "needs_clarification", 
  "message": "This goal needs more specificity to create actionable steps. Consider rephrasing as something like 'Establish a daily meditation practice' or 'Create a weekly exercise routine' instead.",
  "subtasks": []
}}
```

**For Personal/Subjective Decisions:** Return JSON with guidance to use other tools:
```json
{{
  "guidance_type": "personal_reflection",
  "message": "This appears to be a personal decision that would benefit from deeper reflection. Consider using the Socratic Chat mode for guided self-discovery, or speaking with a professional counselor or therapist for personalized guidance.",
  "subtasks": []
}}
```

**For Context-Missing Tasks:** Return JSON with request for details:
```json
{{
  "guidance_type": "needs_context",
  "message": "This task needs more specific details to create meaningful steps. Please provide more context about what exactly you want to accomplish.",
  "subtasks": []
}}
```

**For Extremely Complex Long-term Goals:** Return JSON with project management suggestion:
```json
{{
  "guidance_type": "complex_project",
  "message": "This is a complex, multi-year goal that would benefit from dedicated Project Management functionality (coming soon). For now, consider breaking this into smaller 3-6 month milestones and create subtasks for just the first milestone.",
  "subtasks": []
}}
```

**For Ongoing/Maintenance Tasks:** Create steps for establishing systems:
- Focus on creating sustainable systems, routines, or habits
- Include steps for setup, implementation, and maintenance
- Example: "Stay healthy" → "Design exercise routine", "Plan weekly meal prep", "Schedule regular checkups"

**For Perfect Step-by-Step Tasks:** Use the approach below...

**Examples of your step-by-step approach:**

**Q: "Can you please outline the steps I should take to paint my living room?"**
**A: Your steps would be:**
1. Research Paint Colors and Finishes
2. Measure the Room Dimensions
3. Calculate Square Meters to Paint
4. Purchase Paint, Primer, and Tools
5. Lay Down Protective Sheets
6. Sand and Prepare Wall Surfaces
7. Clean Walls and Remove Dust
8. Apply Painter's Tape to Edges
9. Apply Primer Base Coat
10. Paint First Color Coat
11. Paint Second Color Coat
12. Remove Masking Tape
13. Clean Up All Equipment

**Q: "Can you please outline the steps I should take to learn Python programming?"**
**A: Your steps would be:**
1. Install Python and Set Up Development Environment
2. Learn Basic Syntax and Data Types
3. Master Variables and Basic Operations
4. Understand Control Structures (if/else, loops)
5. Learn Functions and Parameters
6. Practice with Data Structures (lists, dictionaries)
7. Build Your First Complete Project
8. Learn Popular Libraries and Frameworks

**Q: "Can you please outline the steps I should take to start a small business?"**
**A: Your steps would be:**
1. Research Your Business Idea and Market
2. Write a Simple Business Plan
3. Choose Business Structure and Register
4. Obtain Necessary Licenses and Permits
5. Set Up Business Banking and Accounting
6. Create Your Product or Service
7. Develop Marketing Materials
8. Launch and Start Serving Customers

**Now answer this question:**
"Can you please outline the steps I should take to {opportunity_title}?"

**Context to consider:**
- Opportunity Title: {opportunity_title}
- Description: {opportunity_description}
- User Context: {user_context}
- Supplementary Context: {supplementary_context}

**Previous Generation Context (if regenerating):**
{regeneration_context}

**Instructions:**
Create 6-10 specific, actionable steps that someone would need to follow to accomplish "{opportunity_title}". Each step should be:
- A concrete action they can take
- Sequential and logical
- Specific enough to be actionable
- Similar to how you would explain it to a friend asking for help

Think of this as answering: "If someone asked me how to do this step by step, what would I tell them?"

**IMPORTANT REGENERATION RULES:**
- If this is a regeneration, DO NOT create tasks similar to the ones marked as "rejected" in the regeneration context
- DO NOT duplicate any tasks from the "selected" list in the regeneration context
- Create NEW, different approaches that the user might find more suitable
- Focus on alternative methods or different aspects of completing the opportunity

Respond with JSON in this exact format:
{{
  "subtasks": [
    {{
      "title": "Clear milestone or workflow step title",
      "description": "Detailed explanation of this workflow stage, what needs to be accomplished, and what the outcome should be",
      "estimated_hours": 2.5,
      "priority": "high/medium/low",
      "category": "planning/analysis/implementation/testing/deployment/review"
    }}
  ],
  "analysis": {{
    "opportunity_type": "software_development/business/learning/creative/maintenance/etc",
    "complexity_level": "beginner/intermediate/advanced",
    "total_estimated_hours": 12.5,
    "success_factors": ["key factor 1", "key factor 2"],
    "potential_obstacles": ["major obstacle 1", "major obstacle 2"]
  }}
}}

Remember: Each subtask should represent a meaningful phase in the workflow that brings the person significantly closer to completing the opportunity. Think of major milestones rather than micro-tasks."""

async def generate_contextual_subtasks(
    opportunity_title: str,
    opportunity_description: str = "",
    user_context: str = "",
    supplementary_context: str = "",
    current_user: Optional[User] = None,
    regeneration_context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Generate contextual subtasks for an opportunity using LLM intelligence
    """
    logger.info(f"🎯 Generating contextual subtasks for opportunity: {opportunity_title}")
    logger.info(f"📝 User context length: {len(user_context)} chars")
    logger.info(f"📝 Supplementary context length: {len(supplementary_context)} chars")
    
    try:
        # Get user-specific system prompt or use default
        system_prompt_text = DEFAULT_SUBTASK_PROMPT
        
        if current_user:
            try:
                with next(get_db()) as db:
                    custom_prompt = await system_prompt_service.get_prompt_for_user(
                        db, current_user.id, "opportunity_subtask_generation"
                    )
                    if custom_prompt:
                        system_prompt_text = custom_prompt
                        logger.info(f"🎨 Using custom user prompt for subtask generation")
                    else:
                        logger.info(f"📋 Using default system prompt for subtask generation")
            except Exception as prompt_error:
                logger.warning(f"⚠️ Failed to get custom prompt, using default: {prompt_error}")
        
        # Format regeneration context
        regeneration_text = ""
        if regeneration_context:
            selected_tasks = regeneration_context.get('selected_tasks', [])
            rejected_tasks = regeneration_context.get('rejected_tasks', [])
            attempt_number = regeneration_context.get('attempt', 1)
            
            regeneration_text = f"""
REGENERATION - Attempt #{attempt_number}

Selected tasks (DO NOT duplicate these):
{chr(10).join([f"- {task.get('title', 'Unknown')}" for task in selected_tasks]) if selected_tasks else "None selected yet"}

Rejected tasks (avoid similar approaches):
{chr(10).join([f"- {task.get('title', 'Unknown')}: {task.get('description', 'No description')}" for task in rejected_tasks]) if rejected_tasks else "None rejected yet"}

The user has deselected the rejected tasks above, which means they don't find those approaches suitable. Generate DIFFERENT subtasks that take alternative approaches to completing the opportunity.
"""
        else:
            regeneration_text = "This is the first generation attempt. No previous context."

        # Format the prompt with context
        formatted_prompt = system_prompt_text.format(
            opportunity_title=opportunity_title,
            opportunity_description=opportunity_description or "No additional description provided",
            user_context=user_context or "No specific user context provided",
            supplementary_context=supplementary_context or "No supplementary context provided",
            regeneration_context=regeneration_text
        )
        
        logger.info(f"🤖 Invoking LLM for contextual subtask generation...")
        logger.info(f"📏 Formatted prompt length: {len(formatted_prompt)} characters")
        
        # Use LLM to generate contextual subtasks
        response, token_info = await invoke_llm_with_tokens(
            messages=[
                {"role": "system", "content": "You are a task breakdown expert who creates specific, actionable subtasks. Always respond with valid JSON only."},
                {"role": "user", "content": formatted_prompt}
            ],
            model_name="llama3.2:3b",  # Use smaller model for faster response
            category="opportunity_subtask_generation"
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
                
                # Check if this is a guidance response (no subtasks, just guidance)
                guidance_type = parsed_data.get("guidance_type")
                if guidance_type:
                    guidance_message = parsed_data.get("message", "")
                    logger.info(f"📋 Received guidance type: {guidance_type}")
                    logger.info(f"💬 Guidance message: {guidance_message}")
                    
                    # Return a special result that indicates guidance was provided
                    return [{
                        "id": str(uuid.uuid4()),
                        "title": "💡 Guidance Provided",
                        "description": guidance_message,
                        "completed": False,
                        "estimated_hours": 0,
                        "priority": "high",
                        "category": "guidance",
                        "guidance_type": guidance_type,
                        "is_guidance": True
                    }]
                
                # Normal subtask processing
                subtasks_data = parsed_data.get("subtasks", [])
                analysis = parsed_data.get("analysis", {})
                
                logger.info(f"✅ Successfully parsed {len(subtasks_data)} contextual subtasks")
                logger.info(f"📊 Opportunity type: {analysis.get('opportunity_type', 'unknown')}")
                logger.info(f"📊 Complexity: {analysis.get('complexity_level', 'unknown')}")
                logger.info(f"📊 Total estimated hours: {analysis.get('total_estimated_hours', 'unknown')}")
                
                # Convert to required format with UUIDs and check for duplicates
                formatted_subtasks = []
                existing_titles = set()
                
                # Collect existing titles from regeneration context to avoid duplicates
                if regeneration_context:
                    for task in regeneration_context.get('selected_tasks', []):
                        existing_titles.add(task.get('title', '').lower().strip())
                
                for i, subtask_data in enumerate(subtasks_data):
                    subtask_title = subtask_data.get("title", f"Subtask {i+1}")
                    title_lower = subtask_title.lower().strip()
                    
                    # Check for duplicate titles (simple similarity check)
                    is_duplicate = False
                    for existing_title in existing_titles:
                        if title_lower == existing_title or _titles_are_similar(title_lower, existing_title):
                            logger.warning(f"⚠️ Skipping duplicate subtask: {subtask_title}")
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        formatted_subtask = {
                            "id": str(uuid.uuid4()),
                            "title": subtask_title,
                            "description": subtask_data.get("description", ""),
                            "completed": False,
                            "estimated_hours": subtask_data.get("estimated_hours", 1.0),
                            "priority": subtask_data.get("priority", "medium"),
                            "category": subtask_data.get("category", "execution")
                        }
                        formatted_subtasks.append(formatted_subtask)
                        existing_titles.add(title_lower)
                        
                        logger.debug(f"📅 Subtask {i+1}: {formatted_subtask['title']} ({formatted_subtask['estimated_hours']}h)")
                    else:
                        logger.debug(f"🚫 Skipped duplicate: {subtask_title}")
                
                if not formatted_subtasks:
                    logger.warning("❌ No subtasks generated by LLM, using fallback")
                    return _generate_fallback_contextual_subtasks(opportunity_title)
                
                logger.info(f"🎉 Generated {len(formatted_subtasks)} contextual subtasks successfully")
                return formatted_subtasks
                
            except json.JSONDecodeError as json_error:
                logger.error(f"❌ JSON parsing failed: {json_error}")
                logger.error(f"❌ Problematic JSON: {json_str}")
                raise ValueError(f"Could not parse LLM response as JSON: {json_error}")
        else:
            logger.error("❌ No JSON found in LLM response")
            logger.error(f"❌ Response preview: {response[:500]}...")
            raise ValueError("Could not extract JSON from LLM response")
            
    except Exception as e:
        logger.error(f"💥 Error in contextual subtask generation: {e}", exc_info=True)
        logger.warning("🔄 Falling back to contextual fallback subtasks...")
        return _generate_fallback_contextual_subtasks(opportunity_title)

def _generate_fallback_contextual_subtasks(opportunity_title: str) -> List[Dict[str, Any]]:
    """
    Generate fallback subtasks that are more contextual than generic placeholders
    """
    logger.info(f"🔄 Generating fallback contextual subtasks for: {opportunity_title}")
    
    # Analyze opportunity title for context clues
    title_lower = opportunity_title.lower()
    
    # Determine opportunity type from title keywords
    if any(keyword in title_lower for keyword in ["learn", "study", "course", "skill", "training"]):
        opportunity_type = "learning"
    elif any(keyword in title_lower for keyword in ["build", "create", "develop", "make", "design"]):
        opportunity_type = "creation"
    elif any(keyword in title_lower for keyword in ["improve", "enhance", "optimize", "upgrade"]):
        opportunity_type = "improvement"
    elif any(keyword in title_lower for keyword in ["career", "job", "promotion", "interview"]):
        opportunity_type = "career"
    elif any(keyword in title_lower for keyword in ["health", "fitness", "exercise", "diet"]):
        opportunity_type = "health"
    else:
        opportunity_type = "general"
    
    # Generate contextual subtasks based on type
    if opportunity_type == "learning":
        subtasks = [
            {
                "id": str(uuid.uuid4()),
                "title": f"Find and bookmark 3 specific learning resources for {opportunity_title}",
                "description": "Search for highly-rated courses, tutorials, or books specifically about this topic and save the links",
                "completed": False,
                "estimated_hours": 0.5,
                "priority": "high",
                "category": "research"
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"Set up dedicated workspace and install required tools for {opportunity_title}",
                "description": "Create a learning space, download necessary software, apps, or tools specifically needed for this subject",
                "completed": False,
                "estimated_hours": 1.0,
                "priority": "high",
                "category": "preparation"
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"Complete first beginner lesson or chapter of {opportunity_title}",
                "description": "Start with the very first tutorial, lesson, or exercise to build initial understanding",
                "completed": False,
                "estimated_hours": 2.0,
                "priority": "high",
                "category": "learning"
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"Practice {opportunity_title} with a small hands-on project or exercise",
                "description": "Apply what you've learned by doing a simple practice project or completing exercises",
                "completed": False,
                "estimated_hours": 2.5,
                "priority": "medium",
                "category": "execution"
            }
        ]
    elif opportunity_type == "creation":
        subtasks = [
            {
                "id": str(uuid.uuid4()),
                "title": f"Write down exactly what {opportunity_title} should look like when finished",
                "description": "Create a detailed description of the final outcome, including specific features, size, or requirements",
                "completed": False,
                "estimated_hours": 0.5,
                "priority": "high",
                "category": "planning"
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"Gather all materials, tools, or software needed to create {opportunity_title}",
                "description": "Make a list of everything required and acquire or install the necessary items",
                "completed": False,
                "estimated_hours": 1.0,
                "priority": "high",
                "category": "preparation"
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"Build the first working version or basic structure of {opportunity_title}",
                "description": "Create a simple, functional version that demonstrates the core concept",
                "completed": False,
                "estimated_hours": 3.0,
                "priority": "high",
                "category": "execution"
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"Test, improve, and add finishing touches to {opportunity_title}",
                "description": "Check if it works as intended, fix issues, and add any final improvements",
                "completed": False,
                "estimated_hours": 1.5,
                "priority": "medium",
                "category": "execution"
            }
        ]
    elif opportunity_type == "career":
        subtasks = [
            {
                "id": str(uuid.uuid4()),
                "title": f"Update resume and LinkedIn profile to align with {opportunity_title}",
                "description": "Add relevant skills, experiences, and keywords that match this career goal",
                "completed": False,
                "estimated_hours": 1.5,
                "priority": "high",
                "category": "preparation"
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"Identify and reach out to 3 people working in roles related to {opportunity_title}",
                "description": "Find professionals on LinkedIn or through your network and send personalized connection requests",
                "completed": False,
                "estimated_hours": 1.0,
                "priority": "high",
                "category": "communication"
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"Complete one concrete action that directly advances {opportunity_title}",
                "description": "Apply to a specific position, schedule an informational interview, or complete a certification",
                "completed": False,
                "estimated_hours": 2.0,
                "priority": "high",
                "category": "execution"
            }
        ]
    else:
        # General fallback - still more contextual than original
        subtasks = [
            {
                "id": str(uuid.uuid4()),
                "title": f"Find 2-3 specific examples or guides related to {opportunity_title}",
                "description": "Search online for people who have successfully done this exact thing and learn from their experience",
                "completed": False,
                "estimated_hours": 0.5,
                "priority": "high",
                "category": "research"
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"Write down the first 3 specific actions needed to start {opportunity_title}",
                "description": "List concrete steps you can take this week to begin making progress on this goal",
                "completed": False,
                "estimated_hours": 0.5,
                "priority": "high",
                "category": "planning"
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"Complete the first actionable step toward {opportunity_title}",
                "description": "Take the most important initial action that will create visible progress",
                "completed": False,
                "estimated_hours": 2.0,
                "priority": "high",
                "category": "execution"
            },
            {
                "id": str(uuid.uuid4()),
                "title": f"Assess what worked and plan the next specific step for {opportunity_title}",
                "description": "Evaluate your first step, note what you learned, and decide exactly what to do next",
                "completed": False,
                "estimated_hours": 0.5,
                "priority": "medium",
                "category": "review"
            }
        ]
    
    logger.info(f"🔄 Generated {len(subtasks)} fallback contextual subtasks ({opportunity_type} type)")
    return subtasks

def _titles_are_similar(title1: str, title2: str, threshold: float = 0.8) -> bool:
    """
    Check if two subtask titles are similar enough to be considered duplicates.
    Uses a combination of exact word matching and length similarity.
    
    Args:
        title1: First title to compare (lowercase)
        title2: Second title to compare (lowercase)
        threshold: Similarity threshold (0.0 to 1.0)
    
    Returns:
        True if titles are similar enough to be considered duplicates
    """
    if not title1 or not title2:
        return False
    
    # Remove common filler words and punctuation
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    
    def clean_title(title):
        # Remove punctuation and split into words
        import re
        words = re.findall(r'\b\w+\b', title.lower())
        # Remove stop words
        return [word for word in words if word not in stop_words and len(word) > 2]
    
    words1 = set(clean_title(title1))
    words2 = set(clean_title(title2))
    
    if not words1 or not words2:
        return False
    
    # Calculate word overlap
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    if union == 0:
        return False
    
    # Jaccard similarity (intersection over union)
    jaccard_similarity = intersection / union
    
    # Also check if one title is a substring of another (with some flexibility)
    shorter = title1 if len(title1) < len(title2) else title2
    longer = title2 if len(title1) < len(title2) else title1
    
    # If shorter title is mostly contained in longer title
    if len(shorter) > 10 and shorter in longer:
        return True
    
    # Return True if similarity is above threshold
    return jaccard_similarity >= threshold

# Global instance for easy access
opportunity_subtask_service = {
    "generate_contextual_subtasks": generate_contextual_subtasks
}