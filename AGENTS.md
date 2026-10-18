# となり（JPHACKS 2026）

答えを言わない、気づく AI 家庭教師。設計の正は `docs/`（00〜12、`tasks/`）。食い違ったら `docs/` と `openapi.yaml` を信じ、直す前に Slack で高橋に言う。この文書は Claude Code（`CLAUDE.md`）と Codex（`AGENTS.md`）で同じ内容。

## 構成

- `api/` FastAPI（Python 3.12、uv）。起動: `uv run --directory api --env-file .env uvicorn app.main:app --reload --port 8000`
- `web/` Next.js（pnpm ワークスペース）。root で `pnpm dev:mock`（モック）/ `pnpm dev`（本物の API）。検査: `pnpm check`
- `web/lib/` カメラ・動きスコア・音声・音声認識・API・ループ（`loop.ts`）。画面はこれを呼ぶだけ
- 問題は学習者の紙の問題（初見）。ワークシートは使わない（ADR 0026）
- `openapi.yaml` 契約。変える PR には、理由と壊れる画面を書く

## 役割（root の `.role.local` に 1 語：`b` `c` `d` `takahashi`）

10/17 から担当フォルダの線引きは無い（ADR 0030）。誰でも `api/` `web/lib/` `openapi.yaml` を含めて全部触れる。

- 高橋だけが変えるのは、ハーネスと依存のファイル：`.github/` `.githooks/` `.claude/` `team.json` `package.json` `web/package.json` `pnpm-lock.yaml` `pnpm-workspace.yaml` `CLAUDE.md` `AGENTS.md`。git のフックと CI が止める
- `main` には PR で入れ、高橋がレビューしてマージする。CI（`pnpm check` と `pytest`）が緑でない PR は見ない
- 人が今触っているファイルを変えるときは、先に Slack で言う（衝突を避けるため）。頼まれていないファイルを AI が「ついでに直しました」と言ったら戻す
- コミットが止まったら、止まった理由のファイルを `git restore --staged <file>` で外す

## 進め方（手順の型は `docs/prompts/`。Claude Code は同名のスラッシュコマンド）

- `docs/prompts/start.md`（`/start`）カードを読んで、最初に作る 1 部品を決める
- `docs/prompts/check.md`（`/check`）`pnpm check` を回して赤を直す
- `docs/prompts/pr.md`（`/pr`）検査 → コミット → push → PR 作成まで
- `docs/prompts/sync.md`（`/sync`）`main` の最新を自分のブランチに取り込む

1 回の依頼は 1 部品か 1 ファイル。PR は 1 画面ずつ。ブランチ名は `b/…` `c/…` `d/…`。`main` への直接 push・force push・`reset --hard`・`--amend`・依存の追加は禁止（フックが止める）。

## 守ること（web）

- 仕様の文言と色は `docs/06` の表のとおり。自分で文章を作らない
- カメラ・動きスコア・音声・API は `web/lib` の関数を呼ぶだけ。`web/app` に `getUserMedia`・`canvas`・`speechSynthesis`・`SpeechRecognition`・`fetch`・`setInterval` を書かない
- 映像を表示するのは `/device` の映像枠だけ。`localStorage`・`sessionStorage` に映像・フレーム・トークン・鍵を保存しない
- `dangerouslySetInnerHTML`、外部スクリプト・フォント・CDN、`next/font/google` は使わない。ブラウザの機能を使うファイルは `"use client"`、`useSearchParams` は `<Suspense>` で包む
- 字幕は `display` をそのまま出す。`speech` は表示しない
- 正答・`leak_strings`・`typical_mistakes`・`fixed_hints` は画面にもモックにも出さない

## 守ること（api）

- 全ルート `async def`、1 ワーカー、状態はメモリ、JSON ファイルは tmp → rename
- 正答・固定ヒントの表・`leak_strings` はどの応答にも入れない。`session_token` は作成応答だけ
- 生成 AI（Gemini）の呼び出しは `hints.py` と `check.py` だけ。タイムアウト 8 秒、リトライなし。正誤の読み上げ文は AI に作らせない

## 言ってはいけない主張（README・ピッチ・トップページ）

「集中力」「理解度」「絶対に言わない」「学習効果」「正確に読む」「どんな問題でも」「4 段階」「不在を見分ける」。詳細は `docs/01` の「言わないこと」。

## 秘密

`.env`・`api/.env`・`web/.env.local` は読まない、コミットしない、内容を出力しない。鍵は高橋の手元と Railway だけ。
