# 0003. Next.js の agentRules を切り、web/AGENTS.md を作らせない

- ステータス: 承認
- 日付: 2026-10-17

## 文脈

Next.js 16 の `next dev` は、起動のたびに `web/AGENTS.md` に AI 向けの注意書きを書き込み、消しても作り直す。`web/AGENTS.md` は B・C・D の担当外なので、git のフック（guard）がそのコミットを止める。AI 開発の決まりは root の `AGENTS.md` に 1 本でまとめている。

## 検討した選択肢

1. `next.config.ts` に `agentRules: false` を入れ、雛形の `web/AGENTS.md` を消す
2. `web/AGENTS.md` をコミットし、guard で全員に許す

## 決定

選択肢 1。

## 理由

- B・C・D の手元で毎回「担当外のファイル」が出ると、AI に慣れていない 3 人が原因を判断できず止まる
- 決まりの置き場が 2 つになると、root の `AGENTS.md` と食い違う

## 受け入れたトレードオフ

- Next.js の AI 向け注意書き（Next 16 は学習データと違うので `node_modules/next/dist/docs/` を読め）が入らない。必要なら root の `AGENTS.md` に 1 行足す

## 再検討する条件

- AI が Next 16 の古い書き方を繰り返し、注意書きが要ると分かったとき
