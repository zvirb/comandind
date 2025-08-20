# tool_registry.py
"""
Defines the list of available tools for the AI Workflow Engine.
Each tool has an ID, a description (for the LLM to understand its purpose),
and the name of the handler function in tool_handlers.py that executes the tool.
"""
from . import shared_constants as constants


AVAILABLE_TOOLS = [
    {
        "id": constants.UNSTRUCTURED_TOOL_ID,
        "description": "Use for general conversation, direct questions, or when no other tool is a good fit.",
        "handler_name": "handle_unstructured_interaction",
    },
    {
        "id": constants.CALENDAR_TOOL_ID,
        "description": "Comprehensive calendar management tool for all calendar operations: creating, editing, checking, deleting, or managing calendar events and schedules.",
        "handler_name": "handle_calendar_interaction",
    },
    {
        "id": constants.DOCUMENT_QA_TOOL_ID,
        "description": "Use to answer questions about previously uploaded documents.",
        "handler_name": "handle_document_qa",
    },
    {
        "id": constants.HOME_ASSISTANT_TOOL_ID,
        "description": "Use to control smart home devices via Home Assistant (e.g., 'turn on the lights').",
        "handler_name": "handle_home_assistant_interaction",
    },
    {
        "id": constants.WEB_SEARCH_TOOL_ID,
        "description": "Use for general web searches to answer questions about current events or topics not in local documents.",
        "handler_name": "handle_web_search",
    },
    {
        "id": constants.FILE_SYSTEM_TOOL_ID,
        "description": "Use for file operations like reading, writing, or listing files in the agent's workspace.",
        "handler_name": "handle_file_system_interaction",
    },
    {
        "id": "reflective_coach_tool",
        "description": "A suite of tools to act as a Reflective AI Coach, guiding users through self-discovery using Socratic dialogue.",
        "handler_name": "handle_reflective_coach_interaction",
    },
    {
        "id": "user_profile_tool",
        "description": "A suite of tools for managing user profile data, including settings and preferences.",
        "handler_name": "handle_user_profile_interaction",
    },
    {
        "id": constants.EMAIL_TOOL_ID,
        "description": "Use for email management tasks: composing, scheduling, analyzing, and organizing emails.",
        "handler_name": "handle_email_interaction",
    },
    {
        "id": constants.TASK_MANAGEMENT_TOOL_ID,
        "description": "Use for task management: creating, updating, prioritizing, and analyzing tasks and projects.",
        "handler_name": "handle_task_management_interaction",
    },
    {
        "id": "list_parser_tool",
        "description": "Parse hierarchical lists with inheritance patterns for calendar events, tasks, or other structured data.",
        "handler_name": "handle_list_parsing_request",
    },
    {
        "id": "user_input_tool", 
        "description": "Collect additional information from users when needed to complete complex tasks.",
        "handler_name": "handle_user_input_request",
    },
    {
        "id": "llm_calendar_parser_tool",
        "description": "Parse complex calendar lists and assignments using LLM intelligence. Use when structured data contains many due dates or assignments.",
        "handler_name": "handle_llm_calendar_parsing",
    },
    {
        "id": "general_analysis_tool",
        "description": "Analyze data, texts, problems, or situations using AI reasoning. Use for complex analysis, decision-making, problem-solving, or when deeper understanding is needed.",
        "handler_name": "handle_general_analysis",
    },
    {
        "id": "multi_step_planner_tool", 
        "description": "Plan and execute complex multi-step tasks, workflows, or projects. Use when user requests involve multiple sequential actions or coordinated steps.",
        "handler_name": "handle_multi_step_planning",
    },
    {
        "id": "research_synthesis_tool",
        "description": "Research topics, gather information from multiple sources, and synthesize findings. Use for comprehensive research tasks or knowledge compilation.",
        "handler_name": "handle_research_synthesis",
    },
    {
        "id": "creative_assistance_tool",
        "description": "Help with creative tasks like writing, brainstorming, content creation, or ideation. Use for creative projects, writing assistance, or idea generation.",
        "handler_name": "handle_creative_assistance",
    },
    {
        "id": "delegate_to_helios_team",
        "description": "Delegate complex, multi-faceted tasks to the 12-specialist Helios expert team for comprehensive analysis, collaborative problem-solving, and consensus-based solutions. Use for tasks requiring multiple domain expertise, strategic planning, or comprehensive analysis.",
        "handler_name": "handle_helios_delegation",
    },
]
