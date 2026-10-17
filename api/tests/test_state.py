from datetime import UTC, datetime, timedelta

import pytest

from app.state import (
    NEXT_ACTION,
    Accepted,
    Problem,
    Session,
    SessionSettings,
    Signal,
    Thresholds,
    step,
)

THRESHOLDS = Thresholds(
    motion_threshold=0.02,
    signal_timeout_seconds=5,
    speech_seconds_per_char=0.15,
    speech_seconds_base=1.0,
)
START = datetime(2026, 10, 17, 4, 30, tzinfo=UTC)
MOVING = 0.05
STILL = 0.01


def new_session(state: str = "watching") -> Session:
    return Session(
        session_id="ses_test",
        session_token="tok_test",
        worksheet_id="WS-01",
        learner_label="テスト",
        mode="live",
        settings=SessionSettings(stuck_seconds=20, cooldown_seconds=60, max_level=2),
        problems=[Problem(problem_no=1, status="working", started_at=START), Problem(problem_no=2)],
        created_at=START,
        state=state,
    )


def send(session: Session, motions: list[float], start_second: int) -> tuple[Session, list[tuple[str, str | None]]]:
    trace = []
    for offset, motion in enumerate(motions):
        now = START + timedelta(seconds=start_second + offset)
        session, result = step(session, Signal(motion=motion, camera_ok=True), now, THRESHOLDS)
        assert isinstance(result, Accepted)
        trace.append((session.state, result.next_action))
    return session, trace


@pytest.mark.parametrize(
    ("name", "motions", "stuck_at"),
    [
        ("20 秒止まる", [MOVING] * 5 + [STILL] * 20, 25),
        ("19 秒で動き出す", [MOVING] + [STILL] * 19 + [MOVING], None),
    ],
)
def test_stillness_turns_into_stuck_only_after_stuck_seconds(name: str, motions: list[float], stuck_at: int | None) -> None:
    _, trace = send(new_session(), motions, start_second=0)
    stuck_indexes = [index + 1 for index, (state, _) in enumerate(trace) if state == "stuck"]
    assert (stuck_indexes[0] if stuck_indexes else None) == stuck_at, name
    if stuck_at is not None:
        assert trace[stuck_at - 1] == ("stuck", NEXT_ACTION)
    else:
        assert trace[-1] == ("watching", None)


def test_signal_gap_resets_stillness() -> None:
    session, trace = send(new_session(), [MOVING] + [STILL] * 10, start_second=0)
    assert trace[-1][0] == "still"
    session, trace = send(session, [STILL] * 10, start_second=16)
    assert trace[0][0] == "still"
    assert all(state != "stuck" for state, _ in trace)
    assert session.still_since == START + timedelta(seconds=16)


def test_motion_while_stuck_is_ignored_and_next_action_repeats() -> None:
    session, trace = send(new_session(), [MOVING] + [STILL] * 20, start_second=0)
    assert trace[-1] == ("stuck", NEXT_ACTION)
    _, trace = send(session, [MOVING] * 3, start_second=21)
    assert trace == [("stuck", NEXT_ACTION)] * 3


def test_force_stuck_enters_stuck_immediately_and_counts_once() -> None:
    session, result = step(new_session(), Signal(motion=None, camera_ok=False, force_stuck=True), START, THRESHOLDS)
    assert session.state == "stuck"
    assert result == Accepted(next_action=NEXT_ACTION)
    assert session.current_problem.stuck_count == 1
    session, result = step(session, Signal(motion=None, camera_ok=False, force_stuck=True), START, THRESHOLDS)
    assert session.current_problem.stuck_count == 1
    assert result == Accepted(next_action=NEXT_ACTION)
