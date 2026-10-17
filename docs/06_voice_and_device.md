# 06 デバイス画面・音声

担当：B（表示コンポーネント）。カメラ取得・動きスコア・API・音声合成・**1 秒ごとの送信と自動ヒントのループ（`web/lib/loop.ts`）**は高橋が書き、B はそれを呼んで表示するだけ。

**10/16 夜の改訂**：Hack Day 版では「静かに」ボタンと `quiet`・`away` は作らない。SSE は廃止。セッションは `/ops` で作る。

## 役割

デバイス画面 `/device` は、机の横のスマホで開きっぱなしにする 1 画面。やることは 5 つ。

1. カメラで手元を映し続ける（映像は画面に出す。学習者が「何が映っているか」を常に見られるように）。
2. 1 秒ごとに動きスコアを計算してサーバへ送り、返ってきた状態を表示する。
3. サーバの指示でフレームを送り、ヒントを要求する。
4. ヒントを声と字幕で出す。
5. ボタン（はじめる・ヒント・できた・次へ・おわる）。

## 画面の配置（スマホ縦持ち）

```
┌──────────────────────────────┐
│ WS-01 一次方程式    2 / 4 問目 │  ← ヘッダ：シート・問題番号・モード（scripted なら黄色帯）
├──────────────────────────────┤
│                              │
│      カメラ映像（手元）        │  ← 常時表示。暗いときは「明るさが足りません」を重ねる
│                              │
│  ● 見守り中                   │  ← 状態バッジ（左下）。色は下の表
├──────────────────────────────┤
│ 「右辺に移したときの符号、      │  ← 字幕（直近のヒント・チェック結果）。大きい文字
│   もう一回見てみて」           │
├──────────────────────────────┤
│ [ ヒント ]      [ できた ]    │  ← 主ボタン 2 つ（大きい）
│      [ 次へ ]  [ おわる ]     │  ← 副ボタン 2 つ（小さい）
└──────────────────────────────┘
```

PC（横持ち）では映像を左、字幕とボタンを右に置く。部品は同じ。

## 状態と表示

| 状態 | バッジ | 色 | 字幕 | 音 |
|---|---|---|---|---|
| `created` | はじめる前 | 灰 | 「スマホを立てて、手元が映るようにしてね」＋「止まったと判定する秒数」の選択（10 秒・20 秒・30 秒・1 分・3 分・5 分・10 分・20 分。既定はセッションの値） | なし |
| `watching` | 見守り中 | 緑 | 直近のまま | なし |
| `still` | 見守り中（点滅なし。still を学習者に見せない） | 緑 | 直近のまま | なし |
| `stuck` | 考え中？ | 黄 | 直近のまま | なし |
| `speaking` | となり | 青 | ヒント文 | 読み上げ |
| `cooldown` | 見守り中 | 緑 | ヒント文のまま | なし |
| `checking` | 見てるよ | 青 | 「見てるよ…」 | なし |
| `ended` | おつかれさま | 緑 | 「今日はここまで。記録を見てみよう」 | なし |

- `still` を表示で区別しないのは意図的。「止まっている」とカウントされていることを見せると、学習者がカメラを意識して手を動かす。
- `stuck` の「考え中？」は、ヒントが届くまでの 2〜4 秒だけ見える。これが「気づいた」の合図。

## 開始の手順（音声のアンロック）

ブラウザは、ユーザー操作なしに音を出せない。「はじめる」ボタンのクリックハンドラの中で次を順に行う。**1〜3 は `unlockSpeech()` と `startCamera(video)` の中身で、B はこの 2 つと `startSession` を順に呼ぶだけ。`speechSynthesis` や `getUserMedia` を `web/app` に書かない。**

1. `speechSynthesis.speak(new SpeechSynthesisUtterance(""))` を 1 回呼ぶ（無音。これで以後の自動読み上げが許可される。iOS Safari で必須）。
2. `navigator.mediaDevices.getUserMedia({video: {facingMode: "environment", width: {ideal: 1280}, height: {ideal: 720}}, audio: false})` でカメラを取る。
3. `video.srcObject` に流し、`video.play()`。
4. `POST /sessions/{id}/signals` を 1 秒ごとに開始。
5. 状態が `watching` になったら「見守りを始めるよ」と 1 回読み上げる（これがアンロックの確認にもなる）。
6. 「はじめる」の前に学習者が秒数を選んでいたら、1 の前に `patchSettings(id, token, {stuck_seconds})` を送る（既定のままなら送らない）。

- セッションは `/ops` でオペレータが作り、URL（`/device?s=ses_…&t=tok_…`）でスマホに渡す。デバイス画面にセッション作成の機能は置かない。
- `startCamera` が throw したら、B は字幕に「設定からカメラを許可してね。LINE などの中のブラウザなら Safari か Chrome で開いてね」を出し、状態は `created` のまま（もう一度「はじめる」を押せる）。

## PC（Mac）で iPhone を連係カメラとして使うとき

- Mac の Chrome では `facingMode: "environment"` は無視され、既定のカメラ（内蔵）が選ばれる。`web/lib/camera.ts` は `enumerateDevices()` でラベルに「iPhone」を含む入力を優先し、無ければ既定を使う。`/device?cam=iphone` で明示できる。
- 連係カメラは iPhone をロック状態で横向きに近くに置くと候補に出る。出ないときは iPhone を一度ロック解除してから再度ロックする。
- 音声は Mac のスピーカー出力（3.5 mm で会場スピーカーへ）。Meet には「Chrome のタブを共有」でタブの音として乗せる（ウィンドウ共有では乗らない）。

## 音声認識（`web/lib/voice.ts`、高橋が書く）

- `webkitSpeechRecognition`（`lang: ja-JP`、`continuous: false`、`interimResults: false`）。発話ごとに確定した文字列を `onHeard` に渡し、終わったら 0.5 秒おいて自動で再開する（`continuous: true` だと iOS Safari で確定が遅れるため）。エラーの後は 3 秒待つ。非対応なら何もしない。
- 「はじめる」のクリックの中で `primeListening()` を呼び、マイクと音声認識の許可をその場で取る（iOS は操作の直後でないと許可を求められないことがある）。許可されなかったら、そのページではもう聞かない。
- `/device` の URL に `voice=0` を付けると聞き取らない（中間発表や動画の撮影で、会場の声に反応させないため）。
- 合言葉は「わからない」「わかんない」「分からない」「分かんない」「わかりません」「分かりません」「ヒント」（音声認識は漢字で返すことが多い）。
- iOS Safari は「Siri と音声入力」が ON でないと動かない。Mac Chrome は動く（音声は Google のサーバで文字にされる。Safari は Apple）。聞き取った文字だけを使い、音声は保存しない。README と 12 に書く。
- ピッチでは使わない（会場のマイクやスピーカーの音を誤認識するため）。製品説明動画の 3 問目で見せる。

## カメラの置き方

- スマホはアーム式スタンドで、紙の真上 35〜45 cm から、紙面全体が入るように。背面カメラ（`environment`）を使う。
- 顔が入らない角度にする。真上から撮れば、入るのは手と紙と机だけ。
- 卓上ライトを紙の斜め上から当てる（影がペン先に落ちないように）。
- 紙は動かさない。シートの位置がずれると差分が大きく出る。
- 画面には映像を表示し続ける。学習者が自分で「何が映っているか」を確認できる。

## 音声合成（`web/lib/speech.ts`、高橋が書く）

- Web Speech API の `speechSynthesis` を使う。`lang = "ja-JP"`。
- 声の選び方：`speechSynthesis.getVoices()` から `lang` が `ja-JP` のものを選ぶ。iOS は Kyoko、Android Chrome は Google 日本語、PC Chrome は Google 日本語か OS の声。`voiceschanged` イベント後に選び直す（最初の `getVoices()` が空のことがある）。
- 速さ `rate = 1.0`、高さ `pitch = 1.0`。`speech` は 35 文字以内なので 5〜6 秒で終わる。
- 読み上げ中に次のヒントが来たら、`speechSynthesis.cancel()` してから新しい文を読む。
- 音声が出ないときも字幕は必ず出す。会場では PC を会場スピーカーにつなぐ（08 参照）。
- VOICEVOX は使わない（サーバが要る）。Kaizen Sprint の候補。

## ボタンの動き

| ボタン | いつ押せるか | 何が起きるか |
|---|---|---|
| はじめる | `created` | 音声アンロック、カメラ開始、`startSession` でループ開始 |
| ヒント | `watching` `still` `cooldown` のときだけ | `requestManualHint()`（フレームを送ってから `POST /hints {trigger: "manual"}`）。段階は現在の段階 |
| できた | `watching` `still` `cooldown` のときだけ | `requestCheck()`（フレームを送ってから `POST /check`）。結果を読み上げ。`correct` なら問題番号が進む |
| 次へ | `watching` `still` `cooldown` `speaking` のときだけ | 確認ダイアログなしで `advance()`。最後なら `ended` |
| おわる | `created` `ended` 以外 | 確認ダイアログの後 `end()`（`POST /end` → ループ停止 → カメラ停止） |

`stuck`（「考え中？」）の数秒間は主ボタンも「次へ」も押せない。自動ヒントの要求と競合させないため。
| 静かに | 作らない（Kaizen Sprint） | |

- `hints` の応答の `speech` が `null` のときは読まず、字幕も変えない（Hack Day 版では起きないが念のため）。
- `signals` の応答が `ended` になったらループを止め、「おつかれさま」を出す。

- 主ボタンは親指で押せる大きさ（高さ 56px 以上）。
- `speaking` 中は主ボタンを無効にする（読み上げの途中で状態が変わると混乱する）。

## フレームの送り方（`web/lib/camera.ts`、高橋が書く）

- `video` を `canvas` に長辺 1024 で描き、`canvas.toBlob("image/jpeg", 0.7)` で JPEG にする。
- 送るタイミング：`signals` の応答に `next_action` が来たら即 1 枚（`send_frame_and_request_hint` のときは、`send_frame` で先に送っていなければ）、「ヒント」「できた」を押した直後に 1 枚。定期的には送らない。
- 送った `frame_id` を保持し、直後の `hints` / `check` に渡す。
- 回線が落ちているときは送らない（キューに溜めない。古いフレームに意味はない）。

## `web/lib` の関数（固定。B はこれを呼ぶだけ）

| 関数 | 引数 | 戻り値 | 何をするか |
|---|---|---|---|
| `unlockSpeech()` | なし | `void` | 「はじめる」のクリックの中で呼ぶ。無音の読み上げで以後の自動読み上げを許可する |
| `speak(text)` | `string` | `Promise<void>` | 読み上げ。読み上げ中なら止めてから読む。B は普段呼ばない（`loop.ts` が呼ぶ） |
| `startListening(onHeard)` / `stopListening()` | `(text: string) => void` | `() => void` / `void` | 「わからない」の聞き取り（ブラウザの音声認識）。B は呼ばない（`loop.ts` が呼ぶ） |
| `startCamera(video)` | `HTMLVideoElement` | `Promise<void>` | カメラを `video` に流す。許可が出なければ `Error`（`name` が `CameraDenied`）を throw |
| `stopCamera()` | なし | `void` | カメラを止める |
| `captureFrame()` | なし | `Promise<Blob>` | 最新フレームの JPEG。B は呼ばない（`loop.ts` が呼ぶ） |
| `startMotionLoop(video, onScore)` | `(score: number \| null, brightness: number, cameraOk: boolean) => void`（`null` はウォームアップ中） | `() => void`（止める関数） | 1 秒ごとの動きスコア。B は呼ばない（`loop.ts` が呼ぶ） |
| `startSession(video, sessionId, token, handlers)` | `handlers = {onState, onHint, onBrightness, onConnection, onHeard}` | `() => void`（止める関数） | 下の「ループ」 |
| `requestManualHint()` | なし | `Promise<HintResponse>` | 「ヒント」ボタン。フレームを送ってから `hints` を `manual` で呼び、`speech` を読み上げる |
| `requestCheck()` | なし | `Promise<CheckResponse>` | 「できた」ボタン。フレームを送ってから `check` を呼び、`speech` を読み上げる |
| `advance()` | なし | `Promise<AdvanceResponse>` | 「次へ」ボタン。`POST /advance`。`ended` ならループを止める |
| `end()` | なし | `Promise<void>` | 「おわる」ボタン。`POST /end` → ループ停止 → カメラ停止 |
| `api.ts` の関数 | 03 の表 | | `/ops`・`/log` と、`/device` の最初の `getSession` で使う |

型（`HintResponse`・`CheckResponse`・`AdvanceResponse`・`SignalResponse`・`SessionDetail` など `openapi.yaml` の schemas と同名）は `web/lib/api.ts` が export する。10/16 夜に書いた空実装（`loop.ts` はタイマーでモックの状態を一巡させるだけ）が Day 1 10:35 の `main` に入っていて、関数名・引数・戻り値は当日変わらない（中身だけ 13:00 に差し替わる）。

## ループ（`web/lib/loop.ts`、高橋が書く）

`startSession(video, sessionId, token, handlers)` が 1 つで次を全部やる。B は `handlers` で受け取った値を表示するだけ。

- `startMotionLoop` で 1 秒ごとに `motion` と `brightness` を取り、`postSignal` を送る。応答を `handlers.onState(resp)` に渡す（`state`、`current_problem_no`、`still_seconds`）。
- 応答の `next_action` が `send_frame` なら `captureFrame → postFrame` を行い、`frame_id` を覚えておく（静止が途切れたら忘れる。ADR 0028）。
- 応答の `next_action` が `send_frame_and_request_hint` なら、覚えた `frame_id` があればそれで、無ければ `captureFrame → postFrame` をしてから `requestHint({trigger: "auto", frame_id})` を行い、応答を `handlers.onHint(resp)` に渡し、`speech` があれば `speak` する。一度成功したら、`signals` の `state` が `stuck` 以外になるのを見るまで再要求しない（失敗したときだけ次の秒に再試行）。
- `state` が `created`・`checking`・`ended` のとき、`onHint` は呼ばれない（字幕の固定文は B が `state` で出す）。
- 最初に `state` が `watching` になったとき「見守りを始めるよ」を 1 回読み上げる（B は書かない）。
- `brightness` を `handlers.onBrightness(b)` に渡す（B が 60 未満で「明るさが足りません」を重ねる）。
- `postSignal` が連続 3 回失敗したら `handlers.onConnection(false)`、成功したら `true`（B が「つながりにくいみたい」を出す）。
- **声のトリガー**：`watching`・`still`・`cooldown` の間は `startListening` で聞き取り、「わからない」「わかんない」「ヒント」のどれかを含む文が来たら `requestHint({trigger: "voice"})`（フレームを送ってから）を 1 回送り、応答を `onHint` と `speak`。`speaking`・`checking` の間は `stopListening`（自分の読み上げを拾わないため）。聞き取った文字は `handlers.onHeard(text)` に渡す（B は字幕の下に小さく「聞こえた：わからない」と 3 秒だけ出す）。非対応ブラウザでは何もしない。
- `signals`・`hints`・`check`・`advance` のどの応答でも `state` が `ended` になったらループを止める。戻り値の止める関数でも止まる。
- `requestManualHint()` と `requestCheck()` は同じファイルにあり、動いているセッションの id と token を使う。応答を返し、`speech` があれば `speak` する。

## 再接続

- `signals` の送信は 1 秒ごとに `fetch`。失敗しても次の秒にまた送る。連続 3 回失敗したら「つながりにくいみたい」をヘッダに出す。
- サーバが再起動しても `session_token` はそのまま有効（JSON ファイルにある）。状態は `watching` に戻る。

## 字幕の表示

- `state` が `created`・`checking`・`ended` のときは「状態と表示」の表の固定文。それ以外は直近の `display`（`onHint`・`requestManualHint`・`requestCheck` の応答）を 1 つだけ大きく出す。履歴は出さない（記録画面の仕事）。
- 画面の初期 `state` は `created` 固定。`getSession` の `state` は使わない（`state` は `onState` でだけ更新する。リロードしたら「はじめる」からやり直す）。
- 数式は `display` の文字列をそのまま等幅で出す。自分で整形しない。
- 文字は 24px 以上。机の横 50 cm から読める大きさ。

## ブラウザごとの注意（10/16 夜の T0-2 と Day 1 11:00 に実機で確認。結果は 12 の表に書く）

| 項目 | iOS Safari | Android Chrome | PC Chrome |
|---|---|---|---|
| `getUserMedia` | HTTPS 必須。ユーザー操作の中で呼ぶ。他のタブがカメラを使っていると失敗 | HTTPS 必須 | HTTPS か localhost |
| `speechSynthesis` | ユーザー操作の中で 1 回鳴らさないと以後鳴らない。サイレントスイッチが ON だと鳴らない（要確認） | 概ね問題なし | 問題なし |
| `getVoices()` | 最初は空。`voiceschanged` を待つ | 同じ | 同じ |
| 画面の自動ロック | 無操作で消える。`navigator.wakeLock.request("screen")` を使う（要確認） | 同じ | 不要 |
| バックグラウンド | 他のアプリに切り替えるとカメラが止まる | 同じ | タブ切替で `setInterval` が遅くなる |
| アプリ内ブラウザ | カメラ許可が出ないことがある。Safari で開かせる | 同じ | 該当なし |

## モックでの開発

- `NEXT_PUBLIC_MOCK=1` で API はモックになるが、カメラと音声は本物を使う。
- モックの `postSignal` は各状態 5 秒、`watching → still → stuck → speaking → cooldown` の順で一巡 25 秒（03 の表）。`stuck` の 5 秒の間に `onHint` が 1 回来る。モックの `requestHint` は 1 回目 `hint_level1.json`、2 回目から `hint_level2.json`（文が変わるのは正常）。`postCheck` は `check_correct.json`。`checking` と `ended` はモックの一巡に出ないので、字幕の固定文は `state` を手で切り替えて確認するか、B1-6 の実機で見る。これで B は API なしに全状態の表示を確認できる。
- 開発中の表示確認は PC Chrome で `localhost`。スマホでの確認は Vercel のプレビュー URL（HTTPS）で行う。`http://<PCのIP>:3000` ではカメラが取れない。
