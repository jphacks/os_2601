from dataclasses import dataclass

PRINT_LAYOUT = {
    "paper": "A4",
    "id_font_px": 48,
    "gap_mm": 45,
    "footer": "となり：手元だけを見ます。顔は映しません。映像は保存しません",
}


@dataclass(frozen=True)
class Worksheet:
    worksheet_id: str
    title: str
    grade: str
    problem_count: int


FREE_WORKSHEET = Worksheet(worksheet_id="FREE", title="自由な問題", grade="", problem_count=20)
