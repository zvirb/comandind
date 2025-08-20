"""
Adaptive Socratic Interview Service

This service uses the Socratic interview framework as a GUIDE, not a script.
It dynamically adapts questions based on user responses, past interactions,
and contextual insights to create truly personalized and insightful interviews.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from shared.database.models import User, AIAnalysisHistory
from shared.utils.database_setup import get_db
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.qdrant_service import QdrantService
from worker.smart_ai_models import TokenMetrics
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)


class AdaptiveSocraticInterviewService:
    """
    Adaptive Socratic Interview Service that uses prompts as guides and adapts
    based on user context, responses, and conversation history.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.qdrant_service = QdrantService()
        
        # Enhanced Socratic interview framework based on mission_state.txt methodology
        self.interview_frameworks = {
            "mission_statement": {
                "purpose": "Help user craft a powerful personal mission statement through structured Socratic inquiry",
                "overall_plan": "To help you craft a powerful personal mission statement, we'll move through four distinct phases. First, we'll explore your core values. Second, we'll identify your passions and unique skills. Third, we'll think about the impact you want to have. And finally, we'll bring it all together to draft your statement. Does that sound like a good path forward?",
                "phases": [
                    {
                        "name": "value_elicitation", 
                        "title": "Phase 1: Discovering Your Core Values",
                        "intent": "Guide user in unearthing core values through reflection on past actions and decisions",
                        "description": "Rather than asking 'What are your values?' directly, we explore what truly matters through specific situations",
                        "socratic_principles": ["Definition", "Elenchus", "Maieutics"],
                        "guide_questions": [
                            "To start, let's explore what truly matters to you. Instead of trying to name your values directly, could you describe a time when you had to make a really tough choice between two options? What was the situation, and what ultimately guided your decision?",
                            "That's revealing. Can you think of another scenario - perhaps a moment when you felt truly proud of something you accomplished? What was it about that achievement that made you feel proud? Was it the outcome, the process, or something else entirely?",
                            "Let's try a different angle. Can you describe a time when you witnessed something that genuinely upset or frustrated you? What was it about that situation that bothered you so much?"
                        ],
                        "follow_up_themes": ["implicit_values", "decision_criteria", "moral_compass", "pride_sources", "ethical_boundaries"],
                        "confidence_threshold": 0.7
                    },
                    {
                        "name": "passion_and_skills",
                        "title": "Phase 2: Identifying Your Passions & Skills", 
                        "intent": "Help user identify innate interests, strengths, and sources of energy through appreciative inquiry",
                        "description": "We'll uncover your innate interests and strengths through appreciative inquiry and creative exercises",
                        "socratic_principles": ["Maieutics", "Generalization"],
                        "guide_questions": [
                            "Let's try a creative exercise. Imagine you are 90 years old and have lived a completely fulfilling life. Write a brief letter to your present self describing what you accomplished and what makes you most proud. What legacy did you leave behind?",
                            "That's a powerful vision. Now, let's ground it in the present. Can you list three or four successes from your life, whether personal or professional? For each one, what specific actions did you take to make it happen?",
                            "Thinking about those successes, when have you been so absorbed in a task that you lost track of time? What was happening in those moments?"
                        ],
                        "follow_up_themes": ["flow_states", "natural_talents", "intrinsic_motivation", "peak_experiences", "effortless_competence"],
                        "confidence_threshold": 0.7
                    },
                    {
                        "name": "impact_and_legacy",
                        "title": "Phase 3: Exploring Your Impact & Legacy",
                        "intent": "Shift focus from internal desires to external contribution and desired impact",
                        "description": "Now we'll consider your desired contribution to others and the world around you",
                        "socratic_principles": ["Generalization", "Definition"],
                        "guide_questions": [
                            "Thinking beyond yourself for a moment, what does the world need most right now? What challenges or opportunities do you see in your specific corner of the world?",
                            "How do you see your unique skills and passions contributing to addressing that need? If you could achieve one thing in your lifetime that would positively affect others, what would it be?",
                            "Let's get specific about legacy. How do you want to be remembered? What would you want people to say about your contribution when you're no longer around?"
                        ],
                        "follow_up_themes": ["world_vision", "contribution_desire", "legacy_aspiration", "service_orientation", "impact_scope"],
                        "confidence_threshold": 0.7
                    },
                    {
                        "name": "synthesis",
                        "title": "Phase 4: Crafting Your Mission Statement",
                        "intent": "Transition from idea generation to concrete definition through collaborative writing",
                        "description": "Let's weave together your insights into a clear, actionable mission statement",
                        "socratic_principles": ["Generalization", "Definition", "Maieutics"],
                        "guide_questions": [
                            "Let's review the powerful themes we've collected: [values from your choices], [passions from your proudest moments], and [impact from your world vision]. What patterns do you notice emerging?",
                            "Now, let's try to combine a core value with a key skill to describe your impact. Don't worry about perfection - just try to get a first draft down in a single sentence.",
                            "This is a great start. Let's analyze this draft for clarity. Are there any vague terms we could make more specific? For example, if you wrote 'help people' - can we define which people and how you help them?"
                        ],
                        "follow_up_themes": ["integration", "clarity", "specificity", "actionability", "authenticity"],
                        "confidence_threshold": 0.8
                    }
                ],
                "state_fields": {
                    "user_values": "list[str]",
                    "user_passions_skills": "list[str]", 
                    "user_impact_legacy": "list[str]",
                    "draft_mission_statement": "str",
                    "critique_history": "list[str]",
                    "confidence_score": "float",
                    "task_status": "Enum(ELICITING, PROBING, SYNTHESIZING, COMPLETE)",
                    "iteration_count": "int",
                    "current_phase": "str",
                    "phase_completion": "dict"
                }
            },
            "work_style": {
                "purpose": "Help user understand their personal workflow design philosophy and technical decision-making style",
                "overall_plan": "To help you understand your unique work style and design philosophy, we'll explore four key dimensions. First, we'll look at how you prefer to structure workflows. Second, we'll examine your decision-making approach. Third, we'll explore your collaboration and communication preferences. Finally, we'll synthesize insights into actionable strategies. Sound good?",
                "phases": [
                    {
                        "name": "workflow_structure",
                        "title": "Phase 1: Workflow Structure Preferences", 
                        "intent": "Understand preferences for designing and organizing work processes",
                        "description": "Rather than asking about abstract preferences, we'll explore specific design scenarios",
                        "socratic_principles": ["Definition", "Elenchus"],
                        "guide_questions": [
                            "When starting a new project, do you prefer to define a rigid, end-to-end pipeline upfront, or build and connect modular components in a more flexible, adaptive way? Can you walk me through a specific example?",
                            "Think about a recent project where you had to make a structural choice. What factors influenced whether you went with a more structured or flexible approach?",
                            "Describe a time when your initial workflow design didn't work out as planned. How did you adapt, and what did that teach you about your design preferences?"
                        ],
                        "follow_up_themes": ["structure_vs_flexibility", "modularity", "adaptability", "planning_depth", "architecture_philosophy"],
                        "confidence_threshold": 0.7
                    },
                    {
                        "name": "decision_making_style",
                        "title": "Phase 2: Decision Making & Problem Solving",
                        "intent": "Reveal decision-making style when balancing methodical improvement vs. innovative approaches",
                        "description": "We'll use situational judgment scenarios to uncover your technical decision patterns",
                        "socratic_principles": ["Elenchus", "Perspective Taking"],
                        "guide_questions": [
                            "Scenario: Your current model is underperforming. Do you systematically perform a grid search over the hyperparameters, or try a completely novel, less-proven architecture you recently read about? Walk me through your reasoning.",
                            "Tell me about a time when you had to choose between a well-established solution and an experimental approach. What factors guided your decision?",
                            "When debugging a complex issue, do you prefer systematic elimination of possibilities, or do you rely more on intuition and pattern recognition? Can you give me a specific example?"
                        ],
                        "follow_up_themes": ["empirical_vs_experimental", "risk_tolerance", "debugging_approach", "innovation_vs_stability"],
                        "confidence_threshold": 0.7
                    },
                    {
                        "name": "collaboration_communication",
                        "title": "Phase 3: Collaboration & Communication Style",
                        "intent": "Understand communication preferences and documentation style in practical application",
                        "description": "We'll explore your natural communication patterns through role-playing scenarios",
                        "socratic_principles": ["Maieutics", "Definition"],
                        "guide_questions": [
                            "Let's role-play. Your workflow has just completed a 12-hour training run. Please draft the log summary you would save for this run. What would you include and how would you structure it?",
                            "When working with a team, do you prefer detailed documentation and formal handoffs, or more informal knowledge sharing? Can you describe a specific collaboration that went really well?",
                            "Think about how you prefer to receive feedback on your work. Do you like direct, specific critiques, or broader suggestions that let you figure out the details?"
                        ],
                        "follow_up_themes": ["documentation_style", "communication_formality", "feedback_preference", "knowledge_sharing"],
                        "confidence_threshold": 0.7
                    },
                    {
                        "name": "synthesis_strategies",
                        "title": "Phase 4: Synthesizing Your Design Manual",
                        "intent": "Translate stylistic preferences into actionable strategies for project success",
                        "description": "We'll create a personal workflow design manual based on your revealed preferences",
                        "socratic_principles": ["Generalization", "Implication Analysis"],
                        "guide_questions": [
                            "Looking at your preferences for experimental approaches and flexible design, what strategies can you put in place to ensure your projects remain systematic and don't become chaotic?",
                            "Based on our conversation, what patterns do you notice in how you approach technical challenges? What would you want to remember for future projects?",
                            "If you were mentoring someone with a similar work style to yours, what advice would you give them about leveraging their strengths while managing potential blind spots?"
                        ],
                        "follow_up_themes": ["self_awareness", "strategy_formulation", "strength_optimization", "weakness_mitigation"],
                        "confidence_threshold": 0.8
                    }
                ],
                "state_fields": {
                    "workflow_structure_insights": "list[str]",
                    "decision_making_patterns": "list[str]",
                    "collaboration_preferences": "list[str]",
                    "design_principles": "list[str]",
                    "confidence_score": "float",
                    "task_status": "Enum(ELICITING, PROBING, SYNTHESIZING, COMPLETE)",
                    "iteration_count": "int",
                    "current_phase": "str"
                }
            },
            "productivity_patterns": {
                "purpose": "Help user optimize resource management and workflow efficiency using energy-based approaches",
                "overall_plan": "To optimize your productivity through resource management, we'll examine four key areas. First, we'll audit your current performance patterns and bottlenecks. Second, we'll explore optimization strategies that match your style. Third, we'll deep-dive into your biggest workflow constraints. Finally, we'll design your ideal workflow configuration. Ready to optimize?",
                "phases": [
                    {
                        "name": "resource_performance_audit",
                        "title": "Phase 1: Resource & Performance Audit",
                        "intent": "Analyze current resource usage patterns, bottlenecks, and performance metrics",
                        "description": "We'll examine your workflow like a performance analyst, focusing on resource utilization over time management",
                        "socratic_principles": ["Evidence Exploration", "Definition"],
                        "guide_questions": [
                            "Let's analyze your last major workflow run. When did you observe the highest resource utilization (whether mental focus, computational power, or team collaboration)? Conversely, were there periods where resources were idle or underutilized?",
                            "Think about your biological prime time - when do you feel most mentally sharp and capable of complex work? How does this align with when you typically schedule your most demanding tasks?",
                            "Describe a recent day when everything seemed to flow smoothly versus one where you felt constantly blocked. What were the key differences in how resources were being used?"
                        ],
                        "follow_up_themes": ["resource_utilization", "energy_patterns", "bottleneck_identification", "flow_states", "peak_performance"],
                        "confidence_threshold": 0.7
                    },
                    {
                        "name": "optimization_strategy_matching",
                        "title": "Phase 2: Optimization Strategy Matching",
                        "intent": "Match user's style with appropriate resource management and optimization techniques",
                        "description": "Like a systems architect, we'll explore strategies that align with your natural patterns",
                        "socratic_principles": ["Assumption Checking", "Perspective Taking"],
                        "guide_questions": [
                            "Given that you've identified [specific bottleneck] as a key constraint, would a strategy of 'batch processing similar tasks' or 'context-switching for variety' be more effective for your style? What's your intuition?",
                            "When you think about energy management vs. time management, which resonates more with how you naturally work? Can you give me an example of when you've used energy-based planning successfully?",
                            "What productivity methods have you tried before? Which ones felt natural and which ones felt like swimming upstream against your natural tendencies?"
                        ],
                        "follow_up_themes": ["energy_management", "batch_processing", "context_switching", "natural_rhythms", "method_alignment"],
                        "confidence_threshold": 0.7
                    },
                    {
                        "name": "bottleneck_deep_dive",
                        "title": "Phase 3: Bottleneck Deep Dive",
                        "intent": "Map out specific workflow components and identify optimization opportunities",
                        "description": "Acting as a process analyst, we'll dissect your workflow to find leverage points",
                        "socratic_principles": ["Clarification", "Implication Analysis"],
                        "guide_questions": [
                            "Let's map out your [identified bottleneck process] step by step. What is the very first action you take? Where do you notice friction or slowdowns? Could some of these operations be parallelized, batched, or eliminated?",
                            "When this bottleneck occurs, what's your typical response? Do you power through, switch tasks, or take a break? Which approach tends to work best for you?",
                            "If you could redesign this process from scratch, knowing what you know now, what would you change? What constraints would you need to work around?"
                        ],
                        "follow_up_themes": ["process_mapping", "parallel_processing", "constraint_analysis", "redesign_opportunities", "workflow_optimization"],
                        "confidence_threshold": 0.7
                    },
                    {
                        "name": "ideal_workflow_design",
                        "title": "Phase 4: Designing Your Ideal Workflow",
                        "intent": "Create a concrete, actionable workflow configuration that incorporates all insights",
                        "description": "Like a planner, we'll synthesize everything into a practical system you can implement",
                        "socratic_principles": ["Synthesis", "Generalization"],
                        "guide_questions": [
                            "Now let's put it all together. We know your peak energy is [time period], your key bottleneck is [area], and your preferred optimization approach is [strategy]. Let's draft an ideal week template that incorporates these insights.",
                            "What would need to change in your current setup to implement this new workflow? What's the smallest change you could make that would have the biggest impact?",
                            "How will you know if this new approach is working? What metrics or feelings would tell you that your resource optimization is successful?"
                        ],
                        "follow_up_themes": ["ideal_week_design", "implementation_planning", "success_metrics", "incremental_improvement", "sustainable_systems"],
                        "confidence_threshold": 0.8
                    }
                ],
                "state_fields": {
                    "resource_audit_insights": "list[str]",
                    "optimization_strategies": "list[str]",
                    "bottleneck_analysis": "list[str]",
                    "ideal_workflow_config": "str",
                    "implementation_plan": "list[str]",
                    "confidence_score": "float",
                    "task_status": "Enum(ELICITING, PROBING, SYNTHESIZING, COMPLETE)",
                    "iteration_count": "int",
                    "current_phase": "str"
                }
            }
        }
    
    async def initiate_adaptive_interview(self, user_id: int, interview_type: str, 
                                        session_id: Optional[str] = None) -> Tuple[str, TokenMetrics]:
        """
        Initiate an adaptive Socratic interview that uses the framework as a guide
        but adapts to the specific user's context and past interactions.
        """
        try:
            # Gather comprehensive user context
            user_context = await self._gather_user_context(user_id)
            
            # Get interview framework
            framework = self.interview_frameworks.get(interview_type)
            if not framework:
                return f"Interview type '{interview_type}' not supported.", TokenMetrics()
            
            # Generate contextual opening question
            opening_response, token_metrics = await self._generate_adaptive_opening(
                user_context, framework, session_id
            )
            
            # Store interview state
            await self._store_interview_state(user_id, interview_type, "initiated", {
                "opening_response": opening_response,
                "framework": framework,
                "user_context": user_context
            }, session_id)
            
            return opening_response, token_metrics
            
        except Exception as e:
            logger.error(f"Error initiating adaptive interview: {e}", exc_info=True)
            return "I'd like to begin our conversation by understanding what matters most to you. Can you share what's currently on your mind?", TokenMetrics()
    
    async def continue_adaptive_interview(self, user_id: int, user_response: str,
                                        interview_type: str, session_id: Optional[str] = None) -> Tuple[str, TokenMetrics]:
        """
        Continue the interview using enhanced Socratic methodology with confidence scoring and conditional probing.
        """
        try:
            # Get current interview state and framework
            interview_state = await self._get_interview_state(user_id, interview_type, session_id)
            if not interview_state:
                return await self.initiate_adaptive_interview(user_id, interview_type, session_id)
            
            framework = self.interview_frameworks.get(interview_type, {})
            current_phase_name = interview_state.get('current_phase', 'value_elicitation')
            
            # Find current phase in framework
            current_phase = None
            for phase in framework.get('phases', []):
                if phase['name'] == current_phase_name:
                    current_phase = phase
                    break
            
            if not current_phase:
                current_phase = framework.get('phases', [{}])[0]  # Default to first phase
            
            # Update context with new response
            user_context = await self._update_context_with_response(user_id, user_response, interview_state)
            
            # CORE SOCRATIC LOGIC: Analyze response confidence
            confidence_score, analysis = await self._analyze_response_confidence(
                user_response, current_phase, user_context
            )
            
            logger.info(f"Response confidence analysis for user {user_id}: {confidence_score:.2f}")
            
            # CONDITIONAL ROUTING: Probe deeper or continue?
            threshold = current_phase.get('confidence_threshold', 0.7)
            should_probe = analysis.get('should_probe_deeper', False) or confidence_score < threshold
            
            # Track probing iterations to prevent infinite loops
            iteration_count = interview_state.get('iteration_count', 0)
            max_iterations = 3  # Prevent infinite probing
            
            if should_probe and iteration_count < max_iterations:
                # Generate Socratic probe for deeper exploration
                next_question, token_metrics = await self._generate_socratic_probe(
                    user_response, analysis, current_phase, user_context
                )
                
                # Update state with probing iteration
                await self._update_interview_state(user_id, interview_type, {
                    "last_response": user_response,
                    "confidence_analysis": analysis,
                    "current_phase": current_phase_name,
                    "iteration_count": iteration_count + 1,
                    "action_taken": "probing_deeper",
                    "confidence_score": confidence_score
                }, session_id)
                
                return next_question, token_metrics
                
            else:
                # Confidence threshold met or max iterations reached - continue to next phase/question
                iteration_count = 0  # Reset for next phase
                
                # Extract themes and update user context
                extracted_themes = analysis.get('extracted_themes', [])
                
                # Determine if we should advance to next phase
                should_advance_phase = confidence_score >= threshold
                
                if should_advance_phase:
                    # Move to next phase or continue within current phase
                    next_phase = self._get_next_phase(current_phase_name, framework)
                    if next_phase:
                        current_phase = next_phase
                        current_phase_name = next_phase['name']
                        logger.info(f"Advancing to phase: {current_phase_name}")
                
                # Generate adaptive follow-up using traditional method
                response_analysis = await self._analyze_user_response(user_response, user_context, interview_state)
                
                # Merge the two analyses to provide a richer context
                merged_analysis = {**analysis, **response_analysis}

                next_question, token_metrics = await self._generate_adaptive_follow_up(
                    user_response, merged_analysis, user_context, interview_state, session_id
                )
                
                # Update interview state
                await self._update_interview_state(user_id, interview_type, {
                    "last_response": user_response,
                    "confidence_analysis": analysis,
                    "response_analysis": response_analysis,
                    "current_phase": current_phase_name,
                    "iteration_count": iteration_count,
                    "action_taken": "advancing" if should_advance_phase else "continuing",
                    "confidence_score": confidence_score,
                    "extracted_themes": extracted_themes,
                    "updated_context": user_context
                }, session_id)
                
                return next_question, token_metrics
            
        except Exception as e:
            logger.error(f"Error continuing adaptive interview: {e}", exc_info=True)
            return "That's interesting. Can you tell me more about what that means to you?", TokenMetrics()
    
    def _get_next_phase(self, current_phase_name: str, framework: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Determine the next phase in the interview sequence."""
        phases = framework.get('phases', [])
        for i, phase in enumerate(phases):
            if phase['name'] == current_phase_name and i + 1 < len(phases):
                return phases[i + 1]
        return None
    
    async def _gather_user_context(self, user_id: int) -> Dict[str, Any]:
        """
        Gather comprehensive context about the user from database and knowledge base.
        """
        try:
            context = {}
            
            with next(get_db()) as db:
                # Get user profile
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    context.update({
                        "mission_statement": user.mission_statement,
                        "personal_goals": user.personal_goals,
                        "work_style_preferences": user.work_style_preferences,
                        "productivity_patterns": user.productivity_patterns,
                        "interview_insights": user.interview_insights
                    })
                
                # Get recent interview history
                recent_interviews = db.query(AIAnalysisHistory).filter(
                    AIAnalysisHistory.user_id == user_id,
                    AIAnalysisHistory.analysis_type.like('%interview%')
                ).order_by(AIAnalysisHistory.created_at.desc()).limit(5).all()
                
                context["recent_interview_themes"] = []
                for interview in recent_interviews:
                    if interview.output_data:
                        context["recent_interview_themes"].append({
                            "type": interview.analysis_type,
                            "insights": interview.output_data.get("insights", []),
                            "date": interview.created_at.isoformat()
                        })
            
            # Get semantic context from knowledge base
            try:
                search_results = await self.qdrant_service.search_points(
                    query_text="personal development interview insights",
                    limit=5,
                    user_id=user_id
                )
                
                context["knowledge_base_insights"] = []
                for result in search_results:
                    if hasattr(result, 'payload') and result.payload:
                        context["knowledge_base_insights"].append({
                            "text": result.payload.get('text', ''),
                            "source": result.payload.get('source', 'unknown')
                        })
            except Exception as e:
                logger.warning(f"Could not retrieve knowledge base context: {e}")
                context["knowledge_base_insights"] = []
            
            return context
            
        except Exception as e:
            logger.error(f"Error gathering user context: {e}", exc_info=True)
            return {}
    
    async def _generate_adaptive_opening(self, user_context: Dict[str, Any], 
                                       framework: Dict[str, Any], session_id: Optional[str]) -> Tuple[str, TokenMetrics]:
        """
        Generate an opening question that's adapted to the user's specific context.
        """
        try:
            system_prompt = """You are a masterful Socratic coach specializing in mission statement development. Your role is to use gentle, insightful questions to help people discover their own authentic purpose. You NEVER give advice or direct answers - you guide through strategic questioning.

CORE SOCRATIC PRINCIPLES:
- Definition: Clarify meaning of key concepts ("What does 'value' specifically mean to you?")
- Elenchus: Test consistency of beliefs ("How do these two sides of you co-exist?")
- Maieutics: Help birth knowledge they already possess ("Could that be a clue to a strength?")
- Generalization: Draw patterns from specific examples ("What common thread do you notice?")

APPROACH:
1. Create productive discomfort through gentle probing without causing disengagement
2. Use the framework as a GUIDE, not a script - adapt to this specific person
3. Ask follow-up questions that dig deeper into their unique situation
4. Build psychological safety through empathy and validation
5. Demonstrate active listening through paraphrasing and summarizing
6. Maintain curious, non-judgmental stance throughout

CONFIDENCE-BASED PROBING:
- If response feels vague/superficial: Ask clarifying questions to go deeper
- If response shows contradiction: Gently explore the tension
- If response is rich/substantive: Acknowledge and build upon it"""

            # Determine if this is the initial session or returning
            has_prior_mission = bool(user_context.get('mission_statement'))
            recent_themes = user_context.get('recent_interview_themes', [])
            
            user_prompt = f"""I'm conducting a {framework['purpose']} using the Plan-and-Solve approach. Here's what I know about this person:

USER CONTEXT:
- Current Mission Statement: {user_context.get('mission_statement', 'Not yet defined')}
- Personal Goals: {user_context.get('personal_goals', {})}
- Work Style: {user_context.get('work_style_preferences', {})}
- Interview History: {recent_themes}
- Knowledge Insights: {[insight.get('text', '')[:100] + '...' for insight in user_context.get('knowledge_base_insights', [])[:2]]}

INTERVIEW PLAN (Plan-and-Solve approach):
{framework.get('overall_plan', '')}

CURRENT PHASE: {framework['phases'][0]['title']}
Phase Intent: {framework['phases'][0]['intent']}
Description: {framework['phases'][0]['description']}
Socratic Principles to use: {', '.join(framework['phases'][0]['socratic_principles'])}

GUIDE QUESTIONS (adapt, don't copy):
{chr(10).join(f'- {q}' for q in framework['phases'][0]['guide_questions'])}

TASK: Create a personalized opening that:
1. {'Acknowledges their existing mission and suggests refinement' if has_prior_mission else 'Introduces the four-phase plan clearly'}
2. Uses their specific context to make the first question more relevant
3. Incorporates appropriate Socratic principles
4. Creates psychological safety while gently challenging them to think deeper
5. Shows you've been listening to their previous interactions (if any)

Generate a warm, personalized opening message followed by your first Socratic question."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response, token_metrics = await invoke_llm_with_tokens(
                messages,
                self.settings.OLLAMA_GENERATION_MODEL_NAME,
                category="adaptive_interview_opening"
            )
            
            return response, token_metrics
            
        except Exception as e:
            logger.error(f"Error generating adaptive opening: {e}", exc_info=True)
            return "I'd like to explore what matters most to you. Can you think of a time recently when you felt truly energized by what you were doing?", TokenMetrics()
    
    async def _analyze_user_response(self, user_response: str, user_context: Dict[str, Any], 
                                   interview_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the user's response to extract themes, emotions, and follow-up opportunities.
        """
        try:
            analysis_prompt = f"""Analyze this user's response in the context of their Socratic interview:

USER RESPONSE: "{user_response}"

USER CONTEXT:
{json.dumps(user_context, indent=2)}

INTERVIEW STATE:
Current Purpose: {interview_state.get('framework', {}).get('purpose', '')}
Previous Responses: {interview_state.get('conversation_history', [])}

ANALYSIS TASK:
Extract the following and format as JSON:
{{
  "key_themes": ["theme1", "theme2"],
  "emotional_tone": "descriptive emotional state",
  "values_revealed": ["value1", "value2"],
  "potential_contradictions": ["contradiction1"],
  "depth_opportunities": ["deeper question area1", "area2"],
  "personal_connections": ["connection to their context1", "connection2"],
  "suggested_follow_up_direction": "what to explore next"
}}

Focus on what this response reveals about their inner world and what would be most insightful to explore next."""

            messages = [
                {"role": "system", "content": "You are an expert at analyzing human responses for Socratic interviews. Extract deep insights about values, motivations, and areas for further exploration."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response, _ = await invoke_llm_with_tokens(
                messages,
                self.settings.OLLAMA_GENERATION_MODEL_NAME,
                category="response_analysis"
            )
            
            # Parse JSON response
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    return json.loads(response[json_start:json_end])
            except json.JSONDecodeError:
                logger.warning("Could not parse response analysis JSON")
            
            return {
                "key_themes": ["general_response"],
                "emotional_tone": "neutral",
                "values_revealed": [],
                "depth_opportunities": ["explore further"],
                "suggested_follow_up_direction": "dig deeper"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user response: {e}", exc_info=True)
            return {}
    
    async def _generate_adaptive_follow_up(self, user_response: str, response_analysis: Dict[str, Any],
                                         user_context: Dict[str, Any], interview_state: Dict[str, Any],
                                         session_id: Optional[str]) -> Tuple[str, TokenMetrics]:
        """
        Generate a follow-up question that's specifically adapted to their response and context.
        """
        try:
            system_prompt = """You are a masterful Socratic interviewer. Generate the PERFECT follow-up question based on what the user just shared. Your questions should:

1. Build directly on what they just said
2. Use their specific words and examples
3. Probe deeper into the most interesting parts of their response
4. Connect to their broader context and past experiences
5. Reveal underlying values and motivations
6. Feel like a natural continuation of a meaningful conversation

NEVER ask generic questions. Every question should feel personally crafted for this exact moment."""

            user_prompt = f"""The user just responded: "{user_response}"

RESPONSE ANALYSIS:
- Key themes: {response_analysis.get('key_themes', [])}
- Emotional tone: {response_analysis.get('emotional_tone', '')}
- Values revealed: {response_analysis.get('values_revealed', [])}
- Depth opportunities: {response_analysis.get('depth_opportunities', [])}
- Personal connections: {response_analysis.get('personal_connections', [])}
- Suggested direction: {response_analysis.get('suggested_follow_up_direction', '')}

USER'S BROADER CONTEXT:
- Mission: {user_context.get('mission_statement', 'Not defined')}
- Goals: {user_context.get('personal_goals', {})}
- Past themes: {[theme.get('insights', []) for theme in user_context.get('recent_interview_themes', [])][:2]}

INTERVIEW FRAMEWORK (as guide):
{interview_state.get('framework', {})}

CONVERSATION HISTORY:
{interview_state.get('conversation_history', [])}

Generate ONE perfectly crafted follow-up question that:
1. References something specific they just said
2. Builds on the most interesting aspect of their response
3. Helps them discover something new about themselves
4. Feels personally relevant to their unique situation
5. Follows Socratic principles (asks, doesn't tell)"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response, token_metrics = await invoke_llm_with_tokens(
                messages,
                self.settings.OLLAMA_GENERATION_MODEL_NAME,
                category="adaptive_follow_up"
            )
            
            return response, token_metrics
            
        except Exception as e:
            logger.error(f"Error generating adaptive follow-up: {e}", exc_info=True)
            return f"You mentioned something really interesting about {user_response[:50]}... Can you tell me more about what that means to you?", TokenMetrics()
    
    async def _analyze_response_confidence(self, user_response: str, current_phase: Dict[str, Any], 
                                         user_context: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Analyze user response for confidence level and quality using Socratic evaluation criteria.
        Returns confidence score (0.0-1.0) and analysis details.
        """
        try:
            system_prompt = """You are an expert evaluator of interview responses using Socratic methodology. 
            Your task is to assess the quality, depth, and authenticity of a user's response.

EVALUATION CRITERIA:
1. SPECIFICITY: Are examples concrete and detailed, or vague and general?
2. DEPTH: Does the response show self-reflection and insight, or surface-level thinking?
3. AUTHENTICITY: Does it feel genuine and personal, or generic and scripted?
4. COHERENCE: Is the response logically consistent and well-structured?
5. ENGAGEMENT: Does it show genuine reflection on the question asked?

CONFIDENCE SCORING:
- 0.9-1.0: Exceptional - Rich, specific, insightful, authentic response with clear self-awareness
- 0.7-0.8: Good - Solid response with some specificity and reflection, minor areas for deeper exploration
- 0.5-0.6: Moderate - General response with some useful content but lacking depth or specificity
- 0.3-0.4: Limited - Vague, superficial response that skims the surface
- 0.0-0.2: Poor - Very vague, off-topic, or dismissive response requiring significant probing

ANALYSIS OUTPUT: Provide JSON with confidence_score, areas_for_probing, and next_direction."""

            user_prompt = f"""INTERVIEW CONTEXT:
Current Phase: {current_phase.get('name', 'unknown')} - {current_phase.get('intent', '')}
Phase Confidence Threshold: {current_phase.get('confidence_threshold', 0.7)}
User Context: {user_context.get('mission_statement', 'No prior mission')}

USER RESPONSE TO ANALYZE:
"{user_response}"

CURRENT QUESTION THEMES: {current_phase.get('follow_up_themes', [])}

Please analyze this response and provide:
1. A confidence score (0.0-1.0) based on the criteria above
2. Specific areas that need deeper exploration (if any)
3. Assessment of whether we should probe deeper or move forward
4. Key themes or insights extracted from the response

Return ONLY a JSON object with this structure:
{{
    "confidence_score": 0.0,
    "quality_assessment": "explanation of score",
    "areas_for_probing": ["specific area 1", "specific area 2"],
    "extracted_themes": ["theme1", "theme2"],
    "should_probe_deeper": true/false,
    "next_direction": "suggested next step"
}}"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response, token_metrics = await invoke_llm_with_tokens(
                messages,
                self.settings.OLLAMA_GENERATION_MODEL_NAME,
                category="confidence_analysis"
            )
            
            try:
                # Parse JSON response
                analysis = json.loads(response.strip())
                confidence_score = float(analysis.get('confidence_score', 0.5))
                
                return confidence_score, analysis
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(f"Failed to parse confidence analysis JSON: {e}")
                # Fallback: basic heuristic analysis
                response_length = len(user_response.strip())
                word_count = len(user_response.split())
                
                # Simple heuristic scoring
                if response_length < 50 or word_count < 10:
                    confidence = 0.3
                elif response_length < 150 or word_count < 30:
                    confidence = 0.6
                else:
                    confidence = 0.8
                    
                return confidence, {
                    "confidence_score": confidence,
                    "quality_assessment": "Heuristic analysis - response length based",
                    "areas_for_probing": ["depth", "specificity"],
                    "extracted_themes": [],
                    "should_probe_deeper": confidence < current_phase.get('confidence_threshold', 0.7),
                    "next_direction": "probe_deeper" if confidence < 0.7 else "continue"
                }
                
        except Exception as e:
            logger.error(f"Error analyzing response confidence: {e}", exc_info=True)
            return 0.5, {
                "confidence_score": 0.5,
                "quality_assessment": "Analysis failed - using default",
                "areas_for_probing": ["general"],
                "extracted_themes": [],
                "should_probe_deeper": True,
                "next_direction": "probe_deeper"
            }

    async def _generate_socratic_probe(self, user_response: str, analysis: Dict[str, Any], 
                                     current_phase: Dict[str, Any], user_context: Dict[str, Any]) -> Tuple[str, TokenMetrics]:
        """
        Generate a Socratic probe when confidence score is low or when deeper exploration is needed.
        """
        try:
            system_prompt = """You are a masterful Socratic interviewer creating a follow-up probe. Your goal is to gently push deeper without causing the user to disengage.

SOCRATIC PROBING TECHNIQUES:
1. CLARIFICATION: "What do you mean when you say...?" "Can you give me a specific example?"
2. ASSUMPTION CHECKING: "What assumptions are you making here?" "How do you know that?"
3. EVIDENCE EXPLORATION: "What evidence supports that?" "How did you come to that conclusion?"
4. PERSPECTIVE TAKING: "How might someone who disagrees see this?" "What are the strengths/weaknesses?"
5. IMPLICATION ANALYSIS: "If that's true, then what?" "What are the consequences?"
6. META-QUESTIONING: "Why is this question important?" "What does this tell us about...?"

TONE GUIDELINES:
- Curious, not interrogational
- Supportive, not challenging
- Specific, not vague
- Personal, not generic
- Encouraging, not critical

Create a probe that feels like a natural conversation continuation."""

            areas_to_probe = analysis.get('areas_for_probing', [])
            probe_focus = areas_to_probe[0] if areas_to_probe else "general_depth"

            user_prompt = f"""USER'S RESPONSE: "{user_response}"

ANALYSIS INDICATES:
- Confidence Score: {analysis.get('confidence_score', 0.5)}
- Main areas needing exploration: {areas_to_probe}
- Quality assessment: {analysis.get('quality_assessment', '')}

CURRENT CONTEXT:
- Interview Phase: {current_phase.get('name', '')} - {current_phase.get('intent', '')}
- Socratic Principles for this phase: {current_phase.get('socratic_principles', [])}
- User's background: {user_context.get('mission_statement', 'No prior mission')}

FOCUS AREA FOR PROBE: {probe_focus}

Generate ONE gentle, curious follow-up question that:
1. References something specific from their response
2. Helps them go deeper into {probe_focus}
3. Uses appropriate Socratic technique from the list above
4. Maintains psychological safety and encouragement
5. Feels like a natural conversation flow

Just return the question - no explanations or formatting."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response, token_metrics = await invoke_llm_with_tokens(
                messages,
                self.settings.OLLAMA_GENERATION_MODEL_NAME,
                category="socratic_probe"
            )
            
            return response.strip(), token_metrics
            
        except Exception as e:
            logger.error(f"Error generating Socratic probe: {e}", exc_info=True)
            # Fallback to a generic but effective probe
            return f"That's interesting. When you mention '{user_response[:30]}...', can you help me understand what specifically made that meaningful to you?", TokenMetrics()
    
    async def _store_interview_state(self, user_id: int, interview_type: str, state: str,
                                   data: Dict[str, Any], session_id: Optional[str] = None):
        """Store current interview state for continuity."""
        try:
            with next(get_db()) as db:
                analysis_history = AIAnalysisHistory(
                    user_id=user_id,
                    analysis_type=f"adaptive_interview_{interview_type}",
                    input_data={
                        "interview_type": interview_type,
                        "state": state,
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat()
                    },
                    output_data=data,
                    model_used=self.settings.OLLAMA_GENERATION_MODEL_NAME
                )
                
                db.add(analysis_history)
                db.commit()
                
        except Exception as e:
            logger.error(f"Error storing interview state: {e}", exc_info=True)
    
    async def _get_interview_state(self, user_id: int, interview_type: str, 
                                 session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the current interview state."""
        try:
            with next(get_db()) as db:
                query = db.query(AIAnalysisHistory).filter(
                    AIAnalysisHistory.user_id == user_id,
                    AIAnalysisHistory.analysis_type == f"adaptive_interview_{interview_type}"
                )
                
                if session_id:
                    query = query.filter(
                        AIAnalysisHistory.input_data.op('->>')('session_id') == session_id
                    )
                
                latest_state = query.order_by(AIAnalysisHistory.created_at.desc()).first()
                
                if latest_state and latest_state.output_data:
                    return latest_state.output_data
                    
        except Exception as e:
            logger.error(f"Error getting interview state: {e}", exc_info=True)
        
        return None
    
    async def _update_context_with_response(self, user_id: int, user_response: str, 
                                          interview_state: Dict[str, Any]) -> Dict[str, Any]:
        """Update user context with their latest response."""
        try:
            # Get fresh context
            context = await self._gather_user_context(user_id)
            
            # Add conversation history
            conversation_history = interview_state.get('conversation_history', [])
            conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "user_response": user_response
            })
            
            context['conversation_history'] = conversation_history[-10:]  # Keep last 10 exchanges
            
            return context
            
        except Exception as e:
            logger.error(f"Error updating context: {e}", exc_info=True)
            return interview_state.get('user_context', {})
    
    async def _update_interview_state(self, user_id: int, interview_type: str, 
                                    updates: Dict[str, Any], session_id: Optional[str] = None):
        """Update the interview state with new information."""
        try:
            current_state = await self._get_interview_state(user_id, interview_type, session_id)
            if current_state:
                current_state.update(updates)
                await self._store_interview_state(user_id, interview_type, "updated", current_state, session_id)
                
        except Exception as e:
            logger.error(f"Error updating interview state: {e}", exc_info=True)


# Global instance
adaptive_socratic_interview_service = AdaptiveSocraticInterviewService()