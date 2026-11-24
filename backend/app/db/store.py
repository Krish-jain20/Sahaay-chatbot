"""Persistence for facts, corrections and usage.

Two implementations behind one small interface: Supabase (service role, always filtered by the
user id from the verified JWT) and an in-memory one for tests and for running without Supabase.
Only confirmed, masked values are stored here. No uploads, no full ID numbers.
"""

from __future__ import annotations

import copy
import threading
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx


class Store(Protocol):
    def upsert_fact(self, user_id: str, key: str, value: Any, source: str, confirmed: bool) -> None: ...
    def list_facts(self, user_id: str) -> list[dict[str, Any]]: ...
    def add_correction(self, user_id: str, service_id: str, note: str) -> None: ...
    def delete_user_data(self, user_id: str) -> None: ...
    def create_case(self, user_id: str, service_id: str) -> dict[str, Any]: ...
    def list_cases(self, user_id: str) -> list[dict[str, Any]]: ...
    def get_case(self, user_id: str, case_id: str) -> dict[str, Any] | None: ...
    def save_document(
        self, user_id: str, case_id: str, doc_type: str, fields: dict[str, Any], issue_date: str | None
    ) -> dict[str, Any] | None: ...
    def list_documents(self, user_id: str, case_id: str) -> list[dict[str, Any]]: ...
    def add_event(self, user_id: str, case_id: str, step: int, note: str | None) -> bool: ...
    def delete_event(self, user_id: str, case_id: str, step: int) -> bool: ...
    def list_events(self, user_id: str, case_id: str) -> list[dict[str, Any]]: ...
    def save_submission(
        self, user_id: str, case_id: str, reference_masked: str | None, submitted_on: str | None
    ) -> dict[str, Any] | None: ...
    def get_submission(self, user_id: str, case_id: str) -> dict[str, Any] | None: ...
    def update_case_state(self, user_id: str, case_id: str, state: dict[str, Any]) -> bool: ...
    def delete_documents_of_type(self, user_id: str, doc_type: str) -> int: ...
    def delete_case(self, user_id: str, case_id: str) -> bool: ...


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.facts: dict[tuple[str, str], dict[str, Any]] = {}
        self.corrections: list[dict[str, Any]] = []
        self.cases: dict[str, dict[str, Any]] = {}
        self.documents: dict[str, list[dict[str, Any]]] = {}
        self.events: dict[str, list[dict[str, Any]]] = {}
        self.submissions: dict[str, dict[str, Any]] = {}

    def upsert_fact(self, user_id: str, key: str, value: Any, source: str, confirmed: bool) -> None:
        with self._lock:
            self.facts[(user_id, key)] = {
                "key": key,
                "value": value,
                "source": source,
                "confirmed": confirmed,
                "updated_at": datetime.now(UTC).isoformat(),
            }

    def list_facts(self, user_id: str) -> list[dict[str, Any]]:
        return [f for (u, _), f in self.facts.items() if u == user_id]

    def add_correction(self, user_id: str, service_id: str, note: str) -> None:
        self.corrections.append({"user_id": user_id, "service_id": service_id, "note": note})

    def delete_user_data(self, user_id: str) -> None:
        with self._lock:
            self.facts = {k: v for k, v in self.facts.items() if k[0] != user_id}
            self.corrections = [c for c in self.corrections if c["user_id"] != user_id]
            for cid in [c for c, v in self.cases.items() if v["user_id"] == user_id]:
                del self.cases[cid]
                self.documents.pop(cid, None)
                self.events.pop(cid, None)
                self.submissions.pop(cid, None)

    def create_case(self, user_id: str, service_id: str) -> dict[str, Any]:
        with self._lock:
            case = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "service_id": service_id,
                "journey_step": 0,
                "state": {},
                "created_at": datetime.now(UTC).isoformat(),
            }
            self.cases[case["id"]] = case
            return copy.deepcopy(case)

    def list_cases(self, user_id: str) -> list[dict[str, Any]]:
        rows = [copy.deepcopy(c) for c in self.cases.values() if c["user_id"] == user_id]
        return sorted(rows, key=lambda c: c["created_at"], reverse=True)

    def get_case(self, user_id: str, case_id: str) -> dict[str, Any] | None:
        c = self.cases.get(case_id)
        return copy.deepcopy(c) if c and c["user_id"] == user_id else None

    def update_case_state(self, user_id: str, case_id: str, state: dict[str, Any]) -> bool:
        with self._lock:
            c = self.cases.get(case_id)
            if not c or c["user_id"] != user_id:
                return False
            c["state"] = copy.deepcopy(state)
            return True

    def delete_case(self, user_id: str, case_id: str) -> bool:
        with self._lock:
            c = self.cases.get(case_id)
            if not c or c["user_id"] != user_id:
                return False
            del self.cases[case_id]
            self.documents.pop(case_id, None)
            self.events.pop(case_id, None)
            self.submissions.pop(case_id, None)
            return True

    def save_document(
        self, user_id: str, case_id: str, doc_type: str, fields: dict[str, Any], issue_date: str | None
    ) -> dict[str, Any] | None:
        with self._lock:
            if self.get_case(user_id, case_id) is None:
                return None
            docs = self.documents.setdefault(case_id, [])
            docs[:] = [d for d in docs if d["doc_type"] != doc_type]  # one per type; newest wins
            doc = {
                "id": str(uuid.uuid4()),
                "doc_type": doc_type,
                "fields": fields,
                "issue_date": issue_date,
                "confirmed_at": datetime.now(UTC).isoformat(),
            }
            docs.append(doc)
            return dict(doc)

    def list_documents(self, user_id: str, case_id: str) -> list[dict[str, Any]]:
        if self.get_case(user_id, case_id) is None:
            return []
        return [dict(d) for d in self.documents.get(case_id, [])]

    def delete_documents_of_type(self, user_id: str, doc_type: str) -> int:
        """Remove this user's saved document of one type from every case. Returns how many were removed."""
        with self._lock:
            removed = 0
            for cid, c in self.cases.items():
                if c["user_id"] != user_id:
                    continue
                docs = self.documents.get(cid, [])
                keep = [d for d in docs if d["doc_type"] != doc_type]
                removed += len(docs) - len(keep)
                self.documents[cid] = keep
            return removed

    def add_event(self, user_id: str, case_id: str, step: int, note: str | None) -> bool:
        with self._lock:
            if self.get_case(user_id, case_id) is None:
                return False
            evs = self.events.setdefault(case_id, [])
            if not any(e["step"] == step for e in evs):  # recording a step twice keeps the first
                evs.append({"step": step, "note": note, "at": datetime.now(UTC).isoformat()})
            return True

    def delete_event(self, user_id: str, case_id: str, step: int) -> bool:
        with self._lock:
            if self.get_case(user_id, case_id) is None:
                return False
            self.events[case_id] = [e for e in self.events.get(case_id, []) if e["step"] != step]
            return True

    def list_events(self, user_id: str, case_id: str) -> list[dict[str, Any]]:
        if self.get_case(user_id, case_id) is None:
            return []
        return [dict(e) for e in self.events.get(case_id, [])]

    def save_submission(
        self, user_id: str, case_id: str, reference_masked: str | None, submitted_on: str | None
    ) -> dict[str, Any] | None:
        with self._lock:
            if self.get_case(user_id, case_id) is None:
                return None
            cur = self.submissions.get(case_id, {})
            row = {
                "reference_no_masked": reference_masked or cur.get("reference_no_masked"),
                "submitted_on": submitted_on or cur.get("submitted_on"),
            }
            self.submissions[case_id] = row
            return dict(row)

    def get_submission(self, user_id: str, case_id: str) -> dict[str, Any] | None:
        if self.get_case(user_id, case_id) is None:
            return None
        row = self.submissions.get(case_id)
        return dict(row) if row else None


CASE_COLUMNS = "id,user_id,service_id,journey_step,state_json,created_at"


def _case_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in row.items() if k != "state_json"}
    out["state"] = row.get("state_json") or {}
    return out


class SupabaseStore:
    def __init__(self, url: str, secret_key: str, timeout: float = 10.0) -> None:
        self._http = httpx.Client(
            base_url=f"{url.rstrip('/')}/rest/v1",
            headers={"apikey": secret_key, "Authorization": f"Bearer {secret_key}"},
            timeout=timeout,
        )

    def _check(self, r: httpx.Response) -> httpx.Response:
        r.raise_for_status()
        return r

    def upsert_fact(self, user_id: str, key: str, value: Any, source: str, confirmed: bool) -> None:
        self._check(
            self._http.post(
                "/profile_facts",
                params={"on_conflict": "user_id,key"},
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                json={
                    "user_id": user_id,
                    "key": key,
                    "value": value,
                    "source": source,
                    "confirmed": confirmed,
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
        )

    def list_facts(self, user_id: str) -> list[dict[str, Any]]:
        r = self._check(
            self._http.get(
                "/profile_facts",
                params={"user_id": f"eq.{user_id}", "select": "key,value,source,confirmed,updated_at"},
            )
        )
        return r.json()

    def add_correction(self, user_id: str, service_id: str, note: str) -> None:
        self._check(
            self._http.post(
                "/corrections",
                headers={"Prefer": "return=minimal"},
                json={"user_id": user_id, "service_id": service_id, "note": note},
            )
        )

    def delete_user_data(self, user_id: str) -> None:
        for table in ("profile_facts", "corrections", "usage"):
            self._check(self._http.delete(f"/{table}", params={"user_id": f"eq.{user_id}"}))
        # Cases cascade to events, documents and submissions.
        self._check(self._http.delete("/cases", params={"user_id": f"eq.{user_id}"}))

    def create_case(self, user_id: str, service_id: str) -> dict[str, Any]:
        r = self._check(
            self._http.post(
                "/cases",
                headers={"Prefer": "return=representation"},
                json={"user_id": user_id, "service_id": service_id},
            )
        )
        return _case_row(r.json()[0])

    def list_cases(self, user_id: str) -> list[dict[str, Any]]:
        r = self._check(
            self._http.get(
                "/cases",
                params={
                    "user_id": f"eq.{user_id}",
                    "select": CASE_COLUMNS,
                    "order": "created_at.desc",
                },
            )
        )
        return [_case_row(c) for c in r.json()]

    def get_case(self, user_id: str, case_id: str) -> dict[str, Any] | None:
        try:
            uuid.UUID(case_id)
        except ValueError:
            return None
        r = self._check(
            self._http.get(
                "/cases",
                params={
                    "id": f"eq.{case_id}",
                    "user_id": f"eq.{user_id}",
                    "select": CASE_COLUMNS,
                },
            )
        )
        rows = r.json()
        return _case_row(rows[0]) if rows else None

    def update_case_state(self, user_id: str, case_id: str, state: dict[str, Any]) -> bool:
        if self.get_case(user_id, case_id) is None:
            return False
        self._check(
            self._http.patch(
                "/cases",
                params={"id": f"eq.{case_id}", "user_id": f"eq.{user_id}"},
                headers={"Prefer": "return=minimal"},
                json={"state_json": state, "updated_at": datetime.now(UTC).isoformat()},
            )
        )
        return True

    def delete_case(self, user_id: str, case_id: str) -> bool:
        if self.get_case(user_id, case_id) is None:
            return False
        # Events, documents and submissions cascade.
        self._check(self._http.delete("/cases", params={"id": f"eq.{case_id}", "user_id": f"eq.{user_id}"}))
        return True

    def save_document(
        self, user_id: str, case_id: str, doc_type: str, fields: dict[str, Any], issue_date: str | None
    ) -> dict[str, Any] | None:
        if self.get_case(user_id, case_id) is None:
            return None
        # One confirmed document per type per case; the newest replaces the old.
        self._check(
            self._http.delete("/documents", params={"case_id": f"eq.{case_id}", "doc_type": f"eq.{doc_type}"})
        )
        now = datetime.now(UTC).isoformat()
        r = self._check(
            self._http.post(
                "/documents",
                headers={"Prefer": "return=representation"},
                json={
                    "case_id": case_id,
                    "doc_type": doc_type,
                    "fields_masked_json": fields,
                    "issue_date": issue_date,
                    "confirmed_at": now,
                },
            )
        )
        row = r.json()[0]
        return {
            "id": row["id"],
            "doc_type": doc_type,
            "fields": fields,
            "issue_date": issue_date,
            "confirmed_at": now,
        }

    def list_documents(self, user_id: str, case_id: str) -> list[dict[str, Any]]:
        if self.get_case(user_id, case_id) is None:
            return []
        r = self._check(
            self._http.get(
                "/documents",
                params={
                    "case_id": f"eq.{case_id}",
                    "select": "id,doc_type,fields_masked_json,issue_date,confirmed_at",
                },
            )
        )
        return [
            {
                "id": d["id"],
                "doc_type": d["doc_type"],
                "fields": d["fields_masked_json"],
                "issue_date": d["issue_date"],
                "confirmed_at": d["confirmed_at"],
            }
            for d in r.json()
        ]

    def delete_documents_of_type(self, user_id: str, doc_type: str) -> int:
        ids = [c["id"] for c in self.list_cases(user_id)]
        if not ids:
            return 0
        r = self._check(
            self._http.delete(
                "/documents",
                params={"case_id": f"in.({','.join(ids)})", "doc_type": f"eq.{doc_type}"},
                headers={"Prefer": "return=representation"},
            )
        )
        return len(r.json())

    def add_event(self, user_id: str, case_id: str, step: int, note: str | None) -> bool:
        if self.get_case(user_id, case_id) is None:
            return False
        existing = self._check(
            self._http.get(
                "/case_events", params={"case_id": f"eq.{case_id}", "step": f"eq.{step}", "select": "id"}
            )
        ).json()
        if not existing:  # recording a step twice keeps the first
            self._check(
                self._http.post(
                    "/case_events",
                    headers={"Prefer": "return=minimal"},
                    json={"case_id": case_id, "step": step, "note": note},
                )
            )
        return True

    def delete_event(self, user_id: str, case_id: str, step: int) -> bool:
        if self.get_case(user_id, case_id) is None:
            return False
        self._check(
            self._http.delete("/case_events", params={"case_id": f"eq.{case_id}", "step": f"eq.{step}"})
        )
        return True

    def list_events(self, user_id: str, case_id: str) -> list[dict[str, Any]]:
        if self.get_case(user_id, case_id) is None:
            return []
        r = self._check(
            self._http.get("/case_events", params={"case_id": f"eq.{case_id}", "select": "step,note,at"})
        )
        return r.json()

    def get_submission(self, user_id: str, case_id: str) -> dict[str, Any] | None:
        if self.get_case(user_id, case_id) is None:
            return None
        r = self._check(
            self._http.get(
                "/submissions",
                params={
                    "case_id": f"eq.{case_id}",
                    "select": "reference_no_masked,submitted_on",
                    "limit": "1",
                },
            )
        )
        rows = r.json()
        return rows[0] if rows else None

    def save_submission(
        self, user_id: str, case_id: str, reference_masked: str | None, submitted_on: str | None
    ) -> dict[str, Any] | None:
        cur = self.get_submission(user_id, case_id)
        if self.get_case(user_id, case_id) is None:
            return None
        row = {
            "reference_no_masked": reference_masked or (cur or {}).get("reference_no_masked"),
            "submitted_on": submitted_on or (cur or {}).get("submitted_on"),
        }
        self._check(self._http.delete("/submissions", params={"case_id": f"eq.{case_id}"}))
        self._check(
            self._http.post(
                "/submissions", headers={"Prefer": "return=minimal"}, json={"case_id": case_id, **row}
            )
        )
        return row
