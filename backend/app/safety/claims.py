"""Forbidden-claim scan. Sahaay never promises approval, vouches for a document, or states live status.

`find_violations` runs on every answer before it is streamed (see graph.compose) and in tests over
all user-facing text. Patterns are deliberately narrow: "this is not an approval" must pass.
"""

from __future__ import annotations

import re

FORBIDDEN: list[str] = [
    r"guarantee",
    r"will be approved",
    r"(you|your (application|request|claim|case))( (are|is|have been|has been|will be|'ll be))? approved",
    r"(has|have) been (approved|sanctioned|granted|accepted)",
    r"approval (is )?(assured|certain|confirmed)",
    r"definitely (eligible|qualify)",
    r"(document|certificate) is (genuine|authentic|real|valid)",
    r"(verified|checked) (as )?(genuine|authentic)",
    r"authenticity (is |has been )?verified",
    r"live (government )?status",
    r"status of your application is",
    r"₹\[",
    r"\[fee\]",
    r"गारंटी",
    r"ज़रूर (मंज़ूर|स्वीकृत)",
    r"(मंज़ूर|स्वीकृत|अनुमोदित) (हो गया|हो गई|हो जाएगा|हो जाएगी)",
    r"approve (ho gaya|ho gayi|ho jayega|ho jayegi|ho jaayega|ho jaayegi)",
    r"pakka (approve|mil jayega|mil jaayega)",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN]


def find_violations(text: str) -> list[str]:
    return [p.pattern for p in _COMPILED if p.search(text)]
