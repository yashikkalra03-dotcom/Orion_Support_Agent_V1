from __future__ import annotations

import re

POSITIVE_WORDS = {
    "happy", "satisfied", "thankful", "great", "good", "excellent", "resolved", "pleasant"
}
NEGATIVE_WORDS = {
    "angry", "frustrated", "terrible", "awful", "bad", "unacceptable", "complaint", "disappointed"
}
FRUSTRATED_PATTERNS = {
    "third time",
    "again",
    "still",
    "not working",
    "delayed again",
    "this is ridiculous",
    "very frustrated",
    "the third time",
}


def detect_sentiment(text: str) -> str:
    cleaned = text.lower()
    if any(pattern in cleaned for pattern in FRUSTRATED_PATTERNS):
        return "Frustrated"
    if any(word in cleaned for word in ["urgent", "immediately", "critical", "worst", "hate", "angry"]):
        return "Frustrated"
    negative_count = sum(1 for word in NEGATIVE_WORDS if word in cleaned)
    positive_count = sum(1 for word in POSITIVE_WORDS if word in cleaned)
    if negative_count > positive_count:
        return "Negative"
    if positive_count > negative_count:
        return "Positive"
    return "Neutral"


def classify_issue(text: str) -> str:
    cleaned = text.lower()
    if any(term in cleaned for term in ["refund", "money back", "refund status", "refund not received"]):
        return "Refund"
    if any(term in cleaned for term in ["wrong product", "wrong item", "incorrect product", "different product"]):
        return "Wrong Product"
    if any(term in cleaned for term in ["damaged", "broke", "broken", "damage"]):
        return "Damaged Product"
    if any(term in cleaned for term in ["track", "tracking", "order status", "where is my order"]):
        return "Order Tracking"
    if any(term in cleaned for term in ["cancel", "cancellation"]):
        return "Cancellation"
    if any(term in cleaned for term in ["return", "returned", "return request"]):
        return "Returns"
    if any(term in cleaned for term in ["replacement", "replace"]):
        return "Replacement"
    if any(term in cleaned for term in ["shipping", "delivery", "delay", "late", "arrived late", "missing shipment", "shipment is missing", "package is missing", "lost shipment", "package lost"]):
        return "Delivery"
    if any(term in cleaned for term in ["payment", "charged", "billing", "invoice", "card"]):
        return "Payment"
    if any(term in cleaned for term in ["account", "login", "password", "profile", "issue with account"]):
        return "Account"
    if any(term in cleaned for term in ["complaint", "file a complaint", "register a complaint"]):
        return "Complaint"
    if any(term in cleaned for term in ["human support", "human agent", "talk to a human", "speak to a human", "representative"]):
        return "Human Escalation"
    return "General Inquiry"


def determine_priority(issue: str, sentiment: str) -> str:
    if issue in {"Refund", "Account", "Complaint", "Damaged Product"} or sentiment == "Frustrated":
        return "High"
    if issue in {"Delivery", "Replacement", "Wrong Product", "Returns", "Cancellation", "Payment"}:
        return "Medium"
    return "Low"


def extract_order_id(text: str) -> str | None:
    match = re.search(r"\b(?:ORD|order|ORDER)[-_ ]?[A-Z0-9]{4,}\b", text, re.IGNORECASE)
    if match:
        return match.group(0).upper().replace(" ", "")
    match = re.search(r"\b[A-Z]{2,}[0-9]{4,}\b", text)
    if match:
        return match.group(0).upper()
    return None
