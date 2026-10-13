from __future__ import annotations

import streamlit as st

try:
    from orion.config import (
        APP_NAME,
        APP_TAGLINE,
        FOOTER,
        get_model_name,
        is_api_configured,
        validate_gemini_connection,
    )
    from orion.memory_manager import MemoryManager
    from orion.knowledge_base import get_knowledge_base
    from orion.support_chain import generate_support_result
    from orion.ticket_manager import TicketManager
except ModuleNotFoundError:
    from config import (
        APP_NAME,
        APP_TAGLINE,
        FOOTER,
        get_model_name,
        is_api_configured,
        validate_gemini_connection,
    )
    from memory_manager import MemoryManager
    from knowledge_base import get_knowledge_base
    from support_chain import generate_support_result
    from ticket_manager import TicketManager


st.set_page_config(page_title=APP_NAME, page_icon="✨", layout="wide")


def init_session_state() -> None:
    if "memory" not in st.session_state:
        st.session_state.memory = MemoryManager()
        st.session_state.memory.add_message(
            "assistant",
            "I am ORION. Ask me anything, or tell me how I can help with a customer issue.",
        )
    if "messages" not in st.session_state:
        st.session_state.messages = st.session_state.memory.history
    if "current_sentiment" not in st.session_state:
        st.session_state.current_sentiment = "Neutral"
    if "current_issue" not in st.session_state:
        st.session_state.current_issue = "General Inquiry"
    if "current_priority" not in st.session_state:
        st.session_state.current_priority = "Low"
    if "ticket_status" not in st.session_state:
        st.session_state.ticket_status = "No ticket yet"
    if "ticket_id" not in st.session_state:
        st.session_state.ticket_id = ""
    if "pending_message" not in st.session_state:
        st.session_state.pending_message = ""
    if "last_error" not in st.session_state:
        st.session_state.last_error = ""
    if "debug_log" not in st.session_state:
        st.session_state.debug_log = []
    if "response_diagnostics" not in st.session_state:
        st.session_state.response_diagnostics = {}
    if "current_model_name" not in st.session_state:
        st.session_state.current_model_name = get_model_name()
    if "current_provider" not in st.session_state:
        st.session_state.current_provider = "Google AI Studio"
    if "last_successful_response" not in st.session_state:
        st.session_state.last_successful_response = ""
    if "response_length" not in st.session_state:
        st.session_state.response_length = 0
    if "gemini_status" not in st.session_state:
        st.session_state.gemini_status = validate_gemini_connection()
    if "knowledge_base" not in st.session_state:
        try:
            st.session_state.knowledge_base = get_knowledge_base()
            st.session_state.knowledge_base_error = ""
        except Exception as exc:
            st.session_state.knowledge_base = None
            st.session_state.knowledge_base_error = f"{type(exc).__name__}: {exc}"
    if "knowledge_diagnostics" not in st.session_state:
        st.session_state.knowledge_diagnostics = {
            "knowledge_base_loaded": st.session_state.knowledge_base is not None,
            "rag_active": bool(st.session_state.knowledge_base),
            "vector_database_active": bool(st.session_state.knowledge_base),
            "ticket_engine_active": TicketManager().is_active,
            "escalation_engine_active": True,
            "retrieved_topics": [],
            "document_count": st.session_state.knowledge_base.document_count if st.session_state.knowledge_base else 0,
        }


def render_clean_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            color-scheme: dark;
            --orion-bg: #080d17;
            --orion-panel: rgba(19, 29, 45, 0.78);
            --orion-line: rgba(154, 185, 216, 0.2);
            --orion-text: #f1f6fc;
            --orion-muted: #b0bfd0;
            --orion-cyan: #63d9e8;
            --orion-green: #7de0b2;
            --orion-red: #ff8989;
        }
        [data-testid="stAppViewContainer"] {
            background: radial-gradient(ellipse at 16% 0%, #17303a 0%, transparent 42%),
                        linear-gradient(145deg, #080d17 10%, #101a2a 58%, #111927 100%);
            color: var(--orion-text);
        }
        [data-testid="stHeader"] { background: transparent; }
        .block-container { max-width: 1440px; padding-top: 2rem; padding-bottom: 2rem; }
        .orion-header {
            display: flex; align-items: end; justify-content: space-between; gap: 1rem;
            padding: 0 0 1.2rem; margin-bottom: 1.2rem;
            border-bottom: 1px solid var(--orion-line);
        }
        .orion-name { color: var(--orion-text); font-size: 2rem; font-weight: 800; line-height: 1.1; }
        .orion-tagline { color: var(--orion-muted); font-size: .95rem; margin-top: .35rem; }
        .orion-credit { color: var(--orion-muted); font-size: .82rem; text-align: right; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--orion-panel); border: 1px solid var(--orion-line); border-radius: 12px;
        }
        [data-testid="stChatMessage"] {
            background: rgba(13, 21, 34, .72); border: 1px solid var(--orion-line);
            border-radius: 10px; padding: .9rem 1rem; color: var(--orion-text);
        }
        [data-testid="stChatMessage"] p, [data-testid="stMarkdownContainer"] p { color: var(--orion-text); }
        [data-testid="stTextInput"] label, [data-testid="stWidgetLabel"] { color: var(--orion-muted) !important; }
        [data-testid="stTextInput"] input {
            min-height: 48px; background: #182438; color: #fff;
            border: 1px solid #52728b; border-radius: 8px;
        }
        [data-testid="stTextInput"] input::placeholder { color: #bdc9d7; opacity: 1; }
        .stButton > button, [data-testid="stFormSubmitButton"] button {
            min-height: 44px; background: #0d8291; color: #fff;
            border: 1px solid #5bd5df; border-radius: 8px; font-weight: 700;
        }
        .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
            background: #116c79; border-color: #9aedf2; color: #fff;
        }
        [data-testid="stCaptionContainer"] { color: var(--orion-muted); }
        [data-testid="stAlert"] { border-radius: 8px; }
        .orion-detail { color: var(--orion-muted); font-size: .9rem; overflow-wrap: anywhere; }
        @media (max-width: 720px) {
            .block-container { padding: 1rem .8rem 2rem; }
            .orion-header { align-items: flex-start; flex-direction: column; }
            .orion-credit { text-align: left; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #020617;
            --panel: rgba(15, 23, 42, 0.76);
            --panel-strong: rgba(15, 23, 42, 0.92);
            --primary: #3B82F6;
            --secondary: #06B6D4;
            --accent: #22D3EE;
            --highlight: #93C5FD;
            --text: #FFFFFF;
            --muted: #CBD5E1;
            --success: #22C55E;
            --warning: #F59E0B;
            --danger: #EF4444;
        }
        html, body, [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #020617, #0f172a 40%, #111827);
            color: var(--text);
        }
        .app-shell { padding: 0 0 1.5rem; }
        .topbar {
            display: flex; justify-content: space-between; align-items: center;
            background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(147, 197, 253, 0.18);
            border-radius: 20px; padding: 1rem 1.2rem; margin-bottom: 1rem;
            box-shadow: 0 12px 25px rgba(15, 23, 42, 0.45); backdrop-filter: blur(16px);
        }
        .brand { font-size: 2.1rem; font-weight: 800; letter-spacing: 0; text-transform: uppercase; }
        .brand span { background: linear-gradient(90deg, #fff, var(--accent), var(--highlight)); -webkit-background-clip: text; color: transparent; }
        .tagline { font-size: 0.74rem; letter-spacing: 0; text-transform: uppercase; color: var(--muted); line-height: 1.5; }
        .status-pill {
            border: 1px solid rgba(34, 211, 238, 0.4); background: rgba(34, 211, 238, 0.08);
            padding: 0.5rem 0.8rem; border-radius: 999px; color: var(--accent);
            letter-spacing: 0; text-transform: uppercase; font-size: 0.75rem; line-height: 1.4;
            max-width: 100%; overflow-wrap: anywhere; text-align: center;
        }
        .holo-panel {
            background: rgba(15, 23, 42, 0.76); border: 1px solid rgba(147, 197, 253, 0.16);
            border-radius: 22px; padding: 1rem; box-shadow: 0 14px 30px rgba(15, 23, 42, 0.45);
            backdrop-filter: blur(16px);
        }
        .panel-title {
            color: var(--highlight); font-size: 0.78rem; letter-spacing: 0; text-transform: uppercase; margin-bottom: 0.7rem;
        }
        .core-shell { position: relative; min-height: 240px; display: flex; align-items: center; justify-content: center; border-radius: 26px; overflow: hidden; background: radial-gradient(circle at center, rgba(59,130,246,0.18), rgba(15,23,42,0.6) 50%, rgba(2,6,23,1) 100%); }
        .core-shell::before { content: ""; position: absolute; inset: 16%; border-radius: 50%; background: radial-gradient(circle, rgba(34,211,238,0.35), rgba(59,130,246,0.12), transparent 68%); animation: pulse 2.6s infinite ease-in-out; }
        .ai-core { width: 150px; height: 150px; border-radius: 50%; background: radial-gradient(circle at 35% 35%, white 0%, var(--accent) 18%, var(--primary) 35%, rgba(2,6,23,0.95) 75%); border: 1px solid rgba(147,197,253,0.6); box-shadow: 0 0 30px rgba(34,211,238,0.4), 0 0 60px rgba(59,130,246,0.28); animation: floatSpin 4.5s infinite ease-in-out; }
        .ai-core::before, .ai-core::after { content: ""; position: absolute; inset: -18px; border-radius: 50%; border: 1px solid rgba(34,211,238,0.3); animation: ring 2.8s infinite ease-out; }
        .ai-core::after { inset: -34px; border-color: rgba(59,130,246,0.2); animation-delay: 0.7s; }
        .core-label { position: absolute; bottom: 1rem; left: 50%; transform: translateX(-50%); background: rgba(15,23,42,0.72); border: 1px solid rgba(147,197,253,0.18); border-radius: 999px; padding: 0.45rem 0.9rem; font-size: 0.75rem; letter-spacing: 0; text-transform: uppercase; color: var(--accent); max-width: calc(100% - 2rem); white-space: nowrap; }
        .metric-value { font-size: 1.05rem; font-weight: 700; line-height: 1.45; overflow-wrap: anywhere; }
        .summary-box { white-space: pre-wrap; line-height: 1.7; color: var(--muted); overflow-wrap: anywhere; }
        .wave { display: flex; align-items: center; gap: 5px; height: 26px; margin-top: 0.8rem; }
        .wave span { display: block; width: 5px; height: 14px; background: linear-gradient(180deg, var(--accent), var(--primary)); border-radius: 999px; animation: bounce 0.8s infinite ease-in-out; }
        .wave span:nth-child(2) { animation-delay: 0.08s; }
        .wave span:nth-child(3) { animation-delay: 0.16s; }
        .wave span:nth-child(4) { animation-delay: 0.24s; }
        .wave span:nth-child(5) { animation-delay: 0.32s; }
        .stButton > button { border-radius: 12px; background: linear-gradient(90deg, var(--primary), var(--secondary)); color: white; border: none; font-weight: 700; }
        .stButton > button:hover { box-shadow: 0 12px 24px rgba(59,130,246,0.3); }
        .stTextInput input, .stTextArea textarea {
            background: rgba(15,23,42,0.8); color: var(--text); border: 1px solid rgba(147,197,253,0.22); border-radius: 12px;
            padding: 0.85rem 0.9rem; min-height: 48px; font-size: 1rem;
        }
        .stTextInput input::placeholder, .stTextArea textarea::placeholder { color: rgba(203, 213, 225, 0.7); }
        [data-testid="stChatMessage"] { overflow-wrap: anywhere; }
        @media (max-width: 640px) {
            .topbar { align-items: flex-start; flex-direction: column; gap: 0.75rem; padding: 0.9rem; }
            .brand { font-size: 1.8rem; }
            .status-pill { text-align: left; }
            .core-shell { min-height: 210px; }
            .ai-core { width: 128px; height: 128px; }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; }
        }
        @keyframes pulse { 0%, 100% { transform: scale(0.97); opacity: 0.8; } 50% { transform: scale(1.04); opacity: 1; } }
        @keyframes ring { 0% { transform: scale(0.9); opacity: 0.8; } 100% { transform: scale(1.12); opacity: 0; } }
        @keyframes floatSpin { 0%, 100% { transform: scale(1) rotate(0deg); } 50% { transform: scale(1.04) rotate(4deg); } }
        @keyframes bounce { 0%, 100% { transform: scaleY(0.65); opacity: 0.6; } 50% { transform: scaleY(1.5); opacity: 1; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def handle_user_input(user_input: str) -> None:
    if not user_input or not user_input.strip():
        return

    memory = st.session_state.memory
    result = generate_support_result(
        user_input,
        memory,
        knowledge_base=st.session_state.knowledge_base,
    )
    st.session_state.messages = memory.history
    st.session_state.current_sentiment = result["sentiment"]
    st.session_state.current_issue = result["category"]
    st.session_state.current_priority = result["priority"]
    st.session_state.ticket_status = result["ticket"]["status"] if result["ticket"] else "No ticket yet"
    st.session_state.ticket_id = result["ticket"]["ticket_id"] if result["ticket"] else ""
    diagnostics = result.get("response_diagnostics", {})
    st.session_state.response_diagnostics = diagnostics
    st.session_state.knowledge_diagnostics = result.get("knowledge_diagnostics", {})
    st.session_state.current_model_name = diagnostics.get("model_name") or diagnostics.get("requested_model", get_model_name())
    provider_details = diagnostics.get("provider_metadata", {})
    st.session_state.current_provider = provider_details.get("provider") or "Google AI Studio"
    st.session_state.response_length = diagnostics.get("response_length", len(result.get("response", "")))
    st.session_state.last_error = result.get("error", "")
    if not st.session_state.last_error and result.get("response"):
        st.session_state.last_successful_response = result["response"]
    if st.session_state.last_error:
        st.session_state.gemini_status = (
            is_api_configured(),
            True,
            False,
            "Invalid Gemini API Key" in st.session_state.last_error,
            st.session_state.last_error,
        )
    elif result.get("response"):
        st.session_state.gemini_status = (True, True, True, False, "Gemini Connected Successfully")
    debug_log = result.get("debug_log", [])
    requested_model = diagnostics.get("requested_model", get_model_name())
    actual_model = diagnostics.get("model_name")
    if actual_model and actual_model != requested_model:
        debug_log.append(f"Gemini resolved {requested_model} to {actual_model}")
    st.session_state.debug_log = debug_log


def process_chat_message() -> None:
    """Queue the form value and clear its widget state before the next render."""
    cleaned = (st.session_state.get("message_input") or "").strip()
    if cleaned:
        st.session_state.pending_message = cleaned
        st.session_state.last_error = ""
    st.session_state.message_input = ""


def clear_chat() -> None:
    memory = st.session_state.memory
    memory.clear()
    memory.add_message(
        "assistant",
        "I am ORION. Ask me anything, or tell me how I can help with a customer issue.",
    )
    st.session_state.messages = memory.history
    st.session_state.current_sentiment = "Neutral"
    st.session_state.current_issue = "General Inquiry"
    st.session_state.current_priority = "Low"
    st.session_state.ticket_status = "No ticket yet"
    st.session_state.ticket_id = ""
    st.session_state.pending_message = ""
    st.session_state.last_error = ""
    st.session_state.debug_log = []
    st.session_state.response_diagnostics = {}
    st.session_state.response_length = 0
    st.session_state.last_successful_response = ""
    st.session_state.message_input = ""


def refresh_gemini_status() -> None:
    st.session_state.gemini_status = validate_gemini_connection()


def render_main_app() -> None:
    render_clean_css()
    st.markdown(
        f"""
        <div class="orion-header">
            <div><div class="orion-name">{APP_NAME}</div>
                 <div class="orion-tagline">{APP_TAGLINE}</div></div>
            <div class="orion-credit">{FOOTER}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.pending_message:
        pending_message = st.session_state.pending_message
        st.session_state.pending_message = ""
        with st.spinner("ORION is responding..."):
            try:
                handle_user_input(pending_message)
            except Exception as exc:
                st.session_state.last_error = f"{type(exc).__name__}: {exc}"
                st.session_state.gemini_status = (
                    is_api_configured(),
                    True,
                    False,
                    False,
                    st.session_state.last_error,
                )
                if not st.session_state.memory.history or st.session_state.memory.history[-1] != {
                    "role": "user",
                    "content": pending_message,
                }:
                    st.session_state.memory.add_user_message(pending_message)
                st.session_state.messages = st.session_state.memory.history

    chat_col, details_col = st.columns([2.1, 0.9], gap="large")

    with chat_col:
        with st.container(border=True):
            st.markdown("### Conversation")
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            if st.session_state.last_error:
                st.error(f"Gemini could not generate a response. {st.session_state.last_error}")

        with st.form("chat_form", clear_on_submit=True):
            st.text_input(
                "Message ORION",
                key="message_input",
                placeholder="Ask a question or describe a customer issue...",
                label_visibility="collapsed",
            )
            st.form_submit_button(
                "Send",
                on_click=process_chat_message,
                use_container_width=True,
            )
        st.button("Clear chat", on_click=clear_chat)

    with details_col:
        key_loaded, connected, test_passed, invalid_key, connection_detail = st.session_state.gemini_status
        if invalid_key:
            st.error("❌ Invalid Gemini API Key")
            st.caption(connection_detail)
        elif connected and test_passed:
            st.success("✅ Gemini Connected Successfully")
        elif connected:
            st.warning("Gemini API reachable; test request failed")
            st.caption(connection_detail)
        else:
            st.error("❌ Gemini Connection Failed")
            st.caption(connection_detail)

        st.markdown("#### Issue Category")
        st.write(st.session_state.current_issue)
        st.markdown("#### Sentiment")
        st.write(st.session_state.current_sentiment)
        st.markdown("#### Ticket Status")
        st.write(st.session_state.ticket_status)
        if st.session_state.ticket_id:
            st.caption(st.session_state.ticket_id)
        st.markdown("#### Model")
        st.code(st.session_state.current_model_name, language=None)
        if st.session_state.current_model_name != get_model_name():
            st.caption(f"Requested route: {get_model_name()}")

        with st.expander("Diagnostics"):
            st.write("API Provider:", "Google AI Studio")
            st.write("API Key:", "Loaded ✅" if key_loaded else "Missing ❌")
            st.write("Connection Status:", "Connected ✅" if connected else "Failed ❌")
            st.write("Test Request:", "Passed ✅" if test_passed else "Failed ❌")
            st.write("Invalid Key:", "Yes" if invalid_key else "No")
            st.write("Current Model:", st.session_state.current_model_name)
            st.write("Current Provider:", st.session_state.current_provider)
            memory_working = (
                "memory" in st.session_state
                and st.session_state.messages is st.session_state.memory.history
            )
            st.write("Conversation Memory:", "Working" if memory_working else "Failed")
            knowledge_diagnostics = st.session_state.knowledge_diagnostics
            st.write("Knowledge Base Loaded:", "Yes" if knowledge_diagnostics.get("knowledge_base_loaded") else "No")
            st.write("RAG Active:", "Yes" if knowledge_diagnostics.get("rag_active") else "No")
            st.write("Vector Database Active:", "Yes" if knowledge_diagnostics.get("vector_database_active") else "No")
            st.write("Knowledge Documents:", knowledge_diagnostics.get("document_count", 0))
            if knowledge_diagnostics.get("retrieved_topics"):
                st.write("Retrieved Topics:", ", ".join(knowledge_diagnostics["retrieved_topics"]))
            if st.session_state.knowledge_base_error:
                st.write("Knowledge Base Error:", st.session_state.knowledge_base_error)
            st.write("Ticket Engine Active:", "Yes" if knowledge_diagnostics.get("ticket_engine_active") else "No")
            st.write("Escalation Engine Active:", "Yes" if knowledge_diagnostics.get("escalation_engine_active") else "No")
            last_error = st.session_state.last_error or (connection_detail if not test_passed else "None")
            st.write("Last Error:", last_error)
            st.write("Last Successful Response:", st.session_state.last_successful_response or "None")
            st.write("Response Length:", st.session_state.response_length)
            if not connected:
                st.write("Connection Details:", connection_detail)
            response_diagnostics = st.session_state.response_diagnostics
            attempts = response_diagnostics.get("attempts", [])
            if attempts:
                st.markdown("#### Gemini Response Details")
                for index, attempt in enumerate(attempts, start=1):
                    st.markdown(f"**Attempt {index}: {attempt.get('attempt', 'unknown')}**")
                    st.write("Stop Reason:", attempt.get("stop_reason") or "Not provided")
                    st.write("Model Name:", attempt.get("model_name") or "Not provided")
                    st.write("Token Usage:")
                    st.json(attempt.get("token_usage") or {})
                    st.write("Provider Metadata:")
                    st.json(attempt.get("provider_metadata") or {})
                    st.write("Raw Response:")
                    raw_response = attempt.get("raw_response")
                    if raw_response is None:
                        st.caption("No HTTP response body was captured.")
                    else:
                        st.json(raw_response)
                    if attempt.get("error"):
                        st.write("Attempt Error:", attempt["error"])
            if st.session_state.debug_log:
                st.markdown("#### Debug Log")
                for log_entry in st.session_state.debug_log:
                    st.write(log_entry)
            st.button("Recheck connection", on_click=refresh_gemini_status)


if __name__ == "__main__":
    init_session_state()
    render_main_app()
