# 0010. openapi の components には使い回す部品だけを足す

- ステータス: 承認
- 日付: 2026-10-17

## 文脈

T0-1 の文は `components/schemas` の名前を 19 個（`SessionCreateRequest` 〜 `Error`）決めている。`state` の値は 9 か所、`settings` は 4 か所、`leak_check` は 2 か所で同じものを使う。`web/lib/api.ts` は openapi の `components/schemas` と同じ名前の型を export する。

## 検討した選択肢

1. 2 か所以上で使う部品だけを components に足し、1 か所だけのものは inline にする
2. 19 個だけにして、残りは全部 inline で書く
3. 入れ子のオブジェクトも全部 components に出す

## 決定

選択肢 1。足すのは `Settings` `State` `Mode` `Trigger` `HintSource` `HintLevel` `LeakCheck` `Verdict` の 8 個。PATCH settings の応答、advance の本文、問題ごとの経過などは inline。

## 理由

- enum を何か所にも重ねて書くと、値を直すときに漏れる
- B・C が `State` 型で表示を分岐でき、画面と API で値の綴りが揃う
- 1 か所だけのものを名前つきにすると、名前が増えるだけで読む手間が増える

## 受け入れたトレードオフ

- T0-1 の文の 19 個と完全には一致しない（19 個はすべてある）

## 再検討する条件

- inline のものが 2 か所目で使われたとき（そのとき components に出す）
