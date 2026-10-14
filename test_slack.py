"""Slack API 単体の接続テスト。

Claude API / LINE API は呼び出さず、Slack からメッセージを取得できるかだけを確認する。
トークンの値は表示しない。

実行方法: python test_slack.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from slack_client import JST, SlackError, _describe_slack_error, fetch_messages

LOOKBACK_HOURS = 24


def main() -> int:
    load_dotenv()
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    channel_id = os.environ.get("SLACK_CHANNEL_ID", "")

    print("=== 1. 環境変数チェック ===")
    print(f"SLACK_BOT_TOKEN : {'設定あり' if token else '未設定'}"
          + (" (xoxb- 形式)" if token.startswith("xoxb-") else " (※xoxb- で始まっていません)" if token else ""))
    print(f"SLACK_CHANNEL_ID: {channel_id or '未設定'}")
    if not token or not channel_id:
        print("NG: .env に SLACK_BOT_TOKEN / SLACK_CHANNEL_ID を設定してください。")
        return 1

    client = WebClient(token=token)

    print("\n=== 2. 認証チェック (auth.test) ===")
    try:
        auth = client.auth_test()
        print(f"OK: ワークスペース={auth.get('team')} / Bot={auth.get('user')}")
    except SlackApiError as exc:
        print(f"NG: {_describe_slack_error(exc)}")
        return 1

    print("\n=== 3. チャンネルチェック (conversations.info) ===")
    try:
        info = client.conversations_info(channel=channel_id)["channel"]
        print(f"OK: #{info.get('name')} / Bot参加={info.get('is_member')}")
    except SlackApiError as exc:
        # channels:read スコープが無い場合もあるため、ここでは警告にとどめる
        print(f"警告: {_describe_slack_error(exc)}")

    print(f"\n=== 4. 直近{LOOKBACK_HOURS}時間のメッセージ取得 (conversations.history) ===")
    try:
        oldest = str((datetime.now(tz=JST) - timedelta(hours=LOOKBACK_HOURS)).timestamp())
        raw = client.conversations_history(channel=channel_id, oldest=oldest, limit=200)
        raw_count = len(raw.get("messages", []))
        messages = fetch_messages(token, channel_id, LOOKBACK_HOURS)
    except SlackApiError as exc:
        print(f"NG: {_describe_slack_error(exc)}")
        return 1
    except SlackError as exc:
        print(f"NG: {exc}")
        return 1

    print(f"取得件数(生データ)        : {raw_count} 件")
    print(f"取得件数(通常メッセージ)  : {len(messages)} 件"
          "  ※参加通知・Bot投稿・空メッセージは除外")
    print("-" * 60)
    for m in messages:
        print(f"[{m.jst_datetime:%Y-%m-%d %H:%M:%S}] {m.user_name}")
        print(f"    {m.text}")
    print("-" * 60)

    if not messages:
        print("注意: 対象メッセージが0件です。直近24時間に人が投稿したメッセージがあるか確認してください。")
    print("結果: Slack 接続テスト OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
