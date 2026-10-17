from datetime import UTC, datetime, timedelta

import pytest

from app.state import (
    NEXT_ACTION,
    SEND_FRAME_ACTION,
    Accepted,
    Advance,
    CheckDone,
    CheckRequested,
    End,
    Hint,
    HintIssued,
    HintRequested,
    LeakCheck,
    Problem,
    Rejected,
    Session,
    SessionSettings,
    Signal,
    Thresholds,
    step,
)

THRESHOLDS = Thresholds(
    motion_threshold=0.02,
    motion_exit_threshold=0.03,
    signal_timeout_seconds=5,
    prefetch_lead_seconds=3,
    speech_seconds_per_char=0.15,
    speech_seconds_base=1.0,
)
START = datetime(2026, 10, 17, 4, 30, tzinfo=UTC)
MOVING = 0.05
STILL = 0.01
H1_TEXT = "今、何を求めようとしてる？"


def at(second: float) -> datetime:
    return START + timedelta(seconds=second)


def new_session(state: str = "watching") -> Session:
    return Session(
        session_id="ses_test",
        session_token="tok_test",
        worksheet_id="WS-01",
        learner_label="テスト",
        mode="live",
        settings=SessionSettings(stuck_seconds=20, cooldown_seconds=60, max_level=2),
        problems=[Problem(problem_no=1, status="working", started_at=START), Problem(problem_no=2), Problem(problem_no=3)],
        created_at=START,
        state=state,
    )


def send(session: Session, motions: list[float], start_second: float) -> tuple[Session, list[tuple[str, str | None]]]:
    trace = []
    for offset, motion in enumerate(motions):
        session, result = step(session, Signal(motion=motion, camera_ok=True), at(start_second + offset), THRESHOLDS)
        assert isinstance(result, Accepted)
        trace.append((session.state, result.next_action))
    return session, trace


def first_stuck(trace: list[tuple[str, str | None]]) -> int | None:
    return next((index + 1 for index, (state, _) in enumerate(trace) if state == "stuck"), None)


def speak_hint(session: Session, second: float) -> tuple[Session, int]:
    session, accepted = step(session, HintRequested("manual" if session.state != "stuck" else "auto"), at(second), THRESHOLDS)
    assert isinstance(accepted, Accepted)
    session, _ = step(session, HintIssued(len(H1_TEXT)), at(second), THRESHOLDS)
    session.current_problem.hints.append(
        Hint("hnt_test", accepted.level, "auto", H1_TEXT, H1_TEXT, "符号", "fallback", LeakCheck(True, False), None, 0, at(second))
    )
    return session, accepted.level


def frame_requests(trace: list[tuple[str, str | None]]) -> list[int]:
    return [index for index, (_, next_action) in enumerate(trace) if next_action == SEND_FRAME_ACTION]


@pytest.mark.parametrize(
    ("name", "motions", "stuck_at", "last_state", "frame_requested_at"),
    [
        ("書き続けている", [MOVING] * 60, None, "watching", []),
        ("20 秒止まる", [MOVING] * 5 + [STILL] * 20, 25, "stuck", [21]),
        ("19 秒で動き出す", [MOVING] + [STILL] * 19 + [MOVING], None, "watching", [17]),
        ("一瞬の揺れ", [STILL] * 10 + [MOVING] + [STILL] * 15, None, "still", []),
    ],
)
def test_stillness_turns_into_stuck_only_after_stuck_seconds(
    name: str, motions: list[float], stuck_at: int | None, last_state: str, frame_requested_at: list[int]
) -> None:
    _, trace = send(new_session(), motions, start_second=0)
    assert first_stuck(trace) == stuck_at, name
    assert trace[-1][0] == last_state, name
    assert all((next_action == NEXT_ACTION) == (state == "stuck") for state, next_action in trace), name
    assert frame_requests(trace) == frame_requested_at, name


def test_brief_motion_resets_the_stillness_count() -> None:
    _, trace = send(new_session(), [STILL] * 10 + [MOVING] + [STILL] * 15, start_second=0)
    assert trace[10][0] == "watching"


def test_motion_between_the_two_thresholds_does_not_start_stillness() -> None:
    _, trace = send(new_session(), [0.025] * 10, start_second=0)
    assert {state for state, _ in trace} == {"watching"}


def test_exit_threshold_below_the_entry_threshold_is_rejected() -> None:
    with pytest.raises(ValueError):
        Thresholds(
            motion_threshold=0.05,
            motion_exit_threshold=0.045,
            signal_timeout_seconds=5,
            prefetch_lead_seconds=3,
            speech_seconds_per_char=0.15,
            speech_seconds_base=1.0,
        )


def test_signal_gap_resets_stillness() -> None:
    session, trace = send(new_session(), [MOVING] + [STILL] * 10, start_second=0)
    assert trace[-1][0] == "still"
    session, trace = send(session, [STILL] * 10, start_second=16)
    assert trace[0][0] == "still"
    assert first_stuck(trace) is None
    assert session.still_since == at(16)


def test_motion_while_stuck_is_ignored_and_next_action_repeats() -> None:
    session, trace = send(new_session(), [MOVING] + [STILL] * 20, start_second=0)
    assert trace[-1] == ("stuck", NEXT_ACTION)
    _, trace = send(session, [MOVING] * 3, start_second=21)
    assert trace == [("stuck", NEXT_ACTION)] * 3


def test_force_stuck_enters_stuck_immediately_and_counts_once() -> None:
    session, result = step(new_session(), Signal(motion=None, camera_ok=False, force_stuck=True), START, THRESHOLDS)
    assert (session.state, result) == ("stuck", Accepted(next_action=NEXT_ACTION))
    assert session.current_problem.stuck_count == 1
    session, result = step(session, Signal(motion=None, camera_ok=False, force_stuck=True), START, THRESHOLDS)
    assert session.current_problem.stuck_count == 1
    assert result == Accepted(next_action=NEXT_ACTION)


def test_stillness_during_cooldown_waits_for_cooldown_then_counts_again() -> None:
    session, _ = step(new_session(), Signal(motion=None, camera_ok=False, force_stuck=True), START, THRESHOLDS)
    session, _ = speak_hint(session, 0)
    session, trace = send(session, [STILL] * 90, start_second=1)
    states = [state for state, _ in trace]
    assert states[0] == "speaking"
    assert set(states[2:62]) == {"cooldown"}
    assert states[62] == "still"
    assert first_stuck(trace) == 82


def test_second_and_later_manual_hints_are_level_two() -> None:
    session = new_session()
    levels = []
    for round_number in range(4):
        session, level = speak_hint(session, round_number * 10)
        levels.append(level)
    assert levels == [1, 2, 2, 2]


def test_first_signal_after_creation_starts_watching() -> None:
    session, result = step(new_session("created"), Signal(motion=STILL, camera_ok=True), START, THRESHOLDS)
    assert (session.state, result) == ("watching", Accepted())


def test_after_end_signals_stay_ended_and_other_requests_conflict() -> None:
    session, _ = step(new_session(), End(), START, THRESHOLDS)
    session, result = step(session, Signal(motion=MOVING, camera_ok=True), at(1), THRESHOLDS)
    assert (session.state, result) == ("ended", Accepted())
    assert isinstance(step(session, HintRequested("manual"), at(2), THRESHOLDS)[1], Rejected)
    assert isinstance(step(session, CheckRequested(), at(2), THRESHOLDS)[1], Rejected)


def test_stale_signal_from_before_an_outage_does_not_backdate_stillness() -> None:
    session, _ = step(new_session(), Signal(motion=None, camera_ok=False, force_stuck=True), START, THRESHOLDS)
    session, _ = speak_hint(session, 0)
    session, _ = send(session, [STILL] * 10, start_second=1)
    session, trace = send(session, [STILL] * 25, start_second=70)
    assert trace[0][0] == "still"
    assert first_stuck(trace) == 21


def test_advance_while_praising_a_correct_answer_does_not_skip_the_next_problem() -> None:
    session, _ = step(new_session(), CheckRequested(), START, THRESHOLDS)
    session, _ = step(session, CheckDone("correct", 10), START, THRESHOLDS)
    assert (session.state, session.current_problem_no) == ("speaking", 2)
    session, result = step(session, Advance(), at(1), THRESHOLDS)
    assert result == Accepted()
    assert (session.state, session.current_problem_no) == ("watching", 2)
    assert [problem.status for problem in session.problems] == ["done", "working", "pending"]


def test_second_request_while_the_ai_is_answering_is_rejected() -> None:
    session, accepted = step(new_session(), HintRequested("manual"), START, THRESHOLDS)
    assert isinstance(accepted, Accepted)
    assert isinstance(step(session, HintRequested("voice"), at(1), THRESHOLDS)[1], Rejected)
    assert isinstance(step(session, CheckRequested(), at(1), THRESHOLDS)[1], Rejected)
    session, _ = step(session, HintIssued(len(H1_TEXT)), at(2), THRESHOLDS)
    assert session.pending_until is None


def test_check_that_never_finishes_returns_to_watching_after_the_pending_window() -> None:
    session, _ = step(new_session(), CheckRequested(), START, THRESHOLDS)
    assert session.state == "checking"
    session, _ = step(session, Signal(motion=MOVING, camera_ok=True), at(13), THRESHOLDS)
    assert (session.state, session.pending_until) == ("watching", None)


def test_small_tremor_while_still_does_not_restart_the_count() -> None:
    _, trace = send(new_session(), [MOVING] + [STILL] * 5 + [0.025] * 3 + [STILL] * 12, start_second=0)
    assert first_stuck(trace) == 21
    assert all(state != "watching" for state, _ in trace[1:20])


def test_frame_is_requested_again_in_the_next_stillness() -> None:
    _, trace = send(new_session(), [MOVING] + [STILL] * 18 + [MOVING] + [STILL] * 20, start_second=0)
    assert frame_requests(trace) == [17, 36]


def test_scripted_session_is_not_asked_for_a_frame_before_stuck() -> None:
    session = new_session()
    session.mode = "scripted"
    _, trace = send(session, [MOVING] + [STILL] * 20, start_second=0)
    assert frame_requests(trace) == []
    assert first_stuck(trace) == 21

