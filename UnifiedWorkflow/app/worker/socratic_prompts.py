"""
A library of Socratic prompts categorized by purpose.
"""

PROMPT_LIBRARY = {
    "mission_statement": {
        "value_elicitation": {
            "open_ended": [
                "What activities make you feel most alive and engaged?",
                "If you didn't have to worry about money, what would you do with your time?",
                "What change do you most want to see in the world?",
            ],
            "clarifying": [
                "You mentioned [keyword]. What does that mean to you in this context?",
                "Can you give me a specific example of what you mean by [concept]?",
            ],
        },
        "passion_and_skills": {
            "open_ended": [
                "Describe a time you were so absorbed in a task that you lost track of time. What were you doing?",
                "What skills do people typically compliment you on?",
            ],
        },
        "synthesis": {
            "summarizing": [
                "So far, we've identified that you value [values] and you're skilled at [skills]. Does that sound right?",
                "Based on what you've said, it seems like [theme] is a recurring idea. What do you think?",
            ],
        },
    },
    "personal_reflection": {
        "reflection": {
            "open_ended": [
                """An Analysis of The Reflective AI Coach Framework for Personal and Professional Development

The Foundational Architecture of a Reflective Dialogue Engine

This analysis examines the architecture of the \"Reflective AI Coach,\" a framework designed for personal and emotional development. Its core principles represent a significant departure from conventional assessment tools, establishing a methodology grounded in Socratic guidance, engineered psychological safety, and a longitudinal structure. This combination forms the bedrock of a uniquely effective and sustainable development experience, making it a powerful basis for development interviews.

The Socratic Paradigm: Shifting from Oracle to Catalyst

The foundational philosophy of the AI Coach framework positions the Large Language Model (LLM) not as an oracle that dispenses information, but as a catalyst for the user's own reflective process.1 This is achieved through a \"pull\" dynamic, where insights are elicited from the user, rather than a \"push\" dynamic, where information is provided to them. The system is explicitly built upon the Socratic Model, a form of cooperative dialogue designed to stimulate critical thinking by drawing out underlying ideas and presuppositions.1

The AI's primary objective is not to give answers but to pose thoughtful, open-ended questions that guide the user on a journey of self-exploration.1 This pedagogical approach is rooted in the Socratic tradition of using dialogue to foster deeper understanding and encourage individuals to articulate their own reasoning. Research validates this method, demonstrating its effectiveness in developing higher-order thinking skills—such as analysis, evaluation, and synthesis—and enhancing metacognitive abilities.1 By explicitly engineering the AI to avoid direct answers, the framework mirrors the non-directive facilitation style of expert human tutors, which has been shown to encourage learners to construct stronger arguments and engage more critically with diverse perspectives.1

Engineered Psychological Safety: The Anonymity Advantage

A key innovation of the framework is its capacity to engineer psychological safety, a critical component for fostering genuine self-reflection. Traditional human-led coaching, while valuable, can be hindered by interpersonal dynamics such as evaluation apprehension, impression management, and social desirability bias.2 These factors can inhibit a user's willingness to be vulnerable and explore sensitive topics.

The AI Coach mitigates these barriers by providing an anonymous, non-judgmental space for dialogue. This anonymity is a powerful enabler of candor, allowing users to engage with their thoughts and feelings without fear of social repercussions.2 Research has consistently shown that individuals are more likely to disclose sensitive information and express unconventional ideas when interacting with an anonymous system.3 This engineered safety is not merely a feature but a core architectural principle that enhances the quality and depth of the reflective process.

The Longitudinal Approach: Development as a Continuous Journey

The framework is designed for longitudinal engagement, recognizing that personal and professional development is not a one-time event but a continuous journey. The system's architecture supports this by maintaining a persistent, user-specific dialogue history, allowing for the tracking of progress and the identification of recurring themes over time.

This longitudinal structure enables the AI to build a dynamic, evolving model of the user's development, adapting its guidance based on past interactions. This approach is consistent with modern theories of learning and development, which emphasize the importance of sustained, reflective practice.4 By providing a consistent and accessible space for ongoing self-exploration, the framework supports a more holistic and impactful development experience than is possible with episodic, one-off interventions.

Conclusion: A New Frontier in Human-Centered AI

The Reflective AI Coach framework represents a significant advancement in the application of AI for personal and professional development. By combining the Socratic method with engineered psychological safety, and a longitudinal design, it creates a uniquely effective environment for self-discovery and growth. This approach is not only aligns with established pedagogical principles but also leverages the unique affordances of AI to overcome the limitations of traditional coaching methods. As such, it stands as a powerful example of human-centered AI, designed not to replace human judgment but to augment and amplify our innate capacity for reflection and growth."""
            ],
        },
    },
    # ... (other interview types would be defined here)
}
