"""Streamlit frontend for the Enterprise AI Assistant."""

import base64
import json
from datetime import datetime

import requests
import streamlit as st

# --- Page Config ---
st.set_page_config(
    page_title="Enterprise AI Assistant",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Constants ---
API_BASE = "http://localhost:8001"


# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    import uuid

    st.session_state.conversation_id = str(uuid.uuid4())


def query_api(question: str) -> dict:
    """Send query to FastAPI backend."""
    try:
        response = requests.post(
            f"{API_BASE}/query",
            json={
                "query": question,
                "conversation_id": st.session_state.conversation_id,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "error": "Cannot connect to backend. Make sure FastAPI is running on port 8001."
        }
    except requests.exceptions.ReadTimeout:
        return {
            "error": "Request timed out. The query may be too complex. Please try a simpler question or try again."
        }
    except Exception as e:
        return {"error": str(e)}


def get_cost_summary() -> dict:
    """Fetch cost summary from API."""
    try:
        response = requests.get(f"{API_BASE}/cost/summary", timeout=10)
        return response.json()
    except Exception:
        return {}


def get_guardrail_stats() -> dict:
    """Fetch guardrail stats from API."""
    try:
        response = requests.get(f"{API_BASE}/guardrails/stats", timeout=10)
        return response.json()
    except Exception:
        return {}


# --- Sidebar ---
with st.sidebar:
    st.title("Enterprise AI Assistant")
    st.caption("E-Commerce Analytics with MCP + Guardrails")

    st.divider()

    # Cost Dashboard
    st.subheader("Cost Dashboard")
    cost = get_cost_summary()
    if cost:
        col1, col2 = st.columns(2)
        col1.metric("Total Requests", cost.get("total_requests", 0))
        col2.metric("Total Tokens", f"{cost.get('total_tokens', 0):,}")

        col3, col4 = st.columns(2)
        col3.metric("Total Cost", f"${cost.get('total_cost_usd', 0):.6f}")
        col4.metric("Avg Latency", f"{cost.get('avg_latency_ms', 0):.0f}ms")

    st.divider()

    # Guardrail Stats
    st.subheader("Guardrail Stats")
    stats = get_guardrail_stats()
    if stats:
        col1, col2 = st.columns(2)
        col1.metric("Total Checks", stats.get("total_checks", 0))
        col2.metric("Blocked", stats.get("blocks", 0))
        st.metric("Warnings", stats.get("warnings", 0))

    st.divider()

    # Sample Questions
    st.subheader("Try These Questions")
    sample_questions = [
        "What are the top 5 products by total revenue?",
        "Show me a bar chart of revenue by product category",
        "Who are the top 3 customers by lifetime value?",
        "Generate a detailed report on sales performance",
        "Which products have less than 50 units in stock?",
        "What is the average rating for Electronics products?",
        "Show me the count of orders by status",
    ]
    for q in sample_questions:
        if st.button(q, key=f"sample_{q[:20]}", use_container_width=True):
            st.session_state.sample_query = q

    st.divider()

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        import uuid

        st.session_state.conversation_id = str(uuid.uuid4())
        st.rerun()


# --- Main Chat Area ---
st.title("Enterprise AI Assistant")
st.caption("Ask natural language questions about your e-commerce business data")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Show chart if present
        if msg.get("chart"):
            try:
                chart_bytes = base64.b64decode(msg["chart"])
                st.image(chart_bytes, caption="Generated Chart")
            except Exception:
                pass

        # Show metadata in expander
        if msg.get("metadata"):
            with st.expander("Details"):
                meta = msg["metadata"]
                if meta.get("sql"):
                    st.code(meta["sql"], language="sql")
                if meta.get("cost"):
                    cost_info = meta["cost"]
                    st.caption(
                        f"Tokens: {cost_info.get('total_tokens', 0)} | "
                        f"Cost: ${cost_info.get('estimated_cost_usd', 0):.6f} | "
                        f"Latency: {meta.get('execution_time_ms', 0):.0f}ms"
                    )
                if meta.get("guardrails"):
                    for g in meta["guardrails"]:
                        status_icon = (
                            "✅"
                            if g["status"] == "passed"
                            else "⚠️" if g["status"] == "warning" else "🚫"
                        )
                        st.caption(
                            f"{status_icon} {g['guardrail_name']}: {g['message']}"
                        )

# Handle sample query button
if "sample_query" in st.session_state:
    query = st.session_state.pop("sample_query")
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            result = query_api(query)

        if result.get("error"):
            st.error(result["error"])
            st.session_state.messages.append(
                {"role": "assistant", "content": f"Error: {result['error']}"}
            )
        else:
            response_text = result.get("response", "")
            st.markdown(response_text)

            metadata = {
                "sql": (
                    result.get("sql_result", {}).get("sql", "")
                    if result.get("sql_result")
                    else ""
                ),
                "cost": result.get("cost", {}),
                "execution_time_ms": result.get("execution_time_ms", 0),
                "guardrails": result.get("guardrail_checks", []),
            }

            msg_data = {
                "role": "assistant",
                "content": response_text,
                "metadata": metadata,
            }

            # Display chart if present
            chart = result.get("chart")
            if chart and chart.get("chart_base64"):
                try:
                    chart_bytes = base64.b64decode(chart["chart_base64"])
                    st.image(chart_bytes, caption="Generated Chart")
                    msg_data["chart"] = chart["chart_base64"]
                except Exception:
                    pass

            st.session_state.messages.append(msg_data)

    st.rerun()

# Chat input
if prompt := st.chat_input("Ask about your business data..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            result = query_api(prompt)

        if result.get("error"):
            st.error(result["error"])
            st.session_state.messages.append(
                {"role": "assistant", "content": f"Error: {result['error']}"}
            )
        else:
            response_text = result.get("response", "")
            st.markdown(response_text)

            metadata = {
                "sql": (
                    result.get("sql_result", {}).get("sql", "")
                    if result.get("sql_result")
                    else ""
                ),
                "cost": result.get("cost", {}),
                "execution_time_ms": result.get("execution_time_ms", 0),
                "guardrails": result.get("guardrail_checks", []),
            }

            msg_data = {
                "role": "assistant",
                "content": response_text,
                "metadata": metadata,
            }

            chart = result.get("chart")
            if chart and chart.get("chart_base64"):
                try:
                    chart_bytes = base64.b64decode(chart["chart_base64"])
                    st.image(chart_bytes, caption="Generated Chart")
                    msg_data["chart"] = chart["chart_base64"]
                except Exception:
                    pass

            st.session_state.messages.append(msg_data)
