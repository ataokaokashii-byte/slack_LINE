"""Claude API 単体の接続テスト。

Slack API / LINE API は呼び出さず、Claude API で要約できるかだけを確認する。
summarizer.py と同じシステムプロンプト・パラメータで、固定のテスト文章を1回だけ送信する。
APIキーの値は表示しない。

実行方法: python test_claude.py
"""

from __future__ import annotations

import os
import sys

import anthropic
from dotenv import load_dotenv

from slack_client import SlackMessage
from summarizer import _MAX_TOKENS, _SYSTEM_PROMPT, _build_user_content

_DEFAULT_MODEL = "claude-opus-5"  # config.py の既定値と同じ

# Slack を呼ばずに済むよう、テスト用のメッセージを手元で作る
_TEST_MESSAGES = [
    SlackMessage(ts="1791958200", user_id="U_TEST1", user_name="田中",
                 text="来週の定例は水曜15時に変更することに決まりました。"),
    SlackMessage(ts="1791958500", user_id="U_TEST2", user_name="佐藤",
                 text="了解です。議事録テンプレートは私が金曜までに用意します。"),
    SlackMessage(ts="1791958800", user_id="U_TEST1", user_name="田中",
                 text="本番サーバーの証明書が10/31で期限切れになるので要注意です。"),
]


def main() -> int:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    model = os.environ.get("ANTHROPIC_MODEL") or _DEFAULT_MODEL

    print("=== 1. 環境変数チェック ===")
    print(f"ANTHROPIC_API_KEY: {'設定あり' if api_key else '未設定'}"
          + ((" (sk-ant- 形式)" if api_key.startswith("sk-ant-")
              else " (※sk-ant- で始まっていません)") if api_key else ""))
    print(f"ANTHROPIC_MODEL  : {model}")
    if not api_key:
        print("NG: .env の ANTHROPIC_API_KEY が空です。値を入力して保存してから再実行してください。")
        return 1

    # 自動リトライで複数回リクエストが飛ばないようにする
    client = anthropic.Anthropic(api_key=api_key, max_retries=0)

    print("\n=== 2. モデル確認 (Models API・課金なし) ===")
    try:
        info = client.models.retrieve(model)
        print(f"OK: {info.id} ({info.display_name}) は利用可能です")
    except anthropic.AuthenticationError:
        print("NG: APIキーが無効です。Claude Console でキーを確認・再発行してください。")
        return 1
    except anthropic.NotFoundError:
        print(f"NG: モデル '{model}' が見つかりません。ANTHROPIC_MODEL を確認してください。")
        return 1
    except anthropic.APIConnectionError:
        print("NG: ネットワークエラーです。インターネット接続・プロキシを確認してください。")
        return 1

    print("\n=== 3. 要約リクエスト (Messages API・1回のみ) ===")
    print("送信するテスト文章:")
    for m in _TEST_MESSAGES:
        print(f"  {m.format_line()}")
    try:
        response = client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            output_config={"effort": "medium"},
            messages=[{"role": "user", "content": _build_user_content(_TEST_MESSAGES)}],
        )
    except anthropic.BadRequestError as exc:
        print(f"NG: リクエスト不正 (400): {exc.message}")
        return 1
    except anthropic.AuthenticationError:
        print("NG: APIキーが無効です。")
        return 1
    except anthropic.PermissionDeniedError:
        print("NG: このAPIキーには権限がありません (403)。")
        return 1
    except anthropic.RateLimitError:
        print("NG: レート制限 (429)。しばらく待つか、クレジット残高を確認してください。")
        return 1
    except anthropic.APIStatusError as exc:
        print(f"NG: APIエラー (status={exc.status_code}): {exc.message}")
        return 1
    except anthropic.APIConnectionError:
        print("NG: ネットワークエラーです。")
        return 1

    if response.stop_reason == "refusal":
        print("NG: モデルが応答を拒否しました (refusal)。")
        return 1

    summary = "".join(b.text for b in response.content if b.type == "text").strip()
    print("\n--- Claude の要約 ---")
    print(summary or "(空)")
    print("---------------------")

    u = response.usage
    print("\n=== 4. 使用モデル・トークン使用量 ===")
    print(f"使用モデル     : {response.model}")
    print(f"停止理由       : {response.stop_reason}")
    print(f"入力トークン   : {u.input_tokens}")
    print(f"出力トークン   : {u.output_tokens}  (思考トークンを含む)")
    print(f"リクエストID   : {response._request_id}")

    print("\n結果: Claude API 接続テスト " + ("OK" if summary else "NG (要約が空)"))
    return 0 if summary else 1


if __name__ == "__main__":
    sys.exit(main())
