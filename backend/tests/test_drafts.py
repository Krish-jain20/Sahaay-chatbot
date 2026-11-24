import pymupdf
import pytest

from app.pdf import drafts


def _pdf_works() -> bool:
    try:
        drafts.render_pdf(
            "cpgrams", "en", {"full_name": "A", "department": "d", "grievance": "g", "requested_action": "a"}
        )
        return True
    except Exception:  # noqa: BLE001 - WeasyPrint needs system libraries (Pango); skip where absent
        return False


PDF_OK = _pdf_works()
needs_pdf = pytest.mark.skipif(not PDF_OK, reason="WeasyPrint system libraries not available")

RTI = {
    "kind": "rti",
    "fields": {
        "full_name": "Asha Verma",
        "address": "12 Example Lane, Delhi",
        "authority": "PIO, Revenue Department",
        "info_sought": "Status of my application, Aadhaar 2345 6789 0124",
    },
}


def _confirm(client, body):
    p = client.post("/drafts/preview", json=body)
    assert p.status_code == 200, p.text
    return p.json()


def test_preview_masks_identity_numbers(client):
    p = _confirm(client, RTI)
    text = str(p["rows"])
    assert "2345 6789 0124" not in text and "0124" in text
    assert p["confirmed"] is False


def test_missing_required_rejected(client):
    r = client.post("/drafts/preview", json={"kind": "rti", "fields": {"full_name": "A"}})
    assert r.status_code == 422 and "authority" in r.json()["detail"]


def test_unknown_field_rejected(client):
    assert (
        client.post("/drafts/preview", json={**RTI, "fields": {**RTI["fields"], "x": "1"}}).status_code == 422
    )


def test_download_blocked_until_checked(client):
    h = _confirm(client, RTI)["hash"]
    r = client.post("/drafts/pdf", json={**RTI, "confirmed_hash": h})
    assert r.status_code == 409 and r.json()["detail"] == "confirmation_required"


def test_download_blocked_if_changed_after_review(client):
    h = _confirm(client, RTI)["hash"]
    changed = {**RTI, "fields": {**RTI["fields"], "full_name": "Someone Else"}}
    r = client.post("/drafts/pdf", json={**changed, "confirmed_hash": h, "checked_all_fields": True})
    assert r.status_code == 409 and r.json()["detail"] == "changed_since_review"


@needs_pdf
@pytest.mark.parametrize("lang", ["en", "hi"])
def test_confirmed_download_is_a_pdf_without_full_numbers(client, lang):
    body = {**RTI, "lang": lang}
    h = _confirm(client, body)["hash"]
    r = client.post("/drafts/pdf", json={**body, "confirmed_hash": h, "checked_all_fields": True})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf" and r.headers["cache-control"] == "no-store"
    text = "".join(p.get_text() for p in pymupdf.open(stream=r.content, filetype="pdf"))
    assert "2345 6789 0124" not in text and "Asha Verma" in text
    assert "Sahaay" in text or "सहाय" in text


@needs_pdf
def test_hindi_pdf_embeds_a_devanagari_font(client):
    body = {**RTI, "lang": "hi"}
    h = _confirm(client, body)["hash"]
    r = client.post("/drafts/pdf", json={**body, "confirmed_hash": h, "checked_all_fields": True})
    fonts = {f[3] for p in pymupdf.open(stream=r.content, filetype="pdf") for f in p.get_fonts()}
    assert any("Devanagari" in f for f in fonts), fonts


def test_html_escapes_user_text():
    f = drafts.clean_fields(
        "cpgrams", {"full_name": "<b>x</b>", "department": "d", "grievance": "g", "requested_action": "a"}
    )
    html = drafts.build_html("cpgrams", "en", f)
    assert "<b>x</b>" not in html and "&lt;b&gt;" in html


@needs_pdf
@pytest.mark.parametrize("kind", ["complaint", "cpgrams"])
def test_other_kinds_render(client, kind):
    fields = {
        "complaint": {
            "full_name": "A",
            "addressed_to": "DM",
            "service_name": "Income certificate",
            "issue": "Delay",
            "requested_action": "Decide",
        },
        "cpgrams": {
            "full_name": "A",
            "department": "Revenue",
            "grievance": "Delay",
            "requested_action": "Decide",
        },
    }[kind]
    body = {"kind": kind, "fields": fields}
    h = _confirm(client, body)["hash"]
    r = client.post("/drafts/pdf", json={**body, "confirmed_hash": h, "checked_all_fields": True})
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
