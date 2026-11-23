from datetime import date

from app.data.models import DocumentReq
from app.rules.readiness import CheckStatus, Evaluated, _add_months, readiness

TODAY = date(2026, 11, 23)


def record(catalog, reqs):
    rec = catalog.services["delhi-income-certificate"]
    return rec.model_copy(update={"documents": reqs})


def req(doc_type, required=True, alternatives=(), validity=None, after=None):
    return DocumentReq(
        doc_type=doc_type,
        required=required,
        alternatives=list(alternatives),
        validity_months=validity,
        issued_after=after,
        source_ref="s1",
    )


def test_missing_documents_count_against(catalog):
    r = readiness(record(catalog, [req("aadhaar"), req("passport_photo")]), [], TODAY)
    assert (r.completed, r.total) == (0, 2)
    assert {c.status for c in r.checks} == {CheckStatus.MISSING}


def test_alternatives_satisfy_a_requirement(catalog):
    docs = [{"doc_type": "voter_id", "fields": {}}]
    r = readiness(record(catalog, [req("aadhaar", alternatives=["voter_id"])]), docs, TODAY)
    assert r.checks[0].status is CheckStatus.OK and r.checks[0].matched_doc_type == "voter_id"
    assert r.checks[0].evaluated is Evaluated.DECLARED


def test_expired_and_too_old(catalog):
    docs = [{"doc_type": "income_certificate", "fields": {"issue_date": "2026-01-10"}}]
    r = readiness(record(catalog, [req("income_certificate", validity=6)]), docs, TODAY)
    assert r.checks[0].status is CheckStatus.EXPIRED and r.checks[0].expires_on == date(2026, 7, 10)
    assert (r.completed, r.total) == (0, 1)
    r = readiness(record(catalog, [req("income_certificate", after=date(2026, 4, 1))]), docs, TODAY)
    assert r.checks[0].status is CheckStatus.TOO_OLD


def test_valid_scanned_document_counts(catalog):
    docs = [{"doc_type": "income_certificate", "fields": {"issue_date": "2026-09-12"}}]
    r = readiness(record(catalog, [req("income_certificate", validity=6)]), docs, TODAY)
    assert r.checks[0].status is CheckStatus.OK and r.checks[0].evaluated is Evaluated.SCANNED
    assert r.completed == r.total == 1


def test_declared_documents_are_not_date_checked_and_say_so(catalog):
    docs = [{"doc_type": "income_certificate", "fields": {}}]
    r = readiness(record(catalog, [req("income_certificate", validity=6)]), docs, TODAY)
    assert r.checks[0].status is CheckStatus.OK and r.checks[0].evaluated is Evaluated.DECLARED


def test_optional_documents_do_not_change_the_count(catalog):
    r = readiness(record(catalog, [req("aadhaar"), req("caste_certificate", required=False)]), [], TODAY)
    assert (r.completed, r.total) == (0, 1) and len(r.checks) == 2


def test_prefers_scanned_over_declared(catalog):
    docs = [
        {"doc_type": "aadhaar", "fields": {}},
        {"doc_type": "aadhaar", "fields": {"aadhaar_masked": "XXXX XXXX 0124"}},
    ]
    r = readiness(record(catalog, [req("aadhaar")]), docs, TODAY)
    assert r.checks[0].evaluated is Evaluated.SCANNED


def test_add_months_edges():
    assert _add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert _add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert _add_months(date(2026, 11, 23), 3) == date(2027, 2, 23)
