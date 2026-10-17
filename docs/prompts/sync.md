# main の最新を取り込む

PowerShell なので 1 行ずつ実行する（`&&` でつながない）。

1. `git status` で未コミットの変更が無いことを確かめる。あれば先に `docs/prompts/pr.md`。
2. `git switch main`
3. `git pull`
4. 次の作業を始めるなら `git switch -c <役割>/<短い名前>`。続きのブランチがあるなら `git switch <そのブランチ>` → `git merge main`。
5. `pnpm install`（依存が増えていることがある）。
6. `pnpm dev:mock` を起動し直して、画面が出ることを確かめる。
7. 衝突（CONFLICT）が出たら自分で解決せず、`git merge --abort` して高橋に Slack。
