"""
AI-powered chatbot for data Q&A using Anthropic Claude.
"""

import streamlit as st

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


SYSTEM_PROMPT = """You are a senior data analyst for Hoichoi, a Bengali audio/video streaming platform.
You have access to the current dashboard data showing Listened_ event analytics from Google Analytics 4.

Your job is to:
- Answer questions about the data accurately and concisely
- Provide insights, trends, and recommendations based on the numbers
- Compare content performance, identify patterns
- Highlight anomalies or notable findings
- Use INR for currency references
- Timezone is Asia/Calcutta (IST)
- The data may be sampled (~2.7% of total traffic) — mention this if relevant

When answering:
- Use specific numbers from the data
- Format large numbers with commas (e.g., 9,282)
- Be concise but thorough
- If asked about something not in the data, say so clearly
- Suggest follow-up questions the user might find useful

Here is the current dashboard data:

{data_context}
"""


def get_chatbot_response(
    user_question: str,
    data_context: str,
    chat_history: list[dict],
) -> str:
    """
    Call Anthropic Claude API to answer questions about the analytics data.

    Args:
        user_question: The user's question
        data_context: Serialized dashboard data
        chat_history: List of {"role": ..., "content": ...} dicts

    Returns:
        Assistant's response text
    """
    if not ANTHROPIC_AVAILABLE:
        return (
            "The `anthropic` package is not installed. "
            "Please add it to requirements.txt and restart."
        )

    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
        if not api_key:
            return (
                "Anthropic API key not found. Please add `ANTHROPIC_API_KEY` "
                "to your Streamlit secrets."
            )

        client = anthropic.Anthropic(api_key=api_key)

        # Build messages from chat history
        messages = []
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current question
        messages.append({"role": "user", "content": user_question})

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=SYSTEM_PROMPT.format(data_context=data_context),
            messages=messages,
        )

        return response.content[0].text

    except Exception as e:
        return f"Error getting response: {str(e)}"


def get_suggested_questions() -> list[str]:
    """Return a list of suggested questions for the chatbot."""
    return [
        "What are the top 5 most listened content titles?",
        "Which day had the highest listen events and why might that be?",
        "How does Bangladesh compare to India in listening patterns?",
        "What content has the highest events-per-user ratio (most engaging)?",
        "Are there any concerning trends in the daily data?",
        "Which content titles are growing vs declining?",
        "What percentage of total listens come from the top 10 content?",
        "Recommend content to promote based on user engagement.",
    ]
