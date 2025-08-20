from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import ollama

router = APIRouter()

class EventTitle(BaseModel):
    title: str

@router.post("/summarize-event-title")
async def summarize_event_title(event_title: EventTitle):
    """
    Uses an LLM to rephrase an event title for use in UI options.
    """
    try:
        # Prepare the prompt for the LLM
        prompt = f"""
        Given the calendar event title "{event_title.title}", rephrase it for two UI buttons.
        1. For a button that marks the event as a completed task. The text should be concise and in the form of an action, like "Submit '...' as a completed task".
        2. For a button that opens a chat to generate sub-tasks for the event. The text should be like "Generate tasks for EOD planning".

        Your response must be a JSON object with two keys: "option1_text" and "option2_text".
        For example, for the title "Team Meeting", you might return:
        {{
          "option1_text": "Submit 'Team Meeting' as a completed task",
          "option2_text": "Generate tasks for the Team Meeting"
        }}
        """

        # Call the LLM
        response = ollama.chat(
            model='mistral', # Or your preferred model
            messages=[{'role': 'user', 'content': prompt}],
            format='json'
        )

        return response['message']['content']

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
