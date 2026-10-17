# 0005. CLAUDE.md は AGENTS.md の取り込みにする

- ステータス: 承認
- 日付: 2026-10-17

## 文脈

AI 開発の決まりは、Claude Code が読む `CLAUDE.md` と Codex が読む `AGENTS.md` の 2 本に同じ中身で置いていた（ハーネスの作り）。Hack Day 中に決まりを直すことがあり、片方だけ直すと 2 つの道具で決まりが食い違う。

## 検討した選択肢

1. `CLAUDE.md` を `@AGENTS.md` の 1 行にして、中身は `AGENTS.md` だけに持つ
2. 同じ中身の 2 本を持ち、直すときは両方直す
3. `CLAUDE.md` を `AGENTS.md` へのシンボリックリンクにする

## 決定

選択肢 1。

## 理由

- Claude Code は `CLAUDE.md` の `@path` を取り込むので、読む中身は同じになる
- シンボリックリンクは Windows（B・C・D）の git で実体のファイルにならないことがある

## 受け入れたトレードオフ

- `CLAUDE.md` だけを開いた人には中身が見えない

## 再検討する条件

- Claude Code が `AGENTS.md` を直接読むようになったとき（`CLAUDE.md` を消す）
