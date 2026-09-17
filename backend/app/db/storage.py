import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent.parent.parent.parent / "veridian.db"


class SQLiteStore:
    """
    Central SQLite storage engine providing genuine persistence for:
    - Multi-turn conversation sessions & accumulated factual state
    - Structured ticket records & lifecycle transitions
    - Append-only audit events
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DB_FILE)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for high-concurrency read/write
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        """Create database tables if they do not exist."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    employee_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    history_json TEXT NOT NULL,
                    accumulated_facts_json TEXT NOT NULL,
                    active_policy_id TEXT,
                    pending_missing_fields_json TEXT NOT NULL,
                    is_concluded INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    employee_id TEXT NOT NULL,
                    employee_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    policy_id TEXT,
                    policy_citation TEXT,
                    tags_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    assigned_to TEXT,
                    escalation_reason TEXT,
                    resolution_notes TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    employee_id TEXT,
                    actor TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    action_taken TEXT,
                    policy_id TEXT,
                    policy_citation TEXT,
                    details_json TEXT NOT NULL
                );
                """
            )
            conn.commit()

    # ==================== SESSION PERSISTENCE ====================

    def save_session(self, session_data: Dict[str, Any]) -> None:
        """Persist or update a multi-turn session in SQLite."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (
                    session_id, employee_id, created_at, updated_at,
                    history_json, accumulated_facts_json, active_policy_id,
                    pending_missing_fields_json, is_concluded
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    employee_id=excluded.employee_id,
                    updated_at=excluded.updated_at,
                    history_json=excluded.history_json,
                    accumulated_facts_json=excluded.accumulated_facts_json,
                    active_policy_id=excluded.active_policy_id,
                    pending_missing_fields_json=excluded.pending_missing_fields_json,
                    is_concluded=excluded.is_concluded;
                """,
                (
                    session_data["session_id"],
                    session_data["employee_id"],
                    session_data["created_at"],
                    session_data["updated_at"],
                    json.dumps(session_data.get("history", [])),
                    json.dumps(session_data.get("accumulated_facts", {})),
                    session_data.get("active_policy_id"),
                    json.dumps(session_data.get("pending_missing_fields", [])),
                    1 if session_data.get("is_concluded") else 0,
                ),
            )
            conn.commit()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a session from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "session_id": row["session_id"],
                "employee_id": row["employee_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "history": json.loads(row["history_json"]),
                "accumulated_facts": json.loads(row["accumulated_facts_json"]),
                "active_policy_id": row["active_policy_id"],
                "pending_missing_fields": json.loads(row["pending_missing_fields_json"]),
                "is_concluded": bool(row["is_concluded"]),
            }

    def delete_session(self, session_id: str) -> None:
        """Remove a session from SQLite."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
            conn.commit()

    # ==================== TICKET PERSISTENCE ====================

    def save_ticket(self, ticket_data: Dict[str, Any]) -> None:
        """Persist or update a ticket in SQLite."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tickets (
                    id, employee_id, employee_name, category, title, description,
                    severity, status, policy_id, policy_citation, tags_json,
                    created_at, updated_at, assigned_to, escalation_reason, resolution_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    assigned_to=excluded.assigned_to,
                    escalation_reason=excluded.escalation_reason,
                    resolution_notes=excluded.resolution_notes;
                """,
                (
                    ticket_data["id"],
                    ticket_data["employee_id"],
                    ticket_data["employee_name"],
                    ticket_data["category"],
                    ticket_data["title"],
                    ticket_data["description"],
                    ticket_data["severity"],
                    ticket_data["status"],
                    ticket_data.get("policy_id"),
                    ticket_data.get("policy_citation"),
                    json.dumps(ticket_data.get("tags", [])),
                    ticket_data["created_at"],
                    ticket_data["updated_at"],
                    ticket_data.get("assigned_to"),
                    ticket_data.get("escalation_reason"),
                    ticket_data.get("resolution_notes"),
                ),
            )
            conn.commit()

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "employee_id": row["employee_id"],
                "employee_name": row["employee_name"],
                "category": row["category"],
                "title": row["title"],
                "description": row["description"],
                "severity": row["severity"],
                "status": row["status"],
                "policy_id": row["policy_id"],
                "policy_citation": row["policy_citation"],
                "tags": json.loads(row["tags_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "assigned_to": row["assigned_to"],
                "escalation_reason": row["escalation_reason"],
                "resolution_notes": row["resolution_notes"],
            }

    def list_tickets(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tickets ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "employee_id": r["employee_id"],
                    "employee_name": r["employee_name"],
                    "category": r["category"],
                    "title": r["title"],
                    "description": r["description"],
                    "severity": r["severity"],
                    "status": r["status"],
                    "policy_id": r["policy_id"],
                    "policy_citation": r["policy_citation"],
                    "tags": json.loads(r["tags_json"]),
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "assigned_to": r["assigned_to"],
                    "escalation_reason": r["escalation_reason"],
                    "resolution_notes": r["resolution_notes"],
                }
                for r in rows
            ]

    # ==================== AUDIT EVENT PERSISTENCE ====================

    def append_audit_event(self, event_data: Dict[str, Any]) -> None:
        """Append an immutable audit event record to SQLite."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (
                    id, timestamp, session_id, employee_id, actor,
                    event_type, action_taken, policy_id, policy_citation, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event_data["id"],
                    event_data["timestamp"],
                    event_data.get("session_id"),
                    event_data.get("employee_id"),
                    event_data["actor"],
                    event_data["event_type"],
                    event_data.get("action_taken"),
                    event_data.get("policy_id"),
                    event_data.get("policy_citation"),
                    json.dumps(event_data.get("details", {})),
                ),
            )
            conn.commit()

    def list_audit_events(
        self,
        limit: int = 100,
        offset: int = 0,
        session_id: Optional[str] = None,
        employee_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM audit_events WHERE 1=1"
        params: List[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if employee_id:
            query += " AND employee_id = ?"
            params.append(employee_id)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "session_id": r["session_id"],
                    "employee_id": r["employee_id"],
                    "actor": r["actor"],
                    "event_type": r["event_type"],
                    "action_taken": r["action_taken"],
                    "policy_id": r["policy_id"],
                    "policy_citation": r["policy_citation"],
                    "details": json.loads(r["details_json"]),
                }
                for r in rows
            ]


# Global singleton SQLite store instance
sqlite_store = SQLiteStore()
