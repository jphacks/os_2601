# PR を出す

1. `docs/prompts/check.md` の検査を通す。赤のまま進めない。
2. `git status` で触ったファイルが担当内だけか見る。担当外が混ざっていたら `git restore <file>` で戻す。
3. `git add <担当のファイルだけ>`（`git add .` はしない）。
4. `git commit -m "<役割>: <何を作ったか 1 行>"`。コミットがフックで止まったら、理由のファイルを `git restore --staged <file>` で外して、もう一度。
5. `git push -u origin <今のブランチ>`。`main` には push しない。
6. `gh pr create --fill --base main` で PR を作る。本文は `.github/pull_request_template.md` の項目を埋める（スクリーンショットは私が貼る）。
7. PR の URL を出して、Slack に貼る文「<役割> PR: <URL> <1 行>」を作る。
8. マージは高橋がする。マージされたら `docs/prompts/sync.md`。
