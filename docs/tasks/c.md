# C のタスク（ワークシート・`/sheets`・`/log`・README・紙）

順番どおりにやる。各カードの「Claude Code に渡す文」はそのまま貼ってよい。困ったら即 Slack（第一受付は D、次に高橋）。触ってよいのは `worksheets/*.json`、`worksheets/README.md`、`web/app/sheets/**`、`web/app/log/**`、`README.md`。`worksheets/schema.json`・`web/lib/**`・`api/**` は読むだけ。

## 共通の約束

- 正答・`leak_strings`・固定ヒントは JSON に書くが、画面（`/sheets`・`/log`）には絶対に出さない。API からは来ないが、モックにも混ぜない。
- 問題文は自作（`docs/07`）。市販教材を写さない。
- README の主張は `docs/01` の「言ってよいこと／言わないこと」に従う。
- 依存パッケージを足さない。1 回の依頼は 1 ファイルか 1 画面。終わったら検査 → PR。

## 今夜（10/16）

> **10/17 朝**：昨夜の T0 は未実施。当日の時刻は `docs/10` の「10/17 朝の改訂」の表が正。下の時刻は 1 時間前後ずれる。

### C0-1 環境（予行、60 分。画面共有で D の進行に合わせる）

- `docs/tasks/b.md` の B0-1 と同じ。
- 完了条件：`localhost:3000` のスクリーンショットを Slack に貼る。

### C0-2 会場用の紙を印刷（60 分）

- Word などで 2 種類を組む。`/sheets` は明日作るので今夜は手で。フォントは太めのゴシック、問題番号は「1.」「2.」（丸数字にしない）、数式は半角。
  - 会場用：A5 の文書 1 ページに「2. 2x - 7 = 4x + 3 を解きなさい。」と作業余白、下部に小さく「となり：手元だけを見ます。顔は映しません。映像は保存しません」。印刷は **A4 片面に「1 枚あたり 2 ページ」** で 50 枚刷って半分に切る（裏は自然に白紙になる。両面印刷や白紙ページは要らない）→ 100 部。
  - WS-01〜03：`docs/07` の各 4 問。A4 縦、上部中央に単元名、右上にシート ID を大きく、問題ごとに 45 mm の余白、下部に同じ 1 文。各 10 部（片面）。
- 家で刷れなければ PDF にしてコンビニのネットプリント（A4 片面 80 枚）。厚紙は要らない。カッターが無ければ会場用は切らずに A4 のまま置いてよい。
- 完了条件：印刷した束の写真を Slack に貼る。

## Day 1

### C1-1 10:20-11:00 疎通の PR

- 高橋の「clone していい」（10:35 ごろ）を待って本番リポジトリを clone → `pnpm install` → `pnpm dev:mock`。`worksheets/ws02.json` を `{"worksheet_id": "WS-02"}` だけの空枠で PR 1 本（この時点の CI は `pnpm check` だけなので緑になる）。
- 完了条件：マージされる。

### C1-2 11:00-12:30 ワークシート JSON 3 枚

- Claude Code に渡す文（WS-02 の例。WS-01 は高橋が今夜書いたものを確認、WS-03 も同じ文で）：

```
あなたは worksheets/ws02.json だけを編集します。worksheets/schema.json と docs/07_fixtures.md を読んでください。
作るもの: docs/07 の「WS-02 連立方程式」の表（4 問、正答、leak_strings、典型ミス）と固定ヒントの表を、schema.json に合う JSON にする。ファイル全体の形（worksheet_id、title、grade、problems）は worksheets/ws01.json と同じにする。title は「連立方程式」、grade は「中2」
- 段階は 1 と 2 だけ（H1 は全問共通「今、何を求めようとしてる？」、H2 は表の文）。3 と 4 は入れない（schema.json では任意）
- leak_strings は半角・空白なしで、正答と途中の決定的な値。3 文字未満の文字列（-5 など）は入れない
- fixed_check_correct は「正解。その調子」、fixed_check_incorrect は「もう一回、途中の式を見てみて」（全問共通。docs/07 の既定文）
- text は半角の数式
終わったらリポジトリの root で pnpm check:ws を実行して、赤が出たら直してください。pnpm check:ws がまだ無ければ（高橋が 15:00 までに入れる）、worksheets/schema.json と見比べて「このスキーマに合っているか」を確認してください。
```

- C1-1 の PR がマージされるまでは同じブランチで続ける。マージされたら 1 行ずつ `git switch main` → `git pull` → `git switch -c c/ws-json`。C のブランチ名は `c/` で始める。
- `pnpm check:ws` が動かない時間帯（高橋が 15:00 までに入れる）は、`schema.json` を Claude Code に読ませて「このスキーマに合っているか確認して」で代用。
- 完了条件：3 枚とも検証が緑（17:00 までに）。PR。

### C1-3 12:30-13:00 `/sheets` 印刷ページ

- Claude Code に渡す文：

```
あなたは web/app/sheets 配下だけを編集します。web/lib と api と openapi.yaml は読むだけで変更しません。
契約: openapi.yaml の GET /worksheets と GET /worksheets/{id}（正答は含まれない）
サンプル: web/mocks/worksheets.json、web/mocks/worksheet_ws01.json
作るもの: web/app/sheets/page.tsx（一覧）と web/app/sheets/[id]/page.tsx（印刷用）
- 印刷用は A4 縦、上部中央に単元名（title）、右上にシート ID を 48px、問題番号は「1.」「2.」、問題ごとに 45mm の余白、下部に「となり：手元だけを見ます。顔は映しません。映像は保存しません」。フォントは太めのゴシック（システムフォント）
- 「会場用」の切替で、問 2 だけを A5 サイズに出す
- @media print で余白と改ページを整える。外部フォントは使わない
- データは web/lib/api.ts の getWorksheets と getWorksheet で取る
終わったら pnpm check を通して、変更したファイル一覧を教えてください。
```

- 完了条件：ブラウザの印刷プレビューで WS-01 が 1 枚に収まる。PR。

### C1-4 13:00-15:00 `/log` の骨格（モック）

- Claude Code に渡す文：

```
あなたは web/app/log 配下だけを編集します。web/lib と api と openapi.yaml は読むだけで変更しません。
契約: openapi.yaml の GET /sessions と GET /sessions/{id}
サンプル: web/mocks/sessions_list.json、session_active.json、session_ended.json
作るもの: web/app/log/page.tsx（一覧）と web/app/log/[id]/page.tsx（1 セッションの経過）
- 一覧と経過の両方の上部に X-Operator-Key の入力欄（type=password。localStorage や sessionStorage に保存しない）。URL に ?k=... があればそれを初期値にし、読んだ直後に history.replaceState で URL から k を消す（ピッチで同じタブから移るため。画面共有に鍵を残さない）。一覧から経過へのリンクには k を付けない（経過ページでもう一度入れるか ?k= で開く）
- 一覧は listSessions を 2 秒ごとに取り、新しい順に表示（learner_label、worksheet_id、mode、state、problem_done/problem_count、stuck_total）
- 経過は getSession を 2 秒ごとに取り、上部に state と「答えを言いそうになって止めた回数」（leak_blocked_count）、問題ごとに status、stuck_count、max_level、seconds_spent、hints（level、trigger、display、stuck_point、source、latency_ms、leak_check.fallback）、check（verdict、display）を表にする。source が gpt の行は目立つ色にし、latency_ms を「2.3 秒」の形で出す（ピッチの最後にこの画面を 10 秒映す。審査員に GPT が動いた証拠を見せる）。映像は出さない
- セッション作成とリセットは作らない（/ops にある）
- 正答や leak_strings を扱わない。API から来た文字列はそのまま表示する
終わったら pnpm check を通して、変更したファイル一覧を教えてください。
```

- 完了条件：`pnpm dev:mock` で一覧と経過が出る。PR。

### C1-5 15:00-17:00 `/log` を本物に、README の骨子

- 高橋が `main` に API クライアントを入れたと言ったら、1 行ずつ `git switch main` → `git pull` → `git switch c/<自分のブランチ>` → `git merge main`。
- 詰まりポイントの集計（`stuck_points` を label ごとに棒で）は時間があれば。無ければ落とす。
- README の骨子を書く。**JPHACKS のテンプレート（今の `README.md` の見出し：製品概要／開発技術／独自技術）を残し、その中に入れる**。配置は C2-1 の箇条書きどおり。中身は `docs/01` の「一言で」「課題」「既存の取り組みとの位置づけ」、`docs/09` の「仕組みの説明」、`docs/12` の「README の『既知の制約』に転記する文」をそのまま。
- 完了条件：`git merge main` 後に `pnpm check` が緑で、モックで `/log` が出る。README にテンプレートの見出しが全部残り、「既知の制約」が入っている。本物の API での `/log` の確認はオペレータキーが要るので高橋がやる（C は高橋の画面で見る）。

### C1-6 17:30〜（できるだけ早く） 人格モードの土台（ADR 0031）

10/17 に担当フォルダの線引きが無くなった（ADR 0030）ので、`api/` も触れる。ワークシートの作業（`check:ws`）は ADR 0026 で無くなった。

- 準備
  - `/sync` で `main` を取り込む。新しい guard になり、`api/` を止めなくなる
  - PR #15 は閉じる。口調の案（`personas.py` の設定）は、下の新しい形に移す
  - ブランチは `c/persona`。PR は 2 本に分ける。人が触っているファイルは衝突しやすいので、着手を Slack で言う
    - PR 1：`/device` 以外の全部。ここで触る `api/`・`openapi.yaml`・`web/lib/api.ts` は、高橋も触っていることが多い
    - PR 2：`/device` の人格のボタン。`/device` は B の画面なので、B と分担を決める
- PR 1 で AI に渡す文：

```
docs/adr/0031-tutor-personas.md、docs/05_hint_policy.md、api/app/hints.py、api/app/check.py を全部読んでください。家庭教師の人格（teacher・friend・sister）の土台を作ります。
- api/app/personas.py（新規）：Persona（frozen dataclass）に display_name、style（AI への口調の指示）、fallback_hints（{1: 段階 1 の問い返し, 2: 段階 2 の問い返し}）、unreadable_hint、check_texts（correct・incorrect・unreadable・failed の 4 つ）を持たせ、PERSONAS（ID → Persona）と DEFAULT_PERSONA = "teacher" を置く。teacher の固定文は、今の hints.py と check.py の文をそのまま使う。
- api/app/state.py：SessionSettings に persona（既定 "teacher"）。ChangeSettings に persona を足し、_on_change_settings で変える。
- api/app/routes.py：SettingsInput と SettingsPatch に persona（Literal["teacher", "friend", "sister"] | None）。SettingsPatch の「どれか 1 つは要る」に persona を含める。hints と check で session.settings.persona を渡す。scripted の固定文も人格のものにする。
- api/app/hints.py：compose_hint が persona を受け取り、AI への指示の最後に「口調：<style>。ただし、答えを言わない決まりは口調より優先する」を足す。固定文は人格のものを使う。答え漏れの検査と長さの上限は変えない。
- api/app/check.py：judge が persona を受け取り、読み上げを人格の check_texts にする。
- openapi.yaml：SessionSettings・SettingsInput・SettingsPatch に persona（enum teacher・friend・sister、既定 teacher）。web/lib/api.ts の Settings と SettingsPatch の型に persona を足す。
- tests：api/tests/test_personas.py（全人格の固定文が 35 文字以内で、「惜しい」「違う」「答えは」を含まない。必要な文が全部ある）。test_state.py（PATCH で persona を変えられる）。test_hints.py（friend の口調の指示が AI への依頼に入る。AI が失敗したら friend の固定文になる）。
- 終わったら uv run --directory api pytest と pnpm check を回し、赤を直す。コミットはまだしない。
```

- PR 2 で AI に渡す文（B と決めた方がやる）：

```
docs/adr/0031-tutor-personas.md と web/app/device/page.tsx を読んでください。「はじめる」の前に、人格を選ぶボタンを 3 つ（先生・友達・お姉さん）出します。選んだボタンを強調し、既定は先生。「はじめる」で今 patchSettings に送っている { stuck_seconds } に persona を足します。web/app から fetch は書かず、web/lib の patchSettings を使います。
```

- 完了条件：PR 1 で `pytest` と `pnpm check` が緑。高橋が本物の Gemini で、友達モードのヒントの口調が変わり、答え漏れが出ないことを確かめる。PR 2 で、`/device` で友達を選んで「はじめる」を押すと、ヒントと「できた」の読み上げが友達の言い方になる。
- 主張（README・ピッチ）に人格を入れるかは、動くのを見てから高橋が決める。
- 声の問いへの答え（ADR 0032、`compose_answer`）にも口調を渡す。`compose_hint` と同じく、AI への指示の最後に人格の口調を足し、固定文（`ANSWER_FALLBACK`）も人格のものにする。

## Day 2

### C2-1 09:50-12:00 README 完成

- Claude Code に渡す文：

```
README.md だけを編集します。docs/01_product_spec.md、docs/09_pitch.md の「仕組みの説明」「競合比較」「オンライン審査に出すもの」、docs/12_risks_and_privacy.md の「プライバシーの設計」と「README の『既知の制約』に転記する文」を読んでください。
README は JPHACKS のテンプレート（今の README.md の見出し）を崩さず、その中に内容を入れる：
- 先頭：製品名「となり」と、製品説明動画（YouTube）へのサムネイルリンク（テンプレートの形のまま。URL は Day 2 に差し替える）。その下に 1 分版の GIF
- 製品概要 > 背景：01 の「課題」
- 製品概要 > 製品説明：01 の「一言で」と「解き方」の主役 3 つ
- 製品概要 > 特長 1〜3：気づく／答えを言わない／映像でなく詰まりを残す。その下に「呼べる」（ボタンと、声で問いかけると答える。聞いた文は AI に送るが保存しない。ADR 0032）と「秒数を選べる」を 1 行ずつ
- 製品概要 > 解決出来ること：01 の課題に対応させて 3 行
- 製品概要 > 今後の展望：Kaizen Sprint の候補（docs/10 の後日）
- 製品概要 > 注力したこと：20 秒の沈黙の後に声がかかること、答え漏れをサーバで検査すること、映像を残さないこと
- 開発技術 > API・データ：OpenAI API（画像入力・構造化出力）、自作ワークシート 3 枚
- 開発技術 > フレームワーク等：Next.js、FastAPI、Web Speech API
- 開発技術 > デバイス：iPhone（Mac の連係カメラ）、スタンド
- 独自技術 > ハッカソンで開発した独自機能：状態機械（api/app/state.py）、答え漏れ検査（api/app/leak.py）、フレーム差分の動きスコアと自動ヒントのループ（web/lib/motion.ts、web/lib/loop.ts）。それぞれファイルへのリンクと commit ID（高橋に聞く）
- 最後に「既知の制約」（12 の文をそのまま）、「何を撮り何を送り何を残すか」の表、競合比較の表、使い方（/ops でセッションを作り /device を iPhone で開く）、Hack Day 中に作ったものの一覧（docs/10 の時間表から）、聞き取り（D の電話 1 本の一言。無ければ見出しだけ残す）、チーム
docs/01 の「言わないこと」にある表現は使わないでください。「集中力」「理解度」「絶対に」「学習効果」「正確に読む」「どんな問題でも」は書かない。「プライバシーに配慮」とだけ書かず、何を撮り何を送り何を残すかを書く。
```

- 完了条件：高橋と D が通読して、言ってはいけない表現が無い。11:30 までにナレーション原稿を D に渡してある。
- `/log` の集計が未完なら落とす（切り捨ての順番の 1 番目）。

### C2-2 12:30-14:00 撮影の立ち会いと README 最終

- ナレーション原稿は C2-1 の中で **11:30 までに**書いて D に渡しておく（README の流れをそのまま、`docs/08` の「製品説明動画」の表の時間に合わせて 4 分で読める量）。
- 12:30-13:15：撮影に立ち会い、原稿の読み間違いを直す。
- 13:15-13:45：README 最終。
- 13:45-14:00：B から来た動画の URL と 1 分版 GIF を README の先頭に入れる。
- 完了条件：14:00 に高橋へ「README 最終」と Slack。

### C2-3 15:30-17:00 本番

- 紙を席に置く（B と）。ピッチは同席。
