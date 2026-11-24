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


# ---- catalog: every draft type works end to end -------------------------------------------------

from app.pdf.draft_catalog import KINDS  # noqa: E402
from app.safety.claims import find_violations  # noqa: E402


def _sample(kind) -> dict:
    out: dict = {}
    for ref in kind.fields:
        s = ref.spec
        if s.type == "choice":
            out[s.key] = s.options[0][0]
        elif s.type == "date":
            out[s.key] = "2025-03-14"
        elif s.type == "checkbox":
            out[s.key] = True
        else:
            out[s.key] = f"Sample {s.key}"
    return out


def test_catalog_has_many_kinds_in_known_groups(client):
    r = client.get("/drafts/catalog?lang=en")
    assert r.status_code == 200
    body = r.json()
    groups = {g["id"] for g in body["groups"]}
    assert len(body["kinds"]) >= 15
    assert {k["group"] for k in body["kinds"]} <= groups
    assert len({k["id"] for k in body["kinds"]}) == len(body["kinds"])
    # the three original kinds keep their ids
    assert {"complaint", "rti", "cpgrams"} <= {k["id"] for k in body["kinds"]}


@pytest.mark.parametrize("lang", ["hi", "hn"])
def test_catalog_is_localised(client, lang):
    en = client.get("/drafts/catalog?lang=en").json()["kinds"]
    other = client.get(f"/drafts/catalog?lang={lang}").json()["kinds"]
    assert [k["id"] for k in en] == [k["id"] for k in other]
    assert sum(a["title"] != b["title"] for a, b in zip(en, other, strict=True)) >= len(en) - 1


def test_portal_links_use_allowlisted_hosts_only(client, catalog):
    hosts = {d.host for d in catalog.allowlist.domains}
    for k in client.get("/drafts/catalog").json()["kinds"]:
        if k["portal"]:
            assert k["portal"]["host"] in hosts and k["portal"]["date_checked"], k["id"]
            assert k["portal"]["url"] == f"https://{k['portal']['host']}/"


def test_catalog_text_has_no_forbidden_claims_or_placeholders():
    for k in KINDS:
        for lang in ("en", "hi", "hn"):
            texts = [k.title.get(lang), k.blurb.get(lang), k.subject.get(lang)]
            texts += [x.get(lang) for x in (k.intro, k.closing, k.enclose) if x]
            for t in texts:
                assert not find_violations(t) and "[" not in t, (k.id, lang, t)


@pytest.mark.parametrize("kind", KINDS, ids=lambda k: k.id)
def test_every_kind_previews_and_validates(client, kind):
    body = {"kind": kind.id, "fields": _sample(kind)}
    p = _confirm(client, body)
    assert [r["key"] for r in p["rows"]] == [f.key for f in kind.fields]
    # leaving out each required field is rejected and named
    for key in kind.required_keys:
        short = {k: v for k, v in body["fields"].items() if k != key}
        r = client.post("/drafts/preview", json={"kind": kind.id, "fields": short})
        assert r.status_code == 422 and key in r.json()["detail"], (kind.id, key)


@needs_pdf
@pytest.mark.parametrize("lang", ["en", "hi", "hn"])
@pytest.mark.parametrize("kind", KINDS, ids=lambda k: k.id)
def test_every_kind_renders_a_pdf(client, kind, lang):
    body = {"kind": kind.id, "lang": lang, "fields": _sample(kind)}
    h = _confirm(client, body)["hash"]
    r = client.post("/drafts/pdf", json={**body, "confirmed_hash": h, "checked_all_fields": True})
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    text = "".join(p.get_text() for p in pymupdf.open(stream=r.content, filetype="pdf"))
    assert "Sample full_name" in text or "Sample department" in text
    assert "₹[" not in text and "{" not in text


def test_unknown_kind_rejected(client):
    r = client.post("/drafts/preview", json={"kind": "nope", "fields": {}})
    assert r.status_code == 422


def test_field_of_another_kind_rejected(client):
    r = client.post("/drafts/preview", json={"kind": "rti", "fields": {**RTI["fields"], "bank_name": "X"}})
    assert r.status_code == 422


def test_dates_and_choices_are_validated():
    base = {"full_name": "A", "address": "B", "addressed_to": "C", "pio_office": "D", "issue": "i",
            "requested_action": "a", "appeal_ground": "no_reply", "rti_filed_on": "14/03/2025"}
    ok = drafts.clean_fields("rti_first_appeal", base)
    assert ok["rti_filed_on"] == "2025-03-14"  # day/month/year accepted, stored as ISO
    cases = [
        ({"rti_filed_on": "yesterday"}, "invalid_date"),
        ({"rti_filed_on": "2999-01-01"}, "future_date"),
        ({"appeal_ground": "angry"}, "invalid_choice"),
    ]
    for bad, code in cases:
        with pytest.raises(drafts.DraftError, match=code):
            drafts.clean_fields("rti_first_appeal", {**base, **bad})


def test_reference_numbers_keep_last_four_only(client):
    kind = {"kind": "electricity_bill", "fields": {
        "full_name": "A", "address": "B", "utility_company": "C", "consumer_no": "100234567891",
        "bill_issue": "meter", "issue": "i", "requested_action": "a"}}
    text = str(_confirm(client, kind)["rows"])
    assert "100234567891" not in text and "7891" in text


def test_choice_and_date_read_as_words_in_the_letter():
    f = drafts.clean_fields("ration_issue", {
        "full_name": "A", "address": "B", "addressed_to": "C", "ration_issue": "name_missing",
        "applied_on": "2025-03-14", "issue": "i", "requested_action": "a"})
    html = drafts.build_html("ration_issue", "en", f)
    assert "A family member&#x27;s name is missing" in html or "name is missing" in html
    assert "14/03/2025" in html and "name_missing" not in html
    assert "परिवार के सदस्य" in drafts.build_html("ration_issue", "hi", f)
