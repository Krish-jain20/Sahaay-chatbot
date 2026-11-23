"""Deterministic eligibility engine. Pure functions, no I/O.

Unknown is never treated as met. Only confirmed facts produce MET / NOT_MET.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any

from app.data.models import Condition, Exclusion, Rule, ServiceRecord


class RuleResult(StrEnum):
    MET = "met"
    NOT_MET = "not_met"
    UNKNOWN = "unknown"


class Verdict(StrEnum):
    LIKELY = "likely"
    NOT_ELIGIBLE = "not_eligible"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class Fact:
    value: Any
    confirmed: bool = False


@dataclass(frozen=True)
class RuleOutcome:
    rule_id: str
    field: str
    required: bool
    result: RuleResult
    source_ref: str


@dataclass(frozen=True)
class EligibilityResult:
    service_id: str
    verdict: Verdict
    rules: list[RuleOutcome]
    exclusions_hit: list[str]
    unknown_fields: list[str]


def _age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _norm(v: Any) -> Any:
    return v.strip().casefold() if isinstance(v, str) else v


def apply_op(op: str, actual: Any, expected: Any, today: date) -> bool:
    a, e = _norm(actual), expected
    match op:
        case "eq":
            return a == _norm(e)
        case "ne":
            return a != _norm(e)
        case "lt":
            return a < e
        case "lte":
            return a <= e
        case "gt":
            return a > e
        case "gte":
            return a >= e
        case "between":
            return e[0] <= a <= e[1]
        case "in":
            return a in [_norm(x) for x in e]
        case "not_in":
            return a not in [_norm(x) for x in e]
        case "exists":
            return a is not None
        case "is_true":
            return a is True
        case "is_false":
            return a is False
        case "age_between":
            dob = actual if isinstance(actual, date) else date.fromisoformat(actual)
            return e[0] <= _age_on(dob, today) <= e[1]
    raise ValueError(f"unknown operator {op}")


def evaluate_rule(rule: Rule | Exclusion | Condition, facts: dict[str, Fact], today: date) -> RuleResult:
    fact = facts.get(rule.field)
    if fact is None or not fact.confirmed or fact.value is None:
        return RuleResult.UNKNOWN
    try:
        return RuleResult.MET if apply_op(rule.op, fact.value, rule.value, today) else RuleResult.NOT_MET
    except (TypeError, ValueError):
        return RuleResult.UNKNOWN


def _outcome(rule: Rule, facts: dict[str, Fact], today: date) -> RuleOutcome | None:
    """None when the rule does not apply (its applies_if condition is confirmed false)."""
    if rule.applies_if is not None:
        cond = evaluate_rule(rule.applies_if, facts, today)
        if cond is RuleResult.NOT_MET:
            return None
        if cond is RuleResult.UNKNOWN:
            return RuleOutcome(
                rule.id, rule.applies_if.field, rule.required, RuleResult.UNKNOWN, rule.source_ref
            )
    return RuleOutcome(rule.id, rule.field, rule.required, evaluate_rule(rule, facts, today), rule.source_ref)


def check(record: ServiceRecord, facts: dict[str, Fact], today: date) -> EligibilityResult:
    outcomes = [o for r in record.eligibility.rules if (o := _outcome(r, facts, today)) is not None]
    exclusions_hit = [x.id for x in record.exclusions if evaluate_rule(x, facts, today) is RuleResult.MET]
    required = [o for o in outcomes if o.required]
    if exclusions_hit or any(o.result is RuleResult.NOT_MET for o in required):
        verdict = Verdict.NOT_ELIGIBLE
    elif any(o.result is RuleResult.UNKNOWN for o in required):
        verdict = Verdict.INCOMPLETE
    else:
        verdict = Verdict.LIKELY
    unknown = list(dict.fromkeys(o.field for o in required if o.result is RuleResult.UNKNOWN))
    return EligibilityResult(record.id, verdict, outcomes, exclusions_hit, unknown)
