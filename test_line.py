"""LINE Messaging API 単体の送信テスト。

Slack API / Claude API は呼び出さず、push message でテスト通知を1通だけ送信する。
トークン・ユーザーIDの値は表示しない。

実行方法: python test_line.py
"""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

from line_client import _PUSH_URL, _REQUEST_TIMEOUT_SECONDS, _describe_response_error

TEST_TEXT = "Slack要約システムからのテスト通知です！\nLINE APIの接続に成功しました。"


def main() -> int:
    load_dotenv()
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = os.environ.get("LINE_USER_ID", "")

    print("=== 1. 環境変数チェック ===")
    print(f"LINE_CHANNEL_ACCESS_TOKEN: {'設定あり' if token else '未設定'}")
    print(f"LINE_USER_ID             : {'設定あり' if user_id else '未設定'}"
          + ((" (U+32桁 形式)" if len(user_id) == 33 and user_id.startswith("U")
              else " (※形式が想定と異なります)") if user_id else ""))
    if not token or not user_id:
        print("NG: .env に LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID を設定して保存してください。")
        return 1

    print("\n=== 2. push message 送信 (1回のみ) ===")
    print("送信内容:")
    for line in TEST_TEXT.splitlines():
        print(f"  {line}")
    try:
        response = requests.post(
            _PUSH_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"to": user_id, "messages": [{"type": "text", "text": TEST_TEXT}]},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        print(f"NG: ネットワークエラーです ({type(exc).__name__})。接続・プロキシを確認してください。")
        return 1

    print(f"\nHTTPステータス : {response.status_code}")
    print(f"リクエストID   : {response.headers.get('x-line-request-id', '(なし)')}")
    if response.status_code != 200:
        print(f"NG: {_describe_response_error(response)}")
        return 1

    print("結果: LINE API 送信テスト OK（LINEアプリで受信を確認してください）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
