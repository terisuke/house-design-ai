"""寸法線生成機能を提供するモジュール。

このモジュールは、建築CADにおける寸法線の生成と管理を行います。
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import Draft
import FreeCAD as App


@dataclass
class DimensionStyle:
    """寸法線のスタイルを定義するデータクラス。"""

    text_size: float = 2.5  # テキストサイズ (mm)
    extension_line: float = 10.0  # 引出線長さ (mm)
    offset: float = 10.0  # オフセット距離 (mm)
    arrow_size: float = 3.0  # 矢印サイズ (mm)
    line_weight: float = 0.25  # 線の太さ (mm)
    text_position: str = "center"  # テキスト位置 ("center", "above", "below")


class DimensionGenerator:
    """寸法線を生成するクラス。"""

    def __init__(self, document: "CADDocument", style: Optional[DimensionStyle] = None):
        """
        Args:
            document (CADDocument): CADドキュメント
            style (Optional[DimensionStyle], optional): 寸法線スタイル. Defaults to None.
        """
        self.document = document
        self.style = style or DimensionStyle()
        self.dimensions: List[Draft.Dimension] = []

    def add_linear_dimension(
        self,
        start_point: Tuple[float, float],
        end_point: Tuple[float, float],
        offset_direction: str = "right",
    ) -> bool:
        """線形寸法を追加します。

        Args:
            start_point (Tuple[float, float]): 始点座標
            end_point (Tuple[float, float]): 終点座標
            offset_direction (str, optional): オフセット方向. Defaults to "right".

        Returns:
            bool: 追加が成功したかどうか
        """
        try:
            # 始点と終点のベクトルを作成
            p1 = App.Vector(*start_point, 0)
            p2 = App.Vector(*end_point, 0)

            # オフセット方向を計算
            dx = end_point[0] - start_point[0]
            dy = end_point[1] - start_point[1]

            if offset_direction == "right":
                offset = App.Vector(-dy, dx, 0).normalize() * self.style.offset
            else:
                offset = App.Vector(dy, -dx, 0).normalize() * self.style.offset

            # 寸法線の配置点を計算
            dim_pos = (p1 + p2) * 0.5 + offset

            # 寸法線を生成
            dimension = Draft.makeDimension(p1, p2, dim_pos)

            # スタイルを適用
            if hasattr(dimension, "ViewObject"):
                dimension.ViewObject.FontSize = self.style.text_size
                dimension.ViewObject.ArrowSize = self.style.arrow_size
                dimension.ViewObject.LineWidth = self.style.line_weight

            # ラベルを設定
            dimension.Label = f"Dimension_{len(self.dimensions) + 1}"

            self.dimensions.append(dimension)
            return True

        except Exception as e:
            logging.error(f"寸法線の生成に失敗しました: {e}")
            return False

    def add_aligned_dimension(
        self, points: List[Tuple[float, float]], offset: float
    ) -> bool:
        """連続寸法を追加します。

        Args:
            points (List[Tuple[float, float]]): 寸法点のリスト
            offset (float): オフセット距離

        Returns:
            bool: 追加が成功したかどうか
        """
        try:
            if len(points) < 2:
                raise ValueError("寸法点は2点以上必要です")

            # 連続寸法線を生成
            for i in range(len(points) - 1):
                start = App.Vector(*points[i], 0)
                end = App.Vector(*points[i + 1], 0)

                # オフセット位置を計算
                dx = end.x - start.x
                dy = end.y - start.y
                length = math.sqrt(dx * dx + dy * dy)

                if length > 0:
                    offset_vector = App.Vector(-dy / length, dx / length, 0) * offset
                    dim_pos = (start + end) * 0.5 + offset_vector

                    # 寸法線を生成
                    dimension = Draft.makeDimension(start, end, dim_pos)

                    # スタイルを適用
                    if hasattr(dimension, "ViewObject"):
                        dimension.ViewObject.FontSize = self.style.text_size
                        dimension.ViewObject.ArrowSize = self.style.arrow_size
                        dimension.ViewObject.LineWidth = self.style.line_weight

                    dimension.Label = f"AlignedDim_{len(self.dimensions) + 1}"
                    self.dimensions.append(dimension)

            return True

        except Exception as e:
            logging.error(f"連続寸法線の生成に失敗しました: {e}")
            return False

    def add_angular_dimension(
        self,
        center: Tuple[float, float],
        start_point: Tuple[float, float],
        end_point: Tuple[float, float],
    ) -> bool:
        """角度寸法を追加します。

        Args:
            center (Tuple[float, float]): 中心点
            start_point (Tuple[float, float]): 始点
            end_point (Tuple[float, float]): 終点

        Returns:
            bool: 追加が成功したかどうか
        """
        try:
            # ベクトルを作成
            center_vec = App.Vector(*center, 0)
            start_vec = App.Vector(*start_point, 0)
            end_vec = App.Vector(*end_point, 0)

            # 角度寸法線を生成
            dimension = Draft.makeAngularDimension(center_vec, start_vec, end_vec)

            # スタイルを適用
            if hasattr(dimension, "ViewObject"):
                dimension.ViewObject.FontSize = self.style.text_size
                dimension.ViewObject.ArrowSize = self.style.arrow_size
                dimension.ViewObject.LineWidth = self.style.line_weight

            dimension.Label = f"AngularDim_{len(self.dimensions) + 1}"
            self.dimensions.append(dimension)

            return True

        except Exception as e:
            logging.error(f"角度寸法線の生成に失敗しました: {e}")
            return False
