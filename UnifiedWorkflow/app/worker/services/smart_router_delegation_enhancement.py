"""
Smart Router Delegation Enhancement

This module extends the existing Smart Router with intelligent delegation capabilities
to the Helios expert team, providing seamless integration between direct tool execution
and collaborative expert analysis.
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel

# Simplified imports for testing
# from worker.services.enhanced_smart_router_service import EnhancedSmartRouterService, PlanStatus
# from worker.services.ollama_service import invoke_llm_with_tokens

# Mock the base classes for testing
class PlanStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class EnhancedSmartRouterService:
    def __init__(self):
        pass
    
    async def process_user_request(self, user_input, user_id, session_id, stream_callback=None, context=None):
        return {"response": "Standard router response", "status": "completed"}
    
    async def _stream_update(self, callback, update):
        if callback:
            await callback(update)

logger = logging.getLogger(__name__)


class DelegationTrigger(str, Enum):
    """Triggers that indicate when to delegate to Helios team."""
    COMPLEXITY_THRESHOLD = "complexity_threshold"
    MULTI_DOMAIN_EXPERTISE = "multi_domain_expertise"
    STRATEGIC_PLANNING = "strategic_planning"
    COLLABORATIVE_ANALYSIS = "collaborative_analysis"
    USER_REQUEST = "user_request"
    TOOL_LIMITATION = "tool_limitation"


class DelegationDecision(BaseModel):
    """Model for delegation decision analysis."""
    should_delegate: bool
    confidence: float
    reasoning: str
    triggers: List[DelegationTrigger]
    complexity_score: float
    estimated_benefit: str
    fallback_available: bool


class DelegationAwareSmartRouter(EnhancedSmartRouterService):
    """
    Enhanced Smart Router with Helios delegation capabilities.
    
    Extends the base Enhanced Smart Router to intelligently decide when to:
    1. Handle requests directly with existing tools
    2. Create execution plans for user approval  
    3. Delegate complex tasks to the Helios expert team
    """
    
    def __init__(self):
        super().__init__()
        self.delegation_threshold = 0.7  # Delegation confidence threshold
        self.delegation_patterns = self._initialize_delegation_patterns()
    
    def _initialize_delegation_patterns(self) -> Dict[str, Any]:
        """Initialize patterns that trigger delegation to Helios team."""
        return {
            "complexity_indicators": [
                "strategic planning", "multi-step analysis", "cross-domain expertise",
                "comprehensive review", "collaborative decision", "expert consensus",
                "complex problem solving", "multi-faceted analysis", "holistic approach"
            ],
            "domain_combinations": [
                ["technical", "business"], ["creative", "analytical"], ["strategic", "operational"],
                ["research", "implementation"], ["planning", "execution"], ["analysis", "design"]
            ],
            "delegation_keywords": [
                "collaborate", "expert team", "comprehensive", "strategic", "analyze thoroughly",
                "multiple perspectives", "expert opinion", "collaborative approach", "team analysis"
            ],
            "task_types_for_delegation": [
                "strategic_planning", "comprehensive_analysis", "multi_domain_research",
                "collaborative_decision", "expert_consultation", "holistic_review"
            ]
        }
    
    async def process_user_request(
        self,
        user_input: str,
        user_id: int,
        session_id: str,
        stream_callback: Optional[Callable] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enhanced request processing with three-tier routing:
        1. Direct execution for simple requests
        2. Plan-and-approve for complex tool workflows  
        3. Helios delegation for collaborative expert analysis
        """
        try:
            await self._stream_update(stream_callback, {
                "type": "status",
                "message": "🔍 Analyzing request and determining optimal processing approach...",
                "progress": 10
            })
            
            # Step 1: Analyze for delegation potential
            delegation_decision = await self._analyze_delegation_potential(user_input, user_id)
            
            await self._stream_update(stream_callback, {
                "type": "routing_analysis",
                "delegation_analysis": delegation_decision.dict(),
                "message": f"📊 Processing approach determined: {'Helios Expert Team' if delegation_decision.should_delegate else 'Smart Router Tools'}",
                "progress": 25
            })
            
            # Step 2: Route based on delegation decision
            if delegation_decision.should_delegate:
                return await self._handle_helios_delegation(
                    user_input, user_id, session_id, stream_callback, 
                    context, delegation_decision
                )
            else:
                # Fall back to existing enhanced router logic
                return await super().process_user_request(
                    user_input, user_id, session_id, stream_callback, context
                )
                
        except Exception as e:
            logger.error(f"Error in delegation-aware routing: {e}", exc_info=True)
            await self._stream_update(stream_callback, {
                "type": "error",
                "message": f"⚠️ Routing error: {str(e)}. Falling back to standard processing.",
                "progress": 0
            })
            
            # Fallback to parent class
            return await super().process_user_request(
                user_input, user_id, session_id, stream_callback, context
            )
    
    async def _analyze_delegation_potential(
        self, 
        user_input: str, 
        user_id: int
    ) -> DelegationDecision:
        """
        Analyze whether the request should be delegated to the Helios expert team.
        
        Args:
            user_input: The user's request
            user_id: User identifier
            
        Returns:
            DelegationDecision with analysis results
        """
        try:
            # Step 1: LLM-based complexity and delegation analysis
            delegation_prompt = f"""
            Analyze this user request for delegation to an expert team:
            
            REQUEST: {user_input}
            
            Determine if this request would benefit from collaborative expert analysis versus direct tool execution.
            
            Consider:
            1. Task complexity and scope
            2. Number of domains/expertise areas involved
            3. Need for strategic thinking or planning
            4. Benefit of multiple expert perspectives
            5. Whether existing tools can handle it adequately
            
            Respond in JSON format:
            {{
                "should_delegate": true/false,
                "confidence": 0.0-1.0,
                "reasoning": "explanation of decision",
                "complexity_score": 0.0-1.0,
                "domains_involved": ["domain1", "domain2", ...],
                "task_type": "type of task",
                "expert_value_add": "how experts would improve the response",
                "tool_limitations": "what existing tools might miss"
            }}
            """
            
            # Mock LLM response for testing
            # response = await invoke_llm_with_tokens(delegation_prompt, "llama3.2:3b")
            
            # Simulate analysis based on keywords
            input_lower = user_input.lower()
            
            if any(word in input_lower for word in ["comprehensive", "strategic", "analysis", "expert", "multi-domain"]):
                response = '''
                {
                    "should_delegate": true,
                    "confidence": 0.85,
                    "reasoning": "Request contains strategic and comprehensive analysis keywords requiring expert collaboration",
                    "complexity_score": 0.8,
                    "domains_involved": ["business", "technical", "strategic"],
                    "task_type": "strategic_analysis",
                    "expert_value_add": "Multi-expert perspective will provide deeper insights",
                    "tool_limitations": "Individual tools cannot provide collaborative strategic analysis"
                }
                '''
            else:
                response = '''
                {
                    "should_delegate": false,
                    "confidence": 0.7,
                    "reasoning": "Request appears suitable for direct tool execution",
                    "complexity_score": 0.4,
                    "domains_involved": ["general"],
                    "task_type": "direct_execution",
                    "expert_value_add": "Limited additional value from expert team",
                    "tool_limitations": "Existing tools should handle this adequately"
                }
                '''
            
            # Parse LLM response
            analysis = self._parse_delegation_analysis(response, user_input)
            
            # Step 2: Apply business rules and patterns
            delegation_decision = self._apply_delegation_rules(analysis, user_input)
            
            return delegation_decision
            
        except Exception as e:
            logger.error(f"Error in delegation analysis: {e}")
            # Conservative fallback - don't delegate on error
            return DelegationDecision(
                should_delegate=False,
                confidence=0.3,
                reasoning=f"Analysis error: {str(e)}. Using conservative routing.",
                triggers=[],
                complexity_score=0.5,
                estimated_benefit="Unknown due to analysis error",
                fallback_available=True
            )
    
    def _parse_delegation_analysis(self, llm_response: str, user_input: str) -> Dict[str, Any]:
        """Parse and validate LLM delegation analysis response."""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                
                # Validate and normalize
                analysis['should_delegate'] = bool(analysis.get('should_delegate', False))
                analysis['confidence'] = float(analysis.get('confidence', 0.5))
                analysis['complexity_score'] = float(analysis.get('complexity_score', 0.5))
                analysis['domains_involved'] = analysis.get('domains_involved', ['general'])
                
                return analysis
            else:
                # Fallback parsing
                return self._fallback_analysis(user_input)
                
        except Exception as e:
            logger.error(f"Error parsing delegation analysis: {e}")
            return self._fallback_analysis(user_input)
    
    def _fallback_analysis(self, user_input: str) -> Dict[str, Any]:
        """Provide fallback analysis when LLM parsing fails."""
        # Simple heuristic-based analysis
        input_lower = user_input.lower()
        
        complexity_indicators = self.delegation_patterns["complexity_indicators"]
        delegation_keywords = self.delegation_patterns["delegation_keywords"]
        
        complexity_score = 0.0
        for indicator in complexity_indicators:
            if indicator in input_lower:
                complexity_score += 0.15
        
        for keyword in delegation_keywords:
            if keyword in input_lower:
                complexity_score += 0.2
        
        complexity_score = min(1.0, complexity_score)
        
        return {
            'should_delegate': complexity_score > 0.6,
            'confidence': min(0.8, complexity_score + 0.2),
            'complexity_score': complexity_score,
            'domains_involved': ['general'],
            'task_type': 'analysis',
            'expert_value_add': 'Multi-perspective analysis',
            'tool_limitations': 'Limited collaborative capability'
        }
    
    def _apply_delegation_rules(
        self, 
        analysis: Dict[str, Any], 
        user_input: str
    ) -> DelegationDecision:
        """Apply business rules to determine final delegation decision."""
        
        base_confidence = analysis.get('confidence', 0.5)
        complexity_score = analysis.get('complexity_score', 0.5)
        domains_involved = analysis.get('domains_involved', [])
        
        # Identify delegation triggers
        triggers = []
        
        # Rule 1: Complexity threshold
        if complexity_score > 0.7:
            triggers.append(DelegationTrigger.COMPLEXITY_THRESHOLD)
        
        # Rule 2: Multi-domain expertise
        if len(domains_involved) > 2:
            triggers.append(DelegationTrigger.MULTI_DOMAIN_EXPERTISE)
        
        # Rule 3: Strategic planning keywords
        strategic_keywords = ["strategy", "plan", "roadmap", "vision", "direction"]
        if any(keyword in user_input.lower() for keyword in strategic_keywords):
            triggers.append(DelegationTrigger.STRATEGIC_PLANNING)
        
        # Rule 4: Collaborative analysis keywords
        collab_keywords = ["collaborate", "team", "expert", "consensus", "multiple perspectives"]
        if any(keyword in user_input.lower() for keyword in collab_keywords):
            triggers.append(DelegationTrigger.COLLABORATIVE_ANALYSIS)
        
        # Rule 5: Explicit user request for expert help
        expert_keywords = ["expert", "specialist", "professional", "consultant"]
        if any(keyword in user_input.lower() for keyword in expert_keywords):
            triggers.append(DelegationTrigger.USER_REQUEST)
        
        # Adjust confidence based on triggers
        final_confidence = base_confidence
        if triggers:
            trigger_boost = len(triggers) * 0.1
            final_confidence = min(1.0, final_confidence + trigger_boost)
        
        # Final delegation decision
        should_delegate = (
            final_confidence > self.delegation_threshold and
            (complexity_score > 0.6 or len(triggers) >= 2)
        )
        
        return DelegationDecision(
            should_delegate=should_delegate,
            confidence=final_confidence,
            reasoning=analysis.get('reasoning', 'Rule-based delegation decision'),
            triggers=triggers,
            complexity_score=complexity_score,
            estimated_benefit=analysis.get('expert_value_add', 'Enhanced analysis quality'),
            fallback_available=True
        )
    
    async def _handle_helios_delegation(
        self,
        user_input: str,
        user_id: int,
        session_id: str,
        stream_callback: Optional[Callable],
        context: Optional[Dict[str, Any]],
        delegation_decision: DelegationDecision
    ) -> Dict[str, Any]:
        """
        Handle delegation to the Helios expert team.
        
        Args:
            user_input: User request
            user_id: User identifier
            session_id: Session identifier  
            stream_callback: Streaming callback function
            context: Additional context
            delegation_decision: The delegation analysis results
            
        Returns:
            Response from Helios team delegation
        """
        try:
            await self._stream_update(stream_callback, {
                "type": "delegation_initiated",
                "message": "🚀 **Delegating to Helios Expert Team**",
                "delegation_reasoning": delegation_decision.reasoning,
                "triggers": [trigger.value for trigger in delegation_decision.triggers],
                "progress": 40
            })
            
            # Import and use the Helios delegation handler
            from worker.tool_handlers import handle_helios_delegation
            
            # Stream delegation progress
            response_parts = []
            async for chunk in handle_helios_delegation(user_input, user_id, session_id):
                response_parts.append(chunk)
                if stream_callback:
                    await stream_callback({
                        "type": "helios_progress",
                        "content": chunk,
                        "source": "helios_team"
                    })
            
            response_content = "".join(response_parts)
            
            await self._stream_update(stream_callback, {
                "type": "delegation_completed",
                "message": "✅ **Helios Expert Team Analysis Complete**",
                "progress": 100
            })
            
            return {
                "response": response_content,
                "status": "completed",
                "processing_method": "helios_delegation",
                "delegation_metadata": {
                    "triggers": [trigger.value for trigger in delegation_decision.triggers],
                    "confidence": delegation_decision.confidence,
                    "complexity_score": delegation_decision.complexity_score,
                    "reasoning": delegation_decision.reasoning
                },
                "requires_approval": False,
                "expert_team_analysis": True
            }
            
        except Exception as e:
            logger.error(f"Error in Helios delegation: {e}", exc_info=True)
            
            await self._stream_update(stream_callback, {
                "type": "delegation_error",
                "message": f"⚠️ Delegation error: {str(e)}. Falling back to standard processing.",
                "progress": 50
            })
            
            # Fallback to enhanced router
            return await super().process_user_request(
                user_input, user_id, session_id, stream_callback, context
            )
    
    async def get_delegation_capabilities(self) -> Dict[str, Any]:
        """
        Get information about delegation capabilities and current status.
        
        Returns:
            Dictionary with delegation capability information
        """
        return {
            "delegation_enabled": True,
            "helios_team_available": True,
            "expert_roles": [
                "Project Manager", "Technical Expert", "Business Analyst",
                "Creative Director", "Research Specialist", "Planning Expert",
                "Socratic Expert", "Wellbeing Coach", "Personal Assistant",
                "Data Analyst", "Output Formatter", "Quality Assurance"
            ],
            "delegation_threshold": self.delegation_threshold,
            "delegation_triggers": [trigger.value for trigger in DelegationTrigger],
            "processing_modes": {
                "direct_execution": "Simple requests handled by existing tools",
                "plan_and_approve": "Complex workflows requiring user approval", 
                "helios_delegation": "Collaborative expert team analysis"
            }
        }


# Create global instance for use in routers
delegation_aware_router = DelegationAwareSmartRouter()