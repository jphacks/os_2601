import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.leak import contains_leak, leak_strings
from app.reading import to_reading

CASES = Path(__file__).resolve().parents[1] / "tests" / "leak_cases.json"


def main() -> int:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    missed: list[dict] = []
    false_alarms: list[dict] = []
    for case in cases:
        strings = leak_strings(case["answer"], case["key_values"])
        blocked = contains_leak(to_reading(case["hint"]), strings)
        if case["leak"] and not blocked:
            missed.append(case)
        if not case["leak"] and blocked:
            false_alarms.append(case)
    should_block = sum(case["leak"] for case in cases)
    print(f"{len(cases)} 件：止めるべき {should_block} 件のうち見逃し {len(missed)}、通すべき {len(cases) - should_block} 件のうち誤検知 {len(false_alarms)}")
    for case in missed:
        print(f"  見逃し：{case['answer']} / {case['hint']}")
    for case in false_alarms:
        print(f"  誤検知：{case['answer']} / {case['hint']}")
    return 1 if missed or false_alarms else 0


if __name__ == "__main__":
    sys.exit(main())
