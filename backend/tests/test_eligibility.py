from datetime import date

import pytest

from app.rules.eligibility import Fact, RuleResult, Verdict, apply_op, check

TODAY = date(2026, 11, 23)


@pytest.mark.parametrize(
    ("op", "actual", "expected", "ok"),
    [
        ("eq", "delhi", "Delhi", True),
        ("ne", "Delhi", "Delhi", False),
        ("lt", 100, 200, True),
        ("lte", 200, 200, True),
        ("gt", 100, 200, False),
        ("gte", 200, 200, True),
        ("between", 250000, [0, 300000], True),
        ("between", 350000, [0, 300000], False),
        ("in", "SC", ["sc", "st"], True),
        ("not_in", "general", ["sc", "st"], True),
        ("exists", "x", None, True),
        ("is_true", True, None, True),
        ("is_true", "yes", None, False),
        ("is_false", False, None, True),
        ("age_between", "1960-01-01", [60, 200], True),
        ("age_between", date(2000, 1, 1), [60, 200], False),
    ],
)
def test_operators(op, actual, expected, ok):
    assert apply_op(op, actual, expected, TODAY) is ok


def test_unknown_when_fact_missing(catalog):
    rec = catalog.services["delhi-income-certificate"]
    res = check(rec, {}, TODAY)
    assert res.verdict is Verdict.INCOMPLETE
    assert res.rules[0].result is RuleResult.UNKNOWN
    assert res.unknown_fields == ["state_of_residence"]


def test_unconfirmed_fact_is_never_met(catalog):
    rec = catalog.services["delhi-income-certificate"]
    res = check(rec, {"state_of_residence": Fact("Delhi", confirmed=False)}, TODAY)
    assert res.rules[0].result is RuleResult.UNKNOWN
    assert res.verdict is Verdict.INCOMPLETE


def test_confirmed_met_and_not_met(catalog):
    rec = catalog.services["delhi-income-certificate"]
    assert check(rec, {"state_of_residence": Fact("Delhi", True)}, TODAY).verdict is Verdict.LIKELY
    res = check(rec, {"state_of_residence": Fact("Bihar", True)}, TODAY)
    assert res.verdict is Verdict.NOT_ELIGIBLE


def test_bad_type_is_unknown_not_crash(catalog):
    rec = catalog.services["delhi-income-certificate"]
    rule = rec.eligibility.rules[0].model_copy(update={"op": "gt", "value": 5})
    rec2 = rec.model_copy(update={"eligibility": rec.eligibility.model_copy(update={"rules": [rule]})})
    res = check(rec2, {"state_of_residence": Fact("Delhi", True)}, TODAY)
    assert res.rules[0].result is RuleResult.UNKNOWN
