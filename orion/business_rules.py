from __future__ import annotations

import re

try:
    from orion.memory_manager import MemoryManager
except ModuleNotFoundError:
    from memory_manager import MemoryManager


EXPLICIT_TICKET_TRIGGERS = (
    "create ticket",
    "create a ticket",
    "raise ticket",
    "raise a ticket",
    "service request",
    "escalate issue",
    "escalate this",
    "register a service request",
)

HUMAN_ESCALATION_TRIGGERS = (
    "human support",
    "human agent",
    "talk to a human",
    "speak to a human",
    "representative",
    "escalate issue",
    "escalate this",
    "escalate my issue",
)

AUTOMATIC_TICKET_TRIGGERS = (
    "complaint",
    "refund not received",
    "refund has not arrived",
    "refund delayed",
    "wrong product",
    "wrong item",
    "damaged product",
    "item is damaged",
    "replacement request",
    "need a replacement",
    "request a replacement",
)

def evaluate_support_rules(
    user_input: str,
    issue_category: str,
    sentiment: str,
    memory: MemoryManager,
) -> dict[str, object]:
    text = user_input.lower()
    refund_days_match = re.search(r"\b(\d{1,3})\s*(?:calendar\s*)?days?\b", text)
    refund_days = int(refund_days_match.group(1)) if refund_days_match and "refund" in text else 0
    refund_delayed = issue_category == "Refund" and any(
        phrase in text for phrase in ("delayed", "delay", "not received", "not arrived", "hasn't arrived", "has not arrived", "missing")
    )
    shipment_missing = any(
        phrase in text
        for phrase in ("missing shipment", "shipment is missing", "package is missing", "lost shipment", "package lost", "never arrived", "not delivered")
    )
    complaint = issue_category == "Complaint" or "complaint" in text or "unacceptable" in text
    prior_complaints = memory.count_complaints(issue_category)
    repeat_language = any(phrase in text for phrase in ("again", "still unresolved", "same issue", "third time", "repeated"))
    repeated_complaint = prior_complaints > 0 and (complaint or repeat_language)
    safety_risk = any(phrase in text for phrase in ("unsafe", "injured", "fire", "smoke", "electric shock", "allergic reaction"))
    critical_issue = safety_risk or any(term in text for term in ("critical", "immediate danger", "fraud", "account compromised"))
    human_requested = any(phrase in text for phrase in HUMAN_ESCALATION_TRIGGERS)
    explicit_ticket_request = any(phrase in text for phrase in EXPLICIT_TICKET_TRIGGERS)
    automatic_ticket_trigger = any(phrase in text for phrase in AUTOMATIC_TICKET_TRIGGERS)

    if repeated_complaint or critical_issue:
        priority = "Critical"
    elif (
        refund_delayed
        or refund_days >= 14
        or shipment_missing
        or complaint
        or human_requested
        or sentiment == "Frustrated"
        or issue_category == "Damaged Product"
        or (issue_category == "Refund" and explicit_ticket_request)
    ):
        priority = "High"
    elif issue_category in {"Wrong Product", "Replacement", "Delivery", "Returns", "Payment"}:
        priority = "Medium"
    else:
        priority = "Low"

    ticket_required = (
        explicit_ticket_request
        or automatic_ticket_trigger
        or refund_delayed
        or issue_category in {"Complaint", "Damaged Product"}
        or human_requested
        or repeated_complaint
        or critical_issue
        or shipment_missing
        or (issue_category == "Replacement" and any(term in text for term in ("wrong product", "wrong item", "replacement")))
    )
    escalation_required = (
        human_requested
        or refund_delayed
        or refund_days >= 14
        or complaint
        or repeated_complaint
        or critical_issue
        or shipment_missing
        or issue_category in {"Damaged Product", "Wrong Product"}
        or any(term in text for term in ("lost shipment", "package lost", "urgent"))
    )
    if repeated_complaint or critical_issue:
        priority = "Critical"

    reasons = []
    if explicit_ticket_request:
        reasons.append("customer requested a ticket/service request")
    elif automatic_ticket_trigger:
        reasons.append("support policy automatically requires a ticket")
    if refund_days >= 14:
        reasons.append(f"refund delayed {refund_days} days (14-day escalation threshold)")
    elif refund_delayed:
        reasons.append("refund reported missing or delayed")
    if human_requested:
        reasons.append("customer requested human support/escalation")
    if complaint:
        reasons.append("customer registered a complaint")
    if repeated_complaint:
        reasons.append("repeated complaint")
    if critical_issue:
        reasons.append("critical safety, security, or urgency risk")
    if shipment_missing:
        reasons.append("missing or lost shipment requires carrier/retailer review")
    if issue_category in {"Wrong Product", "Damaged Product"}:
        reasons.append(f"{issue_category.lower()} workflow")

    return {
        "ticket_required": ticket_required,
        "escalation_required": escalation_required,
        "priority": priority,
        "refund_days": refund_days,
        "complaint": complaint,
        "repeated_complaint": repeated_complaint,
        "human_requested": human_requested,
        "safety_risk": safety_risk,
        "reasons": reasons,
    }