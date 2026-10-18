from dataclasses import dataclass


@dataclass(frozen=True)
class Worksheet:
    worksheet_id: str
    title: str
    problem_count: int


FREE_WORKSHEET = Worksheet(worksheet_id="FREE", title="自由な問題", problem_count=20)
