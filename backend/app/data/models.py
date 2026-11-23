"""Pydantic models for data/*.json (see docs/DATA_SCHEMA.md)."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Lang = Literal["en", "hi", "hn"]
Op = Literal[
    "eq",
    "ne",
    "lt",
    "lte",
    "gt",
    "gte",
    "between",
    "in",
    "not_in",
    "exists",
    "is_true",
    "is_false",
    "age_between",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LText(Strict):
    """Localised string. `en` may be null only where the value is unknown."""

    en: str | None
    hi: str | None = None
    hn: str | None = None

    def get(self, lang: Lang) -> str | None:
        return getattr(self, lang) or self.en


class Jurisdiction(Strict):
    level: Literal["central", "state", "district"]
    state: str | None = None


class Benefit(Strict):
    amount_text: LText
    amount_inr: int | None
    frequency: str | None
    source_ref: str


class Condition(Strict):
    field: str
    op: Op
    value: Any = None


class Rule(Strict):
    id: str
    field: str
    op: Op
    value: Any = None
    required: bool = True
    applies_if: Condition | None = None  # rule only applies when this condition is met
    label: LText
    source_ref: str


class Eligibility(Strict):
    rules: list[Rule]


class Exclusion(Strict):
    id: str
    field: str
    op: Op
    value: Any = None
    label: LText
    source_ref: str


class DocumentReq(Strict):
    doc_type: str
    required: bool
    alternatives: list[str] = []
    validity_months: int | None = None
    issued_after: date | None = None
    source_ref: str


class Duration(Strict):
    min: int | None
    max: int | None
    source_ref: str


class Fees(Strict):
    official_online_inr: int | None
    csc_max_inr: int | None
    notes: LText
    source_ref: str


class Timeline(Strict):
    sla_days: int | None
    day_type: Literal["working", "calendar"] | None
    source_ref: str


class Step(Strict):
    n: int
    text: LText
    source_ref: str


class Apply(Strict):
    official_url: str | None
    mode: list[Literal["online", "csc", "office"]]
    forms: list[str]
    steps: list[Step]


class Channel(Strict):
    type: Literal["cpgrams", "state_portal", "department", "helpline"]
    name: str | None
    url: str | None
    phone: str | None
    source_ref: str


class Appellate(Strict):
    en: str | None
    source_ref: str | None


class Grievance(Strict):
    channels: list[Channel]
    appellate_authority: Appellate


class Source(Strict):
    id: str
    title: str
    url: str
    publisher: str
    date_checked: date | None
    effective_date: date | None


class Verification(Strict):
    verified_by: str | None
    verified_on: date | None
    notes: str | None


class ServiceRecord(Strict):
    id: str
    kind: Literal["service", "scheme"]
    status: Literal["verified", "partial", "unverified"]
    jurisdiction: Jurisdiction
    name: LText
    department: LText
    category: list[str]
    aliases: list[str] = []
    summary: LText
    benefit: Benefit
    eligibility: Eligibility
    exclusions: list[Exclusion]
    documents: list[DocumentReq]
    prerequisites: list[str]
    typical_duration_days: Duration
    fees: Fees
    timeline: Timeline
    apply: Apply
    grievance: Grievance
    sources: list[Source]
    verification: Verification

    def source(self, ref: str) -> Source:
        return next(s for s in self.sources if s.id == ref)


class AllowedDomain(Strict):
    host: str
    owner: str
    verified_on: date | None


class Allowlist(Strict):
    version: int
    updated_on: date
    domains: list[AllowedDomain]
