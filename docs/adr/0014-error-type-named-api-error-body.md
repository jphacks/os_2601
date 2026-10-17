# 0014. openapi の Error は web/lib では ApiErrorBody の名前で export する

- ステータス: 提案
- 日付: 2026-10-17

## 文脈

T0-1 の文は「`web/lib/api.ts` は openapi.yaml の components/schemas と同名の型を export する」と決めている。schemas の `Error`（`{error: {code, message}}`）を同じ名前で export すると、import した B・C のファイルで JS の組み込みの `Error` が型として隠れる。

## 検討した選択肢

1. `ApiErrorBody` の名前で export し、code の値は `ErrorCode` として別に export する
2. `Error` のまま export する

## 決定

選択肢 1。ほかの 26 の型は openapi と同じ名前。

## 理由

- `catch (e: Error)` などで、組み込みの `Error` と取り違える事故を防ぐ
- 投げる例外が `ApiError` なので、その本文として `ApiErrorBody` は読み取りやすい

## 受け入れたトレードオフ

- openapi と `web/lib` で 1 つだけ名前が違う

## 再検討する条件

- なし
