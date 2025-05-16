"""CAD関連のユーティリティ機能を提供するモジュール。

このモジュールは、FreeCADとの統合や基本的なCAD操作のためのユーティリティ機能を提供します。
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel


class CADEnvironment(BaseModel):
    """FreeCAD環境の設定と管理を行うクラス。"""

    freecad_path: Optional[str] = None
    lib_path: Optional[str] = None

    def setup_environment(self) -> bool:
        """FreeCAD環境をセットアップします。

        Returns:
            bool: セットアップが成功したかどうか
        """
        try:
            # macOSの場合のデフォルトパス
            if sys.platform == "darwin":
                default_paths = [
                    "/Applications/FreeCAD.app/Contents/Resources/lib",
                    "/usr/local/lib/freecad",
                ]

                for path in default_paths:
                    if os.path.exists(path):
                        self.freecad_path = path
                        self.lib_path = os.path.join(path, "lib")
                        break

            if self.freecad_path:
                if self.freecad_path not in sys.path:
                    sys.path.append(self.freecad_path)
                if self.lib_path and self.lib_path not in sys.path:
                    sys.path.append(self.lib_path)

                # FreeCADのインポートを試行
                import FreeCAD

                logging.info("FreeCAD環境のセットアップに成功しました")
                return True
            else:
                logging.error("FreeCADのパスが見つかりません")
                return False

        except ImportError as e:
            logging.error(f"FreeCADのインポートに失敗しました: {e}")
            return False
        except Exception as e:
            logging.error(f"環境セットアップ中にエラーが発生しました: {e}")
            return False


class CADDocument:
    """CADドキュメントを管理するクラス。"""

    def __init__(self, name: str):
        """
        Args:
            name (str): ドキュメント名
        """
        self.name = name
        self._setup_document()

    def _setup_document(self) -> None:
        """新しいCADドキュメントを作成します。"""
        import FreeCAD as App

        # 既存のドキュメントがあれば閉じる
        if self.name in App.listDocuments():
            App.closeDocument(self.name)

        # 新しいドキュメントを作成
        self.doc = App.newDocument(self.name)
        self.doc.Label = self.name

    def save(self, filepath: str) -> bool:
        """ドキュメントを保存します。

        Args:
            filepath (str): 保存先のパス

        Returns:
            bool: 保存が成功したかどうか
        """
        try:
            self.doc.saveAs(filepath)
            return True
        except Exception as e:
            logging.error(f"ドキュメントの保存に失敗しました: {e}")
            return False


class CADGrid:
    """CADグリッドを管理するクラス。"""

    def __init__(self, spacing: float = 910.0):
        """
        Args:
            spacing (float, optional): グリッド間隔(mm). Defaults to 910.0.
        """
        self.spacing = spacing

    def create_grid(self, width: float, height: float, document: CADDocument) -> None:
        """グリッドを作成します。

        Args:
            width (float): 幅(mm)
            height (float): 高さ(mm)
            document (CADDocument): CADドキュメント
        """
        import Draft
        import FreeCAD as App

        # 水平グリッド線
        for y in np.arange(0, height + self.spacing, self.spacing):
            line = Draft.makeLine(App.Vector(0, y, 0), App.Vector(width, y, 0))
            line.ViewObject.LineColor = (0.5, 0.5, 0.5)
            line.ViewObject.LineWidth = 1

        # 垂直グリッド線
        for x in np.arange(0, width + self.spacing, self.spacing):
            line = Draft.makeLine(App.Vector(x, 0, 0), App.Vector(x, height, 0))
            line.ViewObject.LineColor = (0.5, 0.5, 0.5)
            line.ViewObject.LineWidth = 1
