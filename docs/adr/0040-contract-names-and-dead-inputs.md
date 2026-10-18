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
- 保存済みの記録の `gpt` は、読み込むときに `ai` に読み替える（手元の `data/tonari.json` でも、AI のヒントの数え方と段階が変わらない）
- `GET /worksheets` と `GET /worksheets/{id}`、印刷の設定、学年を消す。`/healthz` の `worksheets` を消す。ワークシートの dict をやめ、`FREE` 1 つだけを持つ。セッション作成の `worksheet_id` は `FREE` だけを受け付ける（型で縛り、それ以外は今までどおり 422）
- `POST /signals` の `ts` と、`POST /advance` の本文（`reason`）を契約から消し、web も送らない。サーバは知らない項目を無視するので、古い web が送っても壊れない
- `frame_id`（ヒント・できた・問題文）は残す。サーバはそのセッションの最新の写真を使うことを契約の説明に書く

## 理由

- 契約は読む人への説明でもあり、名前が仕組みと違うと、審査で Git を読む人が最初に引っかかる

## 受け入れたトレードオフ

- `source` と `/healthz` の名前の変更は互換が無い。web と api を同じ時に出す必要がある（api を先に出すと、web の記録画面で AI のヒントのラベルが一時的に出ない）
