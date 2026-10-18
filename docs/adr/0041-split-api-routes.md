# 0041. api のルートを、要求の型・認可・上限・先読み・記録の形に分ける

- ステータス: 承認
- 日付: 2026-10-19

## 文脈

`api/app/routes.py` は約 900 行になり、pydantic のモデル、認可、回数の上限、先読み、記録の応答の形、14 本のルートが 1 つのファイルにあった（Issue #67）。審査で Git を読む人が、どこに何があるかを追えない。

## 決定

中身は変えず、置き場所だけを次のように分ける。依存は `routes` から外へ一方向で、外のモジュールは `routes` を import しない。

| ファイル | 中身 |
|---|---|
| `errors.py` | HTTP のエラーを投げる `fail()` |
| `context.py` | `AppContext`（設定・保存・写真・先読み・回数）と `Prefetch`、`get_context` |
| `schemas.py` | 要求の型 |
| `auth.py` | トークンと運営の鍵の確認 |
| `limits.py` | 作成の口・AI・声の回数の上限、同時に 1 本。時刻は呼び出し側が渡す |
| `composer.py` | 問題の記録と最新の写真から、AI のヒントを作る入口 |
| `prefetch.py` | 詰まりの 3 秒前の先読みを始める・受け取る・捨てる |
| `views.py` | 記録の応答の形 |
| `routes.py` | ルートと、状態機械を当てて保存する処理 |

## 理由

- ルートを読むと、何を確かめ（`auth`・`limits`）、何を作り（`composer`・`prefetch`）、何を返すか（`views`）が import で分かる
- テストが差し替える時刻（`routes._now`）は `routes` に残し、`limits` には引数で渡す

## 受け入れたトレードオフ

- `Prefetch` は `prefetch.py` でなく `context.py` に置く。`AppContext` が `Prefetch` を持ち、`prefetch.py` が `AppContext` を使うので、`prefetch.py` に置くと import が循環する
