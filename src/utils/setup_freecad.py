"""FreeCAD環境のセットアップを行うモジュール。"""

import logging
import os
import requests

# ロギングの設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def setup_freecad_environment() -> bool:
    """FreeCAD APIの接続を確認します。

    Returns:
        bool: 接続が成功したかどうか
    """
    try:
        # Cloud RunのFreeCAD APIのURLを設定
        api_url = os.getenv(
            "FREECAD_API_URL", "https://freecad-api-513507930971.asia-northeast1.run.app"
        )
        
        # APIのヘルスチェック（ルートエンドポイントを使用）
        response = requests.get(f"{api_url}/")
        if response.status_code == 200:
            data = response.json()
            if "message" in data:
                logger.info("FreeCAD APIに接続できました")
                return True
            else:
                logger.error(f"FreeCAD APIのヘルスチェックに失敗しました: 予期しないレスポンス {data}")
                return False
        else:
            logger.error(f"FreeCAD APIのヘルスチェックに失敗しました: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"FreeCAD APIのセットアップ中にエラーが発生しました: {e}")
        return False

def verify_freecad_installation() -> bool:
    """FreeCAD APIの接続状態を確認します。

    Returns:
        bool: 接続が正常かどうか
    """
    return setup_freecad_environment()

if __name__ == "__main__":
    if verify_freecad_installation():
        logger.info("FreeCAD APIのセットアップが完了しました")
    else:
        logger.error("FreeCAD APIのセットアップに失敗しました")
