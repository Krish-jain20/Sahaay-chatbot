"""General guidance topics (complaint vs RTI vs appeal, scam warnings) from data/guidance.json.

Every point names a source; hosts must be in allowlist.json. Texts are localised like service records.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.data.loader import DataError
from app.data.models import Allowlist, Lang, LText, Source, Strict
from app.safety.allowlist import is_allowed
from app.safety.claims import find_violations


class Point(Strict):
    id: str
    heading: LText
    body: LText
    source_ref: str


class Topic(Strict):
    id: str
    title: LText
    intro: LText
    points: list[Point]


class Guidance(Strict):
    version: int
    updated_on: str
    sources: list[Source]
    topics: list[Topic]


@dataclass(frozen=True)
class GuidanceSet:
    topics: dict[str, Topic]
    sources: dict[str, Source]

    def render(self, topic_id: str, lang: Lang) -> dict[str, Any]:
        return render(self.topics[topic_id], self.sources, lang)


def load_guidance(data_dir: Path, allowlist: Allowlist) -> GuidanceSet:
    g = Guidance.model_validate(json.loads((data_dir / "guidance.json").read_text("utf-8")))
    ids = {s.id for s in g.sources}
    for s in g.sources:
        if not is_allowed(s.url, allowlist):
            raise DataError(f"guidance: host of {s.url} is not in allowlist.json")
        if not s.date_checked:
            raise DataError(f"guidance: source {s.id} has no date_checked")
    for topic in g.topics:
        for p in topic.points:
            if p.source_ref not in ids:
                raise DataError(f"guidance {topic.id}/{p.id}: unknown source_ref {p.source_ref}")
            for lang in ("en", "hi", "hn"):
                text = " ".join([p.heading.get(lang) or "", p.body.get(lang) or ""])
                if find_violations(text):
                    raise DataError(f"guidance {topic.id}/{p.id}: forbidden claim in {lang}")
    return GuidanceSet({t.id: t for t in g.topics}, {s.id: s for s in g.sources})


def render(topic: Topic, sources: dict[str, Source], lang: Lang) -> dict[str, Any]:
    """Resolve one topic to plain strings plus numbered citations, in the card/API shape."""
    order = list(dict.fromkeys(p.source_ref for p in topic.points))
    n = {sid: i + 1 for i, sid in enumerate(order)}
    return {
        "type": "guide",
        "id": topic.id,
        "title": topic.title.get(lang),
        "intro": topic.intro.get(lang),
        "points": [
            {
                "id": p.id,
                "heading": p.heading.get(lang),
                "body": p.body.get(lang),
                "source_n": n[p.source_ref],
            }
            for p in topic.points
        ],
        "citations": [
            {
                "n": n[sid],
                "id": sid,
                "title": sources[sid].title,
                "url": sources[sid].url,
                "publisher": sources[sid].publisher,
                "date_checked": sources[sid].date_checked.isoformat() if sources[sid].date_checked else None,
            }
            for sid in order
        ],
    }
