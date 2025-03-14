# src/processing/mask.py
"""
セグメンテーションマスクの処理と操作のためのユーティリティ関数
(2025-03-12 修正版: A3横向きの実サイズ換算でマス目を描画する)
"""

import numpy as np
import cv2
import tempfile
import io
from typing import Optional, Tuple, Dict, Any
from PIL import Image
import logging
import yaml
import os
import requests
import random  # ランダムアルファベット生成用に追加
import sys
from src.processing.arrrangement import Site, Madori, OrderedDict

# ロギング設定
logger = logging.getLogger(__name__)

# data.yamlからクラス名を取得（既存仕様のまま）
with open('config/data.yaml', 'r') as f:
    data_config = yaml.safe_load(f)
    class_names = data_config['names']

# クラス名からIDを取得（既存仕様のまま）
HOUSE_CLASS_ID = class_names.index('House') if 'House' in class_names else None
ROAD_CLASS_ID = class_names.index('Road') if 'Road' in class_names else None

# A3サイズの定義 (150dpi想定)
A3_WIDTH_PX = 2481   # A3横幅: 420mm @ 150dpi
A3_HEIGHT_PX = 1754  # A3高さ: 297mm @ 150dpi
A3_WIDTH_MM = 420.0  # A3横幅: 420mm

# アルファベットのリスト
ALPHABET_LIST = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
]

def offset_mask_by_distance(mask: np.ndarray, offset_px: int) -> np.ndarray:
    """
    マスクを距離変換して内側にオフセットしたバイナリマスクを返します。
    offset_px > 0 の場合に収縮、0以下なら変化なし。

    Args:
        mask: オフセットするバイナリマスク(0,1)
        offset_px: オフセット距離(px)
    Returns:
        内側にオフセットされたバイナリマスク(0,1)
    """
    if offset_px <= 0:
        return mask.copy()

    bin_mask = (mask > 0).astype(np.uint8)
    dist = cv2.distanceTransform(bin_mask, cv2.DIST_L2, 5)
    shrunk = (dist >= offset_px).astype(np.uint8)
    return shrunk

def draw_grid_on_mask(
    image: np.ndarray,
    final_mask: np.ndarray,
    grid_mm: float,
    px_per_mm: float,
    fill_color: Tuple[int, int, int] = (255, 0, 0),
    alpha: float = 0.4,
    line_color: Tuple[int, int, int] = (0, 0, 255),
    line_thickness: int = 2
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    建物マスク領域に固定間隔のマス目（セル）を描画する。
    各セル内にランダムアルファベットを配置する。

    セルは「マスク内部にすべてが収まる場合のみ」描画するため、
    マスク外にはみ出すセルはスキップされる。

    Args:
        image: 描画対象のBGR画像
        final_mask: グリッドを描画する対象のバイナリマスク(0 or 1)
        grid_mm: 紙上(mm)単位のグリッド間隔（本処理では使わないが、引数として残す）
        px_per_mm: mmあたりのピクセル数(A3横420mm想定)
        line_color: グリッド線の色 (BGR)
        line_thickness: グリッド線の太さ(px)

    Returns:
        (drawn_image, stats)
        - drawn_image: グリッド描画後のBGR画像
        - stats: 描画に関する各種統計情報を含む辞書
    """
    out = image.copy()
    
    # 統計情報格納用の辞書
    grid_stats = {
        "cell_px": None,             # 実際に使用したセルサイズ(px)
        "bounding_box": None,        # マスク全体のバウンディングボックス (x, y, width, height)
        "total_cells_in_bbox": 0,    # バウンディングボックス内に理論上配置されるセル数
        "cells_drawn": 0,           # 実際に描画されたセル数
        "cells_skipped": 0,         # スキップされたセル数
        "reason_not_in_mask": 0,    # スキップ理由が「マスク外」だった回数
        "alphabet_counts": {},      # 各アルファベットの使用回数
    }

    # マスクの輪郭を抽出
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        # マスクが空の場合はそのまま返す
        grid_stats["error"] = "マスクが空です"
        return out, grid_stats
    
    big_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(big_contour)

    # まず半透明塗りつぶし（マスク内のみ）
    overlay = out.copy()
    mask_area = np.zeros_like(out)
    mask_area[final_mask == 1] = fill_color
    cv2.addWeighted(mask_area, alpha, out, 1, 0, out)

    # グリッド間隔を固定(px=54)にする（9.1mm相当×5.93px/mm = 約54px）
    cell_px = 54
    grid_stats["cell_px"] = cell_px

    # バウンディングボックス情報を格納
    grid_stats["bounding_box"] = {"x": x, "y": y, "width": w, "height": h}

    # バウンディングボックス範囲
    x_end = x + w
    y_end = y + h

    # 理論上のグリッドサイズ(単純に w,h を cell_px で割った数)
    grid_cols = w // cell_px
    grid_rows = h // cell_px

    # n+1本の線でn個のセルができるため、実際のセル数は線の数-1
    grid_lines_cols = grid_cols + 1  # 線の数
    grid_lines_rows = grid_rows + 1  # 線の数
    actual_grid_cols = max(0, grid_cols)  # セル数 = 線の数-1
    actual_grid_rows = max(0, grid_rows)  # セル数 = 線の数-1

    # グリッド情報を記録
    grid_stats["grid_lines"] = {"rows": grid_lines_rows, "cols": grid_lines_cols}  # 線の数
    grid_stats["grid_cells"] = {"rows": actual_grid_rows, "cols": actual_grid_cols}  # セル数
    # 後方互換性のために残す
    grid_stats["theoretical_grid_size"] = {"rows": grid_rows, "cols": grid_cols}

    # バウンディングボックス内の総セル数
    total_cells_in_bbox = actual_grid_rows * actual_grid_cols
    grid_stats["total_cells_in_bbox"] = total_cells_in_bbox

    # アルファベットの使用回数を初期化
    for letter in ALPHABET_LIST:
        grid_stats["alphabet_counts"][letter] = 0

    # 行(row)方向に走査
    row = 0
    while True:
        cell_y1 = y + row * cell_px
        cell_y2 = cell_y1 + cell_px
        if cell_y2 > y_end:
            break  # バウンディングボックス外なので終了
        
        # 列(col)方向に走査
        col = 0
        while True:
            cell_x1 = x + col * cell_px
            cell_x2 = cell_x1 + cell_px
            if cell_x2 > x_end:
                break  # 右がはみ出すので次の行へ
            
            # (2) マスク内に完全に収まっているか確認
            padding = max(1, line_thickness // 2)
            check_x1 = max(0, cell_x1 - padding)
            check_y1 = max(0, cell_y1 - padding)
            check_x2 = min(final_mask.shape[1] - 1, cell_x2 + padding)
            check_y2 = min(final_mask.shape[0] - 1, cell_y2 + padding)
            
            # セル領域のマスク(部分)を抽出
            cell_roi = final_mask[check_y1:check_y2, check_x1:check_x2]
            
            # マスク外に1ピクセルでもかかるならスキップ
            if not np.all(cell_roi == 1):
                grid_stats["cells_skipped"] += 1
                grid_stats["reason_not_in_mask"] += 1
                col += 1
                continue
            
            # ランダムなアルファベットを選択
            cell_letter = random.choice(ALPHABET_LIST)
            
            # 使用回数を記録
            grid_stats["alphabet_counts"][cell_letter] += 1
            
            # (3) セルの四辺を描画
            cv2.line(out, (cell_x1, cell_y1), (cell_x2, cell_y1), line_color, line_thickness)
            cv2.line(out, (cell_x1, cell_y2), (cell_x2, cell_y2), line_color, line_thickness)
            cv2.line(out, (cell_x1, cell_y1), (cell_x1, cell_y2), line_color, line_thickness)
            cv2.line(out, (cell_x2, cell_y1), (cell_x2, cell_y2), line_color, line_thickness)
            
            # (4) セル中心にアルファベットを描画
            cell_center_x = (cell_x1 + cell_x2) // 2
            cell_center_y = (cell_y1 + cell_y2) // 2
            
            # フォント設定
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.0
            text_color = (0, 0, 0)  # 黒文字
            text_thickness = 2
            
            # テキストサイズを計算して中央揃えの位置を調整
            text_size = cv2.getTextSize(cell_letter, font, font_scale, text_thickness)[0]
            text_x = cell_center_x - text_size[0] // 2
            text_y = cell_center_y + text_size[1] // 2
            
            # アルファベットを描画
            cv2.putText(
                out,
                cell_letter,
                (text_x, text_y),
                font,
                font_scale,
                text_color,
                text_thickness,
                cv2.LINE_AA
            )

            grid_stats["cells_drawn"] += 1
            col += 1
        row += 1

    return out, grid_stats

def draw_floorplan_on_mask(
    image: np.ndarray,
    final_mask: np.ndarray,
    grid_mm: float,
    px_per_mm: float,
    fill_color: Tuple[int, int, int] = (255, 0, 0),
    alpha: float = 0.4,
    line_color: Tuple[int, int, int] = (0, 0, 255),
    line_thickness: int = 2
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    建物マスク領域に間取りを配置し、色分けして表示する。
    
    Args:
        image: 描画対象のBGR画像
        final_mask: グリッドを描画する対象のバイナリマスク(0 or 1)
        grid_mm: 紙上(mm)単位のグリッド間隔
        px_per_mm: mmあたりのピクセル数(A3横420mm想定)
        fill_color: デフォルトの塗りつぶし色 (BGR)
        alpha: 塗りつぶしの透明度(0~1)
        line_color: グリッド線の色 (BGR)
        line_thickness: グリッド線の太さ(px)
        
    Returns:
        (drawn_image, stats)
        - drawn_image: 間取り描画後のBGR画像
        - stats: 描画に関する各種統計情報を含む辞書
    """
    out = image.copy()
    
    # 統計情報格納用の辞書
    floorplan_stats = {
        "cell_px": None,             # 実際に使用したセルサイズ(px)
        "bounding_box": None,        # マスク全体のバウンディングボックス
        "grid_size": None,           # 実際に使用したグリッドサイズ (rows, cols)
        "madori_info": {},           # 間取り情報
        "positions": {}              # 各間取りの配置位置
    }
    
    # マスクの輪郭を抽出
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        # マスクが空の場合はそのまま返す
        floorplan_stats["error"] = "マスクが空です"
        return out, floorplan_stats
    
    big_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(big_contour)
    
    # バウンディングボックス情報を格納
    floorplan_stats["bounding_box"] = {"x": x, "y": y, "width": w, "height": h}
    
    # グリッド間隔を固定(px=54)にする（9.1mm相当×5.93px/mm = 約54px）
    cell_px = 54
    floorplan_stats["cell_px"] = cell_px
    
    # グリッドサイズを計算 (マスク内に収まる最大の行数と列数)
    grid_rows = h // cell_px
    grid_cols = w // cell_px
    
    # あまりに小さすぎる場合は処理しない
    if grid_rows < 3 or grid_cols < 3:
        floorplan_stats["error"] = f"マスクが小さすぎます（{grid_rows}×{grid_cols}グリッド）"
        return out, floorplan_stats
    
    floorplan_stats["grid_size"] = {"rows": grid_rows, "cols": grid_cols}
    
    # 領域が十分に大きい場合は通常の間取り定義を使用
    if grid_rows >= 8 and grid_cols >= 8:
        # 標準サイズの間取り情報の定義
        madori_odict = OrderedDict(
            E=Madori('E', 1, 2, 2, None),  # 玄関
            L=Madori('L', 2, 4, 3, 'E'),   # リビング (サイズを5→4に縮小)
            D=Madori('D', 3, 3, 2, 'L'),   # ダイニング (高さを3→2に縮小)
            K=Madori('K', 4, 2, 2, 'D'),   # キッチン (高さを3→2に縮小)
            B=Madori('B', 5, 2, 2, 'L'),   # バスルーム
            T=Madori('T', 6, 1, 2, 'B')    # トイレ
        )
    else:
        # 小さな領域用の縮小版間取り
        madori_odict = OrderedDict(
            E=Madori('E', 1, 1, 1, None),  # 玄関
            L=Madori('L', 2, 2, 2, 'E'),   # リビング
            D=Madori('D', 3, 2, 1, 'L'),   # ダイニング
            K=Madori('K', 4, 1, 1, 'D'),   # キッチン
            B=Madori('B', 5, 1, 1, 'L'),   # バスルーム
            T=Madori('T', 6, 1, 1, 'B')    # トイレ
        )
    
    # 間取りの配色を定義 (BGR形式)
    colors = {
        'E': (102, 178, 255),  # 玄関: 明るいオレンジ
        'L': (144, 238, 144),  # リビング: 明るい緑
        'D': (255, 191, 0),    # ダイニング: 明るい青
        'K': (147, 20, 255),   # キッチン: 明るい紫
        'B': (95, 158, 160),   # バスルーム: ターコイズ
        'T': (180, 105, 255)   # トイレ: ピンク
    }
    
    # Site オブジェクトを作成して間取り情報を設定
    site = Site(grid_cols, grid_rows)
    site.set_madori_info(madori_odict)
    
    # マス目と位置情報の初期化
    grid = site.init_grid()
    positions = OrderedDict()
    
    # 間取りを配置
    madori_choices = dict()
    
    # 再帰のエラーを防ぐため、元の再帰制限を取得し一時的に引き上げる
    original_recursion_limit = sys.getrecursionlimit()
    try:
        # 再帰制限を一時的に引き上げる(標準は1000)
        sys.setrecursionlimit(2000)
        
        # 各間取りを1つずつ配置していく（玄関から）
        successful_rooms = []
        
        # 最初にEとLは必ず配置を試みる（基本的な部屋）
        for madori in list(site.get_madori_info())[:2]:  # 最初の2つ(E, L)
            try:
                madori_name = madori.name
                neighbor_name = madori.neighbor_name
                grid, positions, madori_choices = site.set_madori(grid, positions, madori_name, neighbor_name, madori_choices)
                successful_rooms.append(madori_name)
            except Exception as e:
                logger.warning(f"{madori_name}の配置中にエラー: {e}")
                break
        
        # 残りの部屋も順に配置を試みる
        for madori in list(site.get_madori_info())[2:]:
            try:
                madori_name = madori.name
                neighbor_name = madori.neighbor_name
                grid, positions, madori_choices = site.set_madori(grid, positions, madori_name, neighbor_name, madori_choices)
                successful_rooms.append(madori_name)
            except Exception as e:
                logger.warning(f"{madori_name}の配置中にエラー: {e}")
                # エラーが発生しても続行（残りの部屋を配置）
                continue
    except Exception as e:
        # グローバルエラーが発生した場合
        logger.warning(f"間取り配置中にエラー: {e}")
        floorplan_stats["warning"] = f"間取り配置の一部が失敗: {str(e)}"
    finally:
        # 再帰制限を元に戻す
        sys.setrecursionlimit(original_recursion_limit)
    
    # 間取り情報と位置情報を統計情報に記録
    for madori_name, pos in positions.items():
        madori = madori_odict[madori_name]
        floorplan_stats["madori_info"][madori_name] = {
            "name": madori.name,
            "width": madori.width,
            "height": madori.height,
            "neighbor": madori.neighbor_name
        }
        floorplan_stats["positions"][madori_name] = {
            "x": pos[0],
            "y": pos[1],
            "grid_x": x + pos[0] * cell_px,
            "grid_y": y + pos[1] * cell_px
        }
    
    # 間取りが1つも配置できなかった場合はフォールバックとして単純な配置を行う
    if not positions:
        logger.warning("間取り配置に失敗したため、フォールバック配置を使用します")
        floorplan_stats["warning"] = "通常の間取り配置に失敗したため、単純配置を使用"
        
        # 左上から順に玄関、リビング、ダイニング、キッチンを配置
        fallback_positions = {
            'E': (0, 0),
            'L': (2, 0),
            'D': (0, 2),
            'K': (3, 2),
            'B': (0, 4),
            'T': (2, 4)
        }
        
        # 各部屋がグリッド内に収まるか確認して配置
        for madori_name, pos in fallback_positions.items():
            if pos[0] + madori_odict[madori_name].width <= grid_cols and pos[1] + madori_odict[madori_name].height <= grid_rows:
                positions[madori_name] = pos
                madori = madori_odict[madori_name]
                floorplan_stats["madori_info"][madori_name] = {
                    "name": madori.name,
                    "width": madori.width,
                    "height": madori.height,
                    "neighbor": madori.neighbor_name
                }
                floorplan_stats["positions"][madori_name] = {
                    "x": pos[0],
                    "y": pos[1],
                    "grid_x": x + pos[0] * cell_px,
                    "grid_y": y + pos[1] * cell_px
                }
    
    # グリッド全体の背景を描画（透明度を下げた版）
    grid_overlay = np.zeros_like(out)
    cv2.rectangle(grid_overlay, (x, y), (x + grid_cols * cell_px, y + grid_rows * cell_px), 
                  (220, 220, 220), -1)  # 薄いグレー
    mask_roi = np.zeros_like(grid_overlay, dtype=np.uint8)
    mask_roi[y:y + grid_rows * cell_px, x:x + grid_cols * cell_px] = 1
    grid_overlay = grid_overlay * np.expand_dims(mask_roi[:,:,0], axis=2)
    cv2.addWeighted(grid_overlay, 0.2, out, 1, 0, out)
    
    # 間取りを描画
    for madori_name, pos in positions.items():
        madori = madori_odict[madori_name]
        grid_x = x + pos[0] * cell_px
        grid_y = y + pos[1] * cell_px
        grid_w = madori.width * cell_px
        grid_h = madori.height * cell_px
        
        # 間取りの色を取得
        color = colors.get(madori_name, (200, 200, 200))  # デフォルトはグレー
        
        # 間取りを塗りつぶし
        cv2.rectangle(out, (grid_x, grid_y), (grid_x + grid_w, grid_y + grid_h), 
                      color, -1)
        
        # 間取りの枠線を描画
        cv2.rectangle(out, (grid_x, grid_y), (grid_x + grid_w, grid_y + grid_h), 
                      (0, 0, 0), line_thickness)
        
        # 間取り名を中央に描画
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0 if madori.width >= 2 and madori.height >= 2 else 0.8
        text_size = cv2.getTextSize(madori_name, font, font_scale, 2)[0]
        text_x = grid_x + (grid_w - text_size[0]) // 2
        text_y = grid_y + (grid_h + text_size[1]) // 2
        cv2.putText(out, madori_name, (text_x, text_y), font, font_scale, 
                    (0, 0, 0), 2, cv2.LINE_AA)
    
    # グリッド線を描画
    for i in range(grid_rows + 1):
        y_pos = y + i * cell_px
        cv2.line(out, (x, y_pos), (x + grid_cols * cell_px, y_pos), (100, 100, 100), 1)
    
    for j in range(grid_cols + 1):
        x_pos = x + j * cell_px
        cv2.line(out, (x_pos, y), (x_pos, y + grid_rows * cell_px), (100, 100, 100), 1)
    
    # 凡例を描画
    legend_x = x
    legend_y = y + grid_rows * cell_px + 20
    legend_spacing = 120
    font_scale = 0.7
    
    # 実際に配置された間取りのみ凡例に表示
    descriptions = {
        'E': '玄関',
        'L': 'リビング',
        'D': 'ダイニング',
        'K': 'キッチン',
        'B': 'バスルーム',
        'T': 'トイレ'
    }
    
    for i, madori_name in enumerate(positions.keys()):
        # 凡例の位置を計算
        legend_pos_x = legend_x + i * legend_spacing
        
        # 色を取得
        color = colors.get(madori_name, (200, 200, 200))
        
        # 色付きの四角形を描画
        cv2.rectangle(out, (legend_pos_x, legend_y), 
                      (legend_pos_x + 30, legend_y + 30), color, -1)
        cv2.rectangle(out, (legend_pos_x, legend_y), 
                      (legend_pos_x + 30, legend_y + 30), (0, 0, 0), 1)
        
        # 間取り名と説明を描画
        description = descriptions.get(madori_name, '')
        text = f"{madori_name}: {description}"
        
        cv2.putText(out, text, (legend_pos_x + 35, legend_y + 22), 
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1, cv2.LINE_AA)
    
    return out, floorplan_stats

def draw_grid_on_rect(
    image: np.ndarray,
    rect: Tuple[int, int, int, int],
    grid_mm: float,
    image_width_px: int,
    fill_color: Tuple[int, int, int] = (255, 0, 0),
    alpha: float = 0.4,
    line_color: Tuple[int, int, int] = (0, 0, 255),
    line_thickness: int = 2
) -> np.ndarray:
    """
    指定した長方形領域に半透明塗りつぶし+グリッド線を描画。
    A3(横420mm)想定で「grid_mm」をピクセル換算し、
    四辺がすべて領域内に収まるマス目だけを描画する。

    Args:
        image: 描画対象のBGR画像
        rect: (x, y, width, height) 長方形領域
        grid_mm: 紙上(mm)単位のグリッド間隔 (例: 9.1mm = 実物910mmの1/100)
        image_width_px: 入力画像の横幅(px)
                       → これを420mmとみなし 1mm = image_width_px/420 px で換算
        fill_color: 塗りつぶし色 (BGR)
        alpha: 塗りつぶしの透明度(0~1)
        line_color: グリッド線の色 (BGR)
        line_thickness: グリッド線の太さ(px)
    Returns:
        グリッド描画後の画像(BGR)
    """
    # 元画像をコピー
    out = image.copy()

    x, y, w, h = rect
    x_end, y_end = x + w, y + h

    # まず半透明塗りつぶし
    overlay = out.copy()
    cv2.rectangle(overlay, (x, y), (x_end, y_end), fill_color, cv2.FILLED)
    cv2.addWeighted(overlay, alpha, out, 1 - alpha, 0, out)

    # 矩形の外枠
    cv2.rectangle(out, (x, y), (x_end, y_end), line_color, line_thickness)

    # A3横420mm→画面幅image_width_pxより1mm→(image_width_px/420)px
    px_per_mm = image_width_px / A3_WIDTH_MM

    # grid_mm（紙上のmm）をピクセル換算
    cell_px = int(round(grid_mm * px_per_mm))

    # セルが領域より大きすぎる場合はfallback
    if cell_px > w or cell_px > h:
        fallback = max(1, min(w, h) // 5)
        logger.warning(f"セルサイズ {cell_px}px が領域より大きいため、{fallback}px に調整します")
        cell_px = fallback

    # 「四辺がすべて領域内に収まる」マス目だけを描画する
    # y方向にセルを走査
    row = 0
    while True:
        cell_y1 = y + row * cell_px
        cell_y2 = cell_y1 + cell_px
        if cell_y2 > y_end:
            # 下がはみ出すので終了
            break
        
        # x方向にセルを走査
        col = 0
        while True:
            cell_x1 = x + col * cell_px
            cell_x2 = cell_x1 + cell_px
            if cell_x2 > x_end:
                # 右がはみ出すので次の行へ
                break
            
            # ===== マスの四隅 (cell_x1, cell_y1) → (cell_x2, cell_y2) =====
            # 四辺をそれぞれ描画

            # 上辺
            cv2.line(out, (cell_x1, cell_y1), (cell_x2, cell_y1), line_color, line_thickness)
            
            # 下辺
            cv2.line(out, (cell_x1, cell_y2), (cell_x2, cell_y2), line_color, line_thickness)
            
            # 左辺
            cv2.line(out, (cell_x1, cell_y1), (cell_x1, cell_y2), line_color, line_thickness)
            
            # 右辺
            cv2.line(out, (cell_x2, cell_y1), (cell_x2, cell_y2), line_color, line_thickness)

            col += 1
        
        row += 1

    return out

def process_image(
    model,
    image_file,
    global_setback_mm: float = 5.0,    # 1. 建物全体のセットバック
    road_setback_mm: float = 50.0,     # 2. 道路近辺の追加セットバック
    grid_mm: float = 9.1,              # グリッド間隔 (A3で描画)
    # 後方互換性のための古いパラメータ（非推奨）
    near_offset_px: Optional[int] = None,
    far_offset_px: Optional[int] = None,
    # 間取り表示モード
    floorplan_mode: bool = False       # Trueなら間取り表示、Falseならランダムアルファベット
) -> Optional[Tuple[Image.Image, Dict[str, Any]]]:
    """
    画像を処理して、セグメンテーション・マスク操作・グリッド生成を行う。
    
    すべての画像をA3サイズ(150dpi: 2481x1754px)にリサイズして処理するため、
    どんな画像でも常に同じスケールでグリッドが描画される。
    
    2段階セットバック処理:
    (1) 全建物を global_setback_mm だけセットバック
    (2) 道路近くの部分だけ road_setback_mm 追加セットバック
    (3) 残った領域にグリッド描画
    
    Args:
        model: YOLO推論モデル(YOLOクラスなど)
        image_file: 入力画像(アップローダ等のファイルオブジェクトやパス)
        global_setback_mm: 建物全体のセットバック量(mm)
        road_setback_mm: 道路近辺の追加セットバック量(mm)
        grid_mm: 紙上のグリッド間隔(mm) (例: 9.1mm = 実物910mmの1/100)
        near_offset_px: [非推奨] 後方互換性のため。代わりにglobal_setback_mmとroad_setback_mmを使用
        far_offset_px: [非推奨] 後方互換性のため。代わりにglobal_setback_mmを使用
        floorplan_mode: 間取り表示モードが有効かどうか (True=間取り表示, False=ランダムアルファベット)
    Returns:
        Tuple[処理後のPIL画像, デバッグ情報の辞書] または None (失敗時)
    """
    try:
        # 後方互換性のための変換 (古いパラメータが指定された場合)
        if near_offset_px is not None or far_offset_px is not None:
            logger.warning(
                "near_offset_px/far_offset_pxパラメータは非推奨です。"
                "代わりにglobal_setback_mm/road_setback_mmを使用してください。"
            )
            # A3サイズのピクセル/mm変換比を概算
            px_per_mm_approx = A3_WIDTH_PX / A3_WIDTH_MM
            
            # 古いパラメータから新しいパラメータへの変換
            if near_offset_px is not None:
                road_setback_mm = near_offset_px / px_per_mm_approx
            
            if far_offset_px is not None:
                global_setback_mm = far_offset_px / px_per_mm_approx
        
        # デバッグ情報を格納する辞書
        debug_info = {
            "params": {
                "global_setback_mm": global_setback_mm,
                "road_setback_mm": road_setback_mm,
                "grid_mm": grid_mm,
                "floorplan_mode": floorplan_mode
            },
            "fallback_activated": False,
            "bounding_box": None,
            "cell_px": None,
            "px_per_mm": None,
            "image_size": None,
            "resized": False,
            "original_size": None,
            "grid_stats": None  # グリッド描画の統計情報
        }

        # 画像ファイルの読み込み (Streamlit or Path対応)
        if hasattr(image_file, 'getvalue'):
            # StreamlitUploaderは getvalue() をもつ
            image_bytes = image_file.getvalue()
        elif hasattr(image_file, 'read'):
            # 一般的なファイルライクオブジェクト
            image_bytes = image_file.read()
        elif isinstance(image_file, bytes):
            # すでにバイト列
            image_bytes = image_file
        elif isinstance(image_file, str) and (os.path.exists(image_file) or image_file.startswith('http')):
            # ファイルパスまたはURL
            if os.path.exists(image_file):
                with open(image_file, 'rb') as f:
                    image_bytes = f.read()
            else:
                resp = requests.get(image_file)
                resp.raise_for_status()
                image_bytes = resp.content
        else:
            logger.error(f"Unsupported image file type: {type(image_file)}")
            return None

        # 画像をOpenCVで読み込み
        nparr = np.frombuffer(image_bytes, np.uint8)
        orig = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if orig is None:
            logger.error("Failed to decode image")
            return None
            
        # 元の画像サイズを記録
        orig_h, orig_w = orig.shape[:2]
        debug_info["original_size"] = {"width_px": orig_w, "height_px": orig_h}
        
        # 画像をA3サイズ（2481x1754px @ 150dpi）にリサイズ
        resized = cv2.resize(orig, (A3_WIDTH_PX, A3_HEIGHT_PX), interpolation=cv2.INTER_LINEAR)
        debug_info["resized"] = True
        debug_info["a3_size"] = {"width_px": A3_WIDTH_PX, "height_px": A3_HEIGHT_PX}
        
        # リサイズした画像を一時ファイルに書き出して推論
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            is_success, buffer = cv2.imencode(".jpg", resized)
            if not is_success:
                logger.error("Failed to encode resized image")
                return None
            tmp.write(buffer)
            tmp.close()
            results = model(tmp.name, task="segment")
            os.unlink(tmp.name)  # 一時ファイル削除

        # 推論元のオリジナル画像（既にA3サイズにリサイズされている）
        a3_img = resized.copy()
        
        # 画像サイズを取得 (h,w) - A3サイズになっているはず
        h, w = a3_img.shape[:2]
        debug_info["image_size"] = {"width_px": w, "height_px": h}

        # マスク初期化
        house_mask = np.zeros((h, w), dtype=np.uint8)
        road_mask = np.zeros((h, w), dtype=np.uint8)

        # セグメンテーション結果を合成
        if results[0].masks is not None:
            for seg_data, cls_id in zip(results[0].masks.data, results[0].boxes.cls):
                m = seg_data.cpu().numpy().astype(np.uint8)
                # YOLO出力マスクを画像サイズ(w,h)にリサイズ
                resized_mask = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)

                if int(cls_id) == HOUSE_CLASS_ID:
                    house_mask = np.maximum(house_mask, resized_mask)
                elif int(cls_id) == ROAD_CLASS_ID:
                    road_mask = np.maximum(road_mask, resized_mask)

        # 元画像をコピー
        out_bgr = a3_img.copy()
        
        # 1) House領域を緑色で可視化
        overlay_house = out_bgr.copy()
        overlay_house[house_mask == 1] = (0, 255, 0)  # BGR(緑)
        cv2.addWeighted(overlay_house, 0.3, out_bgr, 0.7, 0, out_bgr)
        
        # 2) Road領域をマゼンタで可視化
        overlay_road = out_bgr.copy()
        overlay_road[road_mask == 1] = (255, 0, 255)  # BGR(マゼンタ)
        cv2.addWeighted(overlay_road, 0.3, out_bgr, 0.7, 0, out_bgr)

        # --- B) まず建物マスクを "グローバルセットバック" だけ収縮 ---
        # mm→px 換算（A3幅）
        px_per_mm = w / A3_WIDTH_MM  # A3の横幅=420mm, 画像幅=w px
        global_setback_px = int(round(global_setback_mm * px_per_mm))
        debug_info["px_per_mm"] = px_per_mm
        debug_info["global_setback_px"] = global_setback_px
        
        # 1. 全建物を内側に収縮
        house_global = offset_mask_by_distance(house_mask, global_setback_px)
        
        # --- C) 道路近辺のみ追加で セットバック（＝道路近い箇所だけさらに収縮）---
        # 1) 道路との距離マップを計算し "dist < road_setback_px" が近接
        road_setback_px = int(round(road_setback_mm * px_per_mm))
        debug_info["road_setback_px"] = road_setback_px
        
        # 距離変換： 道路を "前景0" にして distanceTransform
        road_bin = (road_mask > 0).astype(np.uint8)
        # distanceTransformは「0からの距離」なので、道路=1を反転して0にする
        dist_map = cv2.distanceTransform(1 - road_bin, cv2.DIST_L2, 5)
        
        # 道路からroad_setback_px以内の領域を「近接」とみなす
        near_road = (dist_map < road_setback_px).astype(np.uint8)
        
        # 2) house_global の "near_road" 部分だけ road_setback_px 分だけ追加収縮
        house_near = (house_global & near_road)
        house_far = (house_global & (1 - near_road))
        
        # 道路近接部のみ追加収縮
        house_near_offset = offset_mask_by_distance(house_near, road_setback_px)
        
        # 最終マスク = 遠い部分 + 近接部分(追加収縮済み)
        final_house = np.maximum(house_far, house_near_offset)

        # 最終マスク内だけにグリッド描画
        if np.sum(final_house) > 0:  # マスクが空でない場合
            if floorplan_mode:
                # 間取り表示モード
                out_bgr, floorplan_stats = draw_floorplan_on_mask(
                    image=out_bgr,
                    final_mask=final_house,
                    grid_mm=grid_mm,
                    px_per_mm=px_per_mm,
                    fill_color=(255, 0, 0),
                    alpha=0.4,
                    line_color=(0, 0, 255),
                    line_thickness=2
                )
                
                # 間取り情報をデバッグ情報に追加
                debug_info["floorplan_stats"] = floorplan_stats
                
                # バウンディングボックス情報をデバッグ情報に追加
                if floorplan_stats.get("bounding_box"):
                    debug_info["bounding_box"] = floorplan_stats["bounding_box"]
                
                # セルサイズ情報をデバッグ情報に追加
                if floorplan_stats.get("cell_px"):
                    debug_info["cell_px"] = floorplan_stats["cell_px"]
                
                # UIに表示する間取り情報
                debug_info["madori_info"] = floorplan_stats.get("madori_info", {})
                
                # 最後にグリッド統計情報にデータをコピー（互換性のため）
                debug_info["grid_stats"] = {
                    "cells_drawn": len(floorplan_stats.get("positions", {})),
                    "cell_px": floorplan_stats.get("cell_px"),
                    "bounding_box": floorplan_stats.get("bounding_box"),
                    "grid_cells": floorplan_stats.get("grid_size")
                }
            else:
                # 通常のランダムアルファベットモード
                out_bgr, grid_stats = draw_grid_on_mask(
                    image=out_bgr,
                    final_mask=final_house,
                    grid_mm=grid_mm,
                    px_per_mm=px_per_mm,
                    fill_color=(255, 0, 0),
                    alpha=0.4,
                    line_color=(0, 0, 255),
                    line_thickness=2
                )
                
                # グリッド統計情報をデバッグ情報に追加
                debug_info["grid_stats"] = grid_stats
                
                # UIに表示するセル数を明示的に設定
                debug_info["grid_cells"] = grid_stats.get("grid_cells", {})
                debug_info["total_cells"] = grid_stats.get("total_cells_in_bbox", 0)
                
                # バウンディングボックス情報をデバッグ情報に追加
                if grid_stats.get("bounding_box"):
                    debug_info["bounding_box"] = grid_stats["bounding_box"]
                
                # セルサイズ情報をデバッグ情報に追加
                if grid_stats.get("cell_px"):
                    debug_info["cell_px"] = grid_stats["cell_px"]
        else:
            logger.warning("オフセット後の住居領域が見つかりません")
            debug_info["error"] = "オフセット後の住居領域が見つかりません"

        # BGR→RGB変換してPIL画像化
        rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb), debug_info

    except Exception as e:
        logger.error(f"画像処理中にエラー: {e}", exc_info=True)
        return None