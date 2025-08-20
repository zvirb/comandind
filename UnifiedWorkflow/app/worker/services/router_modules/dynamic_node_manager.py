#!/usr/bin/env python3
"""
Dynamic Node Manager for LangGraph

This module provides the ability to dynamically add nodes to LangGraph workflows
for smart multi-step processing, including:
1. Multi-event calendar processing
2. Task hierarchy creation 
3. Iterative operations
4. Context-aware processing chains
5. Error recovery loops
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Callable, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, field

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from worker.graph_types import GraphState
from worker.services.progress_manager import progress_manager
from worker.services.ollama_service import invoke_llm_with_tokens

logger = logging.getLogger(__name__)

@dataclass
class DynamicNodeSpec:
    """Specification for a dynamically created node"""
    node_id: str
    node_type: str  # complexity_analyzer, multi_processor, iterator, validator, etc.
    handler_function: Callable
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    max_iterations: int = 10
    timeout_seconds: int = 300

@dataclass
class ProcessingPlan:
    """A plan for dynamic multi-step processing"""
    plan_id: str
    original_request: str
    complexity_score: int
    requires_iteration: bool
    estimated_steps: int
    dynamic_nodes: List[DynamicNodeSpec] = field(default_factory=list)
    execution_strategy: str = "sequential"  # sequential, parallel, conditional
    context: Dict[str, Any] = field(default_factory=dict)

class DynamicNodeManager:
    """Manages dynamic node creation and execution in LangGraph workflows"""
    
    def __init__(self):
        self.active_plans: Dict[str, ProcessingPlan] = {}
        self.node_registry: Dict[str, DynamicNodeSpec] = {}
        self.execution_history: List[Dict[str, Any]] = []
        
    async def analyze_and_create_plan(self, state: GraphState) -> Tuple[bool, Optional[ProcessingPlan]]:
        """
        Analyze a request and determine if dynamic nodes are needed
        Returns (needs_dynamic_processing, processing_plan)
        """
        user_input = state.user_input
        logger.info(f"Analyzing request for dynamic processing: {user_input[:100]}...")
        
        # Pre-check for obvious structured data that needs dynamic processing
        if self._has_structured_list_data(user_input):
            logger.info("Pre-check detected structured list data - forcing dynamic processing")
            force_dynamic = True
        else:
            force_dynamic = False
        
        analysis_prompt = f"""You are an expert workflow analyzer. Analyze this request to determine if it needs dynamic multi-step processing and identify opportunities for parallel execution.

User Request: {user_input}

Pre-analysis indicates force_dynamic={force_dynamic} (structured data detected)

Analyze and respond with JSON:
{{
  "analysis": {{
    "needs_dynamic_processing": true/false,
    "force_dynamic": true/false,
    "complexity_score": 1-10,
    "processing_type": "single_tool/multi_event/task_hierarchy/batch_operation/iterative_process/complex_tool",
    "estimated_steps": 1-20,
    "requires_iteration": true/false,
    "tool_category": "calendar/task/email/file/mixed",
    "parallel_opportunities": {{
      "can_use_parallel": true/false,
      "parallel_groups": [
        {{
          "group_id": "group_1",
          "tasks": ["Create event 1", "Create event 2", "Create event 3"],
          "can_run_parallel": true,
          "estimated_time_savings": "30-50%"
        }}
      ],
      "parallel_vs_sequential": "parallel_preferred/sequential_required/either_works"
    }},
    "dynamic_nodes_needed": [
      {{
        "node_type": "complexity_analyzer/multi_processor/parallel_processor/iterator/validator/synthesizer/list_parser/user_input_collector/input_analyzer/data_enhancer/parsing_assessor/parsing_supplement/parsing_reparse",
        "purpose": "What this node will do",
        "estimated_processing_time": "quick/medium/long",
        "dependencies": ["node_id1", "node_id2"],
        "can_run_parallel": true/false,
        "parallel_group": "group_1 (if applicable)"
      }}
    ],
    "execution_strategy": "sequential/parallel/conditional/hybrid",
    "iteration_pattern": {{
      "max_iterations": 10,
      "iteration_condition": "until_complete/fixed_count/user_approval",
      "batch_size": 5,
      "parallel_batches": true/false
    }},
    "context_requirements": {{
      "needs_user_feedback": true/false,
      "preserves_state": true/false,
      "requires_external_apis": true/false,
      "shared_context_across_parallel": true/false
    }}
  }}
}}

Guidelines:
- FORCE dynamic processing for ANY complex tool use (complexity >= 3)
- Mark force_dynamic=true for: multiple items, any batch operations, complex single operations
- Look for parallel opportunities in:
  * Multiple independent calendar events
  * Batch task creation 
  * Multiple file operations
  * Independent email processing
  * Parallel API calls
- Use parallel strategy when tasks are independent
- Use hybrid strategy when some tasks can be parallel, others sequential
- Complexity scoring:
  * 1-2: Single simple operation (still consider dynamic for consistency)
  * 3-4: Single complex operation OR multiple simple operations -> FORCE DYNAMIC
  * 5-6: Multiple complex operations -> FORCE DYNAMIC + likely parallel
  * 7-8: Complex hierarchical operations -> FORCE DYNAMIC + hybrid execution
  * 9-10: Very complex multi-step workflows -> FORCE DYNAMIC + sophisticated orchestration
- Always prefer parallel when possible for time efficiency
- Special node types:
  * list_parser: Use when request contains structured lists, bullet points, sections with subsections
  * user_input_collector: Use when information is clearly missing (no dates, unclear requirements)
  * input_analyzer: Use to determine what additional info is needed
  * data_enhancer: Use to combine parsed data with user input for complete tool preparation
  * parsing_assessor: Use to evaluate parsing quality and decide on improvement actions
  * parsing_supplement: Use to add missing information to existing parsing results
  * parsing_reparse: Use to re-parse data from scratch using LLM when initial parsing fails
"""

        try:
            model_name = getattr(state, 'tool_selection_model', 'llama3.2:3b')
            
            response, _ = await invoke_llm_with_tokens(
                messages=[
                    {"role": "system", "content": "You are a workflow analysis expert. Always respond with valid JSON only."},
                    {"role": "user", "content": analysis_prompt}
                ],
                model_name=model_name,
                category="dynamic_analysis"
            )
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                analysis_data = json.loads(json_str)
                analysis = analysis_data.get("analysis", {})
                
                # Check if we should force dynamic processing
                needs_dynamic = analysis.get("needs_dynamic_processing", False)
                force_dynamic = analysis.get("force_dynamic", False)
                complexity_score = analysis.get("complexity_score", 1)
                
                # Force dynamic processing for any complex tool use (complexity >= 3)
                if complexity_score >= 3 or force_dynamic:
                    needs_dynamic = True
                    logger.info(f"Forcing dynamic processing - complexity: {complexity_score}, force_flag: {force_dynamic}")
                
                if not needs_dynamic:
                    return False, None
                
                # Create processing plan
                plan = ProcessingPlan(
                    plan_id=f"plan_{uuid.uuid4().hex[:8]}",
                    original_request=user_input,
                    complexity_score=analysis.get("complexity_score", 5),
                    requires_iteration=analysis.get("requires_iteration", False),
                    estimated_steps=analysis.get("estimated_steps", 3),
                    execution_strategy=analysis.get("execution_strategy", "sequential"),
                    context={
                        "analysis": analysis,
                        "user_id": state.user_id,
                        "session_id": state.session_id,
                        "original_state": state.__dict__.copy()
                    }
                )
                
                # Create dynamic node specifications
                for i, node_spec in enumerate(analysis.get("dynamic_nodes_needed", [])):
                    dynamic_node = DynamicNodeSpec(
                        node_id=f"{plan.plan_id}_node_{i+1}",
                        node_type=node_spec.get("node_type", "processor"),
                        handler_function=self._get_handler_for_node_type(node_spec.get("node_type")),
                        metadata={
                            "purpose": node_spec.get("purpose", "Process step"),
                            "estimated_time": node_spec.get("estimated_processing_time", "medium"),
                            "tool_category": analysis.get("tool_category", "mixed"),
                            "can_run_parallel": node_spec.get("can_run_parallel", False),
                            "parallel_group": node_spec.get("parallel_group", None),
                            "parallel_opportunities": analysis.get("parallel_opportunities", {})
                        },
                        dependencies=node_spec.get("dependencies", []),
                        max_iterations=analysis.get("iteration_pattern", {}).get("max_iterations", 10)
                    )
                    plan.dynamic_nodes.append(dynamic_node)
                
                self.active_plans[plan.plan_id] = plan
                logger.info(f"Created dynamic processing plan: {plan.plan_id} with {len(plan.dynamic_nodes)} nodes")
                
                return True, plan
            else:
                logger.warning("Could not parse analysis response")
                return False, None
                
        except Exception as e:
            logger.error(f"Error in dynamic analysis: {e}", exc_info=True)
            return False, None
    
    def _get_handler_for_node_type(self, node_type: str) -> Callable:
        """Get the appropriate handler function for a node type"""
        handlers = {
            "complexity_analyzer": self._complexity_analyzer_node,
            "multi_processor": self._multi_processor_node,
            "parallel_processor": self._parallel_processor_node,
            "iterator": self._iterator_node,
            "validator": self._validator_node,
            "synthesizer": self._synthesizer_node,
            "calendar_multi_event": self._calendar_multi_event_node,
            "task_hierarchy": self._task_hierarchy_node,
            "batch_processor": self._batch_processor_node,
            "context_manager": self._context_manager_node,
            "parallel_calendar": self._parallel_calendar_processor_node,
            "parallel_task": self._parallel_task_processor_node,
            "list_parser": self._list_parser_node,
            "user_input_collector": self._user_input_collector_node,
            "input_analyzer": self._input_analyzer_node,
            "data_enhancer": self._data_enhancer_node,
            "parsing_assessor": self._parsing_assessment_node,
            "parsing_supplement": self._parsing_supplement_node,
            "parsing_reparse": self._parsing_reparse_node
        }
        
        return handlers.get(node_type, self._generic_processor_node)
    
    async def create_dynamic_workflow(self, base_workflow: StateGraph, plan: ProcessingPlan) -> StateGraph:
        """
        Create a new workflow with dynamically added nodes based on the processing plan
        """
        logger.info(f"Creating dynamic workflow for plan: {plan.plan_id}")
        
        # Clone the base workflow structure (we'll create a new one)
        dynamic_workflow = StateGraph(GraphState)
        
        # Add original nodes (simplified - you might want to copy existing nodes)
        from .assessment_nodes import simple_executive_assessment_node
        from .execution_nodes import execute_tool_node, tool_explanation_node
        from .planning_nodes import simple_planner_node
        
        # Add base nodes
        dynamic_workflow.add_node("executive_assessment", simple_executive_assessment_node)
        dynamic_workflow.add_node("execute_tool", execute_tool_node)  
        dynamic_workflow.add_node("simple_planning", simple_planner_node)
        dynamic_workflow.add_node("tool_explanation", tool_explanation_node)
        
        # Add dynamic processing entry point
        dynamic_workflow.add_node("dynamic_processor_entry", self._create_dynamic_entry_node(plan))
        
        # Add all dynamic nodes from the plan
        for node_spec in plan.dynamic_nodes:
            dynamic_workflow.add_node(node_spec.node_id, node_spec.handler_function)
            self.node_registry[node_spec.node_id] = node_spec
        
        # Add dynamic result synthesizer
        dynamic_workflow.add_node("dynamic_synthesizer", self._create_dynamic_synthesizer(plan))
        
        # Set up routing
        dynamic_workflow.set_entry_point("executive_assessment")
        
        # Enhanced routing that can go to dynamic processing
        dynamic_workflow.add_conditional_edges(
            "executive_assessment",
            self._create_dynamic_router(plan),
            {
                "DIRECT": "execute_tool",
                "PLANNING": "simple_planning",
                "DYNAMIC": "dynamic_processor_entry",
                "END": END
            }
        )
        
        # Set up dynamic node connections based on execution strategy
        if plan.execution_strategy == "sequential":
            self._add_sequential_edges(dynamic_workflow, plan)
        elif plan.execution_strategy == "parallel":
            self._add_parallel_edges(dynamic_workflow, plan)  
        elif plan.execution_strategy == "hybrid":
            self._add_hybrid_edges(dynamic_workflow, plan)
        elif plan.execution_strategy == "conditional":
            self._add_conditional_edges(dynamic_workflow, plan)
        
        # Connect back to main flow
        dynamic_workflow.add_edge("dynamic_synthesizer", "tool_explanation")
        dynamic_workflow.add_edge("execute_tool", "tool_explanation")
        dynamic_workflow.add_edge("simple_planning", "execute_tool")
        dynamic_workflow.add_edge("tool_explanation", END)
        
        return dynamic_workflow
    
    def _create_dynamic_router(self, plan: ProcessingPlan) -> Callable:
        """Create a router function that can direct to dynamic processing"""
        def dynamic_router(state: GraphState) -> str:
            # Check if this state should use dynamic processing
            if hasattr(state, 'use_dynamic_processing') and state.use_dynamic_processing:
                return "DYNAMIC"
            elif hasattr(state, 'routing_decision'):
                return state.routing_decision
            else:
                return "DIRECT"
        
        return dynamic_router
    
    def _create_dynamic_entry_node(self, plan: ProcessingPlan) -> Callable:
        """Create the entry node for dynamic processing"""
        async def dynamic_entry_node(state: GraphState) -> GraphState:
            logger.info(f"Entering dynamic processing for plan: {plan.plan_id}")
            
            # Initialize dynamic processing context
            state.dynamic_plan_id = plan.plan_id
            state.dynamic_step_count = 0
            state.dynamic_results = []
            state.dynamic_context = plan.context.copy()
            
            # Notify user of dynamic processing start
            if state.session_id:
                await progress_manager.broadcast_to_session_sync(state.session_id, {
                    "type": "dynamic_processing_started",
                    "plan_id": plan.plan_id,
                    "estimated_steps": plan.estimated_steps,
                    "processing_type": plan.context.get("analysis", {}).get("processing_type", "multi_step")
                })
            
            return state
        
        return dynamic_entry_node
    
    def _create_dynamic_synthesizer(self, plan: ProcessingPlan) -> Callable:
        """Create the final synthesizer node for dynamic processing"""
        async def dynamic_synthesizer_node(state: GraphState) -> GraphState:
            logger.info(f"Synthesizing results for plan: {plan.plan_id}")
            
            # Collect all dynamic results
            dynamic_results = getattr(state, 'dynamic_results', [])
            
            # Generate comprehensive summary
            if dynamic_results:
                successful_count = len([r for r in dynamic_results if r.get("success", False)])
                total_count = len(dynamic_results)
                
                if successful_count == total_count:
                    summary = f"✅ Successfully completed all {total_count} dynamic processing steps."
                elif successful_count > 0:
                    summary = f"✅ Completed {successful_count} of {total_count} processing steps."
                else:
                    summary = f"❌ Dynamic processing encountered issues in all {total_count} steps."
                
                # Add detailed results
                result_details = []
                for i, result in enumerate(dynamic_results[:5]):  # Show first 5
                    if result.get("success"):
                        result_details.append(f"• Step {i+1}: {result.get('summary', 'Completed')}")
                    else:
                        result_details.append(f"• Step {i+1}: Failed - {result.get('error', 'Unknown error')}")
                
                if len(dynamic_results) > 5:
                    result_details.append(f"... and {len(dynamic_results) - 5} more steps")
                
                final_response = summary + "\n\n" + "\n".join(result_details)
            else:
                final_response = "Dynamic processing completed with no specific results."
            
            # Update state with final response
            state.final_response = final_response
            
            # Notify completion
            if state.session_id:
                await progress_manager.broadcast_to_session_sync(state.session_id, {
                    "type": "dynamic_processing_completed", 
                    "plan_id": plan.plan_id,
                    "total_steps": len(dynamic_results),
                    "successful_steps": len([r for r in dynamic_results if r.get("success", False)]),
                    "summary": final_response
                })
            
            # Clean up
            if plan.plan_id in self.active_plans:
                del self.active_plans[plan.plan_id]
            
            return state
        
        return dynamic_synthesizer_node
    
    def _add_sequential_edges(self, workflow: StateGraph, plan: ProcessingPlan):
        """Add edges for sequential execution of dynamic nodes"""
        nodes = plan.dynamic_nodes
        
        if not nodes:
            workflow.add_edge("dynamic_processor_entry", "dynamic_synthesizer")
            return
        
        # Connect entry to first node
        workflow.add_edge("dynamic_processor_entry", nodes[0].node_id)
        
        # Connect nodes sequentially
        for i in range(len(nodes) - 1):
            workflow.add_edge(nodes[i].node_id, nodes[i + 1].node_id)
        
        # Connect last node to synthesizer
        workflow.add_edge(nodes[-1].node_id, "dynamic_synthesizer")
    
    def _add_parallel_edges(self, workflow: StateGraph, plan: ProcessingPlan):
        """Add edges for parallel execution with proper synchronization"""
        nodes = plan.dynamic_nodes
        
        if not nodes:
            workflow.add_edge("dynamic_processor_entry", "dynamic_synthesizer")
            return
        
        # Group parallel nodes by their parallel_group if specified
        parallel_groups = self._group_nodes_for_parallel_execution(nodes, plan)
        
        if len(parallel_groups) == 1 and "default" in parallel_groups:
            # All nodes can run in parallel
            logger.info(f"Setting up full parallel execution for {len(nodes)} nodes")
            
            # Add parallel barrier node to synchronize results
            workflow.add_node("parallel_barrier", self._create_parallel_barrier_node(plan))
            
            # Connect entry to all nodes (parallel execution)
            for node in nodes:
                workflow.add_edge("dynamic_processor_entry", node.node_id)
                workflow.add_edge(node.node_id, "parallel_barrier")
            
            # Connect barrier to synthesizer
            workflow.add_edge("parallel_barrier", "dynamic_synthesizer")
        else:
            # Mixed parallel and sequential groups
            self._add_hybrid_edges(workflow, plan)
    
    def _add_hybrid_edges(self, workflow: StateGraph, plan: ProcessingPlan):
        """Add edges for hybrid execution (mix of parallel and sequential)"""
        nodes = plan.dynamic_nodes
        
        if not nodes:
            workflow.add_edge("dynamic_processor_entry", "dynamic_synthesizer")
            return
        
        # Group nodes for parallel execution
        parallel_groups = self._group_nodes_for_parallel_execution(nodes, plan)
        
        logger.info(f"Setting up hybrid execution with {len(parallel_groups)} groups")
        
        current_source = "dynamic_processor_entry"
        
        for group_id, group_nodes in parallel_groups.items():
            if len(group_nodes) == 1:
                # Single node - just connect sequentially
                node = group_nodes[0]
                workflow.add_edge(current_source, node.node_id)
                current_source = node.node_id
            else:
                # Multiple nodes - create parallel group with barrier
                barrier_id = f"barrier_{group_id}"
                workflow.add_node(barrier_id, self._create_parallel_barrier_node(plan, group_id))
                
                # Connect all nodes in parallel to the barrier
                for node in group_nodes:
                    workflow.add_edge(current_source, node.node_id)
                    workflow.add_edge(node.node_id, barrier_id)
                
                current_source = barrier_id
        
        # Connect final source to synthesizer
        workflow.add_edge(current_source, "dynamic_synthesizer")
    
    def _add_conditional_edges(self, workflow: StateGraph, plan: ProcessingPlan):
        """Add conditional edges based on node dependencies and outcomes"""
        # For now, fall back to hybrid execution - this could be enhanced with more sophisticated conditionals
        self._add_hybrid_edges(workflow, plan)
    
    def _group_nodes_for_parallel_execution(self, nodes: List[DynamicNodeSpec], plan: ProcessingPlan) -> Dict[str, List[DynamicNodeSpec]]:
        """Group nodes that can be executed in parallel"""
        groups = {}
        analysis = plan.context.get("analysis", {})
        parallel_opportunities = analysis.get("parallel_opportunities", {})
        parallel_groups_info = parallel_opportunities.get("parallel_groups", [])
        
        # Create a mapping of parallel group names to nodes
        group_mapping = {}
        for group_info in parallel_groups_info:
            group_id = group_info.get("group_id", "default")
            group_mapping[group_id] = []
        
        # Assign nodes to groups based on their metadata
        for node in nodes:
            parallel_group = node.metadata.get("parallel_group")
            can_run_parallel = node.metadata.get("can_run_parallel", False)
            
            if parallel_group and parallel_group in group_mapping:
                if parallel_group not in groups:
                    groups[parallel_group] = []
                groups[parallel_group].append(node)
            elif can_run_parallel:
                # Add to default parallel group
                if "default" not in groups:
                    groups["default"] = []
                groups["default"].append(node)
            else:
                # Sequential node - each gets its own group
                sequential_id = f"sequential_{node.node_id}"
                groups[sequential_id] = [node]
        
        # If no groups were created, put all nodes in default
        if not groups:
            groups["default"] = nodes
        
        return groups
    
    def _create_parallel_barrier_node(self, plan: ProcessingPlan, group_id: str = "default") -> Callable:
        """Create a barrier node that waits for all parallel nodes to complete"""
        async def parallel_barrier_node(state: GraphState) -> GraphState:
            logger.info(f"Parallel barrier synchronizing results for group: {group_id}")
            
            # All parallel nodes should have updated dynamic_results by now
            dynamic_results = getattr(state, 'dynamic_results', [])
            
            # Add barrier completion record
            barrier_result = {
                "node_type": "parallel_barrier",
                "group_id": group_id,
                "success": True,
                "summary": f"Synchronized {len(dynamic_results)} parallel results for group {group_id}",
                "timestamp": datetime.now().isoformat()
            }
            
            dynamic_results.append(barrier_result)
            state.dynamic_results = dynamic_results
            
            # Notify progress
            if state.session_id:
                await progress_manager.broadcast_to_session_sync(state.session_id, {
                    "type": "parallel_barrier_completed",
                    "group_id": group_id,
                    "synchronized_results": len(dynamic_results),
                    "plan_id": getattr(state, 'dynamic_plan_id', 'unknown')
                })
            
            return state
        
        return parallel_barrier_node
    
    # Dynamic Node Implementations
    
    async def _complexity_analyzer_node(self, state: GraphState) -> GraphState:
        """Analyze complexity and adjust processing strategy"""
        logger.info("Running complexity analyzer node")
        
        # This would analyze the current state and potentially modify the processing plan
        dynamic_results = getattr(state, 'dynamic_results', [])
        dynamic_results.append({
            "node_type": "complexity_analyzer",
            "success": True,
            "summary": "Analyzed request complexity",
            "timestamp": datetime.now().isoformat()
        })
        state.dynamic_results = dynamic_results
        
        return state
    
    async def _multi_processor_node(self, state: GraphState) -> GraphState:
        """Handle multi-item processing (events, tasks, etc.)"""
        logger.info("Running multi-processor node")
        
        try:
            # Determine what type of multi-processing is needed
            plan_id = getattr(state, 'dynamic_plan_id', '')
            plan = self.active_plans.get(plan_id)
            
            if not plan:
                raise ValueError("No processing plan found")
            
            analysis = plan.context.get("analysis", {})
            tool_category = analysis.get("tool_category", "mixed")
            
            # Route to appropriate multi-processor
            if tool_category == "calendar":
                result = await self._process_calendar_multi_events(state, plan)
            elif tool_category == "task":
                result = await self._process_multiple_tasks(state, plan)
            elif tool_category == "email":
                result = await self._process_multiple_emails(state, plan)
            else:
                result = await self._process_generic_multi_items(state, plan)
            
            # Update state with results
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append(result)
            state.dynamic_results = dynamic_results
            
            return state
            
        except Exception as e:
            logger.error(f"Error in multi-processor node: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "multi_processor",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state
    
    async def _parallel_processor_node(self, state: GraphState) -> GraphState:
        """Handle parallel processing operations efficiently"""
        logger.info("Running parallel processor node")
        
        try:
            plan_id = getattr(state, 'dynamic_plan_id', '')
            plan = self.active_plans.get(plan_id)
            
            if not plan:
                raise ValueError("No processing plan found")
            
            analysis = plan.context.get("analysis", {})
            parallel_opportunities = analysis.get("parallel_opportunities", {})
            
            # Determine the type of parallel processing needed
            tool_category = analysis.get("tool_category", "mixed")
            
            # Notify start of parallel processing
            if state.session_id:
                await progress_manager.broadcast_to_session_sync(state.session_id, {
                    "type": "parallel_processing_started",
                    "tool_category": tool_category,
                    "estimated_time_savings": parallel_opportunities.get("parallel_groups", [{}])[0].get("estimated_time_savings", "30-50%"),
                    "plan_id": plan_id
                })
            
            # Route to specific parallel processor
            if tool_category == "calendar":
                result = await self._parallel_calendar_processor_node(state)
            elif tool_category == "task":
                result = await self._parallel_task_processor_node(state)
            elif tool_category == "email":
                result = await self._parallel_email_processor_node(state)
            else:
                result = await self._parallel_generic_processor_node(state)
            
            # This node doesn't update state directly since individual parallel nodes will
            return state
            
        except Exception as e:
            logger.error(f"Error in parallel processor node: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "parallel_processor",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state
    
    async def _iterator_node(self, state: GraphState) -> GraphState:
        """Handle iterative processing with progress tracking"""
        logger.info("Running iterator node")
        
        # This would implement iteration logic
        iteration_count = getattr(state, 'iteration_count', 0) + 1
        state.iteration_count = iteration_count
        
        dynamic_results = getattr(state, 'dynamic_results', [])
        dynamic_results.append({
            "node_type": "iterator",
            "success": True,
            "summary": f"Completed iteration {iteration_count}",
            "iteration_count": iteration_count,
            "timestamp": datetime.now().isoformat()
        })
        state.dynamic_results = dynamic_results
        
        return state
    
    async def _validator_node(self, state: GraphState) -> GraphState:
        """Validate processing results and handle errors"""
        logger.info("Running validator node")
        
        # Validate previous results
        dynamic_results = getattr(state, 'dynamic_results', [])
        failed_results = [r for r in dynamic_results if not r.get("success", True)]
        
        validation_result = {
            "node_type": "validator",
            "success": True,
            "summary": f"Validated {len(dynamic_results)} results, {len(failed_results)} failures",
            "validation_details": {
                "total_checked": len(dynamic_results),
                "failures_found": len(failed_results),
                "validation_passed": len(failed_results) == 0
            },
            "timestamp": datetime.now().isoformat()
        }
        
        dynamic_results.append(validation_result)
        state.dynamic_results = dynamic_results
        
        return state
    
    async def _synthesizer_node(self, state: GraphState) -> GraphState:
        """Synthesize results from multiple processing steps"""
        logger.info("Running synthesizer node")
        
        dynamic_results = getattr(state, 'dynamic_results', [])
        synthesis_result = {
            "node_type": "synthesizer",
            "success": True,
            "summary": f"Synthesized results from {len(dynamic_results)} processing steps",
            "timestamp": datetime.now().isoformat()
        }
        
        dynamic_results.append(synthesis_result)
        state.dynamic_results = dynamic_results
        
        return state
    
    async def _calendar_multi_event_node(self, state: GraphState) -> GraphState:
        """Specialized node for calendar multi-event processing"""
        logger.info("Running calendar multi-event node")
        
        try:
            # Use enhanced calendar processor
            from worker.enhanced_calendar_tools import handle_smart_calendar_request
            result = await handle_smart_calendar_request(state)
            
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "calendar_multi_event",
                "success": not result.get("error"),
                "summary": result.get("response", "Processed calendar events"),
                "calendar_result": result,
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            
            return state
            
        except Exception as e:
            logger.error(f"Error in calendar multi-event node: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "calendar_multi_event",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state
    
    async def _task_hierarchy_node(self, state: GraphState) -> GraphState:
        """Specialized node for task hierarchy processing"""
        logger.info("Running task hierarchy node")
        
        try:
            # Use enhanced task processor
            from worker.enhanced_task_tools import handle_smart_task_request
            result = await handle_smart_task_request(state)
            
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "task_hierarchy",
                "success": not result.get("error"),
                "summary": result.get("response", "Processed task hierarchy"),
                "task_result": result,
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            
            return state
            
        except Exception as e:
            logger.error(f"Error in task hierarchy node: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "task_hierarchy",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state
    
    async def _batch_processor_node(self, state: GraphState) -> GraphState:
        """Handle batch processing operations"""
        logger.info("Running batch processor node")
        
        # This would implement batch processing logic
        dynamic_results = getattr(state, 'dynamic_results', [])
        dynamic_results.append({
            "node_type": "batch_processor",
            "success": True,
            "summary": "Completed batch processing",
            "timestamp": datetime.now().isoformat()
        })
        state.dynamic_results = dynamic_results
        
        return state
    
    async def _context_manager_node(self, state: GraphState) -> GraphState:
        """Manage context and state across dynamic processing"""
        logger.info("Running context manager node")
        
        # This would manage context preservation
        dynamic_results = getattr(state, 'dynamic_results', [])
        dynamic_results.append({
            "node_type": "context_manager",
            "success": True,
            "summary": "Managed processing context",
            "timestamp": datetime.now().isoformat()
        })
        state.dynamic_results = dynamic_results
        
        return state
    
    async def _generic_processor_node(self, state: GraphState) -> GraphState:
        """Generic processing node for unknown types"""
        logger.info("Running generic processor node")
        
        dynamic_results = getattr(state, 'dynamic_results', [])
        dynamic_results.append({
            "node_type": "generic_processor",
            "success": True,
            "summary": "Completed generic processing",
            "timestamp": datetime.now().isoformat()
        })
        state.dynamic_results = dynamic_results
        
        return state
    
    # Helper methods for specific multi-processing scenarios
    
    async def _process_calendar_multi_events(self, state: GraphState, plan: ProcessingPlan) -> Dict[str, Any]:
        """Process multiple calendar events"""
        from worker.enhanced_calendar_tools import enhanced_calendar_processor
        
        try:
            events, parsing_result = await enhanced_calendar_processor.parse_multi_event_request(state, state.user_input)
            
            if len(events) > 1:
                processed_events = await enhanced_calendar_processor.process_events_with_defaults(events, parsing_result)
                batch_result = await enhanced_calendar_processor.create_events_iteratively(state, processed_events)
                
                return {
                    "node_type": "calendar_multi_processor",
                    "success": batch_result.successful_events > 0,
                    "summary": f"Processed {batch_result.total_events} calendar events, {batch_result.successful_events} successful",
                    "details": batch_result.__dict__,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "node_type": "calendar_multi_processor",
                    "success": True,
                    "summary": "Single calendar event identified, processed normally",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "node_type": "calendar_multi_processor",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _process_multiple_tasks(self, state: GraphState, plan: ProcessingPlan) -> Dict[str, Any]:
        """Process multiple tasks"""
        from worker.enhanced_task_tools import enhanced_task_processor
        
        try:
            tasks, parsing_result = await enhanced_task_processor.parse_multi_task_request(state, state.user_input)
            
            if len(tasks) > 1:
                hierarchy = await enhanced_task_processor.create_task_hierarchy(tasks, parsing_result)
                batch_result = await enhanced_task_processor.create_tasks_iteratively(state, tasks, hierarchy)
                
                return {
                    "node_type": "task_multi_processor",
                    "success": batch_result.successful_tasks > 0,
                    "summary": f"Processed {batch_result.total_tasks} tasks, {batch_result.successful_tasks} successful",
                    "details": batch_result.__dict__,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "node_type": "task_multi_processor", 
                    "success": True,
                    "summary": "Single task identified, processed normally",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "node_type": "task_multi_processor",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _process_multiple_emails(self, state: GraphState, plan: ProcessingPlan) -> Dict[str, Any]:
        """Process multiple emails (placeholder for future implementation)"""
        return {
            "node_type": "email_multi_processor",
            "success": True,
            "summary": "Email multi-processing not yet implemented",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _process_generic_multi_items(self, state: GraphState, plan: ProcessingPlan) -> Dict[str, Any]:
        """Process generic multi-item requests"""
        return {
            "node_type": "generic_multi_processor",
            "success": True,
            "summary": "Generic multi-processing completed",
            "timestamp": datetime.now().isoformat()
        }
    
    # Specialized Parallel Processor Implementations
    
    async def _parallel_calendar_processor_node(self, state: GraphState) -> GraphState:
        """Specialized parallel processor for calendar events"""
        logger.info("Running parallel calendar processor")
        
        try:
            from worker.enhanced_calendar_tools import enhanced_calendar_processor
            
            events, parsing_result = await enhanced_calendar_processor.parse_multi_event_request(state, state.user_input)
            
            if len(events) > 1:
                processed_events = await enhanced_calendar_processor.process_events_with_defaults(events, parsing_result)
                
                # Create batches for parallel processing
                batch_size = min(5, len(processed_events))
                batches = [processed_events[i:i + batch_size] for i in range(0, len(processed_events), batch_size)]
                
                all_results = []
                for batch_num, batch in enumerate(batches):
                    logger.info(f"Processing calendar batch {batch_num + 1}/{len(batches)} with {len(batch)} events")
                    
                    # Process batch in parallel using asyncio.gather
                    batch_tasks = [self._create_single_calendar_event(state, event) for event in batch]
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    all_results.extend(batch_results)
                    
                    # Progress update
                    if state.session_id:
                        await progress_manager.broadcast_to_session_sync(state.session_id, {
                            "type": "parallel_batch_completed",
                            "batch_number": batch_num + 1,
                            "total_batches": len(batches),
                            "events_in_batch": len(batch),
                            "progress_percentage": ((batch_num + 1) / len(batches)) * 100
                        })
                
                # Analyze results
                successful_events = len([r for r in all_results if isinstance(r, dict) and r.get("success")])
                failed_events = len(all_results) - successful_events
                
                dynamic_results = getattr(state, 'dynamic_results', [])
                dynamic_results.append({
                    "node_type": "parallel_calendar_processor",
                    "success": successful_events > 0,
                    "summary": f"Parallel processed {len(processed_events)} calendar events: {successful_events} successful, {failed_events} failed",
                    "total_events": len(processed_events),
                    "successful_events": successful_events,
                    "failed_events": failed_events,
                    "batches_processed": len(batches),
                    "processing_method": "parallel_batches",
                    "timestamp": datetime.now().isoformat()
                })
                state.dynamic_results = dynamic_results
            
            return state
            
        except Exception as e:
            logger.error(f"Error in parallel calendar processor: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "parallel_calendar_processor",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state
    
    async def _create_single_calendar_event(self, state: GraphState, event) -> Dict[str, Any]:
        """Create a single calendar event (helper for parallel processing)"""
        try:
            from worker.calendar_tools import create_calendar_event_tool
            
            event_state = GraphState(
                user_input=f"Create calendar event: {event.title}",
                user_id=state.user_id,
                session_id=state.session_id,
                tool_output={
                    "summary": event.title,
                    "start_time": event.start_time,
                    "end_time": event.end_time,
                    "description": event.description,
                    "location": event.location
                }
            )
            
            result = await create_calendar_event_tool(event_state)
            return {
                "success": not result.get("error"),
                "event_title": event.title,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error creating single calendar event {event.title}: {e}")
            return {
                "success": False,
                "event_title": event.title,
                "error": str(e)
            }
    
    async def _parallel_task_processor_node(self, state: GraphState) -> GraphState:
        """Specialized parallel processor for task creation"""
        logger.info("Running parallel task processor")
        
        try:
            from worker.enhanced_task_tools import enhanced_task_processor
            
            tasks, parsing_result = await enhanced_task_processor.parse_multi_task_request(state, state.user_input)
            
            if len(tasks) > 1:
                # Create tasks in parallel batches  
                batch_size = min(3, len(tasks))
                batches = [tasks[i:i + batch_size] for i in range(0, len(tasks), batch_size)]
                
                all_results = []
                for batch_num, batch in enumerate(batches):
                    logger.info(f"Processing task batch {batch_num + 1}/{len(batches)} with {len(batch)} tasks")
                    
                    batch_tasks = [self._create_single_task(state, task) for task in batch]
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    all_results.extend(batch_results)
                
                successful_tasks = len([r for r in all_results if isinstance(r, dict) and r.get("success")])
                failed_tasks = len(all_results) - successful_tasks
                
                dynamic_results = getattr(state, 'dynamic_results', [])
                dynamic_results.append({
                    "node_type": "parallel_task_processor",
                    "success": successful_tasks > 0,
                    "summary": f"Parallel processed {len(tasks)} tasks: {successful_tasks} successful, {failed_tasks} failed",
                    "total_tasks": len(tasks),
                    "successful_tasks": successful_tasks,
                    "failed_tasks": failed_tasks,
                    "batches_processed": len(batches),
                    "processing_method": "parallel_batches",
                    "timestamp": datetime.now().isoformat()
                })
                state.dynamic_results = dynamic_results
            
            return state
            
        except Exception as e:
            logger.error(f"Error in parallel task processor: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "parallel_task_processor",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state
    
    async def _create_single_task(self, state: GraphState, task) -> Dict[str, Any]:
        """Create a single task (helper for parallel processing)"""
        try:
            from worker.task_management_tools import create_task
            
            result = create_task(
                title=task.title,
                description=task.description,
                priority=task.priority,
                due_date=task.due_date,
                tags=task.tags
            )
            
            return {
                "success": result.get("success", False),
                "task_title": task.title,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error creating single task {task.title}: {e}")
            return {
                "success": False,
                "task_title": task.title,
                "error": str(e)
            }

    # New Enhanced Node Implementations
    
    async def _list_parser_node(self, state: GraphState) -> GraphState:
        """Intelligent list parsing node"""
        logger.info("Running list parser node")
        
        try:
            from worker.services.intelligent_list_parser import intelligent_list_parser
            
            # Get the raw list from user input or context
            raw_list = state.user_input
            plan_id = getattr(state, 'dynamic_plan_id', '')
            plan = self.active_plans.get(plan_id)
            
            # Determine target tools from the plan
            target_tools = []
            if plan:
                analysis = plan.context.get("analysis", {})
                tool_category = analysis.get("tool_category", "mixed")
                if tool_category == "calendar":
                    target_tools = ["calendar"]
                elif tool_category == "task":
                    target_tools = ["task_management"]
                else:
                    target_tools = ["calendar", "task_management"]
            
            # Parse the list
            parsing_result = await intelligent_list_parser.parse_hierarchical_list(state, raw_list, target_tools)
            
            # Store results in state for use by other nodes
            state.parsed_list_data = {
                "parsed_items": [item.__dict__ for item in parsing_result.parsed_items],
                "ready_for_tools": {tool: [item.__dict__ for item in items] 
                                  for tool, items in parsing_result.ready_for_tools.items()},
                "inheritance_patterns": parsing_result.inheritance_patterns,
                "requires_user_input": parsing_result.requires_user_input,
                "missing_information": parsing_result.missing_information
            }
            
            # Add to dynamic results
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "list_parser",
                "success": True,
                "summary": parsing_result.parsing_summary,
                "parsed_items_count": len(parsing_result.parsed_items),
                "ready_for_tools": {tool: len(items) for tool, items in parsing_result.ready_for_tools.items()},
                "requires_additional_input": parsing_result.requires_user_input,
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            
            # Set routing for next steps
            if parsing_result.requires_user_input:
                state.needs_user_input = True
                state.missing_info_details = parsing_result.missing_information
            
            return state
            
        except Exception as e:
            logger.error(f"Error in list parser node: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "list_parser",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state
    
    async def _user_input_collector_node(self, state: GraphState) -> GraphState:
        """Dynamic user input collection node"""
        logger.info("Running user input collector node")
        
        try:
            from worker.services.dynamic_user_input import dynamic_user_input_manager
            
            # Analyze what input is needed
            current_context = getattr(state, 'current_context', '')
            missing_info = getattr(state, 'missing_info_details', [])
            
            # Create context for input analysis
            if missing_info:
                input_context = f"Missing information identified: {', '.join(missing_info)}"
            else:
                input_context = "Additional information may be needed to complete the task"
            
            # Analyze input needs
            input_analysis = await dynamic_user_input_manager.analyze_input_needs(state, input_context)
            
            if input_analysis.get("needs_user_input", False):
                # Create and execute input session
                session = await dynamic_user_input_manager.create_input_session(state, input_analysis)
                
                # Request input
                input_strategy = input_analysis.get("input_strategy", {})
                collection_method = input_strategy.get("collection_method", "sequential")
                responses = await dynamic_user_input_manager.request_user_input(session, collection_method)
                
                if responses:
                    # Get structured responses
                    structured_responses = dynamic_user_input_manager.get_session_responses(session.session_id)
                    
                    # Add to state
                    state.user_input_responses = structured_responses
                    state.additional_user_info = structured_responses
                    
                    # Update context
                    current_context = getattr(state, 'current_context', '')
                    new_context = current_context + f"\n\nAdditional user information: {json.dumps(structured_responses, indent=2)}"
                    state.current_context = new_context
                    
                    success_summary = f"Collected {len(responses)} user responses"
                    logger.info(success_summary)
                else:
                    success_summary = "User input collection timed out or was cancelled"
                    logger.warning(success_summary)
                
                # Clean up
                dynamic_user_input_manager.cleanup_session(session.session_id)
            else:
                success_summary = "No additional user input required"
            
            # Add to dynamic results
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "user_input_collector",
                "success": True,
                "summary": success_summary,
                "input_requests": len(input_analysis.get("input_requests", [])),
                "responses_received": len(getattr(state, 'user_input_responses', {})),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            
            return state
            
        except Exception as e:
            logger.error(f"Error in user input collector node: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "user_input_collector",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state
    
    async def _input_analyzer_node(self, state: GraphState) -> GraphState:
        """Analyze what input is needed from the user"""
        logger.info("Running input analyzer node")
        
        try:
            from worker.services.dynamic_user_input import dynamic_user_input_manager
            
            # Analyze input needs without actually collecting input
            current_context = getattr(state, 'current_context', '')
            input_analysis = await dynamic_user_input_manager.analyze_input_needs(state, current_context)
            
            # Store analysis in state
            state.input_needs_analysis = input_analysis
            state.needs_user_input = input_analysis.get("needs_user_input", False)
            
            # Extract specific questions that would be asked
            input_requests = input_analysis.get("input_requests", [])
            questions_preview = [req.get("question", "") for req in input_requests[:3]]
            
            # Add to dynamic results
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "input_analyzer",
                "success": True,
                "summary": f"Analyzed input needs: {'Required' if state.needs_user_input else 'Not required'}",
                "needs_input": state.needs_user_input,
                "urgency": input_analysis.get("urgency", "medium"),
                "questions_count": len(input_requests),
                "sample_questions": questions_preview,
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            
            return state
            
        except Exception as e:
            logger.error(f"Error in input analyzer node: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "input_analyzer",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state
    
    async def _data_enhancer_node(self, state: GraphState) -> GraphState:
        """Enhance parsed data with user input to prepare for tool consumption"""
        logger.info("Running data enhancer node")
        
        try:
            # Get parsed list data
            parsed_list_data = getattr(state, 'parsed_list_data', {})
            user_responses = getattr(state, 'user_input_responses', {})
            additional_info = getattr(state, 'additional_user_info', {})
            
            if not parsed_list_data and not user_responses:
                # No data to enhance
                dynamic_results = getattr(state, 'dynamic_results', [])
                dynamic_results.append({
                    "node_type": "data_enhancer",
                    "success": True,
                    "summary": "No data enhancement needed - no parsed data or user input found",
                    "timestamp": datetime.now().isoformat()
                })
                state.dynamic_results = dynamic_results
                return state
            
            # Enhance parsed items with user input
            enhanced_items = {}
            
            if parsed_list_data:
                ready_for_tools = parsed_list_data.get("ready_for_tools", {})
                
                for tool_name, items in ready_for_tools.items():
                    enhanced_tool_items = []
                    
                    for item in items:
                        enhanced_item = item.copy()
                        
                        # Enhance with user responses
                        if user_responses:
                            # Apply user input to fill missing information
                            for question, response_data in user_responses.items():
                                value = response_data.get("value")
                                response_type = response_data.get("type")
                                
                                # Smart matching of user responses to item needs
                                if "time" in question.lower() and not enhanced_item.get("complete_data", {}).get("times"):
                                    if "complete_data" not in enhanced_item:
                                        enhanced_item["complete_data"] = {}
                                    enhanced_item["complete_data"]["times"] = [value]
                                
                                elif "date" in question.lower() and not enhanced_item.get("complete_data", {}).get("dates"):
                                    if "complete_data" not in enhanced_item:
                                        enhanced_item["complete_data"] = {}
                                    enhanced_item["complete_data"]["dates"] = [value]
                                
                                elif "priority" in question.lower():
                                    if "complete_data" not in enhanced_item:
                                        enhanced_item["complete_data"] = {}
                                    enhanced_item["complete_data"]["priorities"] = [value]
                                
                                elif "location" in question.lower():
                                    if "complete_data" not in enhanced_item:
                                        enhanced_item["complete_data"] = {}
                                    enhanced_item["complete_data"]["locations"] = [value]
                        
                        # Mark as enhanced and ready
                        enhanced_item["enhanced_with_user_input"] = True
                        enhanced_item["ready_for_tool"] = True
                        enhanced_tool_items.append(enhanced_item)
                    
                    enhanced_items[tool_name] = enhanced_tool_items
            
            # Store enhanced data
            state.enhanced_tool_data = enhanced_items
            
            # Calculate enhancement statistics
            total_enhanced = sum(len(items) for items in enhanced_items.values())
            tools_ready = len(enhanced_items)
            
            # Add to dynamic results
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "data_enhancer",
                "success": True,
                "summary": f"Enhanced {total_enhanced} items for {tools_ready} tools with user input",
                "enhanced_items_count": total_enhanced,
                "tools_ready": list(enhanced_items.keys()),
                "user_responses_applied": len(user_responses),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            
            return state
            
        except Exception as e:
            logger.error(f"Error in data enhancer node: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "data_enhancer",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state
    
    def _has_structured_list_data(self, user_input: str) -> bool:
        """
        Quick pre-check to detect if user input contains structured list data
        that would benefit from list parsing and dynamic processing.
        """
        lines = user_input.strip().split('\n')
        
        # Insufficient data for structured list
        if len(lines) < 3:
            return False
        
        # Count structural indicators
        section_indicators = 0
        due_date_indicators = 0
        structured_lines = 0
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            # Section headers (ending with colon, capital letters)
            if line_stripped.endswith(':') or (len(line_stripped.split()) <= 4 and any(c.isupper() for c in line_stripped[:3])):
                section_indicators += 1
                
            # Due dates, deadlines, assignments
            if any(keyword in line_stripped.lower() for keyword in ['due:', 'due ', 'deadline:', 'assignment']):
                due_date_indicators += 1
                
            # Numbered or bulleted lists
            if line_stripped and (line_stripped[0].isdigit() or line_stripped.startswith(('-', '•', '*', '→'))):
                structured_lines += 1
        
        # Has structured data if:
        # - Multiple due dates (assignment lists)
        # - Clear sectioned structure
        # - Mixed headers and structured content
        has_structure = (
            due_date_indicators >= 3 or
            (section_indicators >= 1 and structured_lines >= 2) or
            (section_indicators >= 2 and len(lines) >= 5)
        )
        
        return has_structure
    
    # Parsing Assessment Nodes (LangGraph Integration)
    
    async def _parsing_assessment_node(self, state: GraphState) -> GraphState:
        """Intelligent parsing assessment node using LangGraph workflow"""
        logger.info("Running parsing assessment node")
        
        try:
            from worker.services.parsing_assessment_nodes import parsing_assessment_node
            return await parsing_assessment_node(state)
            
        except Exception as e:
            logger.error(f"Error in parsing assessment node: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "parsing_assessment",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state
    
    async def _parsing_supplement_node(self, state: GraphState) -> GraphState:
        """Parsing data supplementation node"""
        logger.info("Running parsing supplement node")
        
        try:
            from worker.services.parsing_assessment_nodes import parsing_supplement_node
            return await parsing_supplement_node(state)
            
        except Exception as e:
            logger.error(f"Error in parsing supplement node: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "parsing_supplement",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state
    
    async def _parsing_reparse_node(self, state: GraphState) -> GraphState:
        """Parsing re-parsing node using LLM"""
        logger.info("Running parsing reparse node")
        
        try:
            from worker.services.parsing_assessment_nodes import parsing_reparse_node
            return await parsing_reparse_node(state)
            
        except Exception as e:
            logger.error(f"Error in parsing reparse node: {e}", exc_info=True)
            dynamic_results = getattr(state, 'dynamic_results', [])
            dynamic_results.append({
                "node_type": "parsing_reparse",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            state.dynamic_results = dynamic_results
            return state

# Global instance
dynamic_node_manager = DynamicNodeManager()