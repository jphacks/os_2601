# 0002. web の check は next typegen で型を作ってから検査する

- ステータス: 承認
- 日付: 2026-10-17

## 文脈

T0-6 は `web` の `check` を `eslint . && tsc --noEmit && next build` と決めている。Next.js 16 の雛形の `layout.tsx` は、`next dev`・`next build`・`next typegen` が `.next/types` に作る `LayoutProps` を使う。clone したばかりの手元と CI にはこの型が無く、`tsc --noEmit` が `Cannot find name 'LayoutProps'` で落ちることを確かめた。

## 検討した選択肢

1. `check` の先頭に `next typegen` を足す
2. layout で `LayoutProps` を使わず、型を手で書く

## 決定

選択肢 1。`check` は `next typegen && eslint . && tsc --noEmit && next build`。

## 理由

- B・C の AI は Next 16 の生成型（`PageProps` など）を使うので、選択肢 2 では各自のページで同じ失敗が起きる
- 型を作ってから検査すれば、手元と CI で結果が揃う

## 受け入れたトレードオフ

- docs の `check` の定義から 1 語増える。check が 1 秒ほど長くなる

## 再検討する条件

- Next.js が `tsc` の前に型を作らなくても済むようになったとき
