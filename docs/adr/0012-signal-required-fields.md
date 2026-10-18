# 0012. signals の必須項目は force_stuck の有無で変える

- ステータス: 承認
- 日付: 2026-10-17

## 文脈

`docs/03` の signals の本文は `{ts, motion, camera_ok}`。`motion` はウォームアップ中に省略する。`force_stuck: true`（`/ops` の強制 stuck）のときは「`motion` と `camera_ok` は省略可」とある。通常の signals で `camera_ok` が無いときの扱いは書いていない。

## 検討した選択肢

1. `force_stuck: true` なら `ts` だけ必須、それ以外は `ts` と `camera_ok` が必須（JSON Schema の if/then/else）
2. 全部任意にし、`camera_ok` が無ければ false とみなす
3. 常に `ts` と `camera_ok` を必須にする

## 決定

選択肢 1。`motion` はどちらでも任意。

## 理由

- 03 の文をそのまま表せる
- 通常の signals で `camera_ok` を落とすのは `web/lib/loop.ts` の誤りなので、422 で早く気づける
- 選択肢 3 は `/ops` に意味のない `camera_ok` を送らせる

## 受け入れたトレードオフ

- FastAPI 側で、Pydantic のモデルに「force_stuck でなければ camera_ok が必須」の検証を書く必要がある

## 再検討する条件

- 高橋の確認で別の扱いがよいとなったとき
