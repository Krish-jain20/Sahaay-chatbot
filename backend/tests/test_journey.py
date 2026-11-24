from datetime import UTC, datetime

from app.rules.journey import journey


def ev(step, day):
    return {"step": step, "at": datetime(2026, 11, day, tzinfo=UTC).isoformat()}


def test_empty_journey_starts_at_step_one():
    j = journey([])
    assert (j.completed, j.current) == (0, 1) and not any(s.done for s in j.steps)


def test_current_is_first_step_not_done_even_out_of_order():
    j = journey([ev(1, 1), ev(3, 2)])
    assert j.current == 2 and j.completed == 2
    assert [s.done for s in j.steps] == [True, False, True, False, False]


def test_first_record_of_a_step_wins_and_all_done_has_no_current():
    j = journey([ev(1, 5), ev(1, 2), *[ev(n, 6) for n in range(2, 6)]])
    assert j.steps[0].done_at.day == 2
    assert j.completed == 5 and j.current is None
