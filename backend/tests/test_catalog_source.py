import copy
import json

import httpx
import pytest

from app.config import get_settings
from app.data.loader import DataError, read_files
from app.data.remote import CatalogSource, catalog_from_rows
from app.data.seed import plan


def _rows():
    records, infos = read_files(get_settings().data_dir)
    return [{"id": n, "kind": "record", "data": d} for n, d in records] + [
        {"id": n, "kind": "directory", "data": d} for n, d in infos
    ]


def _source(fetch, url="https://example.supabase.co", key="k"):
    return CatalogSource(get_settings().data_dir, url, key, fetch)


def test_without_supabase_the_files_are_used_and_nothing_is_fetched():
    def boom(*_):
        raise AssertionError("must not be called")

    src = _source(boom, url="", key="")
    assert src.refresh() == "files" and len(src.catalog.services) == 3 and len(src.catalog.directory) == 13


def test_database_rows_replace_the_files_and_edits_show_up_on_refresh():
    rows = _rows()
    src = _source(lambda *_: rows)
    assert src.refresh() == "database"
    edited = copy.deepcopy(rows)
    card = next(r for r in edited if r["id"] == "delhi-domicile-certificate")
    card["data"]["time"]["text"]["en"] = "10 days."
    src.fetch = lambda *_: edited
    assert src.refresh() == "database"
    assert src.catalog.directory["delhi-domicile-certificate"].time.text.en == "10 days."


@pytest.mark.parametrize(
    "fetch",
    [
        lambda *_: [],  # table exists but is empty
        lambda *_: (_ for _ in ()).throw(httpx.ConnectError("down")),  # unreachable
        lambda *_: (_ for _ in ()).throw(  # table missing or key refused
            httpx.HTTPStatusError(
                "x", request=httpx.Request("GET", "https://x"), response=httpx.Response(404)
            )
        ),
    ],
    ids=["empty", "unreachable", "http-error"],
)
def test_falls_back_to_the_repo_files(fetch):
    src = _source(fetch)
    assert src.refresh() == "files" and len(src.catalog.services) == 3 and len(src.catalog.directory) == 13


def test_a_bad_row_sends_the_whole_catalog_back_to_the_files():
    rows = _rows()
    bad = next(r for r in rows if r["id"] == "delhi-ration-card")
    bad["data"]["sources"][0]["url"] = "https://not-allowlisted.example.gov.in/x"
    src = _source(lambda *_: rows)
    assert src.refresh() == "files"
    assert "delhi-ration-card" in src.catalog.directory


def test_database_without_verified_records_is_rejected():
    rows = [r for r in _rows() if r["kind"] == "directory"]
    with pytest.raises(DataError, match="no verified"):
        catalog_from_rows(rows, get_settings().data_dir)


def test_a_database_failure_after_a_good_load_goes_back_to_files_not_stale_rows():
    rows = _rows()
    src = _source(lambda *_: rows)
    assert src.refresh() == "database"
    src.fetch = lambda *_: (_ for _ in ()).throw(httpx.ReadTimeout("slow"))
    assert src.refresh() == "files"


def test_health_reports_where_services_come_from(client):
    assert client.get("/health").json()["services"] == "files"


def test_cards_endpoint_serves_the_database_catalog(client):
    rows = _rows()
    next(r for r in rows if r["id"] == "delhi-voter-id")["data"]["summary"]["en"] = "Edited in the database."
    src = _source(lambda *_: rows)
    src.refresh()
    client.app.state.catalog = src.catalog
    card = next(c for c in client.get("/cards").json() if c["id"] == "delhi-voter-id")
    assert card["summary"] == "Edited in the database."


def test_seed_plan_never_overwrites_edits_unless_asked():
    files = _rows()[:3]
    existing = {files[0]["id"]: files[0], files[1]["id"]: {**files[1], "data": {**files[1]["data"], "x": 1}}}
    p = plan(files, existing, overwrite=False)
    assert (p["insert"], p["same"], p["differs_kept"], p["replace"]) == (
        [files[2]["id"]],
        [files[0]["id"]],
        [files[1]["id"]],
        [],
    )
    assert plan(files, existing, overwrite=True)["replace"] == [files[1]["id"]]


def test_migration_gives_the_public_read_only_and_the_service_role_write():
    sql = (get_settings().data_dir.parent / "supabase/migrations/0003_services.sql").read_text("utf-8")
    assert "enable row level security" in sql
    assert "for select to anon, authenticated" in sql
    assert "grant all on public.services to service_role" in sql
    assert "revoke insert, update, delete on public.services from anon, authenticated" in sql
    assert not any(w in sql.lower() for w in ("drop table", "delete from", "truncate"))
    assert json.dumps(sql)  # file is readable text
