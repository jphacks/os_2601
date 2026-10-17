# 0023. Railway と Vercel は Mac から CLI でデプロイする

- ステータス: 承認
- 日付: 2026-10-17

## 文脈

本番リポジトリは JPHACKS の org（jphacks/os_2601）にある。Railway と Vercel の GitHub 連携で push ごとに自動でデプロイするには、両社の GitHub App を org に入れる承認が要り、運営待ちで止まりうる。10/17 の昼の時点で、Railway も Vercel もまだ用意していなかった。

## 検討した選択肢

1. 高橋の Mac から CLI（`railway up`、`vercel deploy`）でデプロイする
2. ダッシュボードで GitHub 連携する
3. Mac で API と Web を動かし、cloudflared の一時 URL で HTTPS にする（docs の退避 L3）

## 決定

選択肢 1。構成は次のとおり。

| 項目 | Railway | Vercel |
|---|---|---|
| プロジェクト | `tonari`、サービス `api` | `tonari`（Hobby） |
| 公開 URL | `https://api-production-67c3.up.railway.app` | `https://tonari-nine.vercel.app` |
| ビルド | `RAILWAY_DOCKERFILE_PATH=api/Dockerfile`、文脈は repo の root | Root Directory `web`、Next.js |
| 環境変数（秘密以外） | `HINT_MODEL` `CHECK_MODEL` `CORS_ORIGINS` `DATA_PATH` `DEMO_MODE` | Production に `NEXT_PUBLIC_API_BASE`、Preview に `NEXT_PUBLIC_MOCK=1` |
| 秘密 | `OPENAI_API_KEY` `OPERATOR_KEY` は高橋がダッシュボードで入れる | なし |
| デプロイ | main を `railway up --service api --ci` | main を `vercel deploy --prod`、ブランチは `vercel deploy` |

CLI で上げるときに `.env*`・`api/`・`docs/` などを上げないよう、root に `.vercelignore` を置く。Railway の `railway up` は `.gitignore` を使う。

## 理由

- org の承認が要らず、その日のうちに縦串まで通せる
- 秘密の値はダッシュボードで入れるので、作業の画面に出ない

## 受け入れたトレードオフ

- push しても自動ではデプロイされない。main へのマージのたびと、B・C のブランチのプレビューは高橋が手で打つ
- デプロイできるのは CLI にログインした高橋の Mac だけ

## 再検討する条件

- org で GitHub App の承認が取れたとき（ダッシュボードの連携に切り替える）
