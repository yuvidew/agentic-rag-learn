import logging
from typing import Literal

from app.core.config import get_settings
from app.core.llm import llm
from app.core.web_search import web_search_tool
from app.rag.state import AgentState, RouteDecision, EvidenceGrade
from app.rag.vectorestore import get_retriever
from app.core.memory import search_memories, save_memory


logger = logging.getLogger(__name__)
settings = get_settings()

# Helper: appends a step message to the trace list so the UI can show what the agent did.
def add_trace(state: AgentState, message: str):
    return [*state.get("trace", []), message]

# Node: LLM decides whether the question needs the company KB ("kb") or is just casual chat ("direct").
def route_question(state: AgentState):
    router = llm().with_structured_output(RouteDecision, method="json_mode")
    decision = router.invoke(f"""
    You route messages for an enterprise IT support assistant.
    Use kb for questions about company IT policies, VPN, password reset, MFA, laptop setup,
    software access, security, email, devices, troubleshooting, or technology support.
    Use direct only for greetings, thanks, or casual chat that needs no company knowledge.
    Question: {state['question']}
    Return valid JSON like {{"route":"kb"}}.
    """)

    return {
        "source_used": decision.route,
        "trace": add_trace(state, f"Router -> {decision.route.upper()}")
    }

# Edge: picks the next node based on the router's decision (kb -> retrieve_kb, else direct_answer).
def router_after_router(state: AgentState) -> Literal["retrieve_kb", "direct_answer"]:
    return "retrieve_kb" if state["source_used"] == "kb" else "direct_answer"

# Node: fetches the most relevant chunks from the private vector store for the current query.
def retrieve_kb(state: AgentState):
    docs = get_retriever().invoke(state["current_query"])

    return {
        "kb_docs": docs,
        "trace": add_trace(state, f"Privat KB retrieval -> {len(docs)} chunks")
    }

# Node: LLM judges whether the retrieved KB chunks are good enough to answer the question.
def grade_kb(state: AgentState):
    grafer = llm().with_structured_output(EvidenceGrade, method="json_mode")
    context = "\n\n".join(f"Source: {d.metadata.get('source', 'unknown')}\n{d.page_content}" for d in state["kb_docs"])

    grade = grafer.invoke(f"""
        You grade evidence for an enterprise IT support assistant.
        Question: {state['question']}
        Private company KB evidence:\n{context}
        Return good only if the evidence is sufficient to answer confidently and specifically.
        Otherwise return weak. JSON: {{"grade":"good"}} or {{"grade":"weak"}}.
    """)

    return {
        "kb_grade": grade.grade,
        "trace": add_trace(state, f"KB evidence grade → {grade.grade.upper()}")
    }

# Edge: good KB evidence -> generate answer, weak evidence -> fall back to web search.
def after_kb(state: AgentState) -> Literal["generate_from_kb", "search_web"]:
    return "generate_from_kb" if state["kb_grade"] == "good" else "search_web"

# Node: runs a Tavily web search as fallback and collects results plus citations.
def search_web(state: AgentState):
    result = web_search_tool().invoke({
        "query" : state["current_query"]
    })

    lines, citations = [], []

    if isinstance(result, dict):
        if result.get("answer"):
            lines.append(f"Search answer: {result['answer']}")
        for item in result.get("results", []):
            title, url, content = item.get("title", ""), item.get("url", ""), item.get("content", "")

            lines.append(f"Title: {title}\nURL: {url}\nContent: {content}")
            citations.append({"title": title or url, "url": url, "type": "web"})
    else:
        lines.append(str(result))

    return {
        "web_results": "\n\n".join(lines),
        "citations": citations,
        "source_used": "web",
        "trace": add_trace(state, "Web fallback → Tavily search"),
    }

# Node: LLM judges whether the web results are relevant and sufficient to answer.
def grade_web(state: AgentState):
    grader = llm().with_structured_output(EvidenceGrade, method="json_mode")
    grade = grader.invoke(f"""
    Question: {state['question']}
    Web evidence:\n{state['web_results']}
    Return good if the evidence is sufficient and directly relevant; otherwise weak.
    Return valid JSON like {{"grade":"good"}}.
    """)

    return {
        "web_grade": grade.grade,
        "trace": add_trace(state, f"Web evidence grade → {grade.grade.upper()}")
    }

# Edge: good web evidence -> answer; weak -> rewrite query and retry (up to max_retries); else give up.
def after_web(state: AgentState)-> Literal["generate_from_web", "rewrite_query", "insufficient"]:
    if state["web_grade"] == "good":
        return "generate_from_web"
    if state["retry_count"] < settings.max_retries:
        return "rewrite_query"

    return "insufficient"

# Node: LLM rewrites the question with better technical keywords and bumps the retry counter.
def rewrite_query(state: AgentState):
    rewritten = llm().invoke(f"""
    Rewrite this IT support question for better private knowledge retrieval and vendor web search.
    Preserve intent, add useful technical keywords, do not answer, return only the query.
    Question: {state['question']}
    """).content.strip()

    return {
        "current_query": rewritten,
        "retry_count": state["retry_count"] + 1,
        "trace": add_trace(state, f"Query rewrite → {rewritten}"),
    }

# Node: generates the final answer strictly from KB chunks and builds de-duplicated source citations.
def generate_from_kb(state: AgentState):
    context = "\n\n".join(f"[Source: {d.metadata.get('source','unknown')}]\n{d.page_content}" for d in state["kb_docs"])

    answer = llm().invoke(f"""
    You are an enterprise IT support copilot. Answer ONLY from the private company KB below.
    Be concise, actionable, and safe. If steps are present, present them clearly.
    Do not invent policy details. Mention that the answer is based on the company's private knowledge base.
    {memory_block(state)}Question: {state['question']}\n\nPrivate KB:\n{context}
    """).content


    citations = []
    seen = set()

    for d in state["kb_docs"]:
        src = d.metadata.get("source", "Private KB")

        if src not in seen:
            seen.add(src)
            citations.append({
                "title": src.split("/")[-1],
                "url":"",
                "type":"private_kb"
            })

    return {
        "answer": answer,
        "source_used": "private_kb",
        "citations": citations,
        "trace": add_trace(state, "Answer generation → PRIVATE KB")
    }

def load_memory(state: AgentState):
    mems = search_memories(state["question"], state["user_id"])

    return {
        "memories": mems,
        "trace": add_trace(state, f"Memory recall -> {len(mems)} items")
    }

def store_memory(state: AgentState):
    save_memory(state["question"], state["answer"], state["user_id"])

    return {
        "trace": add_trace(state, "Memory saved")
    }

def memory_block(state: AgentState) -> str:
    mems = state.get("memories", [])

    if not mems:
        return ""

    return "Known facts about this user:\n" + "\n".join(f"- {m}" for m in mems) + "\n\n"

# Node: generates the final answer from web evidence, warning that it is external and needs IT validation.
def generate_from_web(state: AgentState):
    answer = llm().invoke(f"""
You are an enterprise IT support copilot. The private company KB was insufficient.
Answer ONLY from the web evidence below. Clearly say this is external web information and may need IT validation before changing company-managed systems.
Question: {state['question']}\n\nWeb evidence:\n{state['web_results']}
""").content
    return {"answer": answer, "source_used": "web_search", "trace": add_trace(state, "Answer generation → WEB SEARCH")}

# Node: replies briefly to greetings/casual chat without any retrieval.
def direct_answer(state: AgentState):
    answer = llm().invoke(f"""
    Respond briefly and naturally. Use the known facts about the user below if they are relevant.
    {memory_block(state)}Question: {state['question']}
    """).content

    return {
        "answer": answer,
        "source_used": "direct",
        "trace": add_trace(state, "Direct response -> no retrieval")
    }

# Node: terminal fallback when neither KB nor web gave reliable evidence; asks user to contact IT help desk.
def insufficient(state: AgentState):
    return {
        "answer": "I couldn't find enough reliable evidence in the company knowledge base or external search to answer confidently. Please contact the IT help desk or provide more details.",
        "source_used": "insufficient_evidence",
        "trace": add_trace(state, "Stopped → insufficient reliable evidence"),
    }
