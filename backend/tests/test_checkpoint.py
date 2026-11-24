"""Conversation state: masked, and persistent when a database is configured.

The Postgres test runs only when TEST_DATABASE_URL is set (a throwaway database):
    TEST_DATABASE_URL=postgresql://postgres@localhost:5432/sahaay_test uv run pytest tests/test_checkpoint.py
"""

import os
from datetime import date

import pytest

from app.graph.checkpoint import make_checkpointer
from app.graph.graph import build_graph, run_turn
from app.llm.client import LLM

AADHAAR = "2345 6789 0124"
PHONE = "9876543210"


def _turn(graph, catalog, thread):
    list(
        run_turn(
            graph,
            catalog,
            LLM(),
            f"I am 70, need old age pension. aadhaar {AADHAAR} phone {PHONE}",
            "en",
            {},
            date(2026, 11, 24),
            90,
            user_id="u1",
            thread_id=thread,
        )
    )


def test_memory_saver_is_the_default():
    cp = make_checkpointer("")
    assert not cp.persistent
    cp.close()


def test_checkpointed_state_is_masked(catalog):
    cp = make_checkpointer("")
    graph = build_graph(cp.saver)
    _turn(graph, catalog, "t-mask")
    values = graph.get_state({"configurable": {"thread_id": "t-mask"}}).values
    assert AADHAAR not in str(values) and PHONE not in str(values)


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")
def test_state_survives_a_restart_in_postgres(catalog):
    url = os.environ["TEST_DATABASE_URL"]
    thread = f"t-restart-{os.getpid()}"
    first = make_checkpointer(url)
    assert first.persistent
    _turn(build_graph(first.saver), catalog, thread)
    first.close()  # the "restart"

    second = make_checkpointer(url)
    try:
        state = build_graph(second.saver).get_state({"configurable": {"thread_id": thread}})
        assert state.values.get("service_id") == "delhi-old-age-pension"
        text = str(state.values)
        assert AADHAAR not in text and PHONE not in text and "234567890124" not in text
    finally:
        second.close()
