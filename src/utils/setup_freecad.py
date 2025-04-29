"""FreeCAD環境のセットアップを行うモジュール。"""

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# ロギングの設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_freecad_environment() -> bool:
    """FreeCADの環境をセットアップします。

    Returns:
        bool: セットアップが成功したかどうか
    """
    try:
        # macOSの標準的なFreeCADパス
        freecad_paths = [
            "/Applications/FreeCAD.app/Contents/Resources/lib",
            "/Applications/FreeCAD.app/Contents/Resources/lib/python3.11",
            "/Applications/FreeCAD.app/Contents/Resources/lib/python3.11/lib-dynload",
            "/Applications/FreeCAD.app/Contents/Resources/lib/python3.11/site-packages",
        ]

        # 環境変数の設定
        os.environ["PYTHONPATH"] = os.pathsep.join(freecad_paths)
        os.environ["DYLD_LIBRARY_PATH"] = (
            "/Applications/FreeCAD.app/Contents/Resources/lib:/usr/lib"
        )
        os.environ["DYLD_FRAMEWORK_PATH"] = (
            "/Applications/FreeCAD.app/Contents/Resources/lib"
        )
        os.environ["DYLD_RUN_PATH"] = "/Applications/FreeCAD.app/Contents/Resources/lib"
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
            "/Applications/FreeCAD.app/Contents/Resources/lib:/usr/lib"
        )

        # パスの存在確認と追加
        valid_paths = []
        for path in freecad_paths:
            if os.path.exists(path) and path not in sys.path:
                sys.path.append(path)
                valid_paths.append(path)
                logger.info(f"Added FreeCAD path: {path}")
            else:
                logger.warning(f"FreeCAD path does not exist: {path}")

        if not valid_paths:
            logger.error("有効なFreeCADパスが見つかりませんでした")
            return False

        # FreeCADのインポートテスト
        import FreeCAD

        logger.info("Successfully imported FreeCAD")

        # 必要なモジュールのインポートをテスト
        import Arch
        import Draft
        import Part

        logger.info("Successfully imported required FreeCAD modules")

        return True

    except ImportError as e:
        logger.error(f"FreeCADのインポートに失敗しました: {e}")
        return False
    except Exception as e:
        logger.error(f"FreeCAD環境のセットアップ中にエラーが発生しました: {e}")
        return False


def get_freecad_python_path() -> Optional[str]:
    """FreeCADのPythonパスを取得します。

    Returns:
        Optional[str]: FreeCADのPythonパス
    """
    possible_paths = [
        "/Applications/FreeCAD.app/Contents/Resources/lib/python3.11",
        "/Applications/FreeCAD.app/Contents/Resources/lib/python3.9",
        "/Applications/FreeCAD.app/Contents/Resources/lib/python3.8",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def verify_freecad_installation() -> bool:
    """FreeCADのインストール状態を確認します。

    Returns:
        bool: インストールが正常かどうか
    """
    # FreeCADアプリケーションの存在確認
    if not os.path.exists("/Applications/FreeCAD.app"):
        logger.error("FreeCADアプリケーションが見つかりません")
        return False

    # Pythonパスの確認
    python_path = get_freecad_python_path()
    if not python_path:
        logger.error("FreeCADのPythonパスが見つかりません")
        return False

    logger.info(f"Found FreeCAD Python path: {python_path}")

    # 環境のセットアップ
    if not setup_freecad_environment():
        logger.error("FreeCAD環境のセットアップに失敗しました")
        return False

    return True


if __name__ == "__main__":
    if verify_freecad_installation():
        logger.info("FreeCAD環境のセットアップが完了しました")
    else:
        logger.error("FreeCAD環境のセットアップに失敗しました")
