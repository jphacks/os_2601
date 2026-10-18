# 高橋のタスク

> Hack Day（10/17・18）の当日に使ったカード。その後の変更（ワークシートの廃止 ADR 0026、契約の改名 ADR 0040 など）は反映していない。今の契約は `openapi.yaml` と `docs/03`、今の進め方は `AGENTS.md`。

順番どおりにやる。各カードは「完了条件」を満たしたら次へ。カードの「Claude Code に渡す文」はそのまま貼ってよい。時間割の正は `docs/10`。

## 共通の約束

- 契約（`openapi.yaml`）は今夜書いたものが正。当日 Pydantic から再生成しない。FastAPI 側を契約に合わせる。
- `web/lib` の関数名・引数・戻り値は今夜決めたものを変えない（B・C がそれを呼んで作る）。
- 今夜書くコードは「型と空実装」まで。`fetch` を呼ぶ本物は `api.ts` の非モック経路だけ。`loop.ts` と `voice.ts` の本物は Day 1。
- 縦串（T1-3）が通るまで、GPT・答え漏れ検査・正誤・声のトリガー・記録画面の作り込みに手を出さない。
- Day 2 12:30 以降、撮影中はデプロイしない。

## 今夜（10/16）の順番

> **10/17 朝**：昨夜の T0 は未実施。当日の時刻は `docs/10` の「10/17 朝の改訂」の表が正。下の時刻は 1 時間前後ずれる。

| 順 | カード | 分 | 備考 |
|---|---|---|---|
| 1 | T0-6 使い捨てリポジトリ（予行の土台） | 30 | 最初にやる。終わったら Slack に「予行の案内」と開始時刻を貼る |
| 2 | T0-1 契約・モック・空実装 | 90 | 3 回に分けて Claude Code に渡す |
| 3 | T0-2 本番 iPhone の検証 | 45 | probe は使い捨てリポジトリの `web/public/probe.html` に置いて Vercel で配る |
| 4 | T0-3 OpenAI 疎通 | 20 | scratch の Python 1 本 |
| 5 | T0-4 Railway に hello | 30 | 使い捨てリポジトリの `api/` を当日と同じ設定で |
| 6 | T0-5 連係カメラ | 10 | USB 接続で試す |
| 7 | T0-7 初期化メモと RUNBOOK の骨子 | 30 | 文書なので今夜でよい |
| 並行 | 予行（D が進行、高橋は詰まった人だけ） | 60 | T0-6 の直後に開始 |

合計 約 4 時間 15 分＋予行の割り込み。

### T0-6 使い捨てリポジトリ（30 分。最初にやる）

- GitHub に個人の使い捨てリポジトリ（公開でよい）を作り、B・C・D を collaborator に招待する。
- **pnpm ワークスペース**にする（root の `pnpm install` 1 回で web の依存が入らないと、予行の `pnpm dev:mock` も CI も落ちる）：root に `pnpm-workspace.yaml`（`packages: ["web"]`）、ロックファイルは root の 1 本、`cross-env` は `web` の devDependencies。
- `web/` に `create-next-app`（App Router、TypeScript、Tailwind、`src/` なし、import alias `@/*`）。`web/package.json` の `scripts`：`dev`、`dev:mock`（`cross-env NEXT_PUBLIC_MOCK=1 next dev`）、`check`（`eslint . && tsc --noEmit && next build`。`next lint` は Next.js 16 で無くなったので使わない。pnpm のスクリプトは Windows でも cmd.exe で動くので `&&` でよい）。
- root の `package.json`：`dev`・`dev:mock`・`check` は `pnpm --filter web <同名>`、`check:ws` は `uv run --directory api tools/validate_worksheets.py && uv run --directory api tools/leak_selftest.py`。`packageManager` と `engines` で Node・pnpm を固定、`.gitattributes`（`* text=auto eol=lf`）、`.editorconfig`、`.gitignore` に `api/data/` と `.env*`（`.env.example` は除く）。
- `.github/workflows/check.yml`：PR ごとに `pnpm install --frozen-lockfile` と `pnpm check` **だけ**（`check:ws` と `pytest` は T1-4 で足す。朝から赤にしない）。`.github/workflows/` を含む push は `env -u GH_TOKEN git push`。
- `web/.env.example`：`NEXT_PUBLIC_API_BASE=http://localhost:8000`、`NEXT_PUBLIC_MOCK=1`。`web/public/probe.html` の置き場も作る（T0-2）。`api/` と `worksheets/.gitkeep` も作る（T0-4 で hello を置く）。
- **ハーネスを入れる**：`tonari/harness/` の中身（`AGENTS.md` `CLAUDE.md` `.githooks/` `.claude/` `.github/` `docs/prompts/` `team.json`）を root にコピー。`.gitignore` に `.role.local` を足す。`team.json` の B・C・D の GitHub ログインを埋める（collaborators: kanon-k4 / NakanishiSyosuke / SawaiKoshi / 1610kuishinbou-ops のどれが誰か Slack で聞く）。`.github/workflows/check.yml` は harness のものを使う（`pnpm check` と担当の検査。`check:ws` と `pytest` は T1-4 で足す）。自分は `echo takahashi > .role.local` と `git config core.hooksPath .githooks`。
- Vercel（Root Directory `web`、Production の環境変数 `NEXT_PUBLIC_API_BASE`、Preview の環境変数 `NEXT_PUBLIC_MOCK=1`）と Railway（Root Directory 空、`RAILWAY_DOCKERFILE_PATH=api/Dockerfile`）を**当日と同じ設定で**このリポジトリにつなぐ。T1-1 は「本番リポジトリにつなぎ直す」だけになる。
- Slack に「予行の案内」を 1 ブロックで貼る：開始時刻、画面共有の場所、リポジトリの URL、チャンネル、Git for Windows・Node（版）・pnpm（版）・uv・Claude Code の入手先、`copy web\.env.example web\.env.local`、`echo <役割> > .role.local`、`git config core.hooksPath .githooks`、PR は自分でマージしてよい、ブランチ名は `b/` `c/` `d/`、Claude Code でも Codex でもよい（手順は `docs/prompts/`）。T0-2 の検証ページの URL も後で同じスレッドに貼る。
- 予行の進行は D。高橋は詰まった人だけ見る。
- 完了条件：3 人全員から `localhost:3000` のスクリーンショットが Slack に貼られる。

### T0-1 契約と見本（90 分。3 回に分けて渡す）

- 作るもの：`tonari/openapi.yaml`、`tonari/web/mocks/*.json`（23 本）、`tonari/worksheets/schema.json`、`tonari/worksheets/ws01.json`、`tonari/web/lib/` の型と空実装（6 ファイル）。すべて当日のリポジトリにそのままコピーする（文書と見本であり、審査対象のコードではない）。
- `web/lib` の関数（固定。引数と戻り値は `docs/06` の「web/lib の関数」の表）：
  - `camera.ts`：`startCamera(video: HTMLVideoElement): Promise<void>`、`captureFrame(): Promise<Blob>`、`stopCamera(): void`
  - `motion.ts`：`startMotionLoop(video, onScore: (score: number | null, brightness: number, cameraOk: boolean) => void): () => void`（`null` はウォームアップ中）
  - `speech.ts`：`unlockSpeech(): void`、`speak(text: string): Promise<void>`
  - `voice.ts`：`startListening(onHeard: (text: string) => void): () => void`、`stopListening(): void`（「わからない」の聞き取り。本物は T1-5）
  - `loop.ts`：`startSession(video, sessionId, token, handlers: {onState, onHint, onBrightness, onConnection, onHeard}): () => void`、`requestManualHint(): Promise<HintResponse>`、`requestCheck(): Promise<CheckResponse>`、`advance(): Promise<AdvanceResponse>`、`end(): Promise<void>`
  - `api.ts`：`createSession(body, operatorKey)`、`listSessions(operatorKey)`、`getSession(id, auth)`、`patchSettings(id, token, body)`、`postSignal(id, auth, body)`、`postFrame(id, token, blob)`、`requestHint(id, token, body)`、`postCheck(id, token, body)`、`postAdvance(id, token)`、`postEnd(id, token)`、`demoReset(operatorKey)`。`auth` は `{token}` か `{operatorKey}`
- 1 回目（openapi.yaml）：

```
tonari/docs/03_api_contract.md を読んで、tonari/openapi.yaml を書いてください。
- 入れるのは 03 の「エンドポイント一覧」の 14 本だけ。SSE と quiet は入れない。
- components/schemas の名前は SessionCreateRequest, SessionCreated, SessionList, SessionDetail, SettingsPatch, SignalRequest, SignalResponse, FrameReceived, HintRequest, HintResponse, CheckRequest, CheckResponse, AdvanceResponse, EndResponse, WorksheetList, WorksheetDetail, DemoReset, Health, Error。
- 03 の JSON 例を各応答の example にそのまま入れる。hints の level は 1 か 2 だけ。trigger は "auto" | "manual" | "voice"。source は "gpt" | "fallback" | "scripted"。leak_check は {ok, fallback} の 2 つ。settings は stuck_seconds（5〜1200、既定 20）、cooldown_seconds（0〜300、既定 60）、max_level（1〜2、既定 2）の 3 つ。
- 正答・leak_strings・典型ミスの一覧・固定ヒントの表はどのスキーマにも入れない。
- 認可は 03 の「共通事項」のとおり（Bearer session_token、X-Operator-Key）。signals は force_stuck: true のときだけ X-Operator-Key でも通るので security に両方を書く。
- 各エンドポイントが 409 を返す状態を 03 のとおり description に書く。signals の応答の next_action は stuck の間ずっと返す、と description に書く。
```

- 自分で通読してから 2 回目（モックとワークシート）：

```
tonari/openapi.yaml の example から tonari/web/mocks/ に JSON を 23 本作ってください（docs/03 の「フロントのモック」の表のとおり）：session_created.json（session_id は ses_mock、session_token は tok_mock）、sessions_list.json（ses_mock と ses_mock_ended の 2 件）、session_active.json（ses_mock。問 2 に source: gpt の H2 と、source: fallback・leak_check {ok:false, fallback:true} の H2 を 1 件ずつ、leak_blocked_count: 1）、session_ended.json（ses_mock_ended。問 3 は skipped）、signals_watching.json、signals_still.json、signals_stuck.json（next_action が send_frame_and_request_hint）、signals_speaking.json、signals_cooldown.json、signals_ended.json、frame_received.json（frm_mock）、hint_level1.json（hnt_mock_1、source fallback）、hint_level2.json（hnt_mock_2、source gpt、model gpt-6.1-sol）、hint_fallback.json（level 2、source fallback、leak_check {ok:false, fallback:true}、model なし）、check_correct.json、check_incorrect.json、check_unreadable.json、advance.json、advance_ended.json、end.json、worksheets.json、worksheet_ws01.json、demo_reset.json。answer・leak_strings・typical_mistakes・fixed_hints は入れない。
次に tonari/worksheets/schema.json と tonari/worksheets/ws01.json を docs/07_fixtures.md のとおりに書いてください。ファイル最上位は {worksheet_id, title, grade, problems}。print は JSON に入れない（サーバの定数）。fixed_hints は "1" と "2" が必須で "3" "4" は任意。fixed_check_correct と fixed_check_incorrect は任意（無ければサーバの既定文「正解。その調子」「もう一回、途中の式を見てみて」）。ws01.json には 4 問とも書く：問 1「正解。移項の符号、ばっちり」「もう一回、5 を移した後の符号を見てみて」、問 2「正解。符号の直し方、ばっちり」「もう一回、2 行目の符号を見てみて」、問 3「正解。かっこの外し方、ばっちり」「もう一回、かっこの中の 2 つ目を見てみて」、問 4「正解。3 のかけ方、ばっちり」「もう一回、2 にも 3 をかけたか見てみて」。leak_strings は 07 の表のとおり（3 文字未満なし）。
```

- 3 回目（`web/lib` の空実装）：

```
tonari/web/lib/ に camera.ts、motion.ts、speech.ts、voice.ts、api.ts、loop.ts の型と空実装を書いてください。関数名・引数・戻り値は docs/06_voice_and_device.md の「web/lib の関数」の表のとおり（startCamera(video): Promise<void> / captureFrame(): Promise<Blob> / stopCamera(): void / startMotionLoop(video, onScore(score: number|null, brightness: number, cameraOk: boolean)): () => void / unlockSpeech(): void / speak(text): Promise<void> / startListening(onHeard(text)): () => void / stopListening(): void / startSession(video, sessionId, token, handlers{onState, onHint, onBrightness, onConnection, onHeard}): () => void / requestManualHint(): Promise<HintResponse> / requestCheck(): Promise<CheckResponse> / advance(): Promise<AdvanceResponse> / end(): Promise<void>）。
- api.ts は openapi.yaml の components/schemas と同名の型（SessionCreated, SessionList, SessionDetail, SignalResponse, HintResponse, CheckResponse, AdvanceResponse, EndResponse, WorksheetList, WorksheetDetail …）を export し、関数は createSession(body, operatorKey)、listSessions(operatorKey)、getSession(id, auth)、patchSettings(id, token, body)、postSignal(id, auth, body)、postFrame(id, token, blob)、requestHint(id, token, body)、postCheck(id, token, body)、postAdvance(id, token)、postEnd(id, token)、getWorksheets()、getWorksheet(id)、demoReset(operatorKey)。auth は {token} か {operatorKey}。NEXT_PUBLIC_MOCK=1 なら web/mocks の JSON を docs/03 の「フロントのモック」の表のとおりに返し（postSignal は呼ばれた回数で 5 秒ごとに 5 状態を一巡、requestHint は 1 回目 level1 で 2 回目以降 level2、getSession は id が ses_mock_ended なら session_ended、postAdvance は 4 回目から advance_ended、postEnd か advance_ended の後の postSignal は signals_ended、patchSettings は渡した値をそのまま返す）、そうでなければ NEXT_PUBLIC_API_BASE に fetch する。ヘッダは openapi.yaml のとおり。エラーは ApiError(status, code) を throw。
- 空実装の中身：startCamera は video に getUserMedia({video: {facingMode: "environment"}}) の映像を流す（これだけ本物。拒否されたら name が CameraDenied の Error を throw）、captureFrame は video が無くても必ず 1x1 の JPEG Blob を返す、startMotionLoop は 1 秒ごとに 0.2 と輝度 120 と true を返す、unlockSpeech と speak と startListening と stopListening は console.log だけ、loop.ts の startSession はタイマーだけで 5 秒ごとに onState を web/mocks の signals_watching → still → stuck → speaking → cooldown の順に一巡させ（api.ts は呼ばない）、stuck のときに onHint に hint_level1.json を 1 回渡して speak を呼ぶ。onBrightness は 120 固定、onConnection は true を 1 回、onHeard は呼ばない。requestManualHint は hint_level2.json、requestCheck は check_correct.json、advance は advance.json、end は何もしない。戻り値の止める関数でタイマーを止める。
```

- 完了条件：`openapi.yaml` を目で通読して 03 と矛盾がない。モックの JSON に `answer`・`leak_strings`・`typical_mistakes`・`fixed_hints` が入っていない。`web/lib` の 6 ファイルが使い捨てリポジトリで `pnpm check` を通る。`pnpm dev:mock` で `startSession` を呼ぶと 5 秒ごとに `onState` の `state` が変わり、`stuck` で `onHint` が 1 回だけ呼ばれる。

### T0-2 本番 iPhone の検証（45 分）

- 作るもの：使い捨てリポジトリの `web/public/probe.html` 1 枚（本番には入れない）。背面カメラを `getUserMedia({video:{facingMode:"environment"}})` で表示、`canvas` で 1 秒ごとのフレーム差分スコアと平均輝度を画面に出す、ボタン 1 回で `speechSynthesis` を解錠（無音の `speak`）し、その後 20 秒無操作で「今、何を求めようとしてる？」を自動で鳴らす、`webkitSpeechRecognition`（`lang: ja-JP`、`continuous`）で聞き取った文字をそのまま表示する、`navigator.wakeLock.request("screen")` を試す。
- Vercel のプレビュー URL で本番 iPhone から開き、結果を `docs/12` の要確認の表に書く：音が鳴るか、サイレントスイッチ ON で鳴るか、自動ロックで止まるか、`wakeLock` が効くか、手を止めたときと書いているときのスコア（τ の目安）、音声認識が動くか（iOS Safari は Siri と音声入力が ON でないと動かない。Mac Chrome は動く）。
- **本番 iPhone の設定を「自動ロック：なし」にする。**
- probe の URL を予行の案内のスレッドに貼る（D が Day 1 に使う）。
- 完了条件：20 秒無操作で自動で日本語が鳴る動画を 1 本撮って Slack に貼る。

### T0-3 OpenAI 疎通（20 分）

- `scratch/tonari/probe_gpt.py` 1 本（本番には入れない）。`docs/05` の骨子と同じ呼び方（`client.responses.parse`、`input_image` の base64、`detail: "low"`、`reasoning: {"effort": "low"}`、`text_format=HintOut`、`timeout=8`、`max_retries=0`）で、スマホで撮った手書きの 1 枚を `gpt-6.1-sol` に投げる。所要秒数と、`reasoning` が受理されたかをメモ。4 秒を越えるなら `gpt-6-luna` でも 1 本。
- 月額上限を 10 ドルに設定。
- 完了条件：`HintOut` が返り、`speech` が 40 文字以内。秒数と受理された引数を `docs/12` に書く。

### T0-4 Railway に hello（30 分）

- 使い捨てリポジトリの `api/` に FastAPI の `GET /healthz` と `GET /sessions`（`X-Operator-Key` が無ければ 401 を返すだけ）の hello。`api/pyproject.toml` の依存は fastapi・uvicorn・python-multipart・openai・pydantic・pyyaml・jsonschema、dev に pytest・httpx。`api/Dockerfile` は `COPY api/pyproject.toml api/uv.lock /app/api/` → `RUN uv sync --frozen --no-dev --directory /app/api` → `COPY api/ /app/api/` と `COPY worksheets/ /app/worksheets/` → `CMD uv run --frozen --directory /app/api uvicorn app.main:app --host 0.0.0.0 --port $PORT`（`$PORT` を展開するためシェル形式。JSON 配列形式にしない）。
- Railway：Root Directory は空（ビルド文脈は root）、変数 `RAILWAY_DOCKERFILE_PATH=api/Dockerfile`、Volume なし、**App Sleeping を無効**。環境変数 `CORS_ORIGINS`（Vercel の URL と `http://localhost:3000`）、`CORS_ORIGIN_REGEX`、`OPERATOR_KEY`（`openssl rand -hex 16`。Railway と自分の手元だけ。Slack に貼らない）。
- probe.html から 2 本の `fetch` を打つ：`fetch("https://<railway>/healthz")` と `fetch("https://<railway>/sessions", {headers: {"X-Operator-Key": "x"}})`（401 でよい。プリフライトが通ることの確認。`/healthz` だけでは `allow_headers` の漏れに気づけない）。
- 完了条件：公開 URL で `/healthz` が 200。probe からの 2 本がブラウザのコンソールで CORS エラーなし。

### T0-5 連係カメラ（10 分）

- probe.html を Mac の Chrome で開き、カメラの入力に「iPhone カメラ」が出るか。iPhone はスタンドに固定し、**USB ケーブルで Mac につなぐ**（無線より安定。Mac はテザリング用の別回線につないだ状態で確認する。同じ iPhone をテザリング親機にすると挙動が変わる）。
- 出なければ、ピッチは Mac 内蔵カメラ＋スタンドに切り替え、`docs/08` の機材の節を直す。
- 完了条件：結果（USB か無線か、ロック状態で出るか）を `docs/12` と `docs/08` の機材に書く。

### T0-7 初期化メモと RUNBOOK の骨子（30 分）

- 当日 10:20 に打つコマンドと置くファイルの順を 1 枚に：本番リポジトリに T0-6 の設定一式（ハーネス込み。`team.json` は埋めたもの）と T0-1 の成果物をコピー、`api/tools/create_session.py` の雛形（`uv run --directory api tools/create_session.py --worksheet WS-01 --mode live --stuck 10 --cooldown 0 --count 10` で `/device?s=&t=` と `/log/<id>?k=` の URL を印字。`API_BASE`・`OPERATOR_KEY`・`WEB_BASE` は `api/.env`）、`api/.env.example`（`OPENAI_API_KEY`、`OPERATOR_KEY`、`HINT_MODEL=gpt-6.1-sol`、`CHECK_MODEL=gpt-6-luna`、`CORS_ORIGINS`、`CORS_ORIGIN_REGEX`、`DATA_PATH=./data/tonari.json`、`DEMO_MODE=1`、`WEB_BASE`）、ローカル起動は `uv run --directory api --env-file .env uvicorn app.main:app --reload --port 8000`。
- `RUNBOOK.md` の骨子（文書なので今夜書いてよい）：起動（API・Web）、環境変数の一覧と置き場、デプロイ（Railway・Vercel。GitHub 連携が org で入らなければ `railway up` と `vercel` CLI）、`/demo/reset` の `curl`、セッション作成、退避 L1〜L4 の手順、連係カメラの再接続、Meet のタブ共有（「タブの音声を共有」）、OPERATOR_KEY の変更。
- 完了条件：メモを読めば 10:20〜10:50 に迷わない。RUNBOOK の見出しが全部ある。

## Day 1

### T1-1 10:20-11:15 初期化と読み合わせ

- 手順メモどおり。`jphacks2026/repo/os_2601`（10/16 に clone 済み。中身は JPHACKS のテンプレート README と MIT LICENSE だけ）に T0-6 の設定一式と T0-1 の成果物を入れ、**10:35 に `main` へ push して Slack に「clone していい」と書く**。テンプレート README は消さず、C が中身を埋める。`web/app/page.tsx` はリンク 4 つ（`/device` `/ops` `/log` `/sheets`）だけの 1 ファイルを置く（D が 13:00 に差し替える）。
- Railway（Root Directory 空、`RAILWAY_DOCKERFILE_PATH=api/Dockerfile`）と Vercel（Root Directory `web`）を本番リポジトリにつなぎ直す。GitHub 連携が org で入らなければ Mac から `railway up` と `vercel` CLI でデプロイし、以後 B・C のブランチも高橋が手で打つ。
- Railway の環境変数：`OPERATOR_KEY`、`GEMINI_API_KEY`（10/17 に `OPENAI_API_KEY` から変更、ADR 0025）、`HINT_MODEL`、`CHECK_MODEL`、`CORS_ORIGINS`（`http://localhost:3000` と Vercel の本番 URL）、`CORS_ORIGIN_REGEX`、`DATA_PATH=/app/api/data/tonari.json`、`DEMO_MODE=1`。Vercel の環境変数：Production に `NEXT_PUBLIC_API_BASE`（Railway の URL）、Preview に `NEXT_PUBLIC_MOCK=1`（B・C のプレビューが未完成の API を叩かない）。`OPERATOR_KEY` は Hack Day 後に変える。
- 10:35 の `main` に `web/lib` の 6 ファイル（今夜の版）と `web/.env.example` が入っていること。10:50 から 1 人 3 分ずつ `pnpm dev:mock` の起動を見る。
- 11:00-11:15：D の進行で契約の読み合わせ（`openapi.yaml` を 10 分で説明。B・C に「最初の 1 部品」を言ってもらう）。
- 完了条件：3 人の PC で `/device` の空ページが出る。CI が緑。Railway の `/healthz` と Vercel の `/` が本番リポジトリから出ている。

### T1-2 11:15-13:00 ブラウザの芯（`web/lib`）

- 本物の API は 15:00 まで無いので、検証は `pnpm dev:mock` と本番 iPhone（Vercel のプレビュー URL）で行う。
- 1 本目（camera・motion・speech）：

```
web/lib/camera.ts、motion.ts、speech.ts を実装してください。関数名と型は今の空実装のまま。仕様は docs/06_voice_and_device.md の「開始の手順」「PC（Mac）で iPhone を連係カメラとして使うとき」「音声合成」「フレームの送り方」と docs/04_stuck_detection.md の「ブラウザ側：動きスコア」。
- camera: startCamera(video) は location.search の cam を読む。cam=iphone のときだけ、まず facingMode environment で取得 → enumerateDevices → ラベルに iPhone を含む videoinput があれば一度止めて deviceId で取り直す（許可前はラベルが空なので、この順でないと見つからない）。cam 無しは facingMode environment、1280x720 ideal だけ（L1 の退避で内蔵カメラに戻すため）。video をモジュール変数に保持し、captureFrame はそれを長辺 1024・JPEG 0.7 の Blob にする。stopCamera は全トラックを止める。
- motion: 1 秒ごとに video を 64x36 の canvas に描き、グレースケール（0.299R+0.587G+0.114B）の平均絶対差を 255 で割って 0〜1 に。直近 3 回の生差分の中央値を score にし、最初の 3 回は null。輝度は 64x36 の平均。video.readyState < 2 なら cameraOk=false。onScore(score, brightness, cameraOk) を呼ぶ。
- speech: unlockSpeech は空文字の utterance を 1 回 speak。speak は ja-JP の声を voiceschanged 後に選び、読み上げ中なら cancel してから読み、onend で resolve する。
web/app 配下は触らないでください。
```

- 2 本目（loop）：

```
web/lib/loop.ts を docs/06_voice_and_device.md の「ループ」のとおりに実装してください。関数名と型は今の空実装のまま。api.ts の関数だけを呼びます。
- startSession: startMotionLoop を起動し、setInterval 1 秒で postSignal（前の fetch が未返なら今回は送らない、AbortController で 3 秒、ts は new Date().toISOString()、score が null なら motion を省略、cameraOk を camera_ok に）。応答を onState。最初に state が watching になったら speak("見守りを始めるよ")。連続 3 回失敗で onConnection(false)、成功したら true。
- next_action が send_frame_and_request_hint なら captureFrame → postFrame → requestHint({trigger:"auto", frame_id}) を行い、応答を onHint と speak（await しない）。一度成功したら signals の state が stuck 以外になるまで再要求しない。失敗したときだけ次の秒に再試行。
- signals・hints・check・advance のどの応答でも state が ended ならループを止める（タイマーと motion と聞き取りを止める）。戻り値は止める関数。
- requestManualHint / requestCheck: captureFrame → postFrame → requestHint({trigger:"manual", frame_id}) / postCheck({frame_id})。応答の speech を speak し、応答を返す。
- advance: speechSynthesis.cancel() してから postAdvance。end: postEnd → 停止 → stopCamera。
- voice（T1-5 で本物にするので今は呼ぶだけ）: startSession の中で startListening(text => { onHeard(text); 「わからない」「わかんない」「ヒント」のどれかを含み、state が watching/still/cooldown なら captureFrame → postFrame → requestHint({trigger:"voice", frame_id}) を 1 回、応答を onHint と speak }) を呼び、speaking と checking の間は stopListening、watching/cooldown に戻ったら startListening。
pnpm dev:mock で、はじめる → 25 秒で一巡 → stuck で onHint が 1 回、を確認してください。web/app 配下は触らないでください。
```

- 完了条件：本番 iPhone で、手を止めるとスコアが τ を下回り、書くと上回る。`speak("テスト")` が鳴る。`pnpm dev:mock` で一巡とヒント 1 回。13:00 に `main` に入れて B に渡す（import は変わらない）。

### T1-3 13:00-15:00 縦串（固定文 H1）

- Claude Code に渡す文：

```
openapi.yaml を契約として、api/ に FastAPI を実装してください。ファイルは app/main.py、app/state.py、app/routes.py、app/store.py、app/worksheets.py の 5 つ。hints.py・leak.py・check.py は次の段階で足すので、今は routes.py の中で固定ヒントを返します。
- 全ルートは async def、uvicorn は 1 ワーカー。状態はプロセス内の dict（ロック不要）。JSON ファイル（DATA_PATH、既定 ./data/tonari.json。親ディレクトリを mkdir(parents=True)）への保存はセッション作成・設定変更・ヒント・チェック・進行・終了のときだけ、tmp に書いて rename。signals は保存しない。起動時に読み込み、ended 以外のセッションは watching に戻す。
- worksheets は Path(__file__).resolve().parents[2] / "worksheets"（環境変数 WORKSHEETS_DIR で上書き可）。problems が無いファイル（C の空枠）は警告して読み飛ばす。print は定数（docs/03 の値）。fixed_check_* が無い問題は既定文「正解。その調子」「もう一回、途中の式を見てみて」。
- しきい値と settings の既定は api/settings.yaml（docs/04 の例をそのまま置く）から読む。
- 状態機械 app/state.py は純粋関数 step(session, event, now, settings) -> (session, result)。Event は dataclass の Union：Signal(motion: float|None, camera_ok: bool, force_stuck: bool) / HintRequested(trigger) / HintIssued(speech_chars: int) / CheckRequested / CheckDone(verdict) / Advance / End / Tick。result は Accepted(next_action, …) か Rejected(code)。routes は Rejected を 409 にする。GET /sessions/{id} は Tick で時刻評価だけ行う。遷移は docs/04_stuck_detection.md の「遷移の規則」の表と「時刻」の評価順（途絶 5 秒 → speaking_until → cooldown_until → 今回の motion）のとおり。stuck・speaking・checking の間は motion を無視。
- signals: watching・still・stuck で 5 秒来なければ watching。still が stuck_seconds 続いたら stuck にし、stuck の間の応答すべてで next_action を "send_frame_and_request_hint"。camera_ok が false か motion が無いときは still を watching に戻す。force_stuck は watching・still・cooldown だけ受理し、このときだけ X-Operator-Key でも認可。ended の後の signals は {"state": "ended"} を 200 で返す。created の最初の signals で watching。
- PATCH /sessions/{id}/settings: device 認可。stuck_seconds（5〜1200）と cooldown_seconds（0〜300）を created・watching・still・cooldown で受理（それ以外は 409）。
- hints: level は min(stuck_count, max_level)。manual と voice は「その問題で最後に出した段階、無ければ 1」で上げない。今は全部 worksheets の fixed_hints を返し source を "fallback"、stuck_point は typical_mistakes の 1 つ目。読み上げ推定時間（speech の文字数×0.15 秒＋1 秒）で speaking → cooldown → watching。
- check: scripted なら常に correct（fixed_check_correct）。live は今は常に unreadable の固定文「もう少し明るいところで、もう一回見せて」（GPT は次の段階）。display は speech と同じ文。
- advance・end・/demo/reset（DEMO_MODE=1 のときだけ）・/worksheets*（正答・leak_strings・典型ミス・固定ヒントは返さない）・/healthz も契約どおり。
- 認可：device は Bearer の session_token 一致、operator は X-Operator-Key が環境変数 OPERATOR_KEY と一致。
- CORS は環境変数 CORS_ORIGINS（カンマ区切り）と CORS_ORIGIN_REGEX（既定 https://.*\.vercel\.app|https://.*\.trycloudflare\.com）。allow_headers に Authorization と X-Operator-Key と Content-Type。
- フレームは multipart の frame フィールド、600 KB 上限（413）、セッションごとにメモリに最新 1 枚。
テストは tests/test_state.py に docs/04 の表駆動テストのうち「20 秒止まる」「19 秒で動き出す」「回線断」「詰まり中に動く」「強制 stuck」の 5 ケース。
```

- 完了条件：本番 iPhone で `/device` を開き、「はじめる」→ 手を止めて 20 秒 → 「考え中？」→ 固定文 H1 が鳴る。**Mac の Chrome ＋ `?cam=iphone`（連係カメラ）でも同じが通る**（ピッチの構成はこちら）。通ったら `create_session.py` で `/device` の URL を 10 本作って D 宛スレッドに貼る。

### T1-4 15:00-17:00 答え漏れ検査、検証スクリプト、GPT の H2

- 順番：`app/leak.py`（15:00-15:20）→ `api/tools/leak_selftest.py`・`validate_worksheets.py`・CI に `uv sync --directory api`・`pnpm check:ws`・`uv run --directory api pytest` を足す（15:20-15:40。C が待っている）→ `app/hints.py`（15:40-17:00）。
- Claude Code に渡す文：

```
docs/05_hint_policy.md を全部読んでください。app/leak.py と app/hints.py を書き、routes.py の hints を差し替えます。
- leak.py: normalize(text)（先に ² → ^2・³ → ^3、次に NFKC、空白除去、× ✕ → *、− と数字直前の ー → -、＝ → =）と、leak_strings のいずれかを含むかの判定。
- api/tools/validate_worksheets.py: worksheets/*.json を schema.json で検証。problems が無いファイルは警告だけ。leak_strings が正規化後と一致しない要素と 3 文字未満の要素は赤。fixed_hints に "1" "2" があること、固定ヒントと fixed_check_* が 40 文字以内、text に answer が含まれないこと。api/tools/leak_selftest.py: 全問題の fixed_hints と fixed_check_incorrect を正規化し、その問題の leak_strings を含まないことを確かめる。両方とも worksheets は Path(__file__).resolve().parents[2] / "worksheets"。
- hints.py: HintOut（learner_present, readable, where, stuck_point, speech, display）。Gemini API の generateContent を httpx.AsyncClient(timeout=8) で 1 回だけ呼ぶ（リトライなし、鍵は GEMINI_API_KEY を x-goog-api-key ヘッダで）。model は HINT_MODEL（gemini-3.5-flash-lite）、systemInstruction に SYSTEM_PROMPT、画像は最新フレームを inline_data（image/jpeg、base64）、generationConfig は responseMimeType application/json と HintOut と同じ形の responseSchema（ADR 0025）。SYSTEM_PROMPT には 05 の「システムプロンプトの方針」「段階」の表（H2 だけ）「文言の規則」を全文入れる。ユーザー文には問題文・典型ミス・この問題で既に出したヒント文（「別の着眼点で」）を入れ、正答は渡さない。readable が false なら一般形「2 行目を声に出して読んでみて」。learner_present は記録するだけ。
- routes の hints: level 1 と scripted は GPT を呼ばず fixed_hints["1"] / ["2"]（source は fallback / scripted）。level 2 の live は GPT → speech を 40 文字・display を 60 文字で切ってから leak 検査 → 一致したら fixed_hints["2"] に差し替えて leak_check {ok:false, fallback:true} と leak_blocked_count += 1。タイムアウト・例外・最新フレーム無しは fixed_hints["2"] で source fallback、leak_check {ok:true, fallback:false}。固定文も無ければ 503。frame_id は照合せず最新フレームを使う。GET /sessions/{id} の hints[] に source・latency_ms・leak_check・trigger を含める。
```

- 完了条件：本番 iPhone で 2 回目の静止で GPT の H2 が鳴り、`GET /sessions/{id}` に `source: gpt` と `leak_check` が載る。CI が緑。`pnpm check:ws` が C の 3 枚で通る。

### T1-5 17:00-19:10 声のトリガー、進行、取り込み

- `web/lib/voice.ts` を本物にする（`webkitSpeechRecognition`、`lang: ja-JP`、`continuous: true`、`interimResults: false`、結果の文字列を `onHeard` に渡す。終了イベントで自動再開。非対応ブラウザでは何もしない）。`loop.ts` は T1-2 で呼び方まで書いてあるので、`speaking`・`checking` 中に止めて `watching`/`cooldown` で再開することを本番 iPhone と Mac で確認する。「わからない」と言うと `trigger: voice` の H1（または現在の段階）が鳴る。
- `advance`・`end`・`/demo/reset` の仕上げ。C のワークシート JSON、B の `/device` と `/ops`、C の `/log` の PR を取り込む。
- 18:30：中間発表を版 A・B・C のどれでやるか決めて D に伝える。
- 19:10：中間発表の操作。会場の照明で τ を再計測し `settings.yaml` に書く。静止を抜ける境目 `motion_exit_threshold` も見直す（τ より低いと API が起動しない）。
- 完了条件：本番 iPhone で「わからない」と言うとヒントが鳴り、`/log` に `trigger: voice` が載る。間に合わなければ落とす（切り捨ての順番の 2 番目）。

## Day 2

### T2-1 09:50-11:30 保険と正誤

- 09:50 に `create_session.py --count 10` で `stuck 10・cooldown 0` のセッションを 10 本作り、`/device` の URL を Slack の D 宛スレッドに貼る（D と B はオペレータキーを持たない）。11:00-11:30 は Mac を D に貸して本番構成で 5 回計時させる。
- 強制 stuck（T1-3 で入れてあれば確認だけ）：B の `/ops` のボタンから通ることを確認。D のリハで押すのは高橋。
- B と Meet の録音テスト（B2-1）。結果で 08 の音の経路を確定する。
- `POST .../check`（`app/check.py`）：

```
docs/05_hint_policy.md の「正誤チェック」を読んで app/check.py を書き、routes.py の check を差し替えてください。CheckOut は readable・final_answer_seen・verdict の 3 つだけ。hints.py と同じ Gemini API の呼び方（httpx、timeout 8、リトライなし、responseSchema）、model は CHECK_MODEL（gemini-3.5-flash-lite）、最新フレームと問題文と answer を渡して verdict だけ返させる。読み上げ文は GPT に作らせず固定：correct は fixed_check_correct、incorrect は fixed_check_incorrect、GPT が unreadable と言ったら「もう少し明るいところで、もう一回見せて」、8 秒で返らない・例外・フレーム無しは「うまく読めなかった。もう一回、できたを押してみて」（verdict は unreadable）。display は speech と同じ文。scripted は GPT を呼ばず常に correct。final_answer_seen は保存するが API では返さない。
```

- 11:30 までに終わらなければ「できた」は `advance` するだけにし、D に文言変更を頼む。
- `cooldown_seconds` と `stuck_seconds` の既定値を会場の照明で再確認。
- 完了条件：通しリハ 1 回目（11:30）が最後まで通る。

### T2-2 12:00-12:30 安定版

- 直しだけ。12:30 にデプロイしてタグ `v-video`。以後、撮影が終わるまでデプロイしない。
- 完了条件：タグが push され、Slack に「撮影中デプロイ禁止」を書く。

### T2-3 13:15-14:30 通しリハの操作と最終

- 13:15-13:40：D の通しリハ 3 回を Mac で操作（うち 1 回は強制 stuck）。
- 14:00-14:30：README（C）と提出物を確認して最終コミットにタグ `v-submit`。14:30 デプロイ凍結。

### T2-4 15:30-16:00 本番準備

- `docs/08` の「準備」の 1〜6 の順番どおり（テザリング → reset → scripted で通す → reset → live を作る → 「はじめる」は押さない → タブ共有）。連係カメラの再接続（T0-5 で決めた接続）。`/log/<id>?k=…` の URL をメモに貼る。
- 完了条件：`scripted` で 1 回通し、`live` で作り直してある。

### T2-5 16:00 ピッチ

- 操作とストップウォッチ。ボタンは全部高橋が押す。合図は「落とす」「飛ばす」の 2 語だけ。D が「できた」と言ったら 2 秒以内に押す。`docs/08` の「失敗したとき」の表を手元に置く。
