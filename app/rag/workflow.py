from langgraph.graph import StateGraph, START, END

from app.rag.state import AgentState
from app.rag.nodes import (
    route_question,
    router_after_router,
    retrieve_kb,
    grade_kb,
    after_kb,
    search_web,
    grade_web,
    after_web,
    rewrite_query,
    generate_from_kb,
    generate_from_web,
    direct_answer,
    insufficient,
    load_memory,
    store_memory,
)

def build_graph():
    graph = StateGraph(AgentState)

    for name, fn in {
        "route_question": route_question,
        "retrieve_kb": retrieve_kb,
        "grade_kb": grade_kb,
        "search_web": search_web,
        "grade_web": grade_web,
        "rewrite_query": rewrite_query,
        "generate_from_kb": generate_from_kb,
        "generate_from_web": generate_from_web,
        "direct_answer": direct_answer,
        "insufficient": insufficient,
        "load_memory": load_memory,
        "store_memory": store_memory,

    }.items():
        graph.add_node(name, fn)

    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "route_question")
    graph.add_conditional_edges("route_question", router_after_router, {
        "retrieve_kb": "retrieve_kb",
        "direct_answer": "direct_answer"
    })

    graph.add_edge("retrieve_kb", "grade_kb")

    graph.add_conditional_edges("grade_kb", after_kb, {
        "generate_from_kb": "generate_from_kb",
        "search_web": 'search_web'
    })

    graph.add_edge("search_web", "grade_web")
    graph.add_conditional_edges("grade_web", after_web, {
        "generate_from_web": "generate_from_web",
        "rewrite_query": "rewrite_query",
        "insufficient": "insufficient",
    })

    graph.add_edge("rewrite_query", "retrieve_kb")
    graph.add_edge("generate_from_kb", "store_memory")
    graph.add_edge("generate_from_web", "store_memory")
    graph.add_edge("direct_answer", "store_memory")
    graph.add_edge("insufficient", "store_memory")
    graph.add_edge("store_memory", END)



    return graph.compile()

agent_graph = build_graph()

def ask(question: str, user_id: str = "default"):
    initial: AgentState = {
        "question": question,
        "current_query": question,
        "kb_docs": [],
        "web_results": "",
        "kb_grade": "",
        "web_grade": "",
        "answer": "",
        "source_used": "",
        "retry_count": 0,
        "trace": [],
        "citations": [],
        "user_id": user_id,
        "memories": [],
    }
    return agent_graph.invoke(initial)

