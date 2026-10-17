import argparse
import json
import os
import sys
import urllib.error
import urllib.request

REQUIRED_ENV = ("API_BASE", "OPERATOR_KEY", "WEB_BASE")


def create_session(api_base: str, operator_key: str, body: dict) -> dict:
    request = urllib.request.Request(
        f"{api_base}/sessions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Operator-Key": operator_key},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser(description="セッションを作り、/device と /log の URL を印字する")
    parser.add_argument("--worksheet", default="WS-01")
    parser.add_argument("--mode", choices=["live", "scripted"], default="live")
    parser.add_argument("--stuck", type=int, default=20)
    parser.add_argument("--cooldown", type=int, default=60)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--label", default="デモ")
    args = parser.parse_args()

    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        print(f"api/.env に {', '.join(missing)} が無い。--env-file .env を付けて実行する", file=sys.stderr)
        return 1
    api_base, operator_key, web_base = (os.environ[name].rstrip("/") for name in REQUIRED_ENV)

    body = {
        "worksheet_id": args.worksheet,
        "mode": args.mode,
        "learner_label": args.label,
        "settings": {"stuck_seconds": args.stuck, "cooldown_seconds": args.cooldown},
    }
    for number in range(1, args.count + 1):
        try:
            created = create_session(api_base, operator_key, body)
        except urllib.error.HTTPError as error:
            print(f"{number} 本目で失敗：{error.code} {error.read().decode()}", file=sys.stderr)
            return 1
        session_id, token = created["session_id"], created["session_token"]
        print(f"{number:2d}  {web_base}/device?s={session_id}&t={token}")
        print(f"    {web_base}/log/{session_id}?k={operator_key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
