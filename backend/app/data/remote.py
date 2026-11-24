"""Service cards in Supabase, with the repo files as the fallback.

Rows live in `public.services` (supabase/migrations/0003_services.sql): one row per service, the whole
record as JSON in `data`. The backend reads them with the secret key. If the database is not set up,
unreachable, empty, or its rows do not validate, the repo files are used, so nothing breaks.
Only row contents are read; no user data is touched here and keys are never logged.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from app.data.loader import Catalog, DataError, build_catalog, load_allowlist, load_catalog

log = logging.getLogger("sahaay.catalog")

Rows = list[dict[str, Any]]


def fetch_rows(url: str, secret_key: str, timeout: float = 8.0) -> Rows:
    r = httpx.get(
        f"{url.rstrip('/')}/rest/v1/services",
        params={"select": "id,kind,data", "enabled": "eq.true", "order": "id"},
        headers={"apikey": secret_key, "Authorization": f"Bearer {secret_key}"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def catalog_from_rows(rows: Rows, data_dir: Path) -> Catalog:
    """Build a catalog from database rows. Raises DataError if anything in them is not valid."""
    records = [(r["id"], r["data"]) for r in rows if r.get("kind") == "record"]
    infos = [(r["id"], r["data"]) for r in rows if r.get("kind") == "directory"]
    if not records:
        raise DataError("database has no verified service records")
    try:
        return build_catalog(load_allowlist(data_dir), records, infos)
    except DataError:
        raise
    except Exception as e:  # pydantic validation, missing keys, bad JSON types
        raise DataError(f"database rows do not validate: {type(e).__name__}") from e


class CatalogSource:
    """Holds the catalog the API serves and refreshes it from the database every so often."""

    def __init__(
        self,
        data_dir: Path,
        url: str = "",
        secret_key: str = "",
        fetch: Callable[[str, str], Rows] = fetch_rows,
    ) -> None:
        self.data_dir = data_dir
        self.url, self.secret_key, self.fetch = url, secret_key, fetch
        self.files = load_catalog(data_dir)
        self.catalog = self.files
        self.origin = "files"

    @property
    def uses_database(self) -> bool:
        return bool(self.url and self.secret_key)

    def refresh(self) -> str:
        """Re-read the database. Returns where the catalog now comes from: 'database' or 'files'."""
        if not self.uses_database:
            return self.origin
        try:
            rows = self.fetch(self.url, self.secret_key)
            if not rows:
                raise DataError("database has no service rows yet")
            self.catalog, self.origin = catalog_from_rows(rows, self.data_dir), "database"
        except Exception as e:  # network, auth, missing table, bad rows: all mean "use the files"
            log.warning("service database not used, falling back to repo files: %s", _why(e))
            self.catalog, self.origin = self.files, "files"
        return self.origin


def _why(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        return f"HTTP {e.response.status_code}"
    return f"{type(e).__name__}: {e}" if isinstance(e, DataError) else type(e).__name__


async def keep_fresh(app: Any, source: CatalogSource, every_seconds: int) -> None:
    """Background task: pick up edits made in Supabase without a restart."""
    while True:
        await asyncio.sleep(every_seconds)
        with contextlib.suppress(Exception):
            await asyncio.to_thread(source.refresh)
            app.state.catalog = source.catalog
