# 検査

1. root で `pnpm check` を実行する（PowerShell でも 1 行）。
2. 赤が出たら、原因のファイルと行を 1 行で言ってから直す。担当外のファイルが原因なら直さず、エラーの文をそのまま出して「高橋に送る」と言う。
3. 緑になったら、変えたファイルの一覧と、`pnpm dev:mock` で確認する URL（例：`http://localhost:3000/device?s=ses_mock&t=tok_mock`）を出す。
