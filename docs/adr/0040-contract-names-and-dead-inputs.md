# 0040. 契約の名前を今の仕組みにそろえ、使っていない口と入力を消す

- ステータス: 承認
- 日付: 2026-10-18

## 文脈

生成 AI を OpenAI から Gemini に替え（ADR 0025）、自前のワークシートをやめた（ADR 0026）が、契約には前の名前と口が残っていた。精査（Issue #67・#68）で次を挙げた。

- ヒントの出どころ `source` の値が `gpt`。`/healthz` の鍵の有無も `gpt`。コードと記録を読む人が OpenAI を使っていると取り違える
- `GET /worksheets`・`GET /worksheets/{id}` と印刷の設定（`PRINT_LAYOUT`）は、web から呼ばれていない。`/healthz` の `worksheets` も、ワークシートの dict も、`FREE` 1 件のためにある
- `POST /signals` の `ts` と `POST /advance` の `reason` は、web が送るがサーバは読まない。サーバは自分の時刻で状態を進める（ADR 0020）

## 決定

- `source` の値 `gpt` を `ai` にする。`/healthz` の `gpt` を `ai` にする
- `GET /worksheets` と `GET /worksheets/{id}`、印刷の設定、学年を消す。`/healthz` の `worksheets` を消す。ワークシートの dict をやめ、`FREE` 1 つだけを持つ。セッション作成の `worksheet_id` は `FREE` だけを受け付ける（今までどおり、それ以外は 422）
- `POST /signals` の `ts` と、`POST /advance` の本文（`reason`）を契約から消し、web も送らない。サーバは知らない項目を無視するので、古い web が送っても壊れない
- `frame_id`（ヒント・できた・問題文）は残す。サーバはそのセッションの最新の写真を使うことを契約の説明に書く

## 理由

- 契約は読む人への説明でもあり、名前が仕組みと違うと、審査で Git を読む人が最初に引っかかる
- 本番には永続の保存先が無く（再デプロイで記録は消える）、`gpt` を書いた古い記録を読み替える必要が無い

## 受け入れたトレードオフ

- `source` と `/healthz` の名前の変更は互換が無い。web と api を同じ時に出す必要がある（api を先に出すと、web の記録画面で AI のヒントのラベルが一時的に出ない）
- 手元の `data/tonari.json` に残った `gpt` の記録は、読み込めるが AI のヒントとして数えない
