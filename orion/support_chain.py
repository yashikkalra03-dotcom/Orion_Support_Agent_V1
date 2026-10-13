from __future__ import annotations

from datetime import date
import json
import re

from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from orion.business_rules import evaluate_support_rules
    from orion.config import get_google_api_key, get_model_name
    from orion.knowledge_base import KnowledgeBase, get_knowledge_base
    from orion.memory_manager import MemoryManager
    from orion.prompts import GENERAL_PROMPT, ORION_SYSTEM_PROMPT, SUPPORT_PROMPT
    from orion.sentiment import classify_issue, detect_sentiment, extract_order_id
    from orion.ticket_manager import TicketManager
except ModuleNotFoundError:
    from business_rules import evaluate_support_rules
    from config import get_google_api_key, get_model_name
    from knowledge_base import KnowledgeBase, get_knowledge_base
    from memory_manager import MemoryManager
    from prompts import GENERAL_PROMPT, ORION_SYSTEM_PROMPT, SUPPORT_PROMPT
    from sentiment import classify_issue, detect_sentiment, extract_order_id
    from ticket_manager import TicketManager


def build_chain(prompt_template):
    api_key = get_google_api_key()
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is missing from .env.")
    llm = ChatGoogleGenerativeAI(
        model=get_model_name(),
        api_key=api_key,
        temperature=0.3,
        max_tokens=400,
        request_timeout=45,
        retries=0,
    )
    return prompt_template | llm, llm, [], None


def _is_non_answer(response_text: str) -> bool:
    cleaned = (response_text or "").strip()
    return not cleaned or cleaned.lower().startswith("user safety:")


def _message_text(message) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            str(block.get("text", ""))
            for block in content
            if isinstance(block, dict) and block.get("text")
        ).strip()
    return ""


def _attempt_diagnostics(attempt: str, message, raw_response, error: str = "") -> dict:
    response_metadata = getattr(message, "response_metadata", {}) or {}
    usage_metadata = getattr(message, "usage_metadata", {}) or {}
    response_text = _message_text(message) if message is not None else ""
    provider_response = raw_response or {
        "content": getattr(message, "content", None),
        "response_metadata": response_metadata,
        "usage_metadata": usage_metadata,
    }
    return {
        "attempt": attempt,
        "raw_response": provider_response,
        "stop_reason": response_metadata.get("finish_reason")
        or response_metadata.get("stop_reason"),
        "model_name": response_metadata.get("model_name")
        or response_metadata.get("model")
        or get_model_name(),
        "token_usage": usage_metadata or response_metadata.get("usage_metadata") or response_metadata.get("token_usage"),
        "provider_metadata": {
            "provider": "Google AI Studio",
            "response_metadata": response_metadata,
        },
        "response_length": len(response_text),
        "error": error,
    }


def is_support_query(user_input: str, issue_category: str) -> bool:
    lower_input = user_input.lower()
    support_keywords = [
        "order", "refund", "return", "cancel", "delivery", "shipping", "damaged", "replacement",
        "payment", "account", "tracking", "invoice", "wrong item", "package", "complaint",
        "human support", "human agent", "service request", "support ticket", "replacement request",
        "lost shipment", "create ticket", "raise ticket", "escalate",
    ]
    return issue_category != "General Inquiry" or any(keyword in lower_input for keyword in support_keywords)


def generate_support_result(
    user_input: str,
    memory: MemoryManager,
    knowledge_base: KnowledgeBase | None = None,
):
    debug_log = ["Input received", "Analyzing sentiment and issue type"]
    sentiment = detect_sentiment(user_input)
    detected_issue = classify_issue(user_input)
    previous_issue = memory.customer_context.get("issue_context", "General Inquiry")
    if detected_issue in {"General Inquiry", "Human Escalation"} and previous_issue.lower() != "general inquiry":
        issue_category = previous_issue
    else:
        issue_category = detected_issue
    debug_log.append(f"Sentiment detected: {sentiment}; category: {issue_category}")
    memory.update_customer_context("issue_context", issue_category)

    order_id = extract_order_id(user_input)
    if order_id:
        memory.update_customer_context("order_id", order_id)
        debug_log.append(f"Order ID captured: {order_id}")

    name_match = re.search(r"\bmy name is\s+([\w'-]+(?:\s+[\w'-]+)?)", user_input, re.IGNORECASE)
    if name_match:
        memory.update_customer_context("customer_name", name_match.group(1).strip())

    support_mode = is_support_query(user_input, issue_category)
    debug_log.append(f"Support mode: {'enabled' if support_mode else 'general'}")

    ticket_manager = TicketManager()
    customer_name = memory.customer_context.get("customer_name", "Customer")
    known_order_id = memory.customer_context.get("order_id", "Not provided")
    if customer_name != "Customer" or known_order_id != "Not provided":
        prior_tickets = ticket_manager.list_recent(
            customer_name=customer_name if customer_name != "Customer" else None,
            order_id=known_order_id if known_order_id != "Not provided" else None,
        )
        known_ticket_ids = {item["ticket_id"] for item in memory.previous_tickets}
        for prior_ticket in reversed(prior_tickets):
            if prior_ticket["ticket_id"] not in known_ticket_ids:
                memory.add_ticket(prior_ticket)
                memory.record_issue(
                    prior_ticket["issue"],
                    "Unknown",
                    prior_ticket["summary"],
                    complaint="complaint" in prior_ticket["summary"].lower(),
                )
    context = memory.get_conversation_context()
    customer_details = str(memory.customer_context)
    rules = evaluate_support_rules(user_input, issue_category, sentiment, memory)
    priority = str(rules["priority"])
    complaint = bool(rules["complaint"])
    memory.record_issue(issue_category, sentiment, user_input, complaint)
    memory.add_user_message(user_input)

    ticket = None
    if rules["ticket_required"]:
        ticket = ticket_manager.create_ticket(
            issue=issue_category,
            priority=priority,
            customer_name=memory.customer_context.get("customer_name", "Customer"),
            order_id=memory.customer_context.get("order_id", "Not provided"),
            summary=user_input[:500],
        )
        memory.add_ticket(ticket)
        if rules["escalation_required"]:
            memory.add_escalation(ticket["ticket_id"], "; ".join(rules["reasons"]))
        debug_log.append(f"Ticket engine created {ticket['ticket_id']} at {ticket['created_at']}")

    try:
        knowledge_base = knowledge_base or get_knowledge_base()
        retrieved_documents = knowledge_base.retrieve(user_input, limit=4)
        knowledge_context = "\n\n".join(
            f"[{document.metadata.get('topic', 'Company Policy')}]\n{document.page_content}"
            for document in retrieved_documents
        )
        retrieved_topics = [str(document.metadata.get("topic", "Company Policy")) for document in retrieved_documents]
        debug_log.append(f"RAG retrieved {len(retrieved_documents)} documents: {', '.join(retrieved_topics)}")
    except Exception as exc:
        knowledge_base = None
        retrieved_documents = []
        retrieved_topics = []
        knowledge_context = "Knowledge retrieval is temporarily unavailable. Follow the deterministic business decision and do not invent company policy."
        debug_log.append(f"Knowledge retrieval failed: {type(exc).__name__}: {exc}")

    ticket_details = (
        "\n".join(
            (
                "Ticket created by ORION application logic.",
                f"Ticket ID: {ticket['ticket_id']}",
                f"Issue Category: {ticket['issue']}",
                f"Priority: {ticket['priority']}",
                f"Status: {ticket['status']}",
                f"Timestamp: {ticket['created_at']}",
            )
        )
        if ticket
        else "No ticket was created for this message."
    )
    business_decision = json.dumps(
        {
            "ticket_required": rules["ticket_required"],
            "escalation_required": rules["escalation_required"],
            "priority": priority,
            "reasons": rules["reasons"],
            "refund_days_reported": rules["refund_days"],
            "repeated_complaint": rules["repeated_complaint"],
        },
        ensure_ascii=False,
    )

    raw_responses = []
    http_client = None
    attempts = []
    last_error = ""
    response_text = ""
    prompt_template = SUPPORT_PROMPT if support_mode else GENERAL_PROMPT
    try:
        chain, llm, raw_responses, http_client = build_chain(prompt_template)
        payload = {
            "customer_query": user_input,
            "conversation_context": context,
            "current_date": date.today().isoformat(),
            "knowledge_context": knowledge_context,
        }
        if support_mode:
            payload.update(
                {
                    "system_prompt": ORION_SYSTEM_PROMPT,
                    "sentiment": sentiment,
                    "issue_category": issue_category,
                    "customer_details": customer_details,
                    "ticket_details": ticket_details,
                    "knowledge_context": knowledge_context,
                    "business_decision": business_decision,
                }
            )
        debug_log.append(f"Requested Gemini model: {get_model_name()}")
        for attempt_name in ("normal_prompt", "simplified_prompt"):
            response_start = len(raw_responses)
            message = None
            try:
                if attempt_name == "normal_prompt":
                    message = chain.invoke(payload)
                else:
                    debug_log.append("Normal prompt returned no usable content; retrying simplified prompt")
                    message = llm.invoke(f"Answer this question directly: {user_input}")
                response_text = _message_text(message)
                raw_response = raw_responses[-1] if len(raw_responses) > response_start else None
                attempt_log = _attempt_diagnostics(attempt_name, message, raw_response)
                attempts.append(attempt_log)
                debug_log.append(
                    f"{attempt_name}: model={attempt_log['model_name']}, "
                    f"stop_reason={attempt_log['stop_reason']}, "
                    f"response_length={attempt_log['response_length']}"
                )
                if not _is_non_answer(response_text):
                    break
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                raw_response = raw_responses[-1] if len(raw_responses) > response_start else None
                attempts.append(
                    _attempt_diagnostics(attempt_name, message, raw_response, last_error)
                )
                debug_log.append(f"{attempt_name} failed: {last_error}")
                break
        if _is_non_answer(response_text):
            last_error = last_error or "Gemini returned no usable content after both prompt attempts."
            response_text = "The AI provider returned an empty response. Please try again."
            debug_log.append(last_error)
        else:
            debug_log.append("Gemini response returned")
    except Exception as exc:
        last_error = f"{type(exc).__name__}: {exc}"
        response_text = "The AI provider returned an empty response. Please try again."
        debug_log.append(f"Gemini request failed: {last_error}")
        attempts.append(_attempt_diagnostics("request", None, raw_responses[-1] if raw_responses else None, last_error))
    finally:
        if http_client is not None:
            http_client.close()

    if ticket:
        response_text += (
            f"\n\n✅ Ticket Created Successfully\n"
            f"Ticket ID: {ticket['ticket_id']}\n"
            f"Issue Category: {ticket['issue']}\n"
            f"Priority: {ticket['priority']}\n"
            f"Status: {ticket['status']}\n"
            f"Timestamp: {ticket['created_at']}"
        )
        debug_log.append("Escalation ticket created")

    memory.add_ai_message(response_text)
    debug_log.append("UI message flow complete")

    latest_attempt = attempts[-1] if attempts else {}
    latest_attempt["attempts"] = attempts
    latest_attempt["requested_model"] = get_model_name()
    latest_attempt["last_error"] = last_error
    latest_attempt["last_successful_response"] = response_text if not last_error else ""
    latest_attempt["response_length"] = len(response_text) if not last_error else 0

    return {
        "response": response_text,
        "error": last_error,
        "response_diagnostics": latest_attempt,
        "sentiment": sentiment,
        "category": issue_category,
        "priority": priority,
        "ticket": ticket,
        "escalated": bool(rules["escalation_required"]),
        "support_mode": support_mode,
        "business_rules": rules,
        "knowledge_diagnostics": {
            "knowledge_base_loaded": knowledge_base is not None,
            "rag_active": bool(retrieved_documents),
            "vector_database_active": bool(knowledge_base and knowledge_base.is_active),
            "ticket_engine_active": ticket_manager.is_active,
            "escalation_engine_active": True,
            "retrieved_topics": retrieved_topics,
            "document_count": knowledge_base.document_count if knowledge_base else 0,
        },
        "debug_log": debug_log,
    }
