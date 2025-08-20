# /app/shared_constants.py

# --- Tool IDs ---
PLANNER_TOOL_ID = "handle_planner_interaction"
CALENDAR_TOOL_ID = "handle_calendar_interaction"
CHECK_CALENDAR_EVENTS_TOOL_ID = "check_calendar_events"
CREATE_CALENDAR_EVENT_TOOL_ID = "create_calendar_event_tool"
EDIT_CALENDAR_EVENT_TOOL_ID = "edit_calendar_event_tool"
DELETE_CALENDAR_EVENT_TOOL_ID = "delete_calendar_event_tool"
MOVE_CALENDAR_EVENT_TOOL_ID = "move_calendar_event_tool"
DOCUMENT_QA_TOOL_ID = "handle_document_qa"
HOME_ASSISTANT_TOOL_ID = "handle_home_assistant_interaction"
EMAIL_TOOL_ID = "handle_email_interaction"
DRIVE_TOOL_ID = "handle_drive_interaction"
WEB_SEARCH_TOOL_ID = "handle_web_search"
TASK_MANAGEMENT_TOOL_ID = "handle_task_management_interaction"
UNSTRUCTURED_TOOL_ID = "handle_unstructured_interaction"
FILE_SYSTEM_TOOL_ID = "handle_file_system_interaction"
SOCRATIC_GUIDANCE_TOOL_ID = "handle_socratic_guidance"

# Keys for event data dictionaries
TIME_PREFERENCES_KEY = "time_preferences"
EARLIEST_START_KEY = "earliest_start"
LATEST_FINISH_KEY = "latest_finish"
EVENT_DURATION_KEY = "event_duration"

# --- Event Categories ---
AVAILABLE_CATEGORIES = {"Work", "Health", "Leisure", "Family", "Fitness", "Default"}

# --- Default Scheduling Preferences ---
DEFAULT_PREFERRED_WINDOWS_BY_CATEGORY = {
    "Work": {"start": "09:00", "end": "17:00"},
    "Health": {"start": "08:00", "end": "18:00"}, # Broadly during the day for appointments
    "Leisure": {"start": "18:00", "end": "22:00"},
    "Family": {"start": "17:00", "end": "21:00"},
    "Fitness": {"start": "06:00", "end": "09:00"}, # e.g., Morning workouts
    "Default": {"start": "09:00", "end": "18:00"},
}

# --- System Prompts ---
SYSTEM_PROMPT_CATEGORIZE = """You are an expert event categorizer. Your task is to analyze the summary and description of a calendar event and assign it to one of the following predefined categories.
Output ONLY the category name. Do not add any other text, explanation, or punctuation.

Available Categories:
- Work
- Health
- Leisure
- Family
- Fitness
- Default

If the event does not clearly fit into any of the specific categories, assign it to "Default"."""