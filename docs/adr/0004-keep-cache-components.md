# 0004. create-next-app 既定の cacheComponents を残す

- ステータス: 承認
- 日付: 2026-10-17

## 文脈

create-next-app 16.4.2 は `next.config.ts` に `cacheComponents: true` と `partialPrefetching: true` を入れる。`cacheComponents` が有効だと、`useSearchParams` などの動的な値を読む部分は `<Suspense>` の中に置かないと build が落ちる。`/device`（`?s=&t=`）と `/log`（`?k=`）はクエリを読む。

## 検討した選択肢

1. 既定のまま残す
2. 外して、Suspense なしでも build が通るようにする

## 決定

選択肢 1。

## 理由

- AGENTS.md は既に「`useSearchParams` は `<Suspense>` で包む」と決めていて、追加の決まりが要らない
- 雛形の既定から外すと、AI が読む Next 16 の文書と設定が食い違う

## 受け入れたトレードオフ

- Suspense を忘れると `pnpm check` の build で落ちる。B・C は dev では動くのに build で落ちる経験をしうる（docs/11 の「よく踏む穴」に書いてある）

## 再検討する条件

- Suspense が原因の build の失敗で、B・C の PR が 2 回以上止まったとき
