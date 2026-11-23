import json
from pathlib import Path

from tests.eval.run import evaluate

QUESTIONS = json.loads((Path(__file__).parent / "eval" / "eval_questions.json").read_text("utf-8"))


def test_eval_set_baseline_offline(monkeypatch, capsys):
    import sys

    from tests.eval import run

    monkeypatch.setattr(sys, "argv", ["run"])
    assert run.main() == 0, capsys.readouterr().out


def test_evaluator_catches_planted_approved_claim():
    q = next(x for x in QUESTIONS if x["id"] == "q-001")
    events = [("token", {"text": "Your income certificate is approved. [1]"}), ("done", {"refused": False})]
    assert "forbidden claim: approved" in evaluate(q, events)
