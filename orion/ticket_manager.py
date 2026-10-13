from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TICKET_DB = Path(__file__).resolve().parent.parent / ".orion_data" / "tickets.sqlite3"


class TicketManager:
    def __init__(self, db_path: Path | str = DEFAULT_TICKET_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT UNIQUE,
                    issue TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assigned_team TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    summary TEXT NOT NULL
                )
                """
            )

    @property
    def is_active(self) -> bool:
        return self.db_path.exists()

    def create_ticket(
        self,
        issue: str,
        priority: str,
        status: str = "Open",
        assigned_team: str = "Customer Resolution Team",
        customer_name: str = "Customer",
        order_id: str = "Not provided",
        summary: str = "",
    ) -> dict[str, str]:
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO tickets (
                    ticket_id, issue, priority, status, assigned_team, created_at,
                    customer_name, order_id, summary
                ) VALUES ('', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (issue, priority, status, assigned_team, created_at, customer_name, order_id, summary),
            )
            ticket_id = f"TKT-{datetime.now(timezone.utc).year}-{cursor.lastrowid:06d}"
            connection.execute(
                "UPDATE tickets SET ticket_id = ? WHERE sequence = ?",
                (ticket_id, cursor.lastrowid),
            )
        return {
            "ticket_id": ticket_id,
            "issue": issue,
            "priority": priority,
            "status": status,
            "assigned_team": assigned_team,
            "created_at": created_at,
            "customer_name": customer_name,
            "order_id": order_id,
            "summary": summary,
        }

    def list_recent(
        self,
        customer_name: str | None = None,
        order_id: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, str]]:
        clauses = []
        parameters: list[str | int] = []
        if customer_name:
            clauses.append("customer_name = ?")
            parameters.append(customer_name)
        if order_id and order_id != "Not provided":
            clauses.append("order_id = ?")
            parameters.append(order_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(limit)
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                f"SELECT ticket_id, issue, priority, status, assigned_team, created_at, customer_name, order_id, summary FROM tickets {where} ORDER BY sequence DESC LIMIT ?",
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]
