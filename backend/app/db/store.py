"""Persistence for facts, corrections and usage.

Two implementations behind one small interface: Supabase (service role, always filtered by the
user id from the verified JWT) and an in-memory one for tests and for running without Supabase.
Only confirmed, masked values are stored here. No uploads, no full ID numbers.
"""

from __future__ import annotations

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


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.facts: dict[tuple[str, str], dict[str, Any]] = {}
        self.corrections: list[dict[str, Any]] = []
        self.cases: dict[str, dict[str, Any]] = {}
        self.documents: dict[str, list[dict[str, Any]]] = {}

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

    def create_case(self, user_id: str, service_id: str) -> dict[str, Any]:
        with self._lock:
            case = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "service_id": service_id,
                "journey_step": 0,
                "created_at": datetime.now(UTC).isoformat(),
            }
            self.cases[case["id"]] = case
            return dict(case)

    def list_cases(self, user_id: str) -> list[dict[str, Any]]:
        return [dict(c) for c in self.cases.values() if c["user_id"] == user_id]

    def get_case(self, user_id: str, case_id: str) -> dict[str, Any] | None:
        c = self.cases.get(case_id)
        return dict(c) if c and c["user_id"] == user_id else None

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
        return r.json()[0]

    def list_cases(self, user_id: str) -> list[dict[str, Any]]:
        r = self._check(
            self._http.get(
                "/cases",
                params={
                    "user_id": f"eq.{user_id}",
                    "select": "id,user_id,service_id,journey_step,created_at",
                    "order": "created_at.desc",
                },
            )
        )
        return r.json()

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
                    "select": "id,user_id,service_id,journey_step,created_at",
                },
            )
        )
        rows = r.json()
        return rows[0] if rows else None

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
