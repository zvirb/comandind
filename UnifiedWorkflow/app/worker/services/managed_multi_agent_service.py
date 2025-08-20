
from enum import Enum
from typing import Dict, Any, List, TypedDict, Annotated
import json
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

class AgentRole(str, Enum):
    """Roles for the managed multi-agent system."""
    PROJECT_MANAGER = "Project Manager"
    TECHNICAL_EXPERT = "Technical Expert"
    BUSINESS_ANALYST = "Business Analyst"
    CREATIVE_DIRECTOR = "Creative Director"
    RESEARCH_SPECIALIST = "Research Specialist"
    PLANNING_EXPERT = "Planning Expert"
    SOCRATIC_EXPERT = "Socratic Expert"
    WELLBEING_COACH = "Wellbeing Coach"
    PERSONAL_ASSISTANT = "Personal Assistant"
    DATA_ANALYST = "Data Analyst"
    OUTPUT_FORMATTER = "Output Formatter"
    QUALITY_ASSURANCE = "Quality Assurance"

class AgentState(TypedDict):
    user_request: str
    selected_agents: List[str]
    discussion_context: Annotated[list, lambda x, y: x + y]
    final_response: str
    next_agent: str

class ManagedMultiAgentService:
    """
    A service that implements the "Managed Multi-Agent" workflow with a transparent discussion log,
    refactored to use langgraph.
    """

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("project_manager", self._run_project_manager)
        workflow.add_node("technical_expert", self._run_technical_expert)
        workflow.add_node("business_analyst", self._run_business_analyst)
        workflow.add_node("creative_director", self._run_creative_director)
        workflow.add_node("research_specialist", self._run_research_specialist)
        workflow.add_node("planning_expert", self._run_planning_expert)
        workflow.add_node("socratic_expert", self._run_socratic_expert)
        workflow.add_node("wellbeing_coach", self._run_wellbeing_coach)
        workflow.add_node("personal_assistant", self._run_personal_assistant)
        workflow.add_node("data_analyst", self._run_data_analyst)
        workflow.add_node("output_formatter", self._run_output_formatter)
        workflow.add_node("quality_assurance", self._run_quality_assurance)
        
        workflow.set_entry_point("project_manager")

        workflow.add_conditional_edges(
            "project_manager",
            self._route_to_next_agent,
            {
                "technical_expert": "technical_expert",
                "business_analyst": "business_analyst",
                "creative_director": "creative_director",
                "research_specialist": "research_specialist",
                "planning_expert": "planning_expert",
                "socratic_expert": "socratic_expert",
                "wellbeing_coach": "wellbeing_coach",
                "personal_assistant": "personal_assistant",
                "data_analyst": "data_analyst",
                "output_formatter": "output_formatter",
                "quality_assurance": "quality_assurance",
                "project_manager": "project_manager",
                "end": END
            }
        )
        
        for agent_name in self.get_agent_names():
            if agent_name != "project_manager":
                 workflow.add_edge(agent_name, "project_manager")

        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    def get_agent_names(self):
        return [role.name.lower() for role in AgentRole]

    def _route_to_next_agent(self, state: AgentState) -> str:
        return state.get("next_agent", "end")

    async def process_request(self, user_request: str, selected_agents: List[str] = None) -> Dict[str, Any]:
        config = {"configurable": {"thread_id": "1"}}
        initial_state = {
            "user_request": user_request,
            "selected_agents": selected_agents or [],
            "discussion_context": [],
            "next_agent": "project_manager"
        }
        
        final_state = await self.graph.ainvoke(initial_state, config)
        return final_state

    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().isoformat()

    async def _run_project_manager(self, state: AgentState) -> Dict[str, Any]:
        # Simplified PM logic for the graph
        discussion_context = state.get("discussion_context", [])
        if not discussion_context:
            # First turn
            next_agent = self._suggest_agents_for_request(state["user_request"])[0].name.lower()
            response = f"I'm the Project Manager. Based on your request, I'm delegating to the {next_agent.replace('_', ' ').title()}."
            return {"discussion_context": [{"expert": "Project Manager", "response": response}], "next_agent": next_agent}
        else:
            # Summarize and end
            summary = "Here's a summary of our discussion:\n"
            for entry in discussion_context:
                summary += f"- {entry['expert']}: {entry['response']}\n"
            return {"final_response": summary, "next_agent": "end"}

    async def _run_agent(self, agent_role: AgentRole, state: AgentState) -> Dict[str, Any]:
        response = f"I am the {agent_role.value}. I have analyzed the request and here are my findings."
        return {"discussion_context": [{"expert": agent_role.value, "response": response}], "next_agent": "project_manager"}

    async def _run_technical_expert(self, state: AgentState) -> Dict[str, Any]:
        return await self._run_agent(AgentRole.TECHNICAL_EXPERT, state)

    async def _run_business_analyst(self, state: AgentState) -> Dict[str, Any]:
        return await self._run_agent(AgentRole.BUSINESS_ANALYST, state)
        
    async def _run_creative_director(self, state: AgentState) -> Dict[str, Any]:
        return await self._run_agent(AgentRole.CREATIVE_DIRECTOR, state)

    async def _run_research_specialist(self, state: AgentState) -> Dict[str, Any]:
        return await self._run_agent(AgentRole.RESEARCH_SPECIALIST, state)

    async def _run_planning_expert(self, state: AgentState) -> Dict[str, Any]:
        return await self._run_agent(AgentRole.PLANNING_EXPERT, state)

    async def _run_socratic_expert(self, state: AgentState) -> Dict[str, Any]:
        return await self._run_agent(AgentRole.SOCRATIC_EXPERT, state)

    async def _run_wellbeing_coach(self, state: AgentState) -> Dict[str, Any]:
        return await self._run_agent(AgentRole.WELLBEING_COACH, state)

    async def _run_personal_assistant(self, state: AgentState) -> Dict[str, Any]:
        return await self._run_agent(AgentRole.PERSONAL_ASSISTANT, state)

    async def _run_data_analyst(self, state: AgentState) -> Dict[str, Any]:
        return await self._run_agent(AgentRole.DATA_ANALYST, state)

    async def _run_output_formatter(self, state: AgentState) -> Dict[str, Any]:
        return await self._run_agent(AgentRole.OUTPUT_FORMATTER, state)

    async def _run_quality_assurance(self, state: AgentState) -> Dict[str, Any]:
        return await self._run_agent(AgentRole.QUALITY_ASSURANCE, state)

    def _suggest_agents_for_request(self, request: str) -> List[AgentRole]:
        request_lower = request.lower()
        suggested = []
        if any(word in request_lower for word in ["code", "programming", "technical", "software", "system", "api", "database"]):
            suggested.append(AgentRole.TECHNICAL_EXPERT)
        if any(word in request_lower for word in ["business", "strategy", "market", "revenue", "roi", "growth"]):
            suggested.append(AgentRole.BUSINESS_ANALYST)
        if any(word in request_lower for word in ["design", "creative", "ui", "ux", "brand", "visual"]):
            suggested.append(AgentRole.CREATIVE_DIRECTOR)
        if any(word in request_lower for word in ["research", "data", "analysis", "study", "investigate"]):
            suggested.append(AgentRole.RESEARCH_SPECIALIST)
        if any(word in request_lower for word in ["plan", "timeline", "project", "roadmap", "schedule", "calendar", "time", "pomodoro", "assignment", "deadline", "tomorrow", "organize"]):
            suggested.append(AgentRole.PLANNING_EXPERT)
        if any(word in request_lower for word in ["wellbeing", "break", "pomodoro", "focus", "productivity", "stress", "balance", "wellness"]):
            suggested.append(AgentRole.WELLBEING_COACH)
        if any(word in request_lower for word in ["book", "calendar", "schedule", "organize", "reminder", "appointment", "task"]):
            suggested.append(AgentRole.PERSONAL_ASSISTANT)
        if any(word in request_lower for word in ["assignment", "homework", "study", "exam", "project", "deadline", "due"]):
            if AgentRole.PLANNING_EXPERT not in suggested:
                suggested.append(AgentRole.PLANNING_EXPERT)
            if AgentRole.WELLBEING_COACH not in suggested:
                suggested.append(AgentRole.WELLBEING_COACH)
            if AgentRole.PERSONAL_ASSISTANT not in suggested:
                suggested.append(AgentRole.PERSONAL_ASSISTANT)
        if not suggested:
            suggested.append(AgentRole.PLANNING_EXPERT)
        return suggested

managed_multi_agent_service = ManagedMultiAgentService()
