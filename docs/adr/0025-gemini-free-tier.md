# 0025. ヒントの H2 と正誤判定は Gemini API の無料枠（gemini-3.5-flash-lite）で行う

- ステータス: 承認
- 日付: 2026-10-17

## 文脈

`docs/00` の決定事項（10/15）は、ヒント生成と正誤チェックを OpenAI（`gpt-6.1-sol`・`gpt-6-luna`）にしていた。10/17 に高橋が「費用を抑えたい。Gemini でいけるならそうしたい」とした。OpenAI の見積もりは 2 日で数百円（上限 10 ドル）で、Gemini の無料枠なら 0 円になる。ただし無料枠では、送った内容が Google のサービス改善に使われる（有料枠では使われない）。`hints.py`・`check.py` はまだ書いていない。

10/17 14:30 に、Railway の環境変数の鍵で、無料枠の Gemini に `docs/05` と同じ形の依頼（答案の画像 1 枚、HintOut の JSON）を送って確かめた。

| モデル | 秒数 | 考える工程 | 答え漏れ |
|---|---|---|---|
| gemini-3.5-flash-lite | 2.0 | なし | なし |
| gemini-flash-lite-latest | 2.1 | なし | なし |
| gemini-3.8-flash（考える量 low） | 3.6〜6.0 | 約 90〜130 トークン | なし |
| gemini-3.8-flash | 6.2〜6.3 | 約 440 トークン | なし |

omni 系は無料枠の割り当てが 0 で使えなかった（429）。

## 検討した選択肢

1. Gemini の無料枠、H2 も判定も gemini-3.5-flash-lite
2. Gemini の無料枠、H2 は gemini-3.8-flash（考える量 low）、判定は lite
3. Gemini の有料枠
4. OpenAI のまま

## 決定

選択肢 1（高橋が選んだ）。

- `HINT_MODEL` と `CHECK_MODEL` は `gemini-3.5-flash-lite`、鍵は `GEMINI_API_KEY`（Railway）
- 呼び方は REST の `generateContent`（`systemInstruction`、画像は `inline_data` の JPEG、`responseMimeType: application/json` と `responseSchema`）。SDK を足さず、httpx で 8 秒・リトライなし
- 429・5xx・タイムアウトは、これまでどおり固定ヒント（`source: "fallback"`）と「うまく読めなかった」に落とす
- API の契約は変えない。`source: "gpt"` と `/healthz` の `gpt` は「生成 AI が作った」「生成 AI の鍵がある」の意味で使い続け、実際のモデル名は `model` に入れる。docs の「GPT」も生成 AI の総称として読む
- README・`docs/12`・ピッチのプライバシーの説明は、「Hack Day 版は Gemini API の無料枠を使い、送った 1 枚は Google のサービス改善に使われうる。製品では学習に使わない有料枠にする」と正直に書く

## 理由

- 費用が 0 円で、約 2 秒と速く、壇上で「考え中？」の後の間が空かない
- 送るのは Hack Day の間、チームが解いたワークシートの写真だけで、本物の利用者の画像ではない
- 契約を変えないので、B・C の画面とモックはそのまま使える

## 受け入れたトレードオフ

- 無料枠の間は、送った画像が Google の改善に使われうる。プライバシーの説明が弱くなる
- 無料枠は回数の上限が低い。超えると固定ヒントに落ちる（声は止まらない）
- lite の文は 3.8-flash より少し硬い
- docs の「GPT」という言葉と実際の提供元がずれる

## 再検討する条件

- 無料枠の上限に当たって固定ヒントばかりになったとき（有料枠にする）
- 中間発表や Award Day の前に、プライバシーの説明を強くしたいとき（有料枠にする）
- 文の質が足りないとき（gemini-3.8-flash の考える量 low にする）
