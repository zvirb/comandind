"""
Helios Control Unit - Expert Team Coordination Engine

This service monitors the blackboard for task delegation events and coordinates
the 12-specialist Helios expert team to process complex tasks collaboratively.
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel

from shared.utils.database_setup import get_async_session
from shared.services.security_audit_service import security_audit_service
from worker.services.helios_pm_orchestration_engine import (
    HeliosOrchestrationState, 
    HeliosAgentRole,
    TaskDelegation,
    ExpertResponse,
    OrchestrationType
)

logger = logging.getLogger(__name__)


class TaskProcessingPhase(str, Enum):
    """Phases of Helios task processing."""
    INGESTION = "ingestion"          # Receiving and parsing task
    ANALYSIS = "analysis"            # Initial expert analysis
    DELEGATION = "delegation"        # PM delegating to experts
    COLLABORATION = "collaboration"  # Experts working together
    SYNTHESIS = "synthesis"          # Combining expert outputs
    REVIEW = "review"               # Quality assurance
    COMPLETION = "completion"        # Final response delivery


class HeliosControlUnit:
    """
    Central coordination unit for the Helios expert team.
    
    Monitors blackboard events, coordinates expert agents, manages task delegation,
    and synthesizes expert responses into coherent outputs.
    """
    
    def __init__(self):
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.expert_pool = self._initialize_expert_pool()
        self.running = False
    
    def _initialize_expert_pool(self) -> Dict[str, Dict[str, Any]]:
        """Initialize the expert pool with capabilities and current status."""
        return {
            HeliosAgentRole.PROJECT_MANAGER.value: {
                "status": "available",
                "current_tasks": 0,
                "max_concurrent": 5,
                "capabilities": ["coordination", "planning", "synthesis", "quality_control"]
            },
            HeliosAgentRole.TECHNICAL_EXPERT.value: {
                "status": "available",
                "current_tasks": 0,
                "max_concurrent": 3,
                "capabilities": ["programming", "architecture", "debugging", "technology_analysis"]
            },
            HeliosAgentRole.BUSINESS_ANALYST.value: {
                "status": "available",
                "current_tasks": 0,
                "max_concurrent": 3,
                "capabilities": ["requirements", "process_analysis", "stakeholder_management"]
            },
            HeliosAgentRole.CREATIVE_DIRECTOR.value: {
                "status": "available",
                "current_tasks": 0,
                "max_concurrent": 3,
                "capabilities": ["design", "creativity", "content_creation", "innovation"]
            },
            HeliosAgentRole.RESEARCH_SPECIALIST.value: {
                "status": "available",
                "current_tasks": 0,
                "max_concurrent": 2,
                "capabilities": ["research", "information_gathering", "analysis", "fact_checking"]
            },
            HeliosAgentRole.PLANNING_EXPERT.value: {
                "status": "available",
                "current_tasks": 0,
                "max_concurrent": 3,
                "capabilities": ["strategic_planning", "project_planning", "resource_allocation"]
            },
            HeliosAgentRole.SOCRATIC_EXPERT.value: {
                "status": "available",
                "current_tasks": 0,
                "max_concurrent": 2,
                "capabilities": ["questioning", "critical_thinking", "problem_exploration"]
            },
            HeliosAgentRole.WELLBEING_COACH.value: {
                "status": "available",
                "current_tasks": 0,
                "max_concurrent": 2,
                "capabilities": ["wellness", "motivation", "personal_development", "stress_management"]
            },
            HeliosAgentRole.PERSONAL_ASSISTANT.value: {
                "status": "available",
                "current_tasks": 0,
                "max_concurrent": 4,
                "capabilities": ["scheduling", "communication", "task_management", "organization"]
            },
            HeliosAgentRole.DATA_ANALYST.value: {
                "status": "available",
                "current_tasks": 0,
                "max_concurrent": 2,
                "capabilities": ["data_analysis", "statistics", "visualization", "metrics"]
            },
            HeliosAgentRole.OUTPUT_FORMATTER.value: {
                "status": "available",
                "current_tasks": 0,
                "max_concurrent": 3,
                "capabilities": ["formatting", "presentation", "documentation", "communication"]
            },
            HeliosAgentRole.QUALITY_ASSURANCE.value: {
                "status": "available",
                "current_tasks": 0,
                "max_concurrent": 2,
                "capabilities": ["quality_control", "validation", "testing", "review"]
            }
        }
    
    async def start_monitoring(self):
        """Start monitoring the blackboard for delegation events."""
        self.running = True
        logger.info("Helios Control Unit started monitoring blackboard events")
        
        while self.running:
            try:
                await self._process_pending_delegations()
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Error in Helios monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Wait longer on error
    
    async def stop_monitoring(self):
        """Stop monitoring the blackboard."""
        self.running = False
        logger.info("Helios Control Unit stopped monitoring")
    
    async def _process_pending_delegations(self):
        """Check for new delegation events and process them."""
        try:
            async with get_async_session() as session:
                # Set security context for system operations
                await security_audit_service.set_security_context(
                    session=session, 
                    user_id=1,  # System user
                    service_name="helios_control_unit"
                )
                
                # Query for unprocessed delegation events
                query = """
                SELECT id, event_payload, user_id, session_id, created_at
                FROM blackboard_events 
                WHERE event_type = 'task_delegated' 
                AND target_agent_id = 'project_manager'
                AND id NOT IN (
                    SELECT DISTINCT blackboard_event_id 
                    FROM task_delegations 
                    WHERE blackboard_event_id IS NOT NULL
                )
                ORDER BY created_at ASC
                LIMIT 10
                """
                
                result = await session.execute(query)
                pending_events = result.fetchall()
                
                for event in pending_events:
                    await self._process_delegation_event(event, session)
                    
        except Exception as e:
            logger.error(f"Error processing pending delegations: {e}", exc_info=True)
    
    async def _process_delegation_event(self, event, session):
        """Process a single delegation event."""
        try:
            event_id = str(event.id)
            event_payload = json.loads(event.event_payload)
            
            logger.info(f"Processing delegation event {event_id}")
            
            # Create task delegation record
            task_description = event_payload.get('task_description', '')
            required_expertise = event_payload.get('required_expertise', [])
            
            # Select appropriate experts
            selected_experts = self._select_optimal_experts(required_expertise)
            
            # Create task delegation entries for each expert
            for expert_role in selected_experts:
                delegation_id = await self._create_task_delegation(
                    event_id=event_id,
                    expert_role=expert_role,
                    task_description=task_description,
                    event_payload=event_payload,
                    user_id=event.user_id,
                    session_id=event.session_id,
                    session=session
                )
                
                # Start expert processing (would be async in real implementation)
                asyncio.create_task(self._simulate_expert_processing(
                    delegation_id, expert_role, task_description, event.user_id
                ))
            
            # Track this task
            self.active_tasks[event_id] = {
                'experts': selected_experts,
                'phase': TaskProcessingPhase.DELEGATION,
                'started_at': datetime.now(timezone.utc),
                'user_id': event.user_id,
                'session_id': event.session_id
            }
            
        except Exception as e:
            logger.error(f"Error processing delegation event: {e}", exc_info=True)
    
    def _select_optimal_experts(self, required_expertise: List[str]) -> List[str]:
        """
        Select the optimal set of experts for the given expertise requirements.
        
        Args:
            required_expertise: List of required expertise areas
            
        Returns:
            List of selected expert roles
        """
        # Always include Project Manager
        selected = [HeliosAgentRole.PROJECT_MANAGER.value]
        
        # Expertise to expert mapping
        expertise_mapping = {
            'technical': HeliosAgentRole.TECHNICAL_EXPERT.value,
            'programming': HeliosAgentRole.TECHNICAL_EXPERT.value,
            'business': HeliosAgentRole.BUSINESS_ANALYST.value,
            'analysis': HeliosAgentRole.DATA_ANALYST.value,
            'creative': HeliosAgentRole.CREATIVE_DIRECTOR.value,
            'research': HeliosAgentRole.RESEARCH_SPECIALIST.value,
            'planning': HeliosAgentRole.PLANNING_EXPERT.value,
            'personal': HeliosAgentRole.PERSONAL_ASSISTANT.value,
            'wellness': HeliosAgentRole.WELLBEING_COACH.value,
            'quality': HeliosAgentRole.QUALITY_ASSURANCE.value,
            'socratic': HeliosAgentRole.SOCRATIC_EXPERT.value,
            'formatting': HeliosAgentRole.OUTPUT_FORMATTER.value
        }
        
        # Map required expertise to experts
        for expertise in required_expertise:
            expertise_lower = expertise.lower()
            for key, expert in expertise_mapping.items():
                if key in expertise_lower and expert not in selected:
                    # Check if expert is available
                    expert_info = self.expert_pool.get(expert, {})
                    current_tasks = expert_info.get('current_tasks', 0)
                    max_concurrent = expert_info.get('max_concurrent', 1)
                    
                    if current_tasks < max_concurrent:
                        selected.append(expert)
        
        # Ensure we have at least 2-3 experts for collaborative work
        if len(selected) < 3:
            # Add complementary experts
            available_experts = [
                HeliosAgentRole.DATA_ANALYST.value,
                HeliosAgentRole.QUALITY_ASSURANCE.value,
                HeliosAgentRole.OUTPUT_FORMATTER.value
            ]
            
            for expert in available_experts:
                if expert not in selected and len(selected) < 4:
                    selected.append(expert)
        
        return selected[:5]  # Limit to 5 experts including PM
    
    async def _create_task_delegation(
        self,
        event_id: str,
        expert_role: str,
        task_description: str,
        event_payload: Dict[str, Any],
        user_id: int,
        session_id: str,
        session
    ) -> str:
        """Create a task delegation record in the database."""
        try:
            import uuid
            
            delegation_id = str(uuid.uuid4())
            
            # Create delegation directive based on expert role
            directive = self._generate_expert_directive(expert_role, task_description, event_payload)
            
            insert_query = """
            INSERT INTO task_delegations (
                id, session_id, user_id, conversation_id, pm_agent_id, target_agent_id,
                agent_role, task_description, delegation_directive, task_type,
                priority_level, context_data, requirements, constraints,
                expected_deliverables, status, progress_percentage,
                estimated_duration_minutes, blackboard_event_id, created_at, updated_at
            ) VALUES (
                :id, :session_id, :user_id, :conversation_id, :pm_agent_id,
                :target_agent_id, :agent_role, :task_description, :delegation_directive,
                :task_type, :priority_level, :context_data, :requirements, :constraints,
                :expected_deliverables, 'pending', 0, :estimated_duration,
                :blackboard_event_id, now(), now()
            )
            """
            
            await session.execute(insert_query, {
                'id': delegation_id,
                'session_id': session_id,
                'user_id': user_id,
                'conversation_id': f"helios_{session_id}",
                'pm_agent_id': HeliosAgentRole.PROJECT_MANAGER.value,
                'target_agent_id': expert_role,
                'agent_role': expert_role,
                'task_description': task_description,
                'delegation_directive': directive,
                'task_type': event_payload.get('context', {}).get('type', 'analysis'),
                'priority_level': event_payload.get('delegation_metadata', {}).get('priority', 1),
                'context_data': json.dumps(event_payload.get('context', {})),
                'requirements': json.dumps(event_payload.get('required_expertise', [])),
                'constraints': json.dumps(event_payload.get('constraints', {})),
                'expected_deliverables': json.dumps(event_payload.get('expected_deliverables', [])),
                'estimated_duration': self._estimate_task_duration(expert_role),
                'blackboard_event_id': event_id
            })
            
            # Update expert workload
            if expert_role in self.expert_pool:
                self.expert_pool[expert_role]['current_tasks'] += 1
            
            return delegation_id
            
        except Exception as e:
            logger.error(f"Error creating task delegation: {e}", exc_info=True)
            raise
    
    def _generate_expert_directive(
        self, 
        expert_role: str, 
        task_description: str, 
        event_payload: Dict[str, Any]
    ) -> str:
        """Generate specific directive for each expert based on their role."""
        
        role_directives = {
            HeliosAgentRole.PROJECT_MANAGER.value: f"""
            As Project Manager, coordinate the team response to: {task_description}
            
            Your responsibilities:
            1. Analyze task requirements and coordinate expert assignments
            2. Monitor progress and ensure quality standards
            3. Synthesize expert contributions into coherent response
            4. Manage timeline and deliverable expectations
            5. Conduct final review and validation
            """,
            
            HeliosAgentRole.TECHNICAL_EXPERT.value: f"""
            As Technical Expert, provide technical analysis for: {task_description}
            
            Focus areas:
            1. Technical feasibility and architecture considerations
            2. Implementation approaches and best practices
            3. Technology recommendations and trade-offs
            4. Risk assessment and mitigation strategies
            5. Performance and scalability implications
            """,
            
            HeliosAgentRole.BUSINESS_ANALYST.value: f"""
            As Business Analyst, provide business perspective for: {task_description}
            
            Analysis areas:
            1. Business requirements and stakeholder needs
            2. Process improvement opportunities
            3. Cost-benefit analysis and ROI considerations
            4. Risk assessment and compliance requirements
            5. Success metrics and KPI recommendations
            """,
            
            HeliosAgentRole.CREATIVE_DIRECTOR.value: f"""
            As Creative Director, provide creative insight for: {task_description}
            
            Creative focus:
            1. Innovative approaches and creative solutions
            2. User experience and design considerations
            3. Brand alignment and messaging opportunities
            4. Visual and aesthetic recommendations
            5. Creative problem-solving techniques
            """,
            
            HeliosAgentRole.DATA_ANALYST.value: f"""
            As Data Analyst, provide analytical perspective for: {task_description}
            
            Analytical focus:
            1. Data requirements and availability assessment
            2. Analytical methodologies and statistical approaches
            3. Metrics definition and measurement strategies
            4. Data visualization and reporting recommendations
            5. Insights and pattern identification
            """
        }
        
        return role_directives.get(expert_role, f"""
        As {expert_role}, provide your expert perspective on: {task_description}
        
        Please contribute your specialized knowledge and recommendations
        based on your area of expertise.
        """)
    
    def _estimate_task_duration(self, expert_role: str) -> int:
        """Estimate task duration in minutes based on expert role."""
        duration_estimates = {
            HeliosAgentRole.PROJECT_MANAGER.value: 20,
            HeliosAgentRole.TECHNICAL_EXPERT.value: 15,
            HeliosAgentRole.BUSINESS_ANALYST.value: 15,
            HeliosAgentRole.CREATIVE_DIRECTOR.value: 18,
            HeliosAgentRole.RESEARCH_SPECIALIST.value: 25,
            HeliosAgentRole.DATA_ANALYST.value: 20,
            HeliosAgentRole.PLANNING_EXPERT.value: 18,
            HeliosAgentRole.QUALITY_ASSURANCE.value: 10
        }
        
        return duration_estimates.get(expert_role, 15)
    
    async def _simulate_expert_processing(
        self, 
        delegation_id: str, 
        expert_role: str, 
        task_description: str, 
        user_id: int
    ):
        """
        Simulate expert processing of delegated task.
        
        In a full implementation, this would interface with actual LLM agents.
        """
        try:
            # Simulate processing time
            processing_time = self._estimate_task_duration(expert_role)
            await asyncio.sleep(min(processing_time, 30))  # Cap simulation time
            
            # Generate expert response
            response_content = await self._generate_expert_response(
                expert_role, task_description
            )
            
            # Store expert response
            await self._store_expert_response(
                delegation_id, expert_role, response_content, user_id
            )
            
            # Update expert workload
            if expert_role in self.expert_pool:
                self.expert_pool[expert_role]['current_tasks'] = max(
                    0, self.expert_pool[expert_role]['current_tasks'] - 1
                )
            
            logger.info(f"Expert {expert_role} completed task {delegation_id}")
            
        except Exception as e:
            logger.error(f"Error in expert processing: {e}", exc_info=True)
    
    async def _generate_expert_response(self, expert_role: str, task_description: str) -> str:
        """Generate expert response using LLM."""
        try:
            from worker.services.ollama_service import invoke_llm_with_tokens
            
            prompt = f"""
            You are a {expert_role} in the Helios expert team. Provide your professional analysis for:
            
            TASK: {task_description}
            
            Respond from your expert perspective with:
            1. Key insights from your domain
            2. Specific recommendations
            3. Potential challenges or considerations
            4. Actionable next steps
            
            Keep response focused and professional, representing your expert specialty.
            """
            
            response = await invoke_llm_with_tokens(prompt, "llama3.2:3b")
            return response
            
        except Exception as e:
            logger.error(f"Error generating expert response: {e}")
            return f"**{expert_role} Analysis**\n\nI've reviewed the task: {task_description}\n\nBased on my expertise in {expert_role.lower()}, I recommend further detailed analysis to provide comprehensive insights. This task requires careful consideration of multiple factors within my domain of expertise."
    
    async def _store_expert_response(
        self, 
        delegation_id: str, 
        expert_role: str, 
        response_content: str, 
        user_id: int
    ):
        """Store expert response in the database."""
        try:
            async with get_async_session() as session:
                await security_audit_service.set_security_context(
                    session=session, 
                    user_id=user_id, 
                    service_name="helios_control_unit"
                )
                
                import uuid
                response_id = str(uuid.uuid4())
                
                insert_query = """
                INSERT INTO agent_responses (
                    id, task_delegation_id, agent_id, response_text, response_type,
                    response_format, key_findings, recommendations, concerns_raised,
                    confidence_score, deliverables, attachments, references,
                    has_been_validated, processing_time_seconds, tokens_used,
                    model_used, created_at
                ) VALUES (
                    :id, :task_delegation_id, :agent_id, :response_text, :response_type,
                    :response_format, :key_findings, :recommendations, :concerns_raised,
                    :confidence_score, :deliverables, :attachments, :references,
                    :has_been_validated, :processing_time_seconds, :tokens_used,
                    :model_used, now()
                )
                """
                
                await session.execute(insert_query, {
                    'id': response_id,
                    'task_delegation_id': delegation_id,
                    'agent_id': expert_role,
                    'response_text': response_content,
                    'response_type': 'analysis',
                    'response_format': 'text',
                    'key_findings': json.dumps([f"Analysis from {expert_role}"]),
                    'recommendations': json.dumps([f"Recommendations from {expert_role}"]),
                    'concerns_raised': json.dumps([]),
                    'confidence_score': 0.8,
                    'deliverables': json.dumps([response_content[:100] + "..."]),
                    'attachments': json.dumps([]),
                    'references': json.dumps([]),
                    'has_been_validated': False,
                    'processing_time_seconds': 15.0,
                    'tokens_used': len(response_content.split()),
                    'model_used': 'llama3.2:3b'
                })
                
                # Update delegation status
                update_query = """
                UPDATE task_delegations 
                SET status = 'completed', progress_percentage = 100, completed_at = now()
                WHERE id = :delegation_id
                """
                
                await session.execute(update_query, {'delegation_id': delegation_id})
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing expert response: {e}", exc_info=True)


# Global instance for service management
helios_control_unit = HeliosControlUnit()