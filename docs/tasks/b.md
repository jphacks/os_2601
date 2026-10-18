# B のタスク（デバイス画面 `/device` と `/ops`）

> Hack Day（10/17・18）の当日に使ったカード。その後の変更（ワークシートの廃止 ADR 0026、契約の改名 ADR 0040 など）は反映していない。今の契約は `openapi.yaml` と `docs/03`、今の進め方は `AGENTS.md`。

順番どおりにやる。各カードの「Claude Code に渡す文」はそのまま貼ってよい。困ったら即 Slack（第一受付は D、次に高橋）。触ってよいのは `web/app/device/**` と `web/app/ops/**` だけ。`web/lib/**`・`api/**`・`openapi.yaml` は読むだけで変更しない。

## 共通の約束

- 文言と色は `docs/06` の表のとおり。自分で文章を作らない。
- カメラ・動きスコア・音声・API・1 秒ごとの送信・自動ヒントは `web/lib` の関数を呼ぶだけ（`startSession`、`requestManualHint`、`requestCheck`）。`canvas` から画像を取り出す処理や `setInterval` で API を呼ぶ処理を自分で書かない。
- `speech` は表示しない（読み上げ専用）。字幕は `display` をそのまま出す。
- `dangerouslySetInnerHTML`、外部スクリプト・フォント・CDN、`localStorage` への映像やトークンの保存は使わない。
- 依存パッケージを足さない。
- 1 回の依頼は 1 部品。終わったら `pnpm check` → PR。

## 今夜（10/16）

> **10/17 朝**：昨夜の T0 は未実施。当日の時刻は `docs/10` の「10/17 朝の改訂」の表が正。下の時刻は 1 時間前後ずれる。

### B0-1 環境（予行、60 分。画面共有で D の進行に合わせる）

1. Git for Windows、Node（`corepack enable`。駄目なら `npm i -g pnpm@<指定版>`）、`uv`、Claude Code（Windows 版）を入れる。`git config --global core.longpaths true`。
2. 使い捨てリポジトリを clone → `pnpm install` → `copy web\.env.example web\.env.local` → `echo b > .role.local` → `git config core.hooksPath .githooks` → `pnpm dev:mock` → ブラウザで `localhost:3000`。
   - 試しに `web/lib/api.ts` を 1 文字変えてコミットしてみる → 「[となり guard]」で止まるのを見る → `git checkout web/lib/api.ts` で戻す（担当外は物理的に入らない、を体験しておく）。
3. ブランチ → 1 ファイル変更 → `pnpm check` → PR → マージ → `git switch main` → `git pull`。
- 完了条件：`localhost:3000` のスクリーンショットを Slack に貼る。

### B0-2 画面を紙に描く（30 分）

- `docs/06` の「画面の配置」と「状態と表示」を読み、状態（はじめる前・見守り中・考え中？・となり・見てるよ・おつかれさま）ごとの画面を紙に描く。バッジの色、字幕、押せるボタンを書き込む。
- 完了条件：紙の写真を Slack に貼る。

## Day 1

### B1-1 10:20-11:00 疎通の PR

- 高橋の「clone していい」（10:35 ごろ）を待って本番リポジトリを clone → `pnpm install` → `pnpm dev:mock`。`web/app/device/page.tsx` に「となり device」と書いただけのページで PR 1 本。
- 10:35 の `main` には `web/lib`（`camera.ts` `motion.ts` `speech.ts` `api.ts` `loop.ts`）が入っていて、関数名・引数・戻り値は 06 の表のとおり確定している（中身は 13:00 に差し替わるが import は変わらない）。無ければ Slack で高橋に。
- 完了条件：マージされ、Vercel（または高橋のデプロイ）で `/device` が開く。

### B1-2 11:00-12:00 骨格（映像枠・バッジ・字幕）

- このカードだけは 1 回の依頼で page と部品 4 つをまとめて頼んでよい（分けると 60 分を超える）。
- Claude Code に渡す文：

```
あなたは web/app/device 配下だけを編集します。web/lib と api と openapi.yaml は読むだけで変更しません。
仕様: docs/06_voice_and_device.md の「画面の配置」「状態と表示」
契約: openapi.yaml の GET /sessions/{id}、POST /sessions/{id}/signals、POST /sessions/{id}/hints の応答。ループは web/lib/loop.ts の startSession（docs/06 の「ループ」）
サンプル: web/mocks/session_active.json、signals_watching.json、signals_stuck.json、signals_speaking.json、hint_level1.json
作るもの: web/app/device/page.tsx と部品 4 つ（Header、VideoFrame、StateBadge、Caption）
- page.tsx は "use client"。URL のクエリ s（session_id）と t（session_token）を useSearchParams で読む（Suspense で包む）。最初に web/lib/api.ts の getSession(s, {token: t}) を 1 回呼んで worksheet_id と problem_count を Header に出す（「WS-01 2 / 4 問目」。問題番号は後述の onState の current_problem_no で更新）。getSession の state は使わない。画面の初期 state は created 固定
- VideoFrame は <video> を置く。映像は常に表示する
- StateBadge は state を受け取り、06 の表の文言と色で出す。still は watching と同じ見た目
- Caption は display を 24px 以上の等幅で 1 つだけ出す。speech は出さない
- 状態は web/lib/loop.ts の startSession(video, s, t, handlers) の handlers.onState(resp) で受け取る（resp.state と resp.current_problem_no）。字幕は、state が created / checking / ended なら 06 の表の固定文、それ以外は handlers.onHint(resp) の resp.display（null なら変えない）。この段階では仮のボタン 1 つで unlockSpeech() → await startCamera(video) → startSession(...) の順に呼んでよい（本物のボタンは次の部品）。web/lib の関数の引数と戻り値は docs/06 の「web/lib の関数」の表のとおり
- 自分で postSignal や setInterval を書かない。映像を canvas から取り出す処理を書かない。dangerouslySetInnerHTML と外部スクリプトを使わない
- モックでは 5 秒ごとに状態が一巡し、stuck のときに onHint が 1 回来る
終わったら pnpm check を通して、変更したファイル一覧を教えてください。
```

- 完了条件：`pnpm dev:mock` で `localhost:3000/device?s=ses_mock&t=tok_mock` を開き、仮ボタンを押すと 25 秒で状態が一巡し、`stuck` の後にバッジと字幕が変わる。PR。

### B1-3 12:00-13:00 ボタン

- Claude Code に渡す文：

```
あなたは web/app/device 配下だけを編集します。web/lib と api と openapi.yaml は読むだけで変更しません。
仕様: docs/06_voice_and_device.md の「ボタンの動き」「開始の手順」
作るもの: Buttons 部品（はじめる・ヒント・できた・次へ・おわる。静かには作らない）
- created の画面に「止まったと判定する秒数」の選択（SecondsPicker 部品：10 秒・20 秒・30 秒・1 分・3 分・5 分・10 分・20 分のボタン。既定は getSession の settings.stuck_seconds に一番近いもの）を置く
- はじめる: created のときだけ。押したら、選んだ秒数が既定と違えば api.ts の patchSettings(s, t, {stuck_seconds}) → web/lib/speech.ts の unlockSpeech() → await web/lib/camera.ts の startCamera(video) → web/lib/loop.ts の startSession(video, s, t, handlers)。戻り値（止める関数）を保持する。startCamera が throw したら字幕に「設定からカメラを許可してね。LINE などの中のブラウザなら Safari か Chrome で開いてね」を出し、state は created のまま。「見守りを始めるよ」の読み上げは loop.ts がやるので書かない
- ヒント: state が watching・still・cooldown のときだけ押せる。web/lib/loop.ts の requestManualHint() を呼び、応答の display を Caption に出す（読み上げは loop.ts がやる。speech が null なら何もしない）
- できた: 同じ条件。requestCheck() を呼び、応答の display を Caption に出す
- 次へ: watching・still・cooldown・speaking のときだけ。loop.ts の advance()
- おわる: created と ended 以外で押せる。confirm の後 loop.ts の end()（ループとカメラは end() が止める）
- ボタンの try/catch で ApiError を受けたら何もしない（文言は出さない）
- 主ボタン 2 つは高さ 56px 以上
- onState の state が ended になったら、バッジ「おつかれさま」と字幕「今日はここまで。記録を見てみよう」を出し、ボタンを全部無効にする（映像の下の「記録を見る」だけは押せる。docs/06）
終わったら pnpm check を通して、変更したファイル一覧を教えてください。
```

- 完了条件：モックで秒数を選んで「はじめる」→ 5 秒ごとに状態が一巡 → `stuck` で字幕が変わり、コンソールに speak の出力が出る（声が本当に鳴るのは 13:00 に `web/lib` が本物になってから）。「ヒント」「できた」で字幕が変わる。PR。

### B1-4 13:00-15:00 本物につなぐ

- 13:00 に高橋が `web/lib` の実装を `main` に入れる。PowerShell で 1 行ずつ：`git switch main` → `git pull` → `git switch b/<自分のブランチ>` → `git merge main`。import は変わらないので、動かなければ呼び方の違い。高橋が 10 分隣に座る。
- `web/.env.local` の `NEXT_PUBLIC_API_BASE` を高橋が Slack に貼った Railway の URL にし、`pnpm dev`（`dev:mock` ではない）で起動する。URL は鍵ではないので持ってよい。
- `?debug=1` のときだけ動きスコアと輝度を小さく出す（`handlers.onBrightness` と `onState` の `still_seconds`）。平均輝度が 60 未満なら映像に「明るさが足りません」を重ねる。`handlers.onConnection(false)` で「つながりにくいみたい」をヘッダに出す。
- 完了条件：PC の Chrome（連係カメラでなくてよい）で手を止めると、本物の API から `stuck` → 固定文の声が出る。PR。

### B1-5 15:00-17:00 `/ops` オペレータ画面

- Claude Code に渡す文：

```
あなたは web/app/ops 配下だけを編集します。web/lib と api と openapi.yaml は読むだけで変更しません。
契約: openapi.yaml の POST /sessions、GET /sessions、POST /demo/reset、POST /sessions/{id}/signals（force_stuck）
作るもの: web/app/ops/page.tsx
- 上部に X-Operator-Key の入力欄（保存しない。ページを閉じたら消える）
- セッション作成フォーム: worksheet_id（WS-01/02/03）、mode（live/scripted）、stuck_seconds、cooldown_seconds。送信すると web/lib/api.ts の createSession を呼び、返ってきた session_id と session_token から /device?s=...&t=... のリンクと、そのリンクの文字列を表示する
- 「リセット」ボタン: confirm の後 demoReset
- 「強制 stuck」ボタン: session_id の入力欄（直近に作ったセッションの id を初期値にする。create_session.py で作ったセッションの id も貼れる）と postSignal(session_id, {operatorKey}, {ts, force_stuck:true}) を 1 回送る（応答は捨ててよい。デバイス側は次の signals で next_action を受け取る）
- 下にセッション一覧（listSessions）を 2 秒ごとに更新して表示
- 正答やヒント本文は扱わない
終わったら pnpm check を通して、変更したファイル一覧を教えてください。
```

- 完了条件：モック（`pnpm dev:mock`）で作成 → リンク表示 → リセット → 強制 stuck の 4 つが動く。PR。本物の API での通し（オペレータキーが要る）は高橋がキーを入れて D と行う。B はキーを持たない。

### B1-6 17:00-19:10 仕上げ

- `handlers.onHeard(text)` が来たら字幕の下に小さく「聞こえた：<text>」を 3 秒だけ出す（声のトリガー。17:00 以降に高橋が本物にする。文言は変えない）。

- スマホ縦持ちと PC 横持ちの配置（06 の図。「静かに」ボタンは無い）。ヘッダに `scripted` のときの黄色帯（`getSession` の `mode`）。`checking` の字幕「見てるよ…」と `ended` の表示を本物の API で確認。
- 本番 iPhone で D と通し。見つけた不具合は Slack に書いて自分の担当なら直す。

## Day 2

### B2-1 09:50-11:30 見た目の仕上げと τ

- 高橋と一緒に会場の照明で動きスコアを見て、「明るさが足りません」のしきい値を確認。
- **Meet の録音テスト**：自分の PC で個人の Google アカウントの Meet を立て、高橋の Mac が「Chrome のタブを共有（タブの音声を共有）」で `/device` の H1 を鳴らす。自分の PC 側で録画し、声が入っているかを聞く。入っていなければ 08 の「失敗したとき」の経路（3.5 mm → 会場スピーカー → Mac のマイク ON）を試して、どちらかを Slack に書く。
- バッジ・字幕・ボタンの見た目を整える（文言と色は変えない）。
- 完了条件：通しリハ 1 回目で画面側の不具合ゼロ。

### B2-2 12:30-14:00 動画を撮る

- 12:30-13:15：高橋の Mac で画面収録（4 分以内、`docs/08` の「製品説明動画」の流れ）と、スマホで手元を撮る 1 分版。D が原稿（C が 11:30 までに書く）を読みながらの 1 発撮り。編集はトリミングだけ。
- 13:15-13:45：4 分版を YouTube に限定公開でアップロードし URL を D と C に。1 分版を `ffmpeg -i in.mp4 -vf "fps=10,scale=480:-1" out.gif` で GIF にして（8 MB を超えたら `fps=8`、`scale=400`）C に渡す。
- 撮影中は誰もデプロイしない（12:30 の安定版で撮る）。
- 完了条件：13:45 に URL と GIF が C と D に届いている。

### B2-3 15:30-17:00 本番

- 紙を席に置く。ピッチ中は会場投票の挙手を数える役。
