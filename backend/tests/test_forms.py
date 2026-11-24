import hashlib
import logging

import pymupdf
import pytest

from app.pdf import forms as engine

FORM = "delhi-income-certificate-application"
AADHAAR = "2345 6789 0124"  # Verhoeff-valid test number
VALUES = {
    "uid": AADHAAR,
    "name": "ASHA VERMA",
    "father": "RAM VERMA",
    "mobile": "9876543210",
    "house": "12",
    "locality": "Example Lane",
    "state": "Delhi",
    "pin": "110001",
    "dob_dd": "07",
    "dob_mm": "03",
    "dob_yyyy": "1999",
}


def _preview(client, values=VALUES):
    r = client.post(f"/forms/{FORM}/preview", json={"values": values})
    assert r.status_code == 200, r.text
    return r.json()


def _pdf(client, values=VALUES):
    h = _preview(client, values)["hash"]
    return client.post(
        f"/forms/{FORM}/pdf", json={"values": values, "confirmed_hash": h, "checked_all_fields": True}
    )


def test_form_is_registered_with_source(client):
    forms = client.get("/forms").json()
    f = next(x for x in forms if x["id"] == FORM)
    assert f["source_url"].startswith("https://revenue.delhi.gov.in/") and f["date_checked"]


def test_recorded_checksum_matches_the_committed_pdf(client):
    spec = client.app.state.forms[FORM]
    assert hashlib.sha256(spec.path.read_bytes()).hexdigest()


def test_preview_cuts_aadhaar_to_last_four(client):
    p = _preview(client)
    assert p["values"]["uid"] == "XXXX XXXX 0124"
    assert "6789" not in str(p) and AADHAAR.replace(" ", "") not in str(p)


@pytest.mark.parametrize(
    ("values", "code"),
    [
        ({"name": "A", "uid": "2345 6789 0125"}, "invalid_aadhaar"),
        ({"name": "आशा"}, "ascii_only"),
        ({"name": "A" * 41}, "too_long"),
        ({"father": "X"}, "missing_required"),
        ({"name": "A", "nope": "1"}, "unknown_fields"),
    ],
)
def test_bad_values_rejected(client, values, code):
    r = client.post(f"/forms/{FORM}/preview", json={"values": values})
    assert r.status_code == 422 and code in r.json()["detail"]


def test_download_needs_tick_and_matching_hash(client):
    h = _preview(client)["hash"]
    body = {"values": VALUES, "confirmed_hash": h}
    assert client.post(f"/forms/{FORM}/pdf", json=body).json()["detail"] == "confirmation_required"
    changed = {**body, "values": {**VALUES, "name": "SOMEONE ELSE"}, "checked_all_fields": True}
    assert client.post(f"/forms/{FORM}/pdf", json=changed).json()["detail"] == "changed_since_review"


def test_filled_pdf_has_values_at_the_right_places(client):
    r = _pdf(client)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    page = pymupdf.open(stream=r.content, filetype="pdf")[0]
    # Name sits on the "Name of Beneficiary" line (y 205-217 in the original).
    name = page.search_for("ASHA VERMA")[0]
    assert 200 < name.y0 < 220 and name.x0 > 200
    father = page.search_for("RAM VERMA")[0]
    assert 218 < father.y0 < 236

    # The Aadhaar number goes one digit per printed box on the UID row; mobile and PIN the same way.
    def row(y0, y1):
        return "".join(
            w[4]
            for w in sorted(page.get_text("words", clip=pymupdf.Rect(260, y0, 540, y1)), key=lambda w: w[0])
        )

    assert row(183, 198) == AADHAAR.replace(" ", "")
    assert page.get_text("words", clip=pymupdf.Rect(140, 317, 325, 331)) and "9876543210" in "".join(
        w[4]
        for w in sorted(page.get_text("words", clip=pymupdf.Rect(140, 317, 325, 331)), key=lambda w: w[0])
    )
    assert "110001" in "".join(
        w[4]
        for w in sorted(page.get_text("words", clip=pymupdf.Rect(158, 405, 250, 419)), key=lambda w: w[0])
    )
    assert len(pymupdf.open(stream=r.content, filetype="pdf")) == 3  # original pages kept


def test_aadhaar_never_in_logs(client, caplog):
    caplog.set_level(logging.DEBUG)
    _pdf(client)
    assert "6789" not in caplog.text and "ASHA" not in caplog.text


def test_original_pdf_is_untouched(client):
    spec = client.app.state.forms[FORM]
    before = spec.path.read_bytes()
    _pdf(client)
    assert spec.path.read_bytes() == before


def test_checksum_mismatch_stops_startup(tmp_path, catalog):
    import json
    import shutil

    src = engine.Path(__file__).resolve().parents[2] / "data" / "forms"
    shutil.copytree(src, tmp_path / "forms")
    (tmp_path / "forms" / "delhi-income-certificate-application.pdf").write_bytes(b"%PDF-1.4 tampered")
    with pytest.raises(Exception):  # noqa: B017 - checksum or unreadable PDF, both must stop startup
        engine.load_forms(tmp_path, catalog.allowlist)
    assert json.loads((tmp_path / "forms" / "forms.json").read_text("utf-8"))["forms"]
