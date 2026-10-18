# ADR（設計判断の記録）

設計上の判断を、判断した時点の文脈と一緒に残す。後から「なぜこうなっているか」を読めるようにし、前提が変わったときに見直せるようにする。仕様の正は `docs/00〜12` と `openapi.yaml` で、ADR は docs に書かれていない判断を補う。

## 書く契機

- 選択肢が 2 つ以上あり、後から戻しにくい判断をしたとき
- docs に書かれていない挙動を決めたとき
- 実装より先に書く

## ルール

- 置き場は `docs/adr/NNNN-短いタイトル.md`。番号は 4 桁の連番で欠番を作らない
- 一度承認した ADR は書き換えない。覆すときは新しい ADR を書き、古い方のステータスを「廃止（Superseded by NNNN）」にする
- 1 ファイル 1 テーマ。区切りは見出し階層で表し、水平線は使わない。図は Mermaid
- 書くのは高橋（`docs/adr/` は高橋の担当）
- 項目は下のテンプレートに従う

## テンプレート

```markdown
# NNNN. 判断を一文で

- ステータス: 提案 / 承認 / 廃止（Superseded by NNNN）
- 日付: YYYY-MM-DD

## 文脈

## 検討した選択肢

## 決定

## 理由

## 受け入れたトレードオフ

## 再検討する条件
```

## 一覧

| 番号 | タイトル | ステータス |
|---|---|---|
| 0001 | [pnpm の版は packageManager だけで固定する](0001-pnpm-version-pin.md) | 承認 |
| 0002 | [web の check は next typegen で型を作ってから検査する](0002-check-runs-typegen.md) | 承認 |
| 0003 | [Next.js の agentRules を切り、web/AGENTS.md を作らせない](0003-disable-next-agent-rules.md) | 承認 |
| 0004 | [create-next-app 既定の cacheComponents を残す](0004-keep-cache-components.md) | 承認 |
| 0005 | [CLAUDE.md は AGENTS.md の取り込みにする](0005-claude-md-imports-agents-md.md) | 承認 |
| 0006 | [CI の担当検査は PR の作者の役割で行う](0006-ci-checks-pr-author.md) | 承認 |
| 0007 | [鍵が無いか不一致なら 401、系統違いなら 403 を返す](0007-401-and-403.md) | 承認 |
| 0008 | [エラーの code はステータスごとに固定の 8 値にする](0008-fixed-error-codes.md) | 承認 |
| 0009 | [POST /sessions は 201 を返す](0009-create-session-201.md) | 承認 |
| 0010 | [openapi の components には使い回す部品だけを足す](0010-shared-schema-components.md) | 承認 |
| 0011 | [存在しない worksheet_id は 422 にする](0011-unknown-worksheet-422.md) | 提案 |
| 0012 | [signals の必須項目は force_stuck の有無で変える](0012-signal-required-fields.md) | 提案 |
| 0013 | [読めなかった check の next_problem_no は今の番号にする](0013-unreadable-next-problem.md) | 提案 |
| 0014 | [openapi の Error は web/lib では ApiErrorBody の名前で export する](0014-error-type-named-api-error-body.md) | 提案 |
| 0015 | [WS-01 の正誤の固定文は 4 問とも問題専用にする](0015-ws01-problem-specific-check-text.md) | 廃止（Superseded by 0026） |
| 0016 | [signals 以外の応答で ended になったら onState に ended を渡す](0016-emit-ended-to-on-state.md) | 提案 |
| 0017 | [ended になったらカメラを止める](0017-stop-camera-on-ended.md) | 提案 |
| 0018 | [読み上げの間は聞き取りを止め、ヒントとチェックは 1 つずつ送る](0018-mute-and-serialize-requests.md) | 提案 |
| 0019 | [end() は postEnd が失敗しても手元のループとカメラを止める](0019-end-stops-locally-on-failure.md) | 提案 |
| 0020 | [静止の始まりは、静止に入る直前の signals の時刻にする](0020-still-since-from-previous-signal.md) | 提案 |
| 0021 | [存在しない session id は認可より先に 404 を返す](0021-not-found-before-auth.md) | 提案 |
| 0022 | [正解の読み上げ中の「次へ」は、読み上げを止めるだけにする](0022-advance-after-correct-only-stops-speech.md) | 提案 |
| 0023 | [Railway と Vercel は Mac から CLI でデプロイする](0023-deploy-from-mac-with-cli.md) | 承認 |
| 0024 | [Vercel のプレビューは保護を外して公開する](0024-public-vercel-previews.md) | 承認 |
| 0025 | [ヒントの H2 と正誤判定は Gemini API の無料枠（gemini-3.5-flash-lite）で行う](0025-gemini-free-tier.md) | 承認 |
| 0026 | [ワークシートをやめ、初見の問題に 1 回目から AI のヒントを出す](0026-unseen-problems-ai-first.md) | 承認 |
| 0027 | [動きのスコアから明るさの変化を除き、静止を抜ける境目を高くする](0027-stillness-brightness-and-hysteresis.md) | 承認 |
| 0028 | [stuck の 3 秒前にフレームを送らせ、AI のヒントを先に作っておく](0028-prefetch-hint-before-stuck.md) | 承認 |
| 0029 | [ヒントは最初の誤りか次の一歩を示し、答えまで導く](0029-hint-guides-to-the-answer.md) | 承認 |
| 0030 | [担当フォルダの線引きをなくし、事故の防止だけ残す](0030-remove-folder-ownership.md) | 承認 |
| 0031 | [家庭教師の人格を /device で選び、ヒントの口調と固定文と正誤の読み上げを変える](0031-tutor-personas.md) | 承認 |
| 0032 | [聞こえた文をすべて AI に渡し、問いには説明も含めて答える](0032-answer-what-the-learner-says.md) | 承認 |
| 0033 | [ヒントと声の答えの精度の穴を 6 つふさぐ](0033-hint-precision-holes.md) | 承認 |
| 0034 | [「はじめる」の直後と問題が変わったときに、問題文だけを AI に読ませる](0034-read-problem-at-start.md) | 承認 |
| 0035 | [読み上げを VOICEVOX の声にし、失敗したらブラウザの音声合成に戻す](0035-voicevox-speech.md) | 承認 |
| 0037 | [stuck の間も「できた」「次へ」を受け、作りかけのヒントは捨てる](0037-check-and-advance-while-stuck.md) | 承認 |
