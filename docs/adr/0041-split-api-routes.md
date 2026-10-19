# 0041. api のルートを、要求の型・認可・上限・先読み・記録の形に分ける

- ステータス: 承認
- 日付: 2026-10-19

## 文脈

`api/app/routes.py` は約 900 行になり、pydantic のモデル、認可、回数の上限、先読み、記録の応答の形、15 本のルートが 1 つのファイルにあった（Issue #67）。審査で Git を読む人が、どこに何があるかを追えない。

## 決定

置き場所を次のように分ける。依存は `routes` から外へ一方向で、組み立てる `main` 以外は `routes` を import しない。挙動で変えたのは、回数の上限に使う時刻を要求の始めに読んだ 1 つにそろえたことと、人格や問題が変わった先読みを状態を進めるたびに捨てるようにしたこと（今までは設定の変更のときだけ）。

| ファイル | 中身 |
|---|---|
| `errors.py` | HTTP のエラーを投げる `fail()` |
| `context.py` | `AppContext`（設定・保存・写真・先読み・回数）と `Prefetch`、`get_context` |
| `schemas.py` | 要求の型 |
| `auth.py` | トークンと運営の鍵の確認 |
| `limits.py` | 写真の大きさ、作成の口・AI・声の回数の上限、同時に 1 本。時刻は呼び出し側が渡す |
| `composer.py` | 問題の記録と最新の写真から、AI のヒントと声の答えを作る入口 |
| `prompts.py` | AI への指示文と構造化出力の型（後から `hints.py` を分けた） |
| `utterances.py` | 聞こえた文が「合ってる？」か助けを求める文かの判定（後から `hints.py` を分けた） |
| `prefetch.py` | 詰まりの 3 秒前の先読みを始める・受け取る・残すか捨てるかを決める |
| `views.py` | 応答の形（セッションの作成・一覧・詳細、ヒント、問題の記録） |
| `timing.py` | かかった時間（ミリ秒）を測る `elapsed_ms()`。`routes` と `prefetch` が使う |
| `routes.py` | ルートと、状態機械を当てて保存する処理 |

## 理由

- ルートを読むと、何を確かめ（`auth`・`limits`）、何を作り（`composer`・`prefetch`）、何を返すか（`views`）が import で分かる
- テストが差し替える時刻（`routes._now`）は `routes` に残し、`limits` には引数で渡す

## 受け入れたトレードオフ

- `Prefetch` は `prefetch.py` でなく `context.py` に置く。`AppContext` が `Prefetch` を持ち、`prefetch.py` が `AppContext` を使うので、`prefetch.py` に置くと import が循環する
