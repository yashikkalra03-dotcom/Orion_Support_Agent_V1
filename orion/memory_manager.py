from __future__ import annotations

from typing import Any, Dict, List


class MemoryManager:
    def __init__(self):
        self.history: List[Dict[str, str]] = []
        self.customer_context: Dict[str, str] = {
            "customer_name": "Customer",
            "order_id": "Not provided",
            "issue_context": "General inquiry",
        }
        self.issue_history: List[Dict[str, Any]] = []
        self.previous_tickets: List[Dict[str, str]] = []
        self.escalation_history: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})

    def add_user_message(self, content: str) -> None:
        self.add_message("user", content)

    def add_ai_message(self, content: str) -> None:
        self.add_message("assistant", content)

    def update_customer_context(self, key: str, value: str) -> None:
        if value and value.strip():
            self.customer_context[key] = value

    def record_issue(self, issue: str, sentiment: str, message: str, complaint: bool = False) -> None:
        self.issue_history.append(
            {
                "issue": issue,
                "sentiment": sentiment,
                "message": message,
                "complaint": complaint,
            }
        )

    def count_complaints(self, issue: str | None = None) -> int:
        return sum(
            1
            for item in self.issue_history
            if item["complaint"] and (issue in {None, "Complaint"} or item["issue"] == issue)
        )

    def add_ticket(self, ticket: Dict[str, str]) -> None:
        self.previous_tickets.append(ticket.copy())

    def add_escalation(self, ticket_id: str, reason: str) -> None:
        self.escalation_history.append({"ticket_id": ticket_id, "reason": reason})

    def get_conversation_context(self) -> str:
        context_lines = []
        context_lines.append(f"Known customer details: {self.customer_context}")
        if self.previous_tickets:
            context_lines.append(f"Previous ORION tickets: {self.previous_tickets[-3:]}")
        if self.escalation_history:
            context_lines.append(f"Previous escalations: {self.escalation_history[-3:]}")
        if self.issue_history:
            context_lines.append(f"Prior issues/complaints: {self.issue_history[-3:]}")
        for item in self.history[-6:]:
            content = item["content"].strip()
            if len(content) > 1000:
                content = content[:997] + "..."
            context_lines.append(f"{item['role'].title()}: {content}")
        return "\n".join(context_lines) if context_lines else "No prior conversation."

    def summarize(self) -> str:
        summary_parts = [
            f"Customer: {self.customer_context.get('customer_name', 'Customer')}",
            f"Order ID: {self.customer_context.get('order_id', 'Not provided')}",
            f"Issue: {self.customer_context.get('issue_context', 'General inquiry')}",
            f"Recent messages: {len(self.history)}",
            f"Tickets: {len(self.previous_tickets)}",
            f"Complaints: {self.count_complaints()}",
        ]
        return " | ".join(summary_parts)

    def clear(self) -> None:
        self.history.clear()
        self.customer_context = {
            "customer_name": "Customer",
            "order_id": "Not provided",
            "issue_context": "General inquiry",
        }
        self.issue_history.clear()
        self.previous_tickets.clear()
        self.escalation_history.clear()
