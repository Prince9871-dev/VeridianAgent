import json
import os
from typing import Dict, List, Optional
from backend.app.policy.schema import AuthoritativePolicyRecord, PrecedentRecord

POLICIES_JSON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "derived", "authoritative_policies.json"
)
PRECEDENTS_JSON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "derived", "ticket_queue_precedents.json"
)


class PolicyCatalog:
    """In-memory indexer for derived authoritative policies and historical precedents."""

    def __init__(self):
        self._policies: Dict[str, AuthoritativePolicyRecord] = {}
        self._precedents: Dict[str, PrecedentRecord] = {}
        self._load_data()

    def _load_data(self) -> None:
        if os.path.exists(POLICIES_JSON_PATH):
            with open(POLICIES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("policies", []):
                    record = AuthoritativePolicyRecord(**item)
                    self._policies[record.id] = record

        if os.path.exists(PRECEDENTS_JSON_PATH):
            with open(PRECEDENTS_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("precedents", []):
                    record = PrecedentRecord(**item)
                    self._precedents[record.ticket_id] = record

    def get_policy(self, policy_id: str) -> Optional[AuthoritativePolicyRecord]:
        return self._policies.get(policy_id)

    def list_policies(self) -> List[AuthoritativePolicyRecord]:
        return list(self._policies.values())

    def get_precedent(self, ticket_id: str) -> Optional[PrecedentRecord]:
        return self._precedents.get(ticket_id)

    def list_precedents(self) -> List[PrecedentRecord]:
        return list(self._precedents.values())


# Global singleton instance
policy_catalog = PolicyCatalog()
