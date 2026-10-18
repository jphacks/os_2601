from app.context import AppContext
from app.hints import ComposedHint, compose_answer, compose_hint
from app.state import Problem


def _ai_hints(problem: Problem) -> list[str]:
    return [hint.display for hint in problem.hints if hint.source == "ai"]


async def compose(context: AppContext, problem: Problem, level: int, frame: bytes | None, persona: str) -> ComposedHint:
    return await compose_hint(
        context.ai, context.hint_model, frame, level, _ai_hints(problem), problem.problem_text, problem.leak_strings, persona
    )


async def answer(context: AppContext, problem: Problem, frame: bytes | None, utterance: str, persona: str) -> ComposedHint | None:
    return await compose_answer(
        context.ai, context.hint_model, frame, utterance, _ai_hints(problem), problem.problem_text, problem.leak_strings, persona
    )
