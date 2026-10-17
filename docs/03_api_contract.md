# 03 API 契約（Hack Day 版）

フロント（B・C）とバック（高橋）の結合点。**この文書と `openapi.yaml` が唯一の契約。** `openapi.yaml` は 10/16 夜に高橋がこの文書から書き（T0-1）、当日そのままリポジトリに入れる。食い違ったら `openapi.yaml` を信じる。変更したいときは Slack で高橋に頼む（高橋だけが直す）。

Hack Day 版はヒント 2 段階（H1 固定文・H2 GPT）、SSE なし（記録画面は 2 秒ごとのポーリング）、`quiet`・`away`・サムネイルなし。それらは Kaizen Sprint の候補で、この文書には書かない。

## 共通事項

- **10/17 の変更（ADR 0026）**：契約の形は変えていない。ワークシートはやめ、見えないワークシート `FREE`（`title` は「自由な問題」、`grade` は空、問題の枠 20）だけを置く。`GET /worksheets` は `FREE` だけ、`GET /worksheets/FREE` の `problems` は空。セッション作成は `worksheet_id: "FREE"`。ヒントは 1 回目から AI が作り、`source` は `gpt`（生成 AI の総称）、AI が失敗したときと答え漏れで差し替えたときは `fallback`。`stuck_point` は AI が付けたラベル。
- ベース URL：`NEXT_PUBLIC_API_BASE`（例 `https://tonari-api.up.railway.app`）。
- 認可（02 参照）：デバイス `Authorization: Bearer <session_token>`、オペレータ `X-Operator-Key: <OPERATOR_KEY>`、公開はヘッダなし。
- エラー形式：`{"error": {"code": "STATE_CONFLICT", "message": "..."}}`。使う HTTP ステータス：400 / 401 / 403 / 404 / 409（状態競合）/ 413（フレームが大きい）/ 422（検証）/ 503（固定ヒントも読めない）。
- 時刻は ISO 8601（UTC、`Z` 付き）。ID は推測できない乱数（`ses_`・`tok_`・`frm_`・`hnt_`・`chk_` の接頭辞）。
- **正答・`leak_strings`・典型ミスの一覧・固定ヒントの表（問題ごと・段階ごとの一覧）は、どのエンドポイントからも返さない。** 出したヒント文はその都度 `display` で返る（それは学習者が聞いた文なので隠さない）。
- `speech` は読み上げ用（AI には 35 文字以内で書かせる。記号は言葉に）、`display` は字幕用（50 文字以内。数式は半角）。文が壊れるので切らず、60 文字・80 文字を超えたら固定の問い返しにする（ADR 0029）。フロントは文章を組み立てず、値をそのまま出す。
- `state` の値：`created` | `watching` | `still` | `stuck` | `speaking` | `cooldown` | `checking` | `ended`。
- `mode` の値：`live`（GPT を呼ぶ）| `scripted`（GPT を呼ばず固定ヒント。正誤は常に `correct`）。`mock` はフロントだけの概念でサーバには来ない。

## エンドポイント一覧

| メソッド | パス | 認可 | 役割 |
|---|---|---|---|
| POST | `/sessions` | operator | セッション作成。`session_token` を返す |
| GET | `/sessions` | operator | セッション一覧（`/ops`・`/log`） |
| GET | `/sessions/{id}` | operator・device | セッションの要約と問題ごとの経過 |
| PATCH | `/sessions/{id}/settings` | device | 学習者が「止まったと判定する秒数」を選ぶ（10 秒・20 秒・30 秒・1 分・3 分・5 分・10 分・20 分） |
| POST | `/sessions/{id}/signals` | device（`force_stuck` のときは operator も可） | 1 秒ごとの動きスコア。応答で状態を受け取る |
| POST | `/sessions/{id}/frames` | device | フレーム 1 枚（JPEG） |
| POST | `/sessions/{id}/hints` | device | ヒント要求（`auto` はサーバの指示で、`manual` はボタンで） |
| POST | `/sessions/{id}/check` | device | 「できた」。正誤チェック |
| POST | `/sessions/{id}/advance` | device | 次の問題へ（スキップ） |
| POST | `/sessions/{id}/end` | device・operator | 終了 |
| GET | `/worksheets` | 公開 | ワークシート一覧（正答なし） |
| GET | `/worksheets/{id}` | 公開 | 問題文と印刷用レイアウト情報（正答なし） |
| POST | `/demo/reset` | operator（`DEMO_MODE=1`） | 全セッションを消す |
| GET | `/healthz` | 公開 | 死活 |

## セッション

### POST /sessions（operator）

```json
{"worksheet_id": "WS-01", "learner_label": "デモ", "mode": "live",
 "settings": {"stuck_seconds": 20, "cooldown_seconds": 60, "max_level": 2}}
```

```json
{"session_id": "ses_7f3c…", "session_token": "tok_…", "mode": "live", "state": "created",
 "worksheet": {"worksheet_id": "WS-01", "title": "一次方程式", "problem_count": 4},
 "settings": {"stuck_seconds": 20, "cooldown_seconds": 60, "max_level": 2},
 "created_at": "2026-10-17T01:30:00Z"}
```

- `settings` と `learner_label` は省略可。省略時は `settings.yaml` の既定値と「学習者」。`stuck_seconds` は 5〜1200（`/device` の選択肢は 10・20・30・60・180・300・600・1200）、`cooldown_seconds` は 0〜300、`max_level` は 1〜2。
- `session_token` はこの応答でだけ返す。デバイス画面は URL のクエリ（`/device?s=ses_…&t=tok_…`）で受け取る。`GET /sessions*` には含めない。
- 作成直後の `current_problem_no` は 1、問題 1 は `working`、残りは `pending`。モックの id は `ses_mock` / `tok_mock`。

### GET /sessions/{id}（operator・device）

```json
{"session_id": "ses_…", "worksheet_id": "WS-01", "worksheet_title": "一次方程式", "problem_count": 4,
 "learner_label": "デモ", "mode": "live",
 "state": "watching", "current_problem_no": 2, "still_seconds": 7,
 "settings": {"stuck_seconds": 20, "cooldown_seconds": 60, "max_level": 2},
 "problems": [
   {"problem_no": 1, "status": "done", "stuck_count": 0, "max_level": 0, "seconds_spent": 95,
    "hints": [], "check": {"verdict": "correct", "display": "正解！ 移項がきれい", "created_at": "…"}},
   {"problem_no": 2, "status": "working", "stuck_count": 2, "max_level": 2, "seconds_spent": 140,
    "hints": [
      {"hint_id": "hnt_…", "level": 1, "trigger": "auto", "display": "今、何を求めようとしてる？",
       "stuck_point": "移項の符号", "source": "fallback",
       "leak_check": {"ok": true, "fallback": false}, "latency_ms": 3, "created_at": "…"},
      {"hint_id": "hnt_…", "level": 2, "trigger": "auto", "display": "右辺に移したときの符号、もう一回見てみて",
       "stuck_point": "移項の符号", "source": "gpt",
       "leak_check": {"ok": true, "fallback": false}, "latency_ms": 2300, "created_at": "…"}],
    "check": null},
   {"problem_no": 3, "status": "pending", "stuck_count": 0, "max_level": 0, "seconds_spent": 0, "hints": [], "check": null},
   {"problem_no": 4, "status": "pending", "stuck_count": 0, "max_level": 0, "seconds_spent": 0, "hints": [], "check": null}],
 "stuck_points": [{"label": "移項の符号", "count": 2}],
 "leak_blocked_count": 0,
 "created_at": "…", "ended_at": null}
```

- `problems[].status` は `pending` | `working` | `done` | `skipped`。
- `hints[]` に `speech` は含めない（読み上げは出した瞬間だけ）。`trigger`（`auto` / `manual` / `voice`）は含める。`stuck_point` は H1（固定文）では典型ミスの 1 つ目。
- `leak_blocked_count` は答え漏れ検査で捨てた回数の合計（「答えを言いそうになって止めた回数」として `/log` に出す）。
- `seconds_spent` は `working` になってから `done` / `skipped` になるまで（進行中は現在まで）。

### PATCH /sessions/{id}/settings（device）

```json
{"stuck_seconds": 60}
```

→ `{"settings": {"stuck_seconds": 60, "cooldown_seconds": 60, "max_level": 2}, "state": "created"}`。

- `stuck_seconds`（5〜1200）と `cooldown_seconds`（0〜300）のどちらか、または両方。`created`・`watching`・`still`・`cooldown` で受理し、それ以外は 409。`/device` は「はじめる」の前に学習者が選んだ値を送る（既定は作成時の値）。進行中に変えても次の静止から効く。

### GET /sessions（operator）

```json
{"sessions": [
  {"session_id": "ses_…", "worksheet_id": "WS-01", "learner_label": "デモ", "mode": "live", "state": "watching",
   "problem_done": 1, "problem_count": 4, "stuck_total": 2, "created_at": "…", "ended_at": null}]}
```

新しい順。

## 信号とフレーム

### POST /sessions/{id}/signals（device）

1 秒ごとに送る。

```json
{"ts": "2026-10-17T01:31:05Z", "motion": 0.012, "camera_ok": true}
```

```json
{"state": "still", "still_seconds": 7, "current_problem_no": 2,
 "next_action": null, "cooldown_remaining": 0}
```

- `motion` は 0〜1（04）。ウォームアップ中（最初の 3 秒）は `motion` を省略する。`camera_ok: false` または `motion` 省略のときは「信号が来ていない」のと同じ扱い（`still` なら `watching` に戻し `still_seconds` を 0 に）。
- 省略可の `force_stuck: true` を付けると `motion` を無視して `stuck` に入る（`/ops` の強制 stuck ボタン）。受理するのは `watching`・`still`・`cooldown` だけで、`stuck` なら何もせず 200、それ以外は 409。**このときだけ `X-Operator-Key` でも認可する**（`/ops` はセッショントークンを持たないため。`openapi.yaml` の `security` に両方を書く）。`motion` と `camera_ok` は省略可。
- `still_seconds` は `still` のときだけ正、他は 0。`cooldown_remaining` は `cooldown` のときだけ正、他は 0。
- `next_action` は `null` | `"send_frame_and_request_hint"` | `"send_frame"`。**`stuck` の間の応答すべてに `"send_frame_and_request_hint"` が付く。** デバイス（`web/lib/loop.ts`）は、直ちにフレーム 1 枚を `frames` に送ってから `hints` を `trigger: "auto"` で呼ぶ。**一度 `auto` が成功したら、`signals` の応答で `state` が `stuck` 以外になるのを見るまで再要求しない**（失敗したときだけ次の秒に再試行）。これで二重要求が出ない。サーバのタイマーで GPT を呼ぶ作りにはしない（デバイスの最新フレームが要るため）。
- **静止がひと続きの間に 1 回だけ、`still_seconds` が `stuck_seconds − prefetch_lead_seconds`（3 秒）に達した応答に `"send_frame"` が付く**（`live` のセッションだけ。10/17 に追加、ADR 0028）。デバイスはフレームを送り、その `frame_id` を覚えておく。サーバはそのフレームで次の自動ヒントを裏で作り始め、静止が途切れたら（`still`・`stuck` 以外になったら）取り消す。stuck になったら、デバイスは撮り直さずに覚えた `frame_id` で `hints`（auto）を呼び、サーバは作っておいたヒントを（まだならできるまで待って）返す。AI の時間とフレームの送信が stuck の前に済むので、「考え中？」とほぼ同時に声が出る。
- `stuck`・`speaking`・`checking` の間は `motion` を無視する（状態は変わらない）。
- `watching`・`still`・`stuck` のとき、5 秒以上 `signals` が来なければサーバは状態を `watching` に戻し `still_seconds` を 0 にする（回線断で誤って詰まり判定しない）。`created`・`speaking`・`checking`・`cooldown`・`ended` には適用しない。評価順は 04 の「時刻」。
- `ended` の後に来た `signals` には 200 で `{"state": "ended", "still_seconds": 0, "current_problem_no": n, "next_action": null, "cooldown_remaining": 0}` を返す。デバイスはループを止める。
- `created` のときの `signals` は `watching` に遷移させる（「はじめる」を押した合図）。

### POST /sessions/{id}/frames（device）

`multipart/form-data`、フィールド `frame`（`image/jpeg`、長辺 1024、品質 0.7、上限 600 KB）。

→ `{"frame_id": "frm_…", "received_at": "…", "bytes": 182311}`。

- サーバはセッションごとに最新 1 枚だけメモリに持つ。保存はしない。再起動で消える。
- 送るのは 3 つの瞬間だけ：`next_action`（`send_frame` か、先に送っていなければ `send_frame_and_request_hint`）が来たとき、「ヒント」を押したとき、「できた」を押したとき。定期的には送らない（「手が止まったときだけ 1 枚」を README とピッチで言うため）。
- 大きすぎれば 413。`ended` なら 409。

## ヒント

### POST /sessions/{id}/hints（device）

```json
{"trigger": "auto", "frame_id": "frm_…"}
```

`trigger` は `auto`（`next_action` に従って）| `manual`（ボタン）| `voice`（学習者の発話を聞き取った。ブラウザの音声認識で聞き取り、`web/lib/loop.ts` が `utterance` に文を入れて送る）。**`utterance` があれば、AI がその発話に答えるかを決め、答えるときは説明もする（答えと途中の値は言わない）。答えないときは 204 で、状態は変えず記録にも残さない。AI を待つ間は状態を変えないので、ボタンと「できた」は止まらない。`utterance` は保存しない（10/17、ADR 0032）。**`frame_id` は直前に送ったフレーム（サーバは照合せず最新 1 枚を使う。`auto` で先に作り始めたヒントが同じ問題の同じ詰まり（`stuck_count`）のものなら、それを返す。ADR 0028）。

```json
{"hint_id": "hnt_…", "problem_no": 2, "level": 2, "trigger": "auto",
 "speech": "右辺に移したときの符号、もう一回見てみて",
 "display": "右辺に移したときの符号、もう一回見てみて",
 "stuck_point": "移項の符号",
 "leak_check": {"ok": true, "fallback": false},
 "source": "gpt", "model": "gpt-6.1-sol", "latency_ms": 2300,
 "state": "speaking"}
```

- `source` は `gpt` | `fallback`（固定ヒント。H1 は常に `fallback`）| `scripted`（モードが scripted）。`model` は `gpt` のときだけ。
- `level` は、`auto` ならその問題の `stuck_count` と `max_level` の小さい方（1 回目 H1、2 回目以降 H2）。`manual` と `voice` なら、その問題で初めてなら 1、2 回目以降は 2（ADR 0033）。
- `cooldown`（一度声をかけた後の沈黙）が止めるのは `auto` だけ。`manual` と `voice` は本人が頼んだので `cooldown` 中でも通る（`speaking`・`checking`・`stuck` 中は 409）。
- `leak_check.ok: false` かつ `fallback: true` は、GPT の文が答え漏れ検査に一致したので固定 H2 に差し替えたことを示す。`leak_blocked_count` が 1 増える。
- GPT がタイムアウト（8 秒）・エラーのときは固定 H2 で返し `source: "fallback"`、`leak_check.ok: true`。固定ヒントも読めないほど壊れていれば 503。
- `auto` は `stuck` のときだけ受理（受理の判定はリクエスト到着時。GPT を待つ間に `signals` の途絶で `watching` に戻っていても、応答時に `speaking` へ進める）。それ以外は 409（デバイスは無視する）。`manual` と `voice` は `watching`・`still`・`cooldown` だけ受理し、`created`・`stuck`・`speaking`・`checking`・`ended` で 409。
- 応答を返した時点でサーバは `speaking` にし、読み上げ推定時間（`speech` の文字数 × 0.15 秒 + 1 秒）後に `cooldown`、`cooldown_seconds` 後に `watching` へ戻す。デバイスからの「読み終わった」通知は作らない。
- `speech` が `null` になることは Hack Day 版では無い（不在判定は作らない）。デバイスは念のため `null` なら読まない。

## 正誤チェック

### POST /sessions/{id}/check（device）

```json
{"frame_id": "frm_…"}
```

```json
{"check_id": "chk_…", "problem_no": 2, "verdict": "correct",
 "speech": "正解。符号の直し方、ばっちり", "display": "正解！ 符号の直し方、ばっちり",
 "next_problem_no": 3, "state": "speaking"}
```

- `verdict` は `correct` | `incorrect` | `unreadable`。
- 受理した時点で `checking` にし、GPT の応答で `speaking` → `cooldown` → `watching`（ヒントと同じ時間規則）。
- `correct` のときサーバは問題を `done` にし `current_problem_no` を進める。最後の問題なら `next_problem_no: null`、`state: "ended"`、`ended_at` を入れる。
- `speech`・`display` は固定文で、`display` は `speech` と同じ文（`correct` は `fixed_check_correct`、`incorrect` は `fixed_check_incorrect`。問題に無ければ既定文「正解。その調子」「もう一回、途中の式を見てみて」）。GPT には `verdict` だけを出させる（正答を渡した呼び出しなので、文を作らせると答えを言いうる）。`incorrect` のとき問題は `working` のまま、`next_problem_no` は現在の番号。
- `unreadable` は 2 文：GPT が読めないと言ったら「もう少し明るいところで、もう一回見せて」、GPT が 8 秒で返らない・例外・フレーム無しなら「うまく読めなかった。もう一回、できたを押してみて」。
- `scripted` モードでは GPT を呼ばず常に `correct`（`fixed_check_correct`）。
- 正答の値は応答に含めない。`watching`・`still`・`cooldown` だけ受理し、`created`・`stuck`・`speaking`・`checking`・`ended` では 409。

## 進行

### POST /sessions/{id}/advance（device）

`{"reason": "skip"}` → `{"current_problem_no": 3, "state": "watching"}`。前の問題は `skipped`（`done` なら変えない）。最後の問題なら `state: "ended"`、`current_problem_no` はそのまま。`watching`・`still`・`cooldown`・`speaking` で受理し（`speaking` なら読み上げを打ち切って `watching`）、`created`・`stuck`・`checking`・`ended` では 409。

### POST /sessions/{id}/end（device・operator）

→ `{"state": "ended", "ended_at": "…"}`。最新フレームをメモリから捨てる。`ended` に対してもう一度呼んでも 200。

## ワークシート

### GET /worksheets（公開）

```json
{"worksheets": [{"worksheet_id": "WS-01", "title": "一次方程式", "problem_count": 4, "grade": "中1"}]}
```

### GET /worksheets/{id}（公開）

```json
{"worksheet_id": "WS-01", "title": "一次方程式", "grade": "中1",
 "problems": [{"problem_no": 1, "text": "3x + 5 = 20 を解きなさい。"}],
 "print": {"paper": "A4", "id_font_px": 48, "gap_mm": 45,
           "footer": "となり：手元だけを見ます。顔は映しません。映像は保存しません"}}
```

正答・典型ミス・固定ヒント・`leak_strings` は含めない。

## デモ操作と死活

### POST /demo/reset（operator、`DEMO_MODE=1`）

→ `{"ok": true, "removed_sessions": 3}`。セッション・問題・ヒント・チェック・メモリのフレームをすべて消す。ワークシート定義は消さない。`DEMO_MODE` が `1` でなければ 404。

### GET /healthz（公開）

→ `{"ok": true, "gpt": "ok", "worksheets": 3, "mode_default": "live"}`。`gpt` は `OPENAI_API_KEY` があれば `ok`、無ければ `missing`（疎通確認はしない）。

## フロントのモック（`NEXT_PUBLIC_MOCK=1`）

`web/lib/api.ts` が `web/mocks/` の JSON を返す。ファイル名は次の 23 本で固定。

| 関数 | 返すもの |
|---|---|
| `createSession` | `session_created.json` |
| `listSessions` | `sessions_list.json`（進行中 `ses_mock` と終了済み `ses_mock_ended` の 2 件） |
| `getSession` | `session_active.json`（問 2 に `source: gpt` と `source: fallback`・`leak_check.fallback: true` の H2 を 1 件ずつ、`leak_blocked_count: 1`）。id が `ses_mock_ended` なら `session_ended.json`（問 3 は `skipped`） |
| `patchSettings` | 渡した値をそのまま `settings` に入れて返す |
| `postSignal` | 呼ばれた回数で 5 秒ごとに `signals_watching.json` → `signals_still.json` → `signals_stuck.json` → `signals_speaking.json` → `signals_cooldown.json` を一巡。`force_stuck: true` なら `signals_stuck.json`。`postEnd` か `postAdvance` の応答が `ended` だった後は `signals_ended.json` |
| `postFrame` | `frame_received.json` |
| `requestHint` | 1 回目 `hint_level1.json`、2 回目以降 `hint_level2.json`。`hint_fallback.json` は `source: fallback`・`leak_check.fallback: true` の見本（`/device` の字幕確認用） |
| `postCheck` | `check_correct.json`（`check_incorrect.json`・`check_unreadable.json` は見本用） |
| `postAdvance` | 1〜3 回目 `advance.json`（`current_problem_no` を 1 ずつ増やす）、4 回目から `advance_ended.json` |
| `postEnd` | `end.json` |
| `getWorksheets` / `getWorksheet` | `worksheets.json` / `worksheet_ws01.json` |
| `demoReset` | `demo_reset.json` |

- モックでもカメラと音声合成は本物を使う（ブラウザの機能なので）。
- モックの JSON に `answer`・`leak_strings`・`typical_mistakes`・`fixed_hints` を入れない。

## `web/lib/api.ts` の関数（固定）

| 関数 | 呼ぶもの | 認可 |
|---|---|---|
| `createSession(body, operatorKey)` | `POST /sessions` | operator |
| `listSessions(operatorKey)` | `GET /sessions` | operator |
| `getSession(id, auth)` | `GET /sessions/{id}` | `auth` は `{token}` か `{operatorKey}` |
| `patchSettings(id, token, body)` | `PATCH /sessions/{id}/settings` | device |
| `postSignal(id, auth, body)` | `POST /sessions/{id}/signals` | `auth` は `{token}`（ループ）か `{operatorKey}`（`/ops` の `force_stuck` だけ） |
| `postFrame(id, token, blob)` | `POST /sessions/{id}/frames` | device |
| `requestHint(id, token, body)` | `POST /sessions/{id}/hints` | device |
| `postCheck(id, token, body)` | `POST /sessions/{id}/check` | device |
| `postAdvance(id, token)` | `POST /sessions/{id}/advance` | device |
| `postEnd(id, token)` | `POST /sessions/{id}/end` | device |
| `getWorksheets()` / `getWorksheet(id)` | `GET /worksheets*` | なし |
| `demoReset(operatorKey)` | `POST /demo/reset` | operator |

エラー応答は `ApiError`（`status` と `code` を持つ）を投げる。B・C は `try/catch` で受けて、文言は 06 の表か「つながりにくいみたい」だけを出す。`web/lib/loop.ts` は `hints`・`check`・`advance` の応答の `state` が `ended` でもループを止める。
