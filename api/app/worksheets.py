import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_WORKSHEETS_DIR = Path(__file__).resolve().parents[2] / "worksheets"
SCHEMA_FILE_NAME = "schema.json"
DEFAULT_CHECK_CORRECT = "正解。その調子"
DEFAULT_CHECK_INCORRECT = "もう一回、途中の式を見てみて"
PRINT_LAYOUT = {
    "paper": "A4",
    "id_font_px": 48,
    "gap_mm": 45,
    "footer": "となり：手元だけを見ます。顔は映しません。映像は保存しません",
}


@dataclass(frozen=True)
class WorksheetProblem:
    problem_no: int
    text: str
    answer: str
    leak_strings: list[str]
    typical_mistakes: list[str]
    fixed_hints: dict[str, str]
    fixed_check_correct: str
    fixed_check_incorrect: str


@dataclass(frozen=True)
class Worksheet:
    worksheet_id: str
    title: str
    grade: str
    problems: list[WorksheetProblem]

    def problem(self, problem_no: int) -> WorksheetProblem:
        return self.problems[problem_no - 1]


def _parse_problem(raw: dict) -> WorksheetProblem:
    return WorksheetProblem(
        problem_no=raw["problem_no"],
        text=raw["text"],
        answer=raw["answer"],
        leak_strings=raw["leak_strings"],
        typical_mistakes=raw["typical_mistakes"],
        fixed_hints=raw["fixed_hints"],
        fixed_check_correct=raw.get("fixed_check_correct", DEFAULT_CHECK_CORRECT),
        fixed_check_incorrect=raw.get("fixed_check_incorrect", DEFAULT_CHECK_INCORRECT),
    )


def load_worksheets(directory: Path | None = None) -> dict[str, Worksheet]:
    directory = directory or Path(os.environ.get("WORKSHEETS_DIR", DEFAULT_WORKSHEETS_DIR))
    worksheets: dict[str, Worksheet] = {}
    for path in sorted(directory.glob("*.json")):
        if path.name == SCHEMA_FILE_NAME:
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not raw.get("problems"):
            logger.warning("%s には problems が無いので読み飛ばす", path.name)
            continue
        problems = sorted((_parse_problem(problem) for problem in raw["problems"]), key=lambda p: p.problem_no)
        worksheets[raw["worksheet_id"]] = Worksheet(raw["worksheet_id"], raw["title"], raw["grade"], problems)
    return worksheets
