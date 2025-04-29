"""壁描画機能を提供するモジュール。

このモジュールは、建築CADにおける壁要素の生成と管理を行います。
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import Arch
import Draft
import FreeCAD as App
import Part


@dataclass
class WallSpecification:
    """壁の仕様を定義するデータクラス。"""

    start_point: Tuple[float, float]  # 始点座標 (x, y)
    end_point: Tuple[float, float]  # 終点座標 (x, y)
    height: float = 2400.0  # 高さ (mm)
    thickness: float = 150.0  # 厚さ (mm)
    material: str = "コンクリート"  # 材質
    is_structural: bool = True  # 構造壁かどうか


class WallGenerator:
    """壁要素を生成するクラス。"""

    def __init__(self, document: "CADDocument"):
        """
        Args:
            document (CADDocument): CADドキュメント
        """
        self.document = document
        self.walls: List[WallSpecification] = []

    def add_wall(self, wall_spec: WallSpecification) -> bool:
        """壁を追加します。

        Args:
            wall_spec (WallSpecification): 壁の仕様

        Returns:
            bool: 追加が成功したかどうか
        """
        try:
            # 始点と終点のベクトルを作成
            start = App.Vector(*wall_spec.start_point, 0)
            end = App.Vector(*wall_spec.end_point, 0)

            # 壁を生成
            base_line = Draft.makeLine(start, end)
            wall = Arch.makeWall(
                base_line, height=wall_spec.height, width=wall_spec.thickness
            )

            # 壁のプロパティを設定
            wall.Label = f"Wall_{len(self.walls) + 1}"
            if wall_spec.material:
                wall.Material = wall_spec.material

            # ViewObjectのプロパティを設定
            if hasattr(wall, "ViewObject"):
                if wall_spec.is_structural:
                    wall.ViewObject.LineColor = (0.8, 0.8, 0.8)  # 構造壁は灰色
                else:
                    wall.ViewObject.LineColor = (1.0, 1.0, 1.0)  # 非構造壁は白
                wall.ViewObject.LineWidth = 2

            self.walls.append(wall_spec)
            return True

        except Exception as e:
            logging.error(f"壁の生成に失敗しました: {e}")
            return False

    def add_opening(
        self,
        wall_index: int,
        position: float,
        width: float,
        height: float,
        opening_type: str = "window",
    ) -> bool:
        """開口部を追加します。

        Args:
            wall_index (int): 壁のインデックス
            position (float): 壁の始点からの距離 (mm)
            width (float): 開口部の幅 (mm)
            height (float): 開口部の高さ (mm)
            opening_type (str, optional): 開口部の種類. Defaults to "window".

        Returns:
            bool: 追加が成功したかどうか
        """
        try:
            if wall_index >= len(self.walls):
                raise IndexError("指定された壁が存在しません")

            wall_spec = self.walls[wall_index]

            # 壁の方向ベクトルを計算
            dx = wall_spec.end_point[0] - wall_spec.start_point[0]
            dy = wall_spec.end_point[1] - wall_spec.start_point[1]
            length = math.sqrt(dx * dx + dy * dy)

            # 開口部の位置を計算
            ratio = position / length
            x = wall_spec.start_point[0] + dx * ratio
            y = wall_spec.start_point[1] + dy * ratio

            # 開口部を生成
            opening = None
            if opening_type == "window":
                opening = Arch.makeWindow(width=width, height=height)
                opening.Label = f"Window_{wall_index}_{len(self.walls)}"
            elif opening_type == "door":
                opening = Arch.makeWindow(width=width, height=height)
                opening.Label = f"Door_{wall_index}_{len(self.walls)}"

            if opening:
                # 開口部を壁に配置
                opening.Placement.Base = App.Vector(x, y, 0)
                return True

            return False

        except Exception as e:
            logging.error(f"開口部の生成に失敗しました: {e}")
            return False

    def connect_walls(self, wall1_index: int, wall2_index: int) -> bool:
        """2つの壁を接続します。

        Args:
            wall1_index (int): 1つ目の壁のインデックス
            wall2_index (int): 2つ目の壁のインデックス

        Returns:
            bool: 接続が成功したかどうか
        """
        try:
            if wall1_index >= len(self.walls) or wall2_index >= len(self.walls):
                raise IndexError("指定された壁が存在しません")

            wall1 = self.walls[wall1_index]
            wall2 = self.walls[wall2_index]

            # 接続点の座標を計算
            if wall1.end_point == wall2.start_point:
                connection_point = wall1.end_point
            elif wall1.start_point == wall2.end_point:
                connection_point = wall1.start_point
            else:
                raise ValueError("壁が接続できません")

            # 接続部分の処理（必要に応じて実装）

            return True

        except Exception as e:
            logging.error(f"壁の接続に失敗しました: {e}")
            return False
