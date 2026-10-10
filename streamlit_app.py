import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

SOURCE_LABELS = {
    "private_kb": ":green[Private KB]",
    "web_search": ":violet[Web search]",
    "direct": ":gray[Direct reply]",
    "insufficient_evidence": ":red[Insufficient evidence]",
}
SUGGESTIONS = [
    "How do I reset my password?",
    "How do I set up the VPN on my laptop?",
    "How do I enable MFA?",
    "Hello!",
]

st.set_page_config(page_title="IT Support Copilot", page_icon="🛠️", layout="centered")

if "messages" not in st.session_state:
    st.session_state.messages = []


def render_extras(msg: dict) -> None:
    label = SOURCE_LABELS.get(msg["source_used"], msg["source_used"])
    st.caption(f"Source: {label}")
    citations = msg.get("citations") or []
    if citations:
        links = [f"[{c['title']}]({c['url']})" if c.get("url") else c["title"] for c in citations]
        st.caption("Citations: " + " · ".join(links))
    if msg.get("trace"):
        with st.expander(f"Agent steps ({len(msg['trace'])})"):
            for i, step in enumerate(msg["trace"], 1):
                st.write(f"{i}. {step}")


def ask_backend(question: str) -> dict:
    res = requests.post(f"{API_URL}/api/chat", json={"question": question}, timeout=120)
    if not res.ok:
        try:
            detail = res.json().get("detail", res.text)
        except ValueError:
            detail = res.text
        raise RuntimeError(f"{res.status_code}: {detail}")
    return res.json()


# ---- Sidebar ----
with st.sidebar:
    st.title("🛠️ Support Copilot")
    st.caption("Agentic RAG assistant")

    try:
        requests.get(f"{API_URL}/api/health", timeout=3).raise_for_status()
        st.success("Backend online")
    except requests.RequestException:
        st.error(f"Backend unreachable at {API_URL}")

    st.subheader("Try asking")
    picked = None
    for s in SUGGESTIONS:
        if st.button(s, use_container_width=True):
            picked = s

    st.subheader("Add to knowledge base")
    admin_key = st.text_input("Admin key", type="password")
    uploaded = st.file_uploader("Document", type=["pdf", "txt", "md", "docx"])
    if st.button("Upload & index", type="primary", disabled=uploaded is None):
        with st.spinner("Indexing…"):
            try:
                res = requests.post(
                    f"{API_URL}/api/ingest",
                    headers={"X-Admin-Key": admin_key},
                    files={"file": (uploaded.name, uploaded.getvalue())},
                    timeout=300,
                )
                data = res.json() if res.content else {}
                if res.ok:
                    st.success(f"Indexed {data['file']}: {data['chunks']} chunks")
                else:
                    st.error(data.get("detail", f"Upload failed ({res.status_code})"))
            except requests.RequestException as exc:
                st.error(f"Upload failed: {exc}")

    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ---- Chat ----
st.header("Ask IT support")

if not st.session_state.messages:
    st.info("Answers come from your private knowledge base first, then the web if needed.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("source_used"):
            render_extras(msg)

question = st.chat_input("Describe your IT issue…") or picked
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                data = ask_backend(question)
            except (requests.RequestException, RuntimeError) as exc:
                st.error(f"Something went wrong: {exc}")
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"Something went wrong: {exc}"}
                )
            else:
                msg = {
                    "role": "assistant",
                    "content": data["answer"],
                    "source_used": data["source_used"],
                    "citations": data.get("citations", []),
                    "trace": data.get("trace", []),
                }
                st.markdown(msg["content"])
                render_extras(msg)
                st.session_state.messages.append(msg)
