"""Persistence for facts, corrections and usage.

Two implementations behind one small interface: Supabase (service role, always filtered by the
user id from the verified JWT) and an in-memory one for tests and for running without Supabase.
Only confirmed, masked values are stored here. No uploads, no full ID numbers.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx


class Store(Protocol):
    def upsert_fact(self, user_id: str, key: str, value: Any, source: str, confirmed: bool) -> None: ...
    def list_facts(self, user_id: str) -> list[dict[str, Any]]: ...
    def add_correction(self, user_id: str, service_id: str, note: str) -> None: ...
    def delete_user_data(self, user_id: str) -> None: ...


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.facts: dict[tuple[str, str], dict[str, Any]] = {}
        self.corrections: list[dict[str, Any]] = []

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
