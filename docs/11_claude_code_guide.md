# 11 非開発者向け AI 開発ガイド（Claude Code / Codex）

B・C・D 向け。読めば「バックエンドと `web/lib` を壊さずに、AI と一緒に画面やデータを作れる」状態になるための手引き。10/17 から担当フォルダの線引きは無い（ADR 0030）。Claude Code でも Codex でも同じ。

## ハーネス（リポジトリに入っている仕組み。`tonari/harness/` を当日コピー）

| 何 | どう守るか | 誰に効くか |
|---|---|---|
| `AGENTS.md` / `CLAUDE.md` | AI が最初に読む決まり（担当、禁止、守ること）。中身は同じ | Codex / Claude Code |
| `.role.local` | root に自分の役割を 1 語（`b` `c` `d` `takahashi`）。git には入れない | 全員 |
| `.githooks/`（`pre-commit` `pre-push`） | ハーネスと依存のファイルを含むコミット（高橋以外）、`main` への push、force push を止める。`git config core.hooksPath .githooks` で有効化 | 全員（どのツールでも） |
| CI（`.github/workflows/check.yml`） | `pnpm check`、API の `pytest`、PR がハーネスと依存のファイルを変えていないかの検査（`team.json` で作者を見る） | 全員 |
| `docs/prompts/`（`start` `check` `pr` `sync`） | 手順の型。Codex はファイルの中身を貼る。Claude Code は `/start` `/check` `/pr` `/sync` | 全員 |
| `.claude/settings.json` | 編集前・コマンド前に同じ guard を走らせて早めに止める。`pnpm` と `git` の確認を減らす許可リスト。`.env` を読まない | Claude Code だけ |
| `.github/pull_request_template.md` | PR に書く項目（役割、確認したこと、スクリーンショット、AI に頼んだ文） | 全員 |

予行で 1 回だけやる設定（root で、1 行ずつ）：`echo b > .role.local`（自分の役割）、`git config core.hooksPath .githooks`。止まったら「[となり guard]」の文を読む。止められたファイルは `git restore --staged <file>` で外す。

## 触ってよいもの（10/17 から、ADR 0030）

誰でも全部触れる。ただし次の 2 つは守る。

- ハーネスと依存のファイル（`.github/` `.githooks/` `.claude/` `team.json` `package.json` `web/package.json` `pnpm-lock.yaml` `pnpm-workspace.yaml` `CLAUDE.md` `AGENTS.md`）は高橋だけ。変えたいことは Slack で頼む
- 人が今触っているファイル（`api/` と `web/lib/` は高橋が触っていることが多い）を変えるときは、先に Slack で言う

主な持ち場は今までどおり（B は `/device`・`/ops`、C は `/log`・README・人格、D はトップページ・ピッチ・動画）。

## Windows の人へ（B・C・D）

- 入れるもの：**Git for Windows**（git のフックもこれで動く）、Node（pnpm は `corepack enable`。落ちたら `npm i -g pnpm@<リポジトリの packageManager と同じ版>`）、Python（`uv`）、Claude Code（公式の Windows 版）か Codex CLI（どちらでもよい。両方は要らない）。ターミナルは PowerShell でよい。WSL は要らない。`git config --global core.longpaths true` を 1 回打つ。
- clone したら最初に **`pnpm install`**。それから `pnpm dev:mock`。
- **PowerShell 5.1 では `&&` が使えない。** コマンドは 1 行に 1 つ打つ。検査はリポジトリの root で `pnpm check`（typecheck・lint・build を 1 本にしたスクリプト）、ワークシートは `pnpm check:ws`。`cd web` は要らない（root の `package.json` が委譲する）。
- **2 回目以降の PR**：マージされたら `git switch main` → `git pull` → `git switch -c b/次の名前`（ブランチ名は B が `b/`、C が `c/`、D が `d/` で始める）。高橋が `main` に何かを入れたと言ったら、1 行ずつ `git switch main` → `git pull` → `git switch b/<自分のブランチ>` → `git merge main`（`main` を更新せずに merge しても何も入らない）。
- **依存パッケージを足さない。** `pnpm add` が必要だと思ったら Slack で高橋に。`pnpm-lock.yaml` の衝突を防ぐため。
- import のファイル名は大文字小文字まで一致させる（Windows と Mac では通っても、CI と Vercel の Linux で落ちる）。CI が赤ならその PR は見てもらえない。
- 秘密鍵（`OPENAI_API_KEY`・`OPERATOR_KEY`）は一切持たない。オペレータキーが要る確認（`/ops` を本物の API で）は高橋がやる。
- スマホで自分の画面を見るには `cloudflared tunnel --url http://localhost:3000`（アカウント不要。HTTPS の一時 URL が出る）。Vercel のプレビュー URL は、GitHub 連携が入っていれば PR のコメントに自動で付く。付かなければ cloudflared を使う。
- `.env.local` は `copy web\.env.example web\.env.local` で作る（モックで動く。本物の API につなぐときは `NEXT_PUBLIC_API_BASE` を高橋が貼った URL にして `pnpm dev`）。
- `NEXT_PUBLIC_MOCK=1 pnpm dev` の書き方は PowerShell では動かない。`pnpm dev:mock` を使う（`package.json` に `cross-env` で用意してある）。
- 改行は `.gitattributes` で LF に固定してある。「ファイル全体が差分になる」ときは Claude Code に「改行を LF に直して」と頼む。
- パスは `/` で書く。`\` を含むパスを Claude Code が生成したら直させる。
- カメラと音声の確認は Chrome の `localhost` で動く。スマホで見るときは Vercel のプレビュー URL。
- 画面録画は Win + G（ゲームバー）で足りる。提出用の動画は高橋の Mac で撮る。
- 連係カメラは Mac 専用。Windows でカメラを真上に置いて試すなら、スマホを Vercel の URL で開くほうが早い。

## 作業の型

始めは `docs/prompts/start.md`（Claude Code なら `/start`）、検査は `check.md`（`/check`）、PR は `pr.md`（`/pr`）、`main` の取り込みは `sync.md`（`/sync`）。Codex ではファイルを開いて中身をそのまま貼る。下は、その間の「作る」依頼の型。

1. **読ませる**：Claude Code に、作るものの仕様（`docs/03_api_contract.md` の該当節、`docs/06_voice_and_device.md` または `docs/07_fixtures.md`、`web/mocks/` のサンプル JSON）を読ませる。
   - 例（B）：「`docs/06_voice_and_device.md` の『状態と表示』の表と `web/mocks/signals_stuck.json` を読んで、状態バッジのコンポーネントを作って。文言と色は表のとおり。`web/lib` の関数は呼ぶだけで、中を変えないで」
   - 例（C）：「`docs/07_fixtures.md` の WS-02 の表を読んで、`worksheets/ws02.json` を `schema.json` に合う形で書いて。`leak_strings` は半角・空白なしで」
   - 例（B、`/ops`）：「`docs/03_api_contract.md` の `POST /sessions` と `POST /demo/reset` を読んで、`web/app/ops/page.tsx` にセッション作成フォーム（ワークシート・モード・stuck_seconds・cooldown_seconds）、リセットボタン、強制 stuck ボタンを作って。API は `web/lib/api.ts` の関数を呼ぶだけ。`X-Operator-Key` は入力欄から取り、保存しないで」
   - 例（D、トップページ）：「`README.md` の先頭と `docs/01_product_spec.md` の『一言で』『解き方』を読んで、`web/app/page.tsx` に製品紹介（一言、仕組み 3 点、`/device` と `/log` へのリンク、README へのリンク）を作って。外部のフォントやスクリプトは読み込まないで」
2. **小さく作らせる**：1 回の依頼は 1 画面か 1 部品、または 1 ファイルまで。
3. **ブラウザで確認する**：`pnpm dev:mock` で起動し、モックで見る。カメラと音声は PC の Chrome で `localhost` なら動く。スマホでの確認は Vercel のプレビュー URL で（`http://<PCのIP>:3000` ではカメラが取れない）。
4. **検査を通す**：root で `pnpm check`（web）、`pnpm check:ws`（worksheets）。赤が出たら Claude Code に貼って直させる。
5. **ブランチにコミットして PR**：
   ```
   git switch -c b/device-badge
   git add web/app/device
   git commit -m "device: 状態バッジと字幕"
   git push -u origin b/device-badge
   ```
   GitHub で PR を作り、高橋にレビューを頼む。1 PR 1 画面。

## やってはいけないこと

- `git push --force`、`main` への直接 push、他人のブランチへの push。
- `.env`・API キー・オペレータキー・`session_token` をコードやコミットに書く。
- 頼んでいないファイルを AI に直させる（AI が「ついでに直しました」と言ったら戻す）。
- API の形（`openapi.yaml`）を、理由と壊れる画面を PR に書かずに変える。
- **カメラのフレームを `web/lib` を通さずにどこかへ送る**コードを書く（映像の扱いは 1 箇所に閉じる）。
- **正答や `leak_strings` を画面に出す**コードを書く（API からは来ないはずだが、モックに混ぜない）。
- 「全部作って」「いい感じにして」と頼む。

## プライバシーの約束（画面を作る人）

これは「設計の芯」の一部。AI が生成したコードでも必ず守る。

- 映像を表示するのは `/device` の映像枠だけ。`/log` と `/ops` に映像やサムネイルを出さない。
- `canvas` から画像を取り出す処理を `web/app` 配下に書かない。すべて `web/lib/camera.ts` の関数を呼ぶ。
- `localStorage` に映像・フレーム・`session_token` を保存しない。
- `dangerouslySetInnerHTML` を使わない。API から来た文字列はプレーンテキストとして表示する。
- 外部のスクリプト・フォント・CDN を読み込まない。
- 字幕は `display` をそのまま出す。`speech` を表示しない（読み上げ専用）。

## Claude Code に渡すプロンプトの型

```
あなたは web/app/device 配下だけを編集します。web/lib と api と openapi.yaml は読むだけで変更しません。
仕様: docs/06_voice_and_device.md の「状態と表示」「ボタンの動き」
契約: docs/03_api_contract.md の「POST /sessions/{id}/signals」「POST /sessions/{id}/hints」
サンプル: web/mocks/signals_stuck.json、web/mocks/hint_level2.json
作るもの: デバイス画面の状態バッジ・字幕・主ボタン 2 つ（ヒント・できた）
守ること:
- 文言と色は 06 の表のとおり。自分で文章を作らない
- カメラ・動きスコア・音声・API は web/lib の関数を呼ぶだけ
- speaking 中は主ボタンを無効にする
- 映像を canvas から取り出す処理を書かない
- dangerouslySetInnerHTML と外部スクリプトを使わない
終わったら pnpm check を通して、変更したファイル一覧を教えてください。
```

## Next.js で Claude Code がよく踏む穴（B・C・D）

- ブラウザの機能（カメラ・音声・`useSearchParams`・`useEffect`）を使うファイルは先頭に `"use client"` が要る。無いと `pnpm check` の build で落ちる。
- `useSearchParams()` を使うページは `<Suspense>` で包まないと build で落ちる。Claude Code に「Suspense で包んで」と言えば直る。
- `pnpm check` は `next build` まで回す。「dev では動くのに build で落ちる」はここで気づく。赤を Claude Code に貼る。
- `/sheets/[id]` のように URL に ID が入るページは `web/app/sheets/[id]/page.tsx`（フォルダ名が `[id]`）。
- 画像・フォント・スクリプトを外部から読まない。`next/font/google` も使わない（会場の回線とプライバシーのため）。

## 当日リポジトリの AGENTS.md / CLAUDE.md

正本は `tonari/harness/AGENTS.md`（`CLAUDE.md` は同じ中身）。当日そのまま入れる。下は 10/15 の下書きで、食い違ったら `harness/` を信じる。

```markdown
# となり（JPHACKS 2026）

答えを言わない、気づく AI 家庭教師。設計は docs/ を正とする。

## 構成
- api/        FastAPI（Python 3.12、uv）。起動: uv run --directory api uvicorn app.main:app --reload
- web/        Next.js（pnpm）。root で pnpm dev:mock（モック）/ pnpm dev（本物の API）。検査: pnpm check
- worksheets/ ワークシート定義。検証: pnpm check:ws
- web/lib/loop.ts 1 秒ごとの送信・自動ヒント・声のトリガー。画面はこれを呼ぶだけ
- openapi.yaml 契約。変更は高橋のみ

## 担当フォルダ（これ以外は編集しない）
- 高橋: api/（api/tools/ を含む） web/lib/ openapi.yaml worksheets/schema.json
- B: web/app/device/ web/app/ops/
- C: web/app/log/ web/app/sheets/ worksheets/*.json README.md
- D: web/app/page.tsx docs/pitch/ docs/video/

## ルール
- ブランチで作業し PR を出す。main への直接 push は高橋のみ
- git push --force 禁止。.env と鍵をコミットしない
- API の形を変えたいときは CONTRACT_REQUESTS.md に書く
- PR 前に pnpm check（web）、pnpm check:ws（worksheets）。依存の追加は高橋のみ

## プライバシー規則（web）
- 映像の取り出しは web/lib/camera.ts だけ。web/app に canvas 処理を書かない
- 映像を表示するのは /device の映像枠だけ
- localStorage に映像・フレーム・トークンを保存しない
- dangerouslySetInnerHTML と外部スクリプト・フォント・CDN 禁止

## 正答の扱い
- 正答・leak_strings・固定ヒントはサーバだけが読む。API で返さない。モックにも入れない

## 言ってはいけない主張（README・ピッチ）
- 「集中力を測る」「答えを絶対に言わない」「学習効果がある」→ docs/01 を参照
```

## 困ったときの切り分け

| 症状 | まず見るところ |
|---|---|
| 画面が真っ白 | ブラウザのコンソール（赤いエラー）を Claude Code に貼る |
| カメラが映らない | HTTPS か `localhost` か。他のタブがカメラを使っていないか。アプリ内ブラウザでないか。許可を拒否していないか（アドレスバーのカメラアイコン） |
| 音が出ない | 「はじめる」を押したか（押さないと鳴らない）。iPhone のサイレントスイッチ。音量。字幕は出ているか（出ていれば API は正常） |
| API が 401 / 403 | 認可ヘッダの系統（02 の表）。デバイスは `session_token`、記録画面は `X-Operator-Key` |
| CORS エラー | `localhost:3000`・Vercel・`trycloudflare.com` 以外から開いていないか（高橋に連絡） |
| 20 秒止めても「考え中？」にならない | `?debug=1` で動きスコアを見る。τ より上なら照明・手ぶれ・紙の揺れ。`camera_ok` が false なら映像が止まっている |
| 型エラー | `web/lib/api.ts` の型が正。`git merge main` で最新にしてから Claude Code に赤を貼る |
| `validate_worksheets.py` が赤 | 全角文字・空白・段階の欠け・問題文に正答。メッセージの行番号を見る |

## 10/16 夜の予行でやること（60 分。進行は D）

1. 使い捨てリポジトリを clone、`pnpm install`、`pnpm dev:mock`、`localhost:3000` のスクリーンショットを Slack に。
2. ブランチを切る、ファイルを 1 つ変える、`pnpm check`、PR を出す、マージ、`git switch main`、`git pull`。
3. 当日の自分の最初の一歩（`tasks/<自分>.md` の Day 1 最初のカード）を 1 行で言えるようにする。
