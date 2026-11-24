from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Request

from app.config import get_settings
from app.data.cards import all_cards
from app.data.models import Lang

router = APIRouter()


@router.get("/cards")
def cards(request: Request, lang: Lang = "en") -> list[dict[str, Any]]:
    """Every service as a card: the verified records first, then the sourced directory."""
    return all_cards(request.app.state.catalog, lang, date.today(), get_settings().freshness_days)
