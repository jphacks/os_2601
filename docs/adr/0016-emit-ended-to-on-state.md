# 0016. signals 以外の応答で ended になったら onState に ended を渡す

- ステータス: 提案
- 日付: 2026-10-17

## 文脈

`docs/06` の「ループ」は「signals・hints・check・advance のどの応答でも state が ended ならループを止める」と書く。`docs/tasks/b.md` は「onState の state が ended になったら おつかれさま を出す」と決めている。ended が signals 以外（最後の問題の正解、最後の advance、end）から来ると、ループが止まるので onState に ended が届かず、B の画面が終わらない。

## 検討した選択肢

1. `loop.ts` が、signals 以外で ended になったときにループを止めてから onState に ended を 1 回渡す
2. B が advance・requestCheck・end の戻り値も見て、自分で ended にする

## 決定

選択肢 1。渡すのは `{state: "ended", still_seconds: 0, current_problem_no, next_action: null, cooldown_remaining: 0}`。

## 理由

- B は onState だけを見ればよく、「state は onState でだけ更新する」（docs/06 の字幕の表示）を崩さない
- 終わり方が 4 通りあっても、画面の処理は 1 つで済む

## 受け入れたトレードオフ

- サーバから来ていない SignalResponse を loop.ts が作る

## 再検討する条件

- B の画面が戻り値でも状態を持つようになったとき
