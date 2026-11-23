"""Small eval runner: `cd backend && uv run python -m tests.eval.run [--live]`.

Runs every question through the real graph and checks facts, citations, forbidden claims,
refusals and staleness. Offline stub LLM by default; --live uses GEMINI_API_KEY from .env.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent


def evaluate(q: dict[str, Any], events: list[tuple[str, dict[str, Any]]]) -> list[str]:
    failures: list[str] = []
    text = "".join(d["text"] for n, d in events if n == "token")
    card = next((d for n, d in events if n == "card"), None)
    has_citations = any(n == "citation" and d.get("url") for n, d in events)
    cited = {card["service"]["id"]} if card and has_citations else set()
    lowered = text.lower()
    if events[-1][0] != "done":
        failures.append("stream did not end with done")
    for bad in q["must_not_say"]:
        if bad in lowered:
            failures.append(f"forbidden claim: {bad}")
    if "₹[" in text or "[fee]" in lowered:
        failures.append("placeholder reached the user")
    if q.get("expect_refusal"):
        if card is not None or events[-1][1].get("refused") is not True:
            failures.append("expected a refusal")
        return failures
    if card is None:
        return [*failures, "no card"]
    if card["service"]["id"] != q["expect_service"]:
        failures.append(f"wrong service {card['service']['id']}")
    for need in q["must_cite"]:
        if need not in cited:
            failures.append(f"missing citation for {need}")
    if "[1]" not in text:
        failures.append("answer text has no [n] citation marker")
    for inc in q["must_include"]:
        kind, _, val = inc.partition(":")
        ok = {
            "fee": "fee_strip" in card,
            "verdict": card["eligibility"]["verdict"] == val,
            "prereq": val in [p["id"] for p in card["prerequisites"]],
            "exclusion": val in [x["id"] for x in card["eligibility"]["exclusions_hit"]],
            "stale": card["service"]["stale"] is True,
        }.get(kind, False)
        if not ok:
            failures.append(f"missing: {inc}")
    # Unknown must never read as met.
    if card["eligibility"]["verdict"] == "likely" and any(
        r["required"] and r["result"] != "met" for r in card["eligibility"]["rules"]
    ):
        failures.append("likely verdict with a required rule not met")
    return failures


def main() -> int:
    if "--live" not in sys.argv:
        os.environ["GEMINI_API_KEY"] = ""
    os.environ["SUPABASE_URL"] = ""
    from app.config import get_settings
    from app.data.loader import load_catalog
    from app.graph.graph import build_graph, run_turn
    from app.llm.client import LLM

    settings = get_settings()
    catalog = load_catalog(settings.data_dir)
    llm = LLM()
    graph = build_graph()
    questions = json.loads((HERE / "eval_questions.json").read_text("utf-8"))
    passed = 0
    for q in questions:
        today = date.fromisoformat(q.get("today", "2026-11-23"))
        events = list(
            run_turn(
                graph,
                catalog,
                llm,
                q["question"],
                q["lang"],
                q["profile"],
                today,
                settings.freshness_days,
                "eval",
                thread_id=q["id"],
            )
        )
        failures = evaluate(q, events)
        passed += not failures
        print(f"{'PASS' if not failures else 'FAIL'} {q['id']} [{q['lang']}] {q['question'][:50]}")
        for f in failures:
            print(f"     - {f}")
    print(f"\nScore: {passed}/{len(questions)} ({'live Gemini' if llm.live else 'offline stub'})")
    return 0 if passed == len(questions) else 1


if __name__ == "__main__":
    raise SystemExit(main())
