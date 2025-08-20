"""
Enhanced Router Service with LangChain 0.3+ features:
- Structured outputs with Pydantic models
- Native LCEL streaming
- Enhanced tool calling
- Better error handling and type safety
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator
from uuid import uuid4

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

# Local imports
from worker.graph_types import GraphState
from worker.tool_handlers import get_tool_handler
from shared.schemas.enhanced_chat_schemas import (
    ToolExecutionResult, IntermediateStep, EnhancedGraphState,
    ExecutiveDecision, ToolExecutionStatus, OllamaStructuredRequest, OllamaStructuredResponse
)
from shared.utils.config import get_settings
from worker.services.ollama_service import invoke_llm_with_tokens

logger = logging.getLogger(__name__)
settings = get_settings()

# Structured output schemas for routing decisions
class IntentAnalysis(BaseModel):
    """Structured intent analysis output."""
    primary_intent: str = Field(..., description="Primary user intent category")
    complexity: str = Field(..., description="Request complexity: simple, moderate, complex")
    is_multi_step: bool = Field(..., description="Whether request requires multiple steps")
    confidence: float = Field(..., ge=0, le=1, description="Analysis confidence score")
    recommended_tools: List[str] = Field(default_factory=list, description="Recommended tools")
    context_requirements: List[str] = Field(default_factory=list, description="Required context")
    estimated_steps: Optional[List[str]] = Field(None, description="Estimated processing steps if multi-step")

class ToolSelection(BaseModel):
    """Structured tool selection output."""
    selected_tool: str = Field(..., description="Selected tool identifier")
    confidence: float = Field(..., ge=0, le=1, description="Selection confidence")
    reasoning: str = Field(..., description="Selection reasoning")
    fallback_tools: List[str] = Field(default_factory=list, description="Alternative tools")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")

class ExecutiveRoutingDecision(BaseModel):
    """Structured executive routing decision."""
    decision: ExecutiveDecision = Field(..., description="Routing decision")
    confidence: float = Field(..., ge=0, le=1, description="Decision confidence")
    reasoning: str = Field(..., description="Decision reasoning")
    suggested_approach: str = Field(..., description="Suggested processing approach")
    estimated_complexity: str = Field(..., description="Estimated task complexity")

class EnhancedRouterService:
    """Enhanced router service with LangChain 0.3+ features."""
    
    def __init__(self):
        self.ollama_base_url = settings.OLLAMA_API_BASE_URL
        self.default_model = settings.OLLAMA_GENERATION_MODEL_NAME
        
    async def create_structured_llm(self, model: str, response_schema: BaseModel) -> ChatOllama:
        """Create LLM instance with structured output binding."""
        llm = ChatOllama(
            model=model,
            base_url=self.ollama_base_url,
            temperature=0.1,
            num_ctx=8192
        )
        
        # Bind structured output schema (LangChain 0.3+ feature)
        return llm.with_structured_output(response_schema)
    
    async def analyze_intent_structured(self, user_message: str, state: GraphState) -> IntentAnalysis:
        """Analyze user intent with structured output."""
        try:
            llm = await self.create_structured_llm(
                model=state.chat_model or self.default_model,
                response_schema=IntentAnalysis
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert intent analyzer. Analyze the user's request and provide structured output.
                
                Consider:
                1. What is the user trying to accomplish?
                2. How complex is the request?
                3. Does it require multiple steps or tools?
                4. What tools might be needed?
                5. What context is required?
                
                Available tool categories:
                - Calendar management (scheduling, viewing events)
                - Document processing (search, analysis, Q&A)
                - Email management (compose, search, prioritize)
                - Home automation (device control, status)
                - Web search (information gathering)
                - Task management (create, track, organize)
                - File operations (read, write, organize)
                - Socratic guidance (coaching, reflection)
                """),
                ("human", "{message}")
            ])
            
            chain = prompt | llm
            result = await chain.ainvoke({"message": user_message})
            
            return result
            
        except Exception as e:
            logger.error(f"Error in structured intent analysis: {e}")
            # Fallback to basic analysis
            return IntentAnalysis(
                primary_intent="general_query",
                complexity="simple",
                is_multi_step=False,
                confidence=0.5,
                recommended_tools=["unstructured_interaction"]
            )
    
    async def select_tool_structured(self, intent_analysis: IntentAnalysis, user_message: str, state: GraphState) -> ToolSelection:
        """Select appropriate tool with structured output."""
        try:
            llm = await self.create_structured_llm(
                model=state.tool_routing_model or self.default_model,
                response_schema=ToolSelection
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert tool selector. Based on the intent analysis, select the most appropriate tool.
                
                Available tools:
                - unstructured_interaction: General conversation, unclear requests
                - calendar_management: Schedule, view, edit calendar events
                - document_qa: Search and analyze documents
                - email_management: Compose, search, organize emails
                - home_assistant: Control smart home devices
                - web_search: Search the internet for information
                - task_management: Create, track, organize tasks
                - file_system: Read, write, organize files
                - socratic_guidance: Coaching and reflective questions
                
                Select the single best tool for this request.
                """),
                ("human", """Intent Analysis: {intent}
                User Message: {message}""")
            ])
            
            chain = prompt | llm
            result = await chain.ainvoke({
                "intent": intent_analysis.dict(),
                "message": user_message
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in structured tool selection: {e}")
            # Fallback selection
            return ToolSelection(
                selected_tool="unstructured_interaction",
                confidence=0.5,
                reasoning="Fallback due to error in tool selection",
                parameters={"user_input": user_message}
            )
    
    async def make_executive_decision(self, user_message: str, state: GraphState) -> ExecutiveRoutingDecision:
        """Make executive routing decision with structured output."""
        try:
            llm = await self.create_structured_llm(
                model=state.executive_assessment_model or self.default_model,
                response_schema=ExecutiveRoutingDecision
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an executive decision maker. Determine whether a request should be handled:
                
                DIRECT: Single-step execution with immediate response
                - Simple queries
                - Single tool operations
                - Straightforward requests
                
                PLANNING: Multi-step approach with planning phase
                - Complex multi-part requests
                - Requires coordination between multiple tools
                - Needs strategic thinking or optimization
                
                Make your decision based on complexity and scope.
                """),
                ("human", "{message}")
            ])
            
            chain = prompt | llm
            result = await chain.ainvoke({"message": user_message})
            
            return result
            
        except Exception as e:
            logger.error(f"Error in executive decision making: {e}")
            # Fallback decision
            return ExecutiveRoutingDecision(
                decision=ExecutiveDecision.DIRECT,
                confidence=0.5,
                reasoning="Fallback decision due to error",
                suggested_approach="Direct tool execution",
                estimated_complexity="unknown"
            )
    
    async def execute_tool_with_streaming(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any], 
        state: GraphState
    ) -> AsyncGenerator[IntermediateStep, None]:
        """Execute tool with intermediate step streaming."""
        start_time = datetime.now()
        
        # Emit start step
        yield IntermediateStep(
            step_name=f"tool_execution_{tool_name}",
            description=f"Starting {tool_name} execution",
            status="started"
        )
        
        try:
            # Get tool handler
            handler = get_tool_handler(tool_name)
            if not handler:
                yield IntermediateStep(
                    step_name=f"tool_execution_{tool_name}",
                    description=f"Tool {tool_name} not found",
                    status="error",
                    output={"error": f"Handler not found for tool: {tool_name}"}
                )
                return
            
            # Execute tool
            result = await handler(state)
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Create structured result
            tool_result = ToolExecutionResult(
                tool_name=tool_name,
                status=ToolExecutionStatus.SUCCESS,
                result=result,
                execution_time_ms=execution_time,
                metadata={"parameters": parameters}
            )
            
            # Emit completion step
            yield IntermediateStep(
                step_name=f"tool_execution_{tool_name}",
                description=f"Completed {tool_name} execution",
                status="completed",
                output=tool_result.dict()
            )
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Create error result
            tool_result = ToolExecutionResult(
                tool_name=tool_name,
                status=ToolExecutionStatus.ERROR,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"parameters": parameters}
            )
            
            # Emit error step
            yield IntermediateStep(
                step_name=f"tool_execution_{tool_name}",
                description=f"Error in {tool_name} execution: {str(e)}",
                status="error",
                output=tool_result.dict()
            )
    
    async def process_request_with_streaming(
        self, 
        user_message: str, 
        state: GraphState
    ) -> AsyncGenerator[IntermediateStep, None]:
        """Process request with full streaming of intermediate steps."""
        
        # Step 1: Executive Decision
        yield IntermediateStep(
            step_name="executive_decision",
            description="Making executive routing decision",
            status="started"
        )
        
        executive_decision = await self.make_executive_decision(user_message, state)
        
        yield IntermediateStep(
            step_name="executive_decision",
            description=f"Executive decision: {executive_decision.decision.value}",
            status="completed",
            output=executive_decision.dict()
        )
        
        # Step 2: Intent Analysis
        yield IntermediateStep(
            step_name="intent_analysis",
            description="Analyzing user intent",
            status="started"
        )
        
        intent_analysis = await self.analyze_intent_structured(user_message, state)
        
        yield IntermediateStep(
            step_name="intent_analysis",
            description=f"Intent: {intent_analysis.primary_intent}",
            status="completed",
            output=intent_analysis.dict()
        )
        
        # Step 3: Tool Selection
        if executive_decision.decision == ExecutiveDecision.DIRECT:
            yield IntermediateStep(
                step_name="tool_selection",
                description="Selecting appropriate tool",
                status="started"
            )
            
            tool_selection = await self.select_tool_structured(intent_analysis, user_message, state)
            
            yield IntermediateStep(
                step_name="tool_selection",
                description=f"Selected tool: {tool_selection.selected_tool}",
                status="completed",
                output=tool_selection.dict()
            )
            
            # Step 4: Tool Execution
            async for step in self.execute_tool_with_streaming(
                tool_selection.selected_tool,
                tool_selection.parameters,
                state
            ):
                yield step
        
        else:
            # Planning approach would be implemented here
            yield IntermediateStep(
                step_name="planning",
                description="Planning multi-step approach",
                status="started"
            )
            
            # For now, fallback to simple execution
            tool_selection = await self.select_tool_structured(intent_analysis, user_message, state)
            
            async for step in self.execute_tool_with_streaming(
                tool_selection.selected_tool,
                tool_selection.parameters,
                state
            ):
                yield step
    
    async def create_enhanced_graph_state(self, user_input: str, session_id: str, user_id: Optional[str] = None) -> EnhancedGraphState:
        """Create enhanced graph state with better structure."""
        return EnhancedGraphState(
            user_input=user_input,
            session_id=session_id,
            user_id=user_id,
            processing_metadata={
                "created_at": datetime.now().isoformat(),
                "service_version": "enhanced_0.3.0"
            }
        )

# Global instance
enhanced_router_service = EnhancedRouterService()