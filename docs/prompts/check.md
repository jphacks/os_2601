# 検査

1. root で `pnpm check` を実行する（PowerShell でも 1 行）。
2. `worksheets/` を触っていたら `pnpm check:ws` も実行する（まだ無いと言われたら、`worksheets/schema.json` と見比べて合っているかを確認して報告する）。
3. 赤が出たら、原因のファイルと行を 1 行で言ってから直す。担当外のファイルが原因なら直さず、エラーの文をそのまま出して「高橋に送る」と言う。
4. 緑になったら、変えたファイルの一覧と、`pnpm dev:mock` で確認する URL（例：`http://localhost:3000/device?s=ses_mock&t=tok_mock`）を出す。
