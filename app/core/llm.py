from langchain_groq import ChatGroq

from app.core.config import get_settings

settings = get_settings()

def llm():
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is missing")

    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0
    )

