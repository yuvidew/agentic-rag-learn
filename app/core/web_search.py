from langchain_tavily import TavilySearch

from app.core.config import get_settings

settings = get_settings()

def web_search_tool():
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is missing")

    return TavilySearch(
        tavily_api_key=settings.tavily_api_key,
        max_results=5,
        topic="general",
        include_answer=True,
        include_raw_content=False
    )

if __name__ == "__main__":
    print(web_search_tool().invoke({"query": "Nana patekar"}))