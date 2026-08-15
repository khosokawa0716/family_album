---
name: ship-issue
description: family_albumリポジトリでGitHub Issueを着手から本番反映まで一気通貫で進めるフロー。「Issue #Nを実装して」「実装してPR作って本番まで反映して」のような依頼で使う。決めるべき事項の確認→ローカル実装・検証→PR作成→マージ→Raspberry Pi本番反映の手順と、このリポジトリ固有の注意点（bare-metal開発、SSH接続先、本番の秘密情報管理）をまとめる。
---

# family_album: Issueから本番反映までのフロー

このリポジトリ（family_album）でGitHub Issueに対応し、本番のRaspberry Piまで反映する際の標準フロー。各フェーズの間で、次に進む前にユーザーの意思を確認すること（特にPRのpush/マージ、本番反映は元に戻しにくい操作なので、明示的な許可なく連続実行しない）。

## 0. Issueの確認と、決めるべき事項の質問

- `gh issue view <番号> --repo khosokawa0716/family_album --json title,body,comments,labels,state` で内容を取得する。
- Issue本文に「決めるべき事項」のチェックリストがある場合、実装前に `AskUserQuestion` でまとめて質問する。関連コードを先に読んでから、選択肢に具体的な推奨案（ファイルパス・現状の挙動を踏まえたもの）を提示すると精度が上がる。
- 曖昧さがなく明らかに1つの正解しかない項目（例: 既存画面と表示ロジックを揃えるだけ、等）は質問せず、その場で決めて実装時に一言添える。

## 1. ローカル開発環境（bare-metal がデフォルト）

Docker Composeではなく直接起動する。Docker Composeで確認するのは、nginx込みの本番相当構成を明示的に確認したい時だけ。

```bash
# バックエンド
cd backend && venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000

# フロントエンド（別プロセス）
cd frontend && npm run dev
```

- `venv` はPython 3.10で作成済み・依存インストール済み。`frontend/.env.local` に `NEXT_PUBLIC_API_BASE=http://localhost:8000/api` 設定済み。
- DBはローカルMySQL（brew services、`family_album` DB、接続情報は `backend/.env`）。
- 起動確認: `curl -sf http://localhost:8000/api/health`、`curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:3000/`
- ログはターミナル出力を直接見るか、`> /path/to/scratchpad/backend.log 2>&1 &` のようにバックグラウンド化してscratchpadに出力する。
- テスト用ログイン情報は `docs/local-dev-credentials.md`（gitignore対象、`*credential*`パターン）を参照。消えていた場合の再作成手順もそこに記載。

## 2. 実装・テスト

- バックエンド: `cd backend && venv/bin/python -m pytest tests/ -q`
  - **既存で100件前後の失敗がベースラインとして存在する**（`current_user.nickname` のMagicMock型検証エラー等、本リポジトリの既存不具合でmain上から存在）。新しい変更が原因か切り分けたい場合は `git stash` で変更を退避し、同じテストを再実行して失敗数を比較する（stashしたら必ず `git stash pop` で戻すこと）。
- フロントエンド: `cd frontend && npx tsc --noEmit` と `npx eslint <変更ファイル>`
- UI/フロントエンドが絡む変更は、claude-in-chrome でブラウザ実機確認する（下記4を参照）。型チェックとlintは「コードが壊れていないか」であって「機能が動くか」の確認にはならない。

## 3. ブラウザでの実機確認（claude-in-chrome）

- ネイティブの `alert()` / `confirm()` / `prompt()` を踏むとタブがJS実行ごとブロックされ、`Runtime.evaluate` や screenshot がタイムアウトし続ける。踏んでしまったら `tabs_close_mcp` でタブを閉じて新しいタブでやり直す（クリックで無理に閉じようとしない）。
- Next.js pages routerの動的ルート（`/photo/detail/[id]` 等）で、`router.isReady` を待たずに `router.asPath` を使うと、初回レンダリングでは実URLではなくプレースホルダー（`/photo/detail/[id]` のような未解決の形）が返ることがある。ログイン後リダイレクト先などに使う場合は `router.isReady` を条件に含める。
- テスト用の実データ（group_idなど）が必要な場合、ローカルAPIに直接ログインしてcurlで取得できる:
  ```bash
  TOKEN=$(curl -s -X POST http://localhost:8000/api/login -H "Content-Type: application/json" \
    -d '{"user_name":"nickname_demo","password":"demopass123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
  curl -s "http://localhost:8000/api/pictures?limit=1" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
  ```
- 確認が終わったらローカルサーバーを停止する: `lsof -i :8000 -sTCP:LISTEN` / `lsof -i :3000 -sTCP:LISTEN` でPIDを確認し `kill <PID>`。
- `tsc --noEmit` を実行すると `frontend/tsconfig.tsbuildinfo`（gitトラッキング対象）が更新される。意図しない差分としてコミットに混ざらないよう、コミット前に `git status` で確認し、不要なら `git checkout -- frontend/tsconfig.tsbuildinfo` で戻す。

## 4. PR作成（ユーザーの許可を得てから push）

```bash
git checkout -b <種別>/<内容を表す短い名前>   # feat/... や fix/...
git add <変更ファイルを明示的に列挙>            # git add -A や git add . は使わない
git commit -m "$(cat <<'EOF'
<type>: <日本語で要約>

<背景・理由（whyを中心に）>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

push・PR作成はshared stateを変更する操作なので、実行前にユーザーに確認する。

```bash
git push -u origin <branch>
gh pr create --title "<type>: <要約>" --body "$(cat <<'EOF'
## Summary
- ...

Closes #<issue番号>   # Issue対応の場合

## Test plan
- [x] ...

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

## 5. マージ

- `gh pr view <番号> --json state,mergeable,mergeStateStatus` でマージ可能か確認。
- このリポジトリの過去のコミット履歴にマージコミットが存在しない（`git log --all --merges` が空）ため、squash mergeが慣習に合う:
  ```bash
  gh pr merge <番号> --squash --delete-branch
  ```
- マージもshared stateへの変更のため、実行前にユーザーに確認する。

## 6. 本番（Raspberry Pi）への反映

- 接続先は `album.local`（mDNS）。IP直指定（`192.168.x.x`）はDHCPで変わるため避ける。`~/.ssh/config` の `Host album` は `HostName album.local` になっているはず。
- 本番リポジトリのパス: `/srv/family_album/api`。`docker compose` で運用（`docker-compose.yml` はリポジトリ管理下）。
- **秘密情報・環境変数はリポジトリの `docker-compose.yml` に直書きしない。** Pi上の `/srv/family_album/api/docker-compose.override.yml`（`.gitignore`対象、mode 600）に集約されている（`LINE_CHANNEL_ACCESS_TOKEN`、`FRONTEND_URL` 等）。新しい環境変数が必要な変更をデプロイする際は、pull後にこのファイルを編集する。

### 反映手順

```bash
# 1. 本番のgit状態がcleanか確認してからpull
ssh album.local "cd /srv/family_album/api && git status --short"
ssh album.local "cd /srv/family_album/api && git pull --ff-only"

# 2. 新しい環境変数が必要な場合のみ: バックアップしてから override ファイルを編集
ssh album.local "cd /srv/family_album/api && cp docker-compose.override.yml docker-compose.override.yml.bak"
# sed か手動編集で環境変数を追記する

# 3. 変更のあったサービスだけ再ビルド・再起動（api / frontend / nginx を必要に応じて）
ssh album.local "cd /srv/family_album/api && docker compose up --build -d api"
# フロントエンドも変更していれば: docker compose up --build -d api frontend

# 4. 動作確認
ssh album.local "cd /srv/family_album/api && docker compose ps"                     # 全サービスhealthyか
ssh album.local "curl -sf http://localhost:80/api/health"                            # {"status":"ok"}
ssh album.local "cd /srv/family_album/api && docker compose logs api --tail 20"      # エラーがないか
```

- 本番反映は最も取り返しがつきにくい操作。pull・rebuild・restartの各ステップの前に、状況を簡潔に伝えながら進める。
- `docker compose down` や `system prune` などの破壊的操作は、ユーザーが明示的に依頼した場合以外は使わない。

## 7. 完了報告

- 何を実装し、どう検証し（テスト結果・ブラウザ確認内容）、本番のどのコンテナを再ビルドしたかを簡潔にまとめる。
- 実機（LINE通知など、ローカルで完全には再現できないもの）でしか確認できない項目が残っている場合は、その旨を明記する。
