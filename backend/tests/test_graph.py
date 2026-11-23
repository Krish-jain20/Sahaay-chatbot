from datetime import date

from app.graph.graph import build_graph, run_turn
from app.llm.client import LLM

TODAY = date(2026, 11, 23)


def turn(catalog, message, facts=None, lang="en"):
    llm = LLM()
    assert not llm.live  # tests always use the offline stub
    return list(run_turn(build_graph(), catalog, llm, message, lang, facts or {}, TODAY, 90, "u1"))


def names(events):
    return [n for n, _ in events]


def test_graph_runs_message_to_answer(catalog):
    ev = turn(catalog, "How do I get an income certificate in Delhi?")
    n = names(ev)
    assert n[-1] == "done" and "card" in n and "token" in n and "citation" in n
    # Statuses arrive in graph order.
    ids = [d["id"] for k, d in ev if k == "status" and d["state"] == "running"]
    assert ids == ["understand", "search", "eligibility"]
    # The card is emitted before the text; chips come after the citations.
    assert n.index("card") < n.index("token") < n.index("citation") < n.index("chips")


def test_graph_refuses_when_no_source(catalog):
    ev = turn(catalog, "passport renewal please")
    assert "card" not in names(ev) and ev[-1] == ("done", {"refused": True})
    assert "eligibility" not in [d["id"] for k, d in ev if k == "status"]


def test_graph_unknown_never_met(catalog):
    ev = turn(catalog, "income certificate")
    card = next(d for k, d in ev if k == "card")
    assert card["eligibility"]["verdict"] == "incomplete"
    assert {r["result"] for r in card["eligibility"]["rules"]} == {"unknown"}


def test_graph_llm_failure_is_a_clean_error(catalog):
    class Broken(LLM):
        def understand(self, text, *, user_id="anonymous"):
            from app.llm.client import LLMError

            raise LLMError("boom")

    ev = list(run_turn(build_graph(), catalog, Broken(), "hi", "en", {}, TODAY, 90, "u1"))
    assert [n for n, _ in ev if n in ("error", "done")] == ["error", "done"]
