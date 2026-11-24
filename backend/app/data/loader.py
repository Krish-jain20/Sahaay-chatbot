"""Load and validate data/*.json at startup."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.data.models import Allowlist, InfoService, ServiceRecord
from app.safety.allowlist import is_allowed

PROFILE_KEYS = {
    "full_name",
    "date_of_birth",
    "gender",
    "state_of_residence",
    "district",
    "annual_family_income_inr",
    "social_category",
    "occupation",
    "education_level",
    "institution_type",
    "has_disability",
    "receives_other_scholarship",
    "receives_pension",
    "has_bank_account_linked",
    "marital_status",
    "years_resident_in_state",
    "age",
    "previous_year_marks_percent",
}


class DataError(ValueError):
    pass


@dataclass(frozen=True)
class Catalog:
    services: dict[str, ServiceRecord]
    allowlist: Allowlist
    directory: dict[str, InfoService] = field(default_factory=dict)

    def served(self) -> list[ServiceRecord]:
        return [s for s in self.services.values() if s.status != "unverified"]


def _refs(rec: ServiceRecord) -> list[str]:
    refs = [
        rec.benefit.source_ref,
        rec.typical_duration_days.source_ref,
        rec.fees.source_ref,
        rec.timeline.source_ref,
    ]
    refs += [r.source_ref for r in rec.eligibility.rules]
    refs += [x.source_ref for x in rec.exclusions]
    refs += [d.source_ref for d in rec.documents]
    refs += [s.source_ref for s in rec.apply.steps]
    refs += [c.source_ref for c in rec.grievance.channels]
    if rec.grievance.appellate_authority.source_ref:
        refs.append(rec.grievance.appellate_authority.source_ref)
    return refs


def validate_record(rec: ServiceRecord, filename: str, allowlist: Allowlist) -> None:
    if rec.id != filename:
        raise DataError(f"{filename}: id '{rec.id}' does not match filename")
    source_ids = {s.id for s in rec.sources}
    for ref in _refs(rec):
        if ref not in source_ids:
            raise DataError(f"{rec.id}: source_ref '{ref}' not in sources")
    urls = [s.url for s in rec.sources] + ([rec.apply.official_url] if rec.apply.official_url else [])
    for url in urls:
        if not is_allowed(url, allowlist):
            raise DataError(f"{rec.id}: host of {url} is not in allowlist.json")
    conditions = [r.applies_if for r in rec.eligibility.rules if r.applies_if]
    for rule in [*rec.eligibility.rules, *rec.exclusions, *conditions]:
        if rule.field not in PROFILE_KEYS:
            raise DataError(f"{rec.id}: unknown profile key '{rule.field}'")
    if rec.status == "verified":
        v = rec.verification
        if not (v.verified_by and v.verified_on):
            raise DataError(f"{rec.id}: verified records need verified_by and verified_on")
        if not any(s.date_checked for s in rec.sources):
            raise DataError(f"{rec.id}: verified records need a source with date_checked")
        if not rec.apply.official_url:
            raise DataError(f"{rec.id}: verified records need apply.official_url")


def _check_prerequisites(services: dict[str, ServiceRecord]) -> None:
    for rec in services.values():
        for p in rec.prerequisites:
            if p not in services:
                raise DataError(f"{rec.id}: prerequisite '{p}' does not exist")
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(sid: str) -> None:
        if sid in done:
            return
        if sid in visiting:
            raise DataError(f"prerequisite cycle through '{sid}'")
        visiting.add(sid)
        for p in services[sid].prerequisites:
            visit(p)
        visiting.discard(sid)
        done.add(sid)

    for sid in services:
        visit(sid)


def validate_info(info: InfoService, filename: str, allowlist: Allowlist) -> None:
    if info.id != filename:
        raise DataError(f"{filename}: id '{info.id}' does not match filename")
    source_ids = {s.id for s in info.sources}
    facts = [info.benefit, info.fee, info.time, *info.who, *info.documents, *info.steps]
    for f in facts:
        if f is not None and f.source_ref not in source_ids:
            raise DataError(f"{info.id}: source_ref '{f.source_ref}' not in sources")
    for url in [s.url for s in info.sources] + ([info.apply_url] if info.apply_url else []):
        if not is_allowed(url, allowlist):
            raise DataError(f"{info.id}: host of {url} is not in allowlist.json")
    if not info.sources or not all(s.date_checked for s in info.sources):
        raise DataError(f"{info.id}: every source needs a date_checked")


Raw = list[tuple[str, dict[str, Any]]]


def build_catalog(
    allowlist: Allowlist,
    records: Raw,
    infos: Raw,
) -> Catalog:
    """Validate and assemble a catalog from raw JSON, whether it came from files or from the database."""
    services: dict[str, ServiceRecord] = {}
    for name, raw in records:
        rec = ServiceRecord.model_validate(raw)
        validate_record(rec, name, allowlist)
        if rec.id in services:
            raise DataError(f"duplicate id {rec.id}")
        services[rec.id] = rec
    _check_prerequisites(services)
    directory: dict[str, InfoService] = {}
    for name, raw in infos:
        info = InfoService.model_validate(raw)
        validate_info(info, name, allowlist)
        if info.id in services or info.id in directory:
            raise DataError(f"duplicate id {info.id}")
        directory[info.id] = info
    return Catalog(services=services, allowlist=allowlist, directory=directory)


def load_allowlist(data_dir: Path) -> Allowlist:
    return Allowlist.model_validate_json((data_dir / "allowlist.json").read_text("utf-8"))


def read_files(data_dir: Path) -> tuple[Raw, Raw]:
    def read(folder: str) -> Raw:
        return [
            (p.stem, json.loads(p.read_text("utf-8"))) for p in sorted((data_dir / folder).glob("*.json"))
        ]

    return read("schemes"), read("directory")


def load_catalog(data_dir: Path) -> Catalog:
    """The repo files: the source of truth for tests and the fallback when the database is not usable."""
    records, infos = read_files(data_dir)
    return build_catalog(load_allowlist(data_dir), records, infos)
