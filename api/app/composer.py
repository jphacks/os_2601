from app.context import AppContext
from app.hints import ComposedHint, compose_hint
from app.state import Problem


def ai_hints(problem: Problem) -> list[str]:
    return [hint.display for hint in problem.hints if hint.source == "ai"]


async def compose(context: AppContext, problem: Problem, level: int, frame: bytes | None, persona: str = "teacher") -> ComposedHint:
    return await compose_hint(
        context.ai, context.hint_model, frame, level, ai_hints(problem), problem.problem_text, problem.leak_strings, persona
    )
