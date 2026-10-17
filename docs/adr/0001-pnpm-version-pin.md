# 0001. pnpm の版は packageManager だけで固定する

- ステータス: 承認
- 日付: 2026-10-17

## 文脈

`docs/tasks/takahashi.md` の T0-6 は「`packageManager` と `engines` で Node・pnpm を固定」と書いている。手元の pnpm は 11.9.0 だが、lockfile の形式は 9.0 で、pnpm 9・10・11 のどれでも読める。Vercel は lockfile の形式から pnpm の版を選ぶので、corepack を有効にしない限り 11 を使うとは限らない。

## 検討した選択肢

1. `packageManager: pnpm@11.9.0` で固定し、`engines` には Node だけを書く
2. `engines.pnpm` にも `^11.9.0` を書く

## 決定

選択肢 1。`engines` は `"node": ">=22"` だけにする。

## 理由

- `engines.pnpm` を書くと、Vercel が pnpm 9・10 で install したときに `ERR_PNPM_UNSUPPORTED_ENGINE` で落ちうる
- B・C・D は `corepack enable` で `packageManager` の版が入り、CI の `pnpm/action-setup` も `packageManager` を読むので、版は揃う

## 受け入れたトレードオフ

- `npm i -g pnpm` で別の版を入れた人は止められない。lockfile の差分で気づく

## 再検討する条件

- Vercel のビルドで pnpm の版の差による不具合が出たとき（Vercel に `ENABLE_EXPERIMENTAL_COREPACK=1` を入れる）
