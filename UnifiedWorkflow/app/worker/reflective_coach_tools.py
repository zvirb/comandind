"""
This module provides a suite of tools for an LLM to act as a Reflective AI Coach, 
guiding users through a process of self-discovery using Socratic dialogue.
"""

from worker.interview_state_manager import InterviewStateManager
from worker.socratic_prompts import PROMPT_LIBRARY

def initiate_socratic_dialogue(state_manager: InterviewStateManager):
    """
    Starts a Socratic dialogue based on the interview type.
    """
    interview_type = state_manager.interview_type
    # Get the first prompt for the first phase of the interview
    first_phase = list(PROMPT_LIBRARY[interview_type].keys())[0]
    first_prompt = PROMPT_LIBRARY[interview_type][first_phase]["open_ended"][0]
    
    state_manager.transition_to_phase(first_phase)
    state_manager.state["current_question"] = first_prompt
    return first_prompt

def ask_clarifying_question(state_manager: InterviewStateManager, last_statement: str):
    """
    Asks a clarifying question based on the user's last statement.
    This version simulates keyword extraction by finding the first noun.
    """
    interview_type = state_manager.interview_type
    current_phase = state_manager.get_current_phase()
    clarifying_prompt = PROMPT_LIBRARY[interview_type][current_phase]["clarifying"][0]

    # Simple keyword extraction (e.g., find the first noun)
    # In a real app, this would use a proper NLP library (like spaCy or NLTK)
    words = last_statement.split()
    # This is a mock list of nouns for demonstration
    nouns = [word for word in words if word.lower() in ["time", "project", "team", "skill", "passion", "goal", "challenge", "work"]]
    keyword = nouns[0] if nouns else "that"

    clarifying_question = clarifying_prompt.replace("[keyword]", keyword)
    
    state_manager.state["current_question"] = clarifying_question
    return clarifying_question

def summarize_and_reflect(state_manager: InterviewStateManager):
    """
    Summarizes the conversation and offers a reflective prompt.
    """
    user_responses = state_manager.get_user_responses()
    
    # This is a simplified summary. A real implementation would use a summarization model.
    if len(user_responses) == 0:
        return "We haven't talked much yet. What's on your mind?"
        
    summary = " ".join(user_responses)
    
    # In a real implementation, an LLM would generate this reflection.
    reflection_prompt = f"Based on what you've shared so far, it seems like you're focusing on: '{summary[:100]}...'. What connections or patterns do you see in these thoughts?"
    
    return reflection_prompt

def present_scenario_question(state_manager: InterviewStateManager):
    """
    Presents a scenario-based question to the user.
    """
    # This is a placeholder for a more sophisticated scenario selection logic
    scenario = "Imagine you are given a one-year sabbatical with all expenses paid. What project would you undertake?"
    state_manager.state["current_question"] = scenario
    return scenario

def letter_from_the_future_tool(state_manager: InterviewStateManager):
    """
    Guides the user through the 'Letter from the Future' exercise.
    """
    prompt = "Let's try a creative exercise. Imagine it's 10 years from now, and you are living your ideal life. Write a letter to your present self describing what you have accomplished and what your life is like. Please write the letter in a separate text editor and paste it here when you are ready."
    state_manager.state["current_question"] = prompt
    return prompt


def personal_reflection_tool(state_manager: InterviewStateManager):
    """
    Guides the user through the 'Personal Reflection' exercise.
    """
    prompt = """
An Analysis of The Reflective AI Coach Framework for Personal and Professional Development

The Foundational Architecture of a Reflective Dialogue Engine

This analysis examines the architecture of the "Reflective AI Coach," a framework designed for personal and emotional development. Its core principles represent a significant departure from conventional assessment tools, establishing a methodology grounded in Socratic guidance, engineered psychological safety, and a longitudinal structure. This combination forms the bedrock of a uniquely effective and sustainable development experience, making it a powerful basis for development interviews.

The Socratic Paradigm: Shifting from Oracle to Catalyst

The foundational philosophy of the AI Coach framework positions the Large Language Model (LLM) not as an oracle that dispenses information, but as a catalyst for the user's own reflective process.1 This is achieved through a "pull" dynamic, where insights are elicited from the user, rather than a "push" dynamic, where information is provided to them. The system is explicitly built upon the Socratic Model, a form of cooperative dialogue designed to stimulate critical thinking by drawing out underlying ideas and presuppositions.1

The AI's primary objective is not to give answers but to pose thoughtful, open-ended questions that guide the user on a journey of self-exploration.1 This pedagogical approach is rooted in the Socratic tradition of using dialogue to foster deeper understanding and encourage individuals to articulate their own reasoning. Research validates this method, demonstrating its effectiveness in developing higher-order thinking skills—such as analysis, evaluation, and synthesis—and enhancing metacognitive abilities.1 By explicitly engineering the AI to avoid direct answers, the framework mirrors the non-directive facilitation style of expert human tutors, which has been shown to encourage learners to construct stronger arguments and engage more critically with diverse perspectives.1

Engineered Psychological Safety: The Anonymity Advantage

A key innovation of the framework is its capacity to engineer psychological safety, a critical component for fostering genuine self-reflection. Traditional human-led coaching, while valuable, can be hindered by interpersonal dynamics such as evaluation apprehension, impression management, and social desirability bias.2 These factors can inhibit a user's willingness to be vulnerable and explore sensitive topics.

The AI Coach mitigates these barriers by providing an anonymous, non-judgmental space for dialogue. This anonymity is a powerful enabler of candor, allowing users to engage with their thoughts and feelings without fear of social repercussions.2 Research has consistently shown that individuals are more likely to disclose sensitive information and express unconventional ideas when interacting with an anonymous system.3 This engineered safety is not merely a feature but a core architectural principle that enhances the quality and depth of the reflective process.

The Longitudinal Approach: Development as a Continuous Journey

The framework is designed for longitudinal engagement, recognizing that personal and professional development is not a one-time event but a continuous journey. The system's architecture supports this by maintaining a persistent, user-specific dialogue history, allowing for the tracking of progress and the identification of recurring themes over time.

This longitudinal structure enables the AI to build a dynamic, evolving model of the user's development, adapting its guidance based on past interactions. This approach is consistent with modern theories of learning and development, which emphasize the importance of sustained, reflective practice.4 By providing a consistent and accessible space for ongoing self-exploration, the framework supports a more holistic and impactful development experience than is possible with episodic, one-off interventions.

Conclusion: A New Frontier in Human-Centered AI

The Reflective AI Coach framework represents a significant advancement in the application of AI for personal and professional development. By combining the Socratic method with engineered psychological safety and a longitudinal design, it creates a uniquely effective environment for self-discovery and growth. This approach is not only aligns with established pedagogical principles but also leverages the unique affordances of AI to overcome the limitations of traditional coaching methods. As such, it stands as a powerful example of human-centered AI, designed not to replace human judgment but to augment and amplify our innate capacity for reflection and growth.
"""
    state_manager.state["current_question"] = prompt
    return prompt


import random

def dynamic_assessment_tool(state_manager: InterviewStateManager):
    """
    Presents a dynamic assessment question to the user.
    """
    questions = [
        "On a scale of 1-5, how much do you agree with the statement: 'I prefer a structured work environment'?",
        "You are given a project with a tight deadline and ambiguous requirements. Do you: (a) start immediately and adapt as you go, or (b) spend more time planning and clarifying before you begin?",
        "On a scale of 1-5, how important is it for you to have a collaborative work environment?",
    ]
    question = random.choice(questions)
    state_manager.state["current_question"] = question
    return question

def role_playing_tool(state_manager: InterviewStateManager):
    """
    Initiates a role-playing scenario with the user.
    """
    scenario = "Let's role-play. I'll be a difficult colleague who is resistant to your ideas. How would you respond to this message: 'I don't think your proposal is feasible, and I don't have time to discuss it.'"
    state_manager.state["current_question"] = scenario
    return scenario


def summarize_and_reflect(conversation_history: list):
    """
    Summarizes the conversation and offers a reflective prompt.

    Args:
        conversation_history: A list of statements from the conversation.
    """
    # This is a placeholder implementation.
    summary = "\n".join(conversation_history)
    return f"So far, we've talked about:\n{summary}\n\nWhat connections do you see between these points?"

def identify_themes_and_patterns(conversation_history: list):
    """
    Identifies recurring themes and patterns in the user's responses.

    Args:
        conversation_history: A list of statements from the conversation.
    """
    # This is a placeholder implementation.
    # In a real implementation, this would involve NLP to identify themes.
    return "I'm noticing a recurring theme of 'challenge' in your responses. Does that resonate with you?"

def guide_goal_setting(identified_theme: str):
    """
    Helps the user set meaningful goals based on an identified theme.

    Args:
        identified_theme: The theme to focus on for goal setting.
    """
    # This is a placeholder implementation.
    return f"Let's explore the theme of '{identified_theme}'. What is one small, actionable step you could take to address this?"

def measure_progress(goal: str, start_date: str, current_date: str):
    """
    Measures progress against a user-defined goal.

    Args:
        goal: The goal to measure progress against.
        start_date: The start date of the goal.
        current_date: The current date.
    """
    # This is a placeholder implementation.
    return f"Let's check in on your goal: '{goal}'. How do you feel you've progressed since {start_date}?"

def conclude_session(summary: str):
    """
    Concludes the reflective session with a summary and a forward-looking prompt.

    Args:
        summary: A summary of the session's key insights.
    """
    # This is a placeholder implementation.
    return f"We've had a productive session. Here's a summary of what we discussed:\n{summary}\n\nWhat will you take with you from this conversation?"
