"""Load the service files into Supabase `public.services`.

    cd backend && uv run python -m app.data.seed            # dry run: shows what would change
    cd backend && uv run python -m app.data.seed --apply    # insert rows that are missing
    cd backend && uv run python -m app.data.seed --apply --overwrite   # also replace rows that differ

It validates the files first, prints the project host (never a key), and never deletes rows. By default a
row that already exists and differs is kept, so edits made in Supabase are not lost.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import get_settings
from app.data.loader import build_catalog, load_allowlist, read_files


def plan(
    files: list[dict[str, Any]], existing: dict[str, dict[str, Any]], overwrite: bool
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"insert": [], "same": [], "differs_kept": [], "replace": []}
    for row in files:
        have = existing.get(row["id"])
        if have is None:
            out["insert"].append(row["id"])
        elif have["data"] == row["data"]:
            out["same"].append(row["id"])
        else:
            out["replace" if overwrite else "differs_kept"].append(row["id"])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write to the database (default is a dry run)")
    ap.add_argument("--overwrite", action="store_true", help="replace rows that already exist and differ")
    args = ap.parse_args(argv)

    s = get_settings()
    if not (s.supabase_url and s.supabase_secret_key):
        print("SUPABASE_URL and SUPABASE_SECRET_KEY must be set in .env")
        return 2
    records, infos = read_files(s.data_dir)
    build_catalog(load_allowlist(s.data_dir), records, infos)  # raises if any file is invalid
    rows = [{"id": n, "kind": "record", "data": d} for n, d in records]
    rows += [{"id": n, "kind": "directory", "data": d} for n, d in infos]

    host = urlparse(s.supabase_url).hostname
    print(f"Target: {host}  ({len(records)} records + {len(infos)} directory services from files)")
    http = httpx.Client(
        base_url=f"{s.supabase_url}/rest/v1",
        headers={"apikey": s.supabase_secret_key, "Authorization": f"Bearer {s.supabase_secret_key}"},
        timeout=20,
    )
    r = http.get("/services", params={"select": "id,data"})
    if r.status_code == 404:
        print("The services table is missing. Run supabase/migrations/0003_services.sql first.")
        return 3
    r.raise_for_status()
    existing = {row["id"]: row for row in r.json()}
    p = plan(rows, existing, args.overwrite)
    for k, ids in p.items():
        print(f"  {k:13} {len(ids)}" + (f"  {', '.join(ids)}" if ids and k != "same" else ""))
    todo = set(p["insert"]) | set(p["replace"])
    if not args.apply:
        print("Dry run. Nothing written. Add --apply to write.")
        return 0
    batch = [row for row in rows if row["id"] in todo]
    if batch:
        http.post(
            "/services",
            params={"on_conflict": "id"},
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            json=batch,
        ).raise_for_status()
    print(f"Wrote {len(batch)} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
