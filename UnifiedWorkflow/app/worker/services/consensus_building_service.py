"""
Consensus Building Service for Multi-Agent Collaboration

Implements computational Delphi method, debate-based consensus, and convergence detection
for structured decision-making in expert group workflows.
"""

import json
import logging
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.blackboard_integration_service import (
    blackboard_integration_service, EventType, Performative
)
from shared.database.models.cognitive_state_models import (
    ConsensusMemoryNode, ValidationStatus
)

logger = logging.getLogger(__name__)


class ConsensusPhase(str, Enum):
    """Phases of the consensus building process."""
    INDEPENDENT_PROPOSALS = "independent_proposals"
    ANONYMIZED_FEEDBACK = "anonymized_feedback"
    ITERATIVE_REFINEMENT = "iterative_refinement"
    DEBATE_PREPARATION = "debate_preparation"
    STRUCTURED_DEBATE = "structured_debate"
    CONVERGENCE_ANALYSIS = "convergence_analysis"
    FINAL_CONSENSUS = "final_consensus"
    ARBITRATION = "arbitration"


class DebateRole(str, Enum):
    """Roles in structured debate."""
    PROPOSER = "proposer"
    CHALLENGER = "challenger"
    MEDIATOR = "mediator"
    VALIDATOR = "validator"


@dataclass
class ConsensusProposal:
    """Represents a consensus proposal with supporting evidence."""
    id: str
    agent_id: str
    agent_role: str
    proposal_text: str
    supporting_evidence: List[str]
    confidence_level: float
    reasoning: str
    trade_offs: List[str]
    implementation_considerations: List[str]
    created_at: datetime


@dataclass
class DebateArgument:
    """Represents a structured argument in debate."""
    id: str
    agent_id: str
    argument_type: str  # "support", "challenge", "counter", "clarification"
    target_proposal_id: Optional[str]
    premise: str
    evidence: List[str]
    logical_structure: str
    strength: float
    created_at: datetime


class ConsensusBuildingService:
    """Service for facilitating consensus building between agents."""
    
    def __init__(self):
        self.active_consensus_sessions = {}
        self.consensus_history = {}
    
    async def initiate_consensus_process(
        self,
        user_id: int,
        session_id: str,
        topic: str,
        participating_agents: List[Dict[str, str]],
        consensus_criteria: Dict[str, Any],
        method: str = "delphi"  # "delphi", "debate", "hybrid"
    ) -> str:
        """Initiate a consensus building process."""
        
        consensus_id = str(uuid.uuid4())
        
        # Initialize consensus session
        consensus_session = {
            "id": consensus_id,
            "user_id": user_id,
            "session_id": session_id,
            "topic": topic,
            "participating_agents": participating_agents,
            "consensus_criteria": consensus_criteria,
            "method": method,
            "current_phase": ConsensusPhase.INDEPENDENT_PROPOSALS,
            "proposals": [],
            "feedback_rounds": [],
            "debate_arguments": [],
            "convergence_metrics": {},
            "final_consensus": None,
            "started_at": datetime.now(timezone.utc),
            "completed_at": None
        }
        
        self.active_consensus_sessions[consensus_id] = consensus_session
        
        # Post blackboard event
        await blackboard_integration_service.post_blackboard_event(
            user_id=user_id,
            session_id=session_id,
            source_agent_id="consensus_facilitator",
            agent_role="Consensus Facilitator",
            event_type=EventType.GOAL_ESTABLISHED,
            performative=Performative.INFORM,
            event_payload={
                "consensus_id": consensus_id,
                "topic": topic,
                "method": method,
                "participating_agents": [agent["agent_id"] for agent in participating_agents],
                "criteria": consensus_criteria
            }
        )
        
        logger.info(f"Initiated {method} consensus process for topic: {topic}")
        return consensus_id
    
    async def collect_independent_proposals(
        self,
        consensus_id: str,
        timeout_minutes: int = 10
    ) -> List[ConsensusProposal]:
        """Collect independent proposals from all agents (Delphi Phase 1)."""
        
        session = self.active_consensus_sessions.get(consensus_id)
        if not session:
            raise ValueError(f"Consensus session {consensus_id} not found")
        
        logger.info(f"Collecting independent proposals for consensus {consensus_id}")
        
        proposals = []
        participating_agents = session["participating_agents"]
        
        # Collect proposals from each agent in parallel
        tasks = []
        for agent in participating_agents:
            task = self._collect_agent_proposal(session, agent)
            tasks.append(task)
        
        try:
            # Wait for all proposals with timeout
            proposal_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout_minutes * 60
            )
            
            for result in proposal_results:
                if isinstance(result, Exception):
                    logger.error(f"Error collecting proposal: {result}")
                elif result:
                    proposals.append(result)
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout collecting proposals for consensus {consensus_id}")
        
        # Store proposals in session
        session["proposals"] = proposals
        session["current_phase"] = ConsensusPhase.ANONYMIZED_FEEDBACK
        
        # Post blackboard event
        await blackboard_integration_service.post_blackboard_event(
            user_id=session["user_id"],
            session_id=session["session_id"],
            source_agent_id="consensus_facilitator",
            agent_role="Consensus Facilitator",
            event_type=EventType.AGENT_CONTRIBUTION,
            performative=Performative.INFORM,
            event_payload={
                "consensus_id": consensus_id,
                "phase": "proposals_collected",
                "proposal_count": len(proposals),
                "anonymized_proposals": [
                    {
                        "id": p.id,
                        "proposal": p.proposal_text,
                        "confidence": p.confidence_level,
                        "evidence_count": len(p.supporting_evidence)
                    }
                    for p in proposals
                ]
            }
        )
        
        logger.info(f"Collected {len(proposals)} proposals for consensus {consensus_id}")
        return proposals
    
    async def conduct_anonymized_feedback(
        self,
        consensus_id: str,
        max_rounds: int = 3
    ) -> List[Dict[str, Any]]:
        """Conduct anonymized feedback rounds (Delphi Phase 2)."""
        
        session = self.active_consensus_sessions.get(consensus_id)
        if not session:
            raise ValueError(f"Consensus session {consensus_id} not found")
        
        feedback_rounds = []
        current_proposals = session["proposals"]
        
        for round_num in range(max_rounds):
            logger.info(f"Conducting feedback round {round_num + 1} for consensus {consensus_id}")
            
            # Anonymize proposals for feedback
            anonymized_proposals = [
                {
                    "proposal_id": p.id,
                    "proposal_text": p.proposal_text,
                    "supporting_evidence": p.supporting_evidence,
                    "confidence_level": p.confidence_level,
                    "reasoning": p.reasoning
                }
                for p in current_proposals
            ]
            
            # Collect feedback from each agent
            round_feedback = []
            for agent in session["participating_agents"]:
                feedback = await self._collect_agent_feedback(
                    session, agent, anonymized_proposals, round_num + 1
                )
                if feedback:
                    round_feedback.append(feedback)
            
            feedback_rounds.append({
                "round": round_num + 1,
                "feedback": round_feedback,
                "convergence_score": self._calculate_convergence_score(round_feedback)
            })
            
            # Check for convergence
            if self._check_convergence(feedback_rounds):
                logger.info(f"Convergence detected after {round_num + 1} rounds")
                break
        
        session["feedback_rounds"] = feedback_rounds
        session["current_phase"] = ConsensusPhase.ITERATIVE_REFINEMENT
        
        return feedback_rounds
    
    async def conduct_structured_debate(
        self,
        consensus_id: str,
        debate_rounds: int = 3
    ) -> List[DebateArgument]:
        """Conduct structured debate with formal argumentation."""
        
        session = self.active_consensus_sessions.get(consensus_id)
        if not session:
            raise ValueError(f"Consensus session {consensus_id} not found")
        
        logger.info(f"Starting structured debate for consensus {consensus_id}")
        
        debate_arguments = []
        proposals = session["proposals"]
        
        # Assign debate roles
        agents = session["participating_agents"]
        role_assignments = self._assign_debate_roles(agents, proposals)
        
        for round_num in range(debate_rounds):
            logger.info(f"Debate round {round_num + 1}")
            
            # Each round: proposer presents, challengers respond, mediator facilitates
            round_arguments = []
            
            # Proposers present arguments
            for agent_id, role_info in role_assignments.items():
                if role_info["role"] == DebateRole.PROPOSER:
                    argument = await self._generate_debate_argument(
                        session, agent_id, role_info, "support", round_num + 1
                    )
                    if argument:
                        round_arguments.append(argument)
            
            # Challengers respond
            for agent_id, role_info in role_assignments.items():
                if role_info["role"] == DebateRole.CHALLENGER:
                    argument = await self._generate_debate_argument(
                        session, agent_id, role_info, "challenge", round_num + 1
                    )
                    if argument:
                        round_arguments.append(argument)
            
            # Mediator synthesizes
            mediator_id = next(
                (aid for aid, info in role_assignments.items() 
                 if info["role"] == DebateRole.MEDIATOR), 
                None
            )
            if mediator_id:
                argument = await self._generate_debate_argument(
                    session, mediator_id, role_assignments[mediator_id], 
                    "synthesize", round_num + 1
                )
                if argument:
                    round_arguments.append(argument)
            
            debate_arguments.extend(round_arguments)
            
            # Post round summary to blackboard
            await blackboard_integration_service.post_blackboard_event(
                user_id=session["user_id"],
                session_id=session["session_id"],
                source_agent_id="consensus_facilitator",
                agent_role="Consensus Facilitator",
                event_type=EventType.AGENT_CONTRIBUTION,
                performative=Performative.INFORM,
                event_payload={
                    "consensus_id": consensus_id,
                    "debate_round": round_num + 1,
                    "arguments_count": len(round_arguments),
                    "argument_types": [arg.argument_type for arg in round_arguments]
                }
            )
        
        session["debate_arguments"] = debate_arguments
        session["current_phase"] = ConsensusPhase.CONVERGENCE_ANALYSIS
        
        return debate_arguments
    
    async def analyze_convergence(self, consensus_id: str) -> Dict[str, Any]:
        """Analyze convergence and prepare final consensus."""
        
        session = self.active_consensus_sessions.get(consensus_id)
        if not session:
            raise ValueError(f"Consensus session {consensus_id} not found")
        
        logger.info(f"Analyzing convergence for consensus {consensus_id}")
        
        convergence_analysis = {
            "proposal_similarity": self._analyze_proposal_similarity(session["proposals"]),
            "feedback_consistency": self._analyze_feedback_consistency(session.get("feedback_rounds", [])),
            "debate_resolution": self._analyze_debate_resolution(session.get("debate_arguments", [])),
            "confidence_convergence": self._analyze_confidence_convergence(session["proposals"]),
            "overall_convergence_score": 0.0,
            "convergence_achieved": False,
            "consensus_recommendation": None
        }
        
        # Calculate overall convergence score
        scores = [
            convergence_analysis["proposal_similarity"],
            convergence_analysis["feedback_consistency"],
            convergence_analysis["debate_resolution"],
            convergence_analysis["confidence_convergence"]
        ]
        convergence_analysis["overall_convergence_score"] = sum(scores) / len(scores)
        
        # Determine if convergence achieved
        convergence_threshold = session["consensus_criteria"].get("convergence_threshold", 0.75)
        convergence_analysis["convergence_achieved"] = (
            convergence_analysis["overall_convergence_score"] >= convergence_threshold
        )
        
        if convergence_analysis["convergence_achieved"]:
            # Generate consensus recommendation
            convergence_analysis["consensus_recommendation"] = await self._generate_consensus_recommendation(session)
            session["current_phase"] = ConsensusPhase.FINAL_CONSENSUS
        else:
            # Prepare for arbitration
            session["current_phase"] = ConsensusPhase.ARBITRATION
        
        session["convergence_metrics"] = convergence_analysis
        
        return convergence_analysis
    
    async def finalize_consensus(self, consensus_id: str) -> Optional[Dict[str, Any]]:
        """Finalize consensus or initiate arbitration."""
        
        session = self.active_consensus_sessions.get(consensus_id)
        if not session:
            raise ValueError(f"Consensus session {consensus_id} not found")
        
        convergence_metrics = session.get("convergence_metrics", {})
        
        if convergence_metrics.get("convergence_achieved", False):
            # Finalize successful consensus
            final_consensus = convergence_metrics["consensus_recommendation"]
            session["final_consensus"] = final_consensus
            session["completed_at"] = datetime.now(timezone.utc)
            
            # Post consensus achieved event
            await blackboard_integration_service.post_blackboard_event(
                user_id=session["user_id"],
                session_id=session["session_id"],
                source_agent_id="consensus_facilitator",
                agent_role="Consensus Facilitator",
                event_type=EventType.CONSENSUS_REACHED,
                performative=Performative.CONFIRM,
                event_payload={
                    "consensus_id": consensus_id,
                    "final_consensus": final_consensus,
                    "convergence_score": convergence_metrics["overall_convergence_score"],
                    "participating_agents": [agent["agent_id"] for agent in session["participating_agents"]]
                }
            )
            
            logger.info(f"Consensus achieved for {consensus_id}")
            return final_consensus
        
        else:
            # Initiate arbitration
            arbitration_result = await self._conduct_arbitration(session)
            session["final_consensus"] = arbitration_result
            session["completed_at"] = datetime.now(timezone.utc)
            
            logger.info(f"Arbitration completed for {consensus_id}")
            return arbitration_result
    
    async def _collect_agent_proposal(
        self, 
        session: Dict[str, Any], 
        agent: Dict[str, str]
    ) -> Optional[ConsensusProposal]:
        """Collect independent proposal from a single agent."""
        
        agent_id = agent["agent_id"]
        agent_role = agent["agent_role"]
        
        proposal_prompt = f"""
        As the {agent_role}, provide an independent proposal for the following topic:
        
        Topic: {session['topic']}
        
        Your proposal should include:
        1. PROPOSAL: A clear, specific recommendation or solution
        2. REASONING: Your logical reasoning for this proposal
        3. EVIDENCE: Supporting evidence, facts, or considerations
        4. TRADE_OFFS: Potential drawbacks or limitations
        5. IMPLEMENTATION: Key implementation considerations
        6. CONFIDENCE: Your confidence level (0.0 to 1.0)
        
        Format your response as:
        PROPOSAL: [Your specific proposal]
        REASONING: [Your reasoning]
        EVIDENCE:
        - [Evidence point 1]
        - [Evidence point 2]
        TRADE_OFFS:
        - [Trade-off 1]
        - [Trade-off 2]
        IMPLEMENTATION:
        - [Implementation consideration 1]
        - [Implementation consideration 2]
        CONFIDENCE: [0.0 to 1.0]
        
        Provide your independent perspective without considering other proposals.
        """
        
        try:
            response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": proposal_prompt}],
                model_name="llama3.1:8b"
            )
            
            # Parse response
            parsed = self._parse_proposal_response(response)
            if parsed:
                proposal = ConsensusProposal(
                    id=str(uuid.uuid4()),
                    agent_id=agent_id,
                    agent_role=agent_role,
                    proposal_text=parsed["proposal"],
                    supporting_evidence=parsed["evidence"],
                    confidence_level=parsed["confidence"],
                    reasoning=parsed["reasoning"],
                    trade_offs=parsed["trade_offs"],
                    implementation_considerations=parsed["implementation"],
                    created_at=datetime.now(timezone.utc)
                )
                
                logger.info(f"Collected proposal from {agent_id}")
                return proposal
            
        except Exception as e:
            logger.error(f"Failed to collect proposal from {agent_id}: {e}")
        
        return None
    
    async def _collect_agent_feedback(
        self,
        session: Dict[str, Any],
        agent: Dict[str, str],
        anonymized_proposals: List[Dict[str, Any]],
        round_num: int
    ) -> Optional[Dict[str, Any]]:
        """Collect feedback from agent on anonymized proposals."""
        
        agent_id = agent["agent_id"]
        agent_role = agent["agent_role"]
        
        feedback_prompt = f"""
        As the {agent_role}, review these anonymized proposals for: {session['topic']}
        
        Round {round_num} Feedback Instructions:
        - Rate each proposal (1-5 scale)
        - Identify strengths and weaknesses
        - Suggest improvements
        - Assess feasibility
        
        Proposals to review:
        {json.dumps(anonymized_proposals, indent=2)}
        
        For each proposal, provide:
        PROPOSAL_ID: [proposal_id]
        RATING: [1-5]
        STRENGTHS: [What works well]
        WEAKNESSES: [Areas for improvement]
        SUGGESTIONS: [Specific improvement suggestions]
        FEASIBILITY: [Implementation feasibility assessment]
        
        Provide constructive, professional feedback focusing on improving the overall solution.
        """
        
        try:
            response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": feedback_prompt}],
                model_name="llama3.1:8b"
            )
            
            feedback = {
                "agent_id": agent_id,
                "agent_role": agent_role,
                "round": round_num,
                "feedback_text": response,
                "parsed_feedback": self._parse_feedback_response(response),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            return feedback
            
        except Exception as e:
            logger.error(f"Failed to collect feedback from {agent_id}: {e}")
            return None
    
    def _parse_proposal_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse agent proposal response."""
        try:
            lines = response.split('\n')
            proposal_data = {
                "proposal": "",
                "reasoning": "",
                "evidence": [],
                "trade_offs": [],
                "implementation": [],
                "confidence": 0.5
            }
            
            current_section = None
            for line in lines:
                line = line.strip()
                
                if line.startswith("PROPOSAL:"):
                    proposal_data["proposal"] = line.replace("PROPOSAL:", "").strip()
                    current_section = None
                elif line.startswith("REASONING:"):
                    proposal_data["reasoning"] = line.replace("REASONING:", "").strip()
                    current_section = None
                elif line.startswith("EVIDENCE:"):
                    current_section = "evidence"
                elif line.startswith("TRADE_OFFS:"):
                    current_section = "trade_offs"
                elif line.startswith("IMPLEMENTATION:"):
                    current_section = "implementation"
                elif line.startswith("CONFIDENCE:"):
                    try:
                        conf_str = line.replace("CONFIDENCE:", "").strip()
                        proposal_data["confidence"] = float(conf_str)
                    except ValueError:
                        proposal_data["confidence"] = 0.5
                elif line.startswith("-") and current_section:
                    item = line[1:].strip()
                    if item:
                        proposal_data[current_section].append(item)
            
            return proposal_data if proposal_data["proposal"] else None
            
        except Exception as e:
            logger.error(f"Failed to parse proposal response: {e}")
            return None
    
    def _parse_feedback_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse feedback response into structured format."""
        # Simplified parsing - in production, would use more robust parsing
        feedback_items = []
        
        try:
            # Basic parsing logic - extract key information
            lines = response.split('\n')
            current_feedback = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith("PROPOSAL_ID:"):
                    if current_feedback:
                        feedback_items.append(current_feedback)
                    current_feedback = {"proposal_id": line.replace("PROPOSAL_ID:", "").strip()}
                elif line.startswith("RATING:"):
                    try:
                        rating = int(line.replace("RATING:", "").strip())
                        current_feedback["rating"] = rating
                    except ValueError:
                        current_feedback["rating"] = 3
                elif line.startswith("STRENGTHS:"):
                    current_feedback["strengths"] = line.replace("STRENGTHS:", "").strip()
                elif line.startswith("WEAKNESSES:"):
                    current_feedback["weaknesses"] = line.replace("WEAKNESSES:", "").strip()
                elif line.startswith("SUGGESTIONS:"):
                    current_feedback["suggestions"] = line.replace("SUGGESTIONS:", "").strip()
                elif line.startswith("FEASIBILITY:"):
                    current_feedback["feasibility"] = line.replace("FEASIBILITY:", "").strip()
            
            if current_feedback:
                feedback_items.append(current_feedback)
                
        except Exception as e:
            logger.error(f"Failed to parse feedback response: {e}")
        
        return feedback_items
    
    def _calculate_convergence_score(self, feedback_round: List[Dict[str, Any]]) -> float:
        """Calculate convergence score for a feedback round."""
        if not feedback_round:
            return 0.0
        
        # Simplified convergence calculation based on rating variance
        all_ratings = []
        for feedback in feedback_round:
            parsed_feedback = feedback.get("parsed_feedback", [])
            for item in parsed_feedback:
                rating = item.get("rating", 3)
                all_ratings.append(rating)
        
        if not all_ratings:
            return 0.0
        
        # Calculate variance - lower variance indicates higher convergence
        mean_rating = sum(all_ratings) / len(all_ratings)
        variance = sum((r - mean_rating) ** 2 for r in all_ratings) / len(all_ratings)
        
        # Convert variance to convergence score (0-1)
        max_variance = 4.0  # Maximum possible variance for 1-5 scale
        convergence_score = max(0.0, 1.0 - (variance / max_variance))
        
        return convergence_score
    
    def _check_convergence(self, feedback_rounds: List[Dict[str, Any]]) -> bool:
        """Check if convergence has been achieved."""
        if len(feedback_rounds) < 2:
            return False
        
        # Check if convergence score is improving and above threshold
        recent_scores = [round_data["convergence_score"] for round_data in feedback_rounds[-2:]]
        
        return (
            recent_scores[-1] > 0.75 and  # High convergence score
            recent_scores[-1] >= recent_scores[-2]  # Not decreasing
        )
    
    def _assign_debate_roles(
        self, 
        agents: List[Dict[str, str]], 
        proposals: List[ConsensusProposal]
    ) -> Dict[str, Dict[str, Any]]:
        """Assign debate roles to agents."""
        role_assignments = {}
        
        # Assign roles based on proposal confidence and agent expertise
        sorted_agents = sorted(
            agents, 
            key=lambda a: max(
                (p.confidence_level for p in proposals if p.agent_id == a["agent_id"]), 
                default=0.5
            ),
            reverse=True
        )
        
        for i, agent in enumerate(sorted_agents):
            if i == 0:
                role = DebateRole.PROPOSER
            elif i == 1:
                role = DebateRole.CHALLENGER
            elif i == 2:
                role = DebateRole.MEDIATOR
            else:
                role = DebateRole.VALIDATOR
            
            role_assignments[agent["agent_id"]] = {
                "role": role,
                "agent_info": agent
            }
        
        return role_assignments
    
    async def _generate_debate_argument(
        self,
        session: Dict[str, Any],
        agent_id: str,
        role_info: Dict[str, Any],
        argument_type: str,
        round_num: int
    ) -> Optional[DebateArgument]:
        """Generate a structured debate argument."""
        
        # Implementation would generate formal arguments with evidence
        # This is a simplified version
        
        try:
            argument = DebateArgument(
                id=str(uuid.uuid4()),
                agent_id=agent_id,
                argument_type=argument_type,
                target_proposal_id=None,
                premise=f"Argument from {role_info['agent_info']['agent_role']}",
                evidence=[],
                logical_structure="premise -> evidence -> conclusion",
                strength=0.7,
                created_at=datetime.now(timezone.utc)
            )
            
            return argument
            
        except Exception as e:
            logger.error(f"Failed to generate debate argument: {e}")
            return None
    
    def _analyze_proposal_similarity(self, proposals: List[ConsensusProposal]) -> float:
        """Analyze similarity between proposals."""
        # Simplified similarity analysis
        if len(proposals) < 2:
            return 1.0
        
        # In production, would use semantic similarity analysis
        return 0.6  # Placeholder
    
    def _analyze_feedback_consistency(self, feedback_rounds: List[Dict[str, Any]]) -> float:
        """Analyze consistency in feedback across rounds."""
        if not feedback_rounds:
            return 0.0
        
        # Simplified consistency analysis
        return 0.7  # Placeholder
    
    def _analyze_debate_resolution(self, debate_arguments: List[DebateArgument]) -> float:
        """Analyze resolution achieved through debate."""
        if not debate_arguments:
            return 0.5
        
        # Simplified debate resolution analysis
        return 0.65  # Placeholder
    
    def _analyze_confidence_convergence(self, proposals: List[ConsensusProposal]) -> float:
        """Analyze convergence in confidence levels."""
        if not proposals:
            return 0.0
        
        confidence_levels = [p.confidence_level for p in proposals]
        mean_confidence = sum(confidence_levels) / len(confidence_levels)
        variance = sum((c - mean_confidence) ** 2 for c in confidence_levels) / len(confidence_levels)
        
        # Convert variance to convergence score
        return max(0.0, 1.0 - variance)
    
    async def _generate_consensus_recommendation(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final consensus recommendation."""
        
        # Synthesize proposals and feedback into final recommendation
        consensus_prompt = f"""
        Based on the following expert group discussion about: {session['topic']}
        
        Proposals submitted:
        {json.dumps([{"proposal": p.proposal_text, "confidence": p.confidence_level} for p in session["proposals"]], indent=2)}
        
        Generate a comprehensive consensus recommendation that:
        1. Synthesizes the best elements from all proposals
        2. Addresses concerns raised in feedback
        3. Provides clear implementation guidance
        4. Balances trade-offs identified
        
        Format your response as:
        CONSENSUS_RECOMMENDATION: [Clear, actionable recommendation]
        RATIONALE: [Why this recommendation represents the group consensus]
        IMPLEMENTATION_STEPS: [Specific steps for implementation]
        CONFIDENCE_LEVEL: [0.0 to 1.0]
        """
        
        try:
            response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": consensus_prompt}],
                model_name="llama3.1:8b"
            )
            
            # Parse consensus recommendation
            lines = response.split('\n')
            recommendation = {
                "recommendation": "",
                "rationale": "",
                "implementation_steps": [],
                "confidence_level": 0.8,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            current_section = None
            for line in lines:
                line = line.strip()
                if line.startswith("CONSENSUS_RECOMMENDATION:"):
                    recommendation["recommendation"] = line.replace("CONSENSUS_RECOMMENDATION:", "").strip()
                elif line.startswith("RATIONALE:"):
                    recommendation["rationale"] = line.replace("RATIONALE:", "").strip()
                elif line.startswith("IMPLEMENTATION_STEPS:"):
                    current_section = "implementation"
                elif line.startswith("CONFIDENCE_LEVEL:"):
                    try:
                        conf_str = line.replace("CONFIDENCE_LEVEL:", "").strip()
                        recommendation["confidence_level"] = float(conf_str)
                    except ValueError:
                        pass
                elif line.startswith("-") and current_section == "implementation":
                    step = line[1:].strip()
                    if step:
                        recommendation["implementation_steps"].append(step)
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Failed to generate consensus recommendation: {e}")
            return {
                "recommendation": "Unable to reach consensus - arbitration required",
                "rationale": "Insufficient convergence in expert opinions",
                "implementation_steps": [],
                "confidence_level": 0.3,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
    
    async def _conduct_arbitration(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct arbitration when consensus cannot be reached."""
        
        logger.info(f"Conducting arbitration for consensus session {session['id']}")
        
        # In production, this would implement formal arbitration protocols
        # For now, return a mediated decision
        
        arbitration_result = {
            "decision": "Arbitrated decision based on expert input",
            "rationale": "Consensus could not be reached through normal processes",
            "implementation_steps": ["Implement arbitrated solution", "Monitor for effectiveness"],
            "confidence_level": 0.6,
            "arbitration_method": "expert_mediation",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Post arbitration event
        await blackboard_integration_service.post_blackboard_event(
            user_id=session["user_id"],
            session_id=session["session_id"],
            source_agent_id="consensus_facilitator",
            agent_role="Consensus Facilitator",
            event_type=EventType.DECISION_MADE,
            performative=Performative.ASSERT,
            event_payload={
                "consensus_id": session["id"],
                "arbitration_result": arbitration_result,
                "reason": "consensus_not_achieved"
            }
        )
        
        return arbitration_result


# Global service instance
consensus_building_service = ConsensusBuildingService()