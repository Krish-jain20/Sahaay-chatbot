import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import get_settings
from app.data.loader import DataError, load_catalog, validate_info
from app.data.models import InfoService


def test_cards_list_records_first_then_the_sourced_directory(client):
    cards = client.get("/cards", params={"lang": "en"}).json()
    kinds = [c["kind"] for c in cards]
    assert kinds[:3] == ["record"] * 3 and set(kinds[3:]) == {"directory"} and len(cards) >= 15
    assert len({c["id"] for c in cards}) == len(cards)


def test_every_card_line_points_at_a_citation_with_a_check_date(client):
    for lang in ("en", "hi", "hn"):
        for c in client.get("/cards", params={"lang": lang}).json():
            numbers = {x["n"] for x in c["citations"]}
            assert c["citations"] and all(
                x["date_checked"] and x["url"].startswith("https://") for x in c["citations"]
            )
            lines = [*c["who"], *c["not_if"], *c["documents"], *c["steps"]]
            lines += [x for x in (c["benefit"], c["fee"], c["time"]) if x]
            assert lines and all(x["source_n"] in numbers and x["text"] for x in lines), c["id"]


def test_no_placeholder_or_empty_text_reaches_a_card(client):
    text = json.dumps(client.get("/cards").json(), ensure_ascii=False)
    assert not re.search(r"₹\[|\[fee\]|TODO|None", text)


def test_income_certificate_card_is_filled_in(client):
    card = next(c for c in client.get("/cards").json() if c["id"] == "delhi-income-certificate")
    assert "14 days" in card["benefit"]["text"] and card["fee"]["text"].startswith("No fee")
    assert card["time"]["text"] == "14 days."


def test_directory_amounts_match_the_official_page_text(client):
    cards = {c["id"]: c for c in client.get("/cards").json()}
    assert "₹2,500 a month" in cards["delhi-disability-pension"]["benefit"]["text"]
    assert "₹20,000" in cards["delhi-family-benefit-scheme"]["benefit"]["text"]
    assert "₹400" in cards["delhi-permanent-driving-licence"]["fee"]["text"]
    assert cards["delhi-domicile-certificate"]["fee"]["text"] == "No fee."


def _info(**over):
    path = get_settings().data_dir / "directory" / "delhi-domicile-certificate.json"
    return InfoService.model_validate({**json.loads(path.read_text("utf-8")), **over})


def test_directory_rejects_unknown_source_ref_and_unlisted_host():
    catalog = load_catalog(get_settings().data_dir)
    good = _info()
    validate_info(good, good.id, catalog.allowlist)
    bad_ref = good.model_copy(update={"fee": good.fee.model_copy(update={"source_ref": "nope"})})
    with pytest.raises(DataError, match="source_ref"):
        validate_info(bad_ref, good.id, catalog.allowlist)
    with pytest.raises(DataError, match="allowlist"):
        validate_info(
            good.model_copy(update={"apply_url": "https://evil.gov.in/"}), good.id, catalog.allowlist
        )


def test_directory_record_needs_a_check_date():
    data = json.loads(
        (Path(get_settings().data_dir) / "directory" / "delhi-domicile-certificate.json").read_text("utf-8")
    )
    data["sources"][0]["date_checked"] = None
    catalog = load_catalog(get_settings().data_dir)
    with pytest.raises(DataError, match="date_checked"):
        validate_info(InfoService.model_validate(data), data["id"], catalog.allowlist)


def test_directory_schema_is_strict():
    with pytest.raises(ValidationError):
        _info(surprise="x")
