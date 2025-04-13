import json
import os
from typing import Any, Dict

import requests


def test_freecad_api() -> Dict[str, Any]:
    """
    FreeCAD APIの動作確認を行うテスト関数

    Returns:
        Dict[str, Any]: APIレスポンス
    """
    # Cloud RunのエンドポイントURLを環境変数から取得
    api_url = os.getenv("FREECAD_API_URL", "http://localhost:8080")

    # テスト用の入力データ
    test_data = {
        "width": 10.0,
        "length": 15.0,
        "height": 3.0,
        "parameters": {"wall_thickness": 0.2, "window_size": 1.5},
    }

    try:
        # APIエンドポイントにPOSTリクエストを送信
        response = requests.post(
            f"{api_url}/generate",
            json=test_data,
            headers={"Content-Type": "application/json"},
        )

        # レスポンスの確認
        response.raise_for_status()
        result = response.json()

        print("✅ FreeCAD APIテスト成功")
        print(f"レスポンス: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ FreeCAD APIテスト失敗: {str(e)}")
        raise


if __name__ == "__main__":
    test_freecad_api()
