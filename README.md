# Slack → Claude 要約 → LINE 通知 (MVP)

指定したSlackチャンネルの直近メッセージを取得し、Claude APIで日本語要約し、
LINE Messaging APIで自分のLINEへ送信するだけのシンプルなCLIツールです。

DB・Web画面・ログイン機能・複雑な設定画面は持ちません。`python main.py` を
手動実行することだけを想定しています。

## できること

1. Slack `conversations.history` から指定チャンネルの直近 `LOOKBACK_HOURS` 時間分の
   通常テキストメッセージを取得する（システムメッセージ・Bot投稿・スレッド返信は対象外）
2. Claude APIで「重要事項 / 決定事項 / TODO・期限 / その他」の4項目に沿って日本語要約する
3. LINE Messaging APIのpush messageで指定ユーザーへ送信する

対象メッセージが1件も無い場合は、Claude APIもLINE APIも呼ばずに終了します。

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. `.env` の作成

```bash
cp .env.example .env
```

`.env` に以下を設定します。

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-5
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=U0123456789abcdef0123456789abcdef
LOOKBACK_HOURS=24
```

`ANTHROPIC_MODEL` と `LOOKBACK_HOURS` は省略可能です（それぞれ
`claude-opus-5` / `24` がデフォルト値として使われます）。

### 3. Slack側の準備

1. https://api.slack.com/apps で新規Appを作成（または既存Appを利用）
2. 「OAuth & Permissions」→「Bot Token Scopes」に以下を追加
   - `channels:history`（パブリックチャンネルの場合）または `groups:history`（プライベートチャンネルの場合）
   - `users:read`（投稿者の表示名を解決するため）
3. ワークスペースにインストールし、`Bot User OAuth Token`（`xoxb-`で始まる）を `SLACK_BOT_TOKEN` に設定
4. 対象チャンネルで `/invite @アプリ名` を実行し、Botをチャンネルに参加させる
   （参加していないと `not_in_channel` エラーになります）
5. 対象チャンネルを開き、チャンネル名をクリックして表示される Channel ID を `SLACK_CHANNEL_ID` に設定

### 4. Claude API側の準備

1. https://console.anthropic.com の「API Keys」でキーを発行し `ANTHROPIC_API_KEY` に設定

### 5. LINE側の準備

1. https://developers.line.biz/ で Messaging API チャンネルを作成
2. 「Messaging API設定」タブで `Channel access token (long-lived)` を発行し
   `LINE_CHANNEL_ACCESS_TOKEN` に設定
3. 同チャンネルの「チャンネル基本設定」最下部にある `Your user ID`（自分自身のuserId、
   `U`で始まる文字列）を `LINE_USER_ID` に設定
   - 自分以外のユーザーに送る場合は、Webhookを受けて `events[0].source.userId` を取得する必要があります（MVPの対象外）
4. 「Messaging API設定」タブのQRコードから、このBotを友だち追加しておく
   （友だち追加していないと push 送信が `403` エラーになります）

## 実行方法

```bash
python main.py
```

成功すると、取得件数・要約内容・LINE送信完了がコンソールに表示されます。

## 定期実行と重複通知防止

- 取得期間は「前回正常に処理した終了時刻より後 ～ 今回の処理開始時刻」です。
  終了時刻は `state.json` に UTC で保存されます（初回は直近 `LOOKBACK_HOURS` 時間）。
- 新着0件の場合は Claude / LINE を呼ばず、確認した時刻だけを保存します。
- Slack取得・Claude要約・LINE送信のいずれかが失敗した場合は時刻を更新しないため、
  次回実行時に同じ期間を再処理します。
- `state.json` を削除すると、次回は初回扱い（直近 `LOOKBACK_HOURS` 時間）になります。
- 実行結果は `logs/main.log` に記録されます（トークン類はマスク）。
- 終了コード: 0 正常 / 1 設定 / 2 Slack / 3 Claude / 4 LINE / 5 state.json
- 毎日9:00の自動実行は `register_task.ps1` で Windows タスクスケジューラに登録します。

テスト（APIはすべてモック、実送信なし）:

```bash
python -m unittest discover -s tests -t . -v
```

## 要約フォーマット

```
【Slackまとめ】

■ 重要事項
内容（または「なし」）

■ 決定事項
内容（または「なし」）

■ TODO・期限
内容（または「なし」）

■ その他
内容（または「なし」）
```

Slackに書かれていない内容を推測で補うことはしません。該当項目が無ければ
「なし」とだけ出力されます。

## エラー発生時の挙動

以下のケースではコンソールに原因が分かるメッセージを表示し、処理を中断します
（複雑なリトライ・監視の仕組みは実装していません。Anthropic SDKが持つ
標準のリトライ（429/5xx、最大2回）のみ有効です）。

- 環境変数の不足・不正（`.env` の設定ミス）
- Slack API取得失敗（トークン不正、Bot未参加、スコープ不足など）
- Claude API失敗（キー不正、モデル不正、レート制限など）
- LINE API送信失敗（トークン不正、友だち未追加、不正なuserIdなど）

## 既知の制約（MVPスコープ外）

- スレッド返信（`conversations.replies` が必要）は取得対象外です
- LINEのテキストは1通最大5000文字・1回のpushで最大5メッセージという制限があり、
  要約がこれを超える場合はエラーで中断します（通常の要約文量では発生しません）
- スケジュール実行（cron等）は組み込んでいません。手動実行、または任意のスケジューラ
  （タスクスケジューラ、cron等）と組み合わせて利用してください
