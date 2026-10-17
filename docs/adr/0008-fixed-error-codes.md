# 0008. エラーの code はステータスごとに固定の 8 値にする

- ステータス: 承認
- 日付: 2026-10-17

## 文脈

`docs/03` のエラー形式は `{"error": {"code": "STATE_CONFLICT", "message": "..."}}` で、code の例は 1 つだけ。`web/lib/api.ts` はエラーを `ApiError(status, code)` で投げ、B・C の画面はそれを受けて文言を選ぶ。

## 検討した選択肢

1. ステータスごとに固定の code を enum で決める
2. code は自由な文字列で、例だけ置く

## 決定

選択肢 1。

| status | code | いつ |
|---|---|---|
| 400 | `BAD_REQUEST` | 本文が JSON（frames は multipart）として読めない |
| 401 | `UNAUTHORIZED` | 鍵が無いか一致しない |
| 403 | `FORBIDDEN` | 鍵は正しいが系統が違う（ADR 0007） |
| 404 | `NOT_FOUND` | セッションかワークシートが無い。`DEMO_MODE` でない `/demo/reset` |
| 409 | `STATE_CONFLICT` | 今の状態では受理できない |
| 413 | `FRAME_TOO_LARGE` | フレームが 600 KB を超えた |
| 422 | `VALIDATION_ERROR` | 型・範囲・必須の違反 |
| 503 | `HINT_UNAVAILABLE` | 固定ヒントも読めない |

## 理由

- B・C の AI が code で分岐を書きやすく、モックと本物で値が揃う
- 値が増えたり綴りが揺れたりしても、openapi の enum との差で気づける

## 受け入れたトレードオフ

- FastAPI の既定の 422（`{"detail": [...]}`）と HTTPException の形を、この形に包み直す例外ハンドラが要る

## 再検討する条件

- 同じステータスの中で画面の動きを変えたい理由が出たとき（code を足す）
