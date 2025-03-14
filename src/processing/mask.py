# src/processing/mask.py
"""
セグメンテーションマスクの処理と操作のためのユーティリティ関数
(改変版:
 1)最初から「マスク内のみ」でのレイアウト配置を行うようにし、
 2)トイレTは (1×2)=2マス、
 3)LDKやRなどは縮小・拡大をサイトのmadori_info設定にまかせる
)
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
import random
import sys
from collections import OrderedDict

from src.processing.arrangement import (
    Site,
    Madori,
    create_madori_odict,
    arrange_rooms_with_constraints,
    fill_corridor
)

logger = logging.getLogger(__name__)

# data.yamlからクラス名を読み込む（既存）
with open('config/data.yaml', 'r') as f:
    data_config = yaml.safe_load(f)
class_names = data_config['names']

# クラスID（House, Road）
HOUSE_CLASS_ID = class_names.index('House') if 'House' in class_names else None
ROAD_CLASS_ID = class_names.index('Road') if 'Road' in class_names else None

# A3サイズ (150dpi想定)
A3_WIDTH_PX  = 2481
A3_HEIGHT_PX = 1754
A3_WIDTH_MM  = 420.0  # 420mm (A3横幅)

# ランダムアルファベット用 (通常モード)
ALPHABET_LIST = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def offset_mask_by_distance(mask: np.ndarray, offset_px: int) -> np.ndarray:
    """
    マスクを距離変換して内側に収縮
    offset_px > 0 の場合に収縮
    """
    if offset_px <= 0:
        return mask.copy()

    bin_mask = (mask > 0).astype(np.uint8)
    dist = cv2.distanceTransform(bin_mask, cv2.DIST_L2, 5)
    shrunk = (dist >= offset_px).astype(np.uint8)
    return shrunk


def process_image(
    model,
    image_file,
    global_setback_mm: float = 5.0,
    road_setback_mm: float = 50.0,
    grid_mm: float = 9.1,
    near_offset_px: Optional[int] = None,
    far_offset_px: Optional[int] = None,
    floorplan_mode: bool = False
) -> Optional[Tuple[Image.Image, Dict[str, Any]]]:
    """
    画像を推論し、マスク処理・レイアウト生成(またはランダムアルファベット)を行う
    1) 全建物を global_setback_mmだけ内側に収縮
    2) 道路近辺だけ road_setback_mm 追加収縮
    3) 旗竿形状除去
    4) floorplan_mode=Trueなら間取り配置, Falseならランダムアルファベット
    """
    try:
        # 古いパラメータの置き換え (near_offset_px, far_offset_px)
        if near_offset_px is not None or far_offset_px is not None:
            logger.warning(
                "near_offset_px/far_offset_pxは非推奨。"
                "global_setback_mm/road_setback_mmをご利用ください。"
            )
            px_per_mm_approx = A3_WIDTH_PX / A3_WIDTH_MM
            if near_offset_px is not None:
                road_setback_mm = near_offset_px / px_per_mm_approx
            if far_offset_px is not None:
                global_setback_mm = far_offset_px / px_per_mm_approx

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
            "grid_stats": None
        }

        # 画像読み込み (StreamlitUploader / パス / URLに対応)
        if hasattr(image_file, 'getvalue'):
            image_bytes = image_file.getvalue()
        elif hasattr(image_file, 'read'):
            image_bytes = image_file.read()
        elif isinstance(image_file, bytes):
            image_bytes = image_file
        elif isinstance(image_file, str) and (os.path.exists(image_file) or image_file.startswith('http')):
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

        nparr = np.frombuffer(image_bytes, np.uint8)
        orig = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if orig is None:
            logger.error("Failed to decode image")
            return None

        # 元サイズを記録
        orig_h, orig_w = orig.shape[:2]
        debug_info["original_size"] = {"width_px": orig_w, "height_px": orig_h}

        # A3にリサイズ
        resized = cv2.resize(orig, (A3_WIDTH_PX, A3_HEIGHT_PX), interpolation=cv2.INTER_LINEAR)
        debug_info["resized"] = True
        debug_info["a3_size"] = {"width_px": A3_WIDTH_PX, "height_px": A3_HEIGHT_PX}

        # 推論 (一時ファイル化して model に渡す)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            is_success, buffer = cv2.imencode(".jpg", resized)
            if not is_success:
                logger.error("Failed to encode resized image")
                return None
            tmp.write(buffer)
            tmp.close()
            results = model(tmp.name, task="segment")
            os.unlink(tmp.name)

        # 画像サイズ
        a3_img = resized.copy()
        h, w = a3_img.shape[:2]
        debug_info["image_size"] = {"width_px": w, "height_px": h}

        # House, Roadマスク合成
        house_mask = np.zeros((h, w), dtype=np.uint8)
        road_mask = np.zeros((h, w), dtype=np.uint8)

        if results[0].masks is not None:
            for seg_data, cls_id in zip(results[0].masks.data, results[0].boxes.cls):
                m = seg_data.cpu().numpy().astype(np.uint8)
                resized_mask = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
                if int(cls_id) == HOUSE_CLASS_ID:
                    house_mask = np.maximum(house_mask, resized_mask)
                elif int(cls_id) == ROAD_CLASS_ID:
                    road_mask = np.maximum(road_mask, resized_mask)

        # 緑(家) & マゼンタ(道路)で可視化
        out_bgr = a3_img.copy()
        overlay_house = out_bgr.copy()
        overlay_house[house_mask == 1] = (0, 255, 0)
        cv2.addWeighted(overlay_house, 0.3, out_bgr, 0.7, 0, out_bgr)

        overlay_road = out_bgr.copy()
        overlay_road[road_mask == 1] = (255, 0, 255)
        cv2.addWeighted(overlay_road, 0.3, out_bgr, 0.7, 0, out_bgr)

        # mm→px
        px_per_mm = w / A3_WIDTH_MM
        debug_info["px_per_mm"] = px_per_mm

        # グローバルセットバック
        global_setback_px = int(round(global_setback_mm * px_per_mm))
        debug_info["global_setback_px"] = global_setback_px
        house_global = offset_mask_by_distance(house_mask, global_setback_px)

        # 道路近接セットバック
        road_setback_px = int(round(road_setback_mm * px_per_mm))
        debug_info["road_setback_px"] = road_setback_px

        road_bin = (road_mask > 0).astype(np.uint8)
        dist_map = cv2.distanceTransform(1 - road_bin, cv2.DIST_L2, 5)
        near_road = (dist_map < road_setback_px).astype(np.uint8)

        house_near = (house_global & near_road)
        house_far = (house_global & (1 - near_road))

        house_near_offset = offset_mask_by_distance(house_near, road_setback_px)
        final_house = np.maximum(house_far, house_near_offset)

        # 旗竿形状除去: 最大連結成分のみ
        num_labels, labels = cv2.connectedComponents(final_house.astype(np.uint8))
        if num_labels > 1:
            largest_label = 1
            largest_size = 0
            for label_i in range(1, num_labels):
                size = np.sum(labels == label_i)
                if size > largest_size:
                    largest_size = size
                    largest_label = label_i
            final_house = (labels == largest_label).astype(np.uint8)

        # 細長旗竿も除去
        contours, _ = cv2.findContours(final_house, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            rx, ry, rw, rh = cv2.boundingRect(contour)
            aspect_ratio = max(rw/rh, rh/rw)
            area = rw * rh
            if aspect_ratio > 5.0 and area < (h * w * 0.2):
                cv2.fillPoly(final_house, [contour], 0)

        # マスクが空になってしまったら終了
        if np.sum(final_house) == 0:
            logger.warning("オフセット後の住居領域が見つかりません")
            debug_info["error"] = "オフセット後の住居領域が見つかりません"
            rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb), debug_info

        # ====== 間取り表示モード or ランダムアルファベットモード ======
        if floorplan_mode:
            # 間取り表示モード
            out_img, floorplan_stats = draw_floorplan_on_mask_with_mask(
                base_image=out_bgr,
                final_mask=final_house,
                grid_mm=grid_mm,
                px_per_mm=px_per_mm
            )
            debug_info["floorplan_stats"] = floorplan_stats
            if floorplan_stats.get("bounding_box"):
                debug_info["bounding_box"] = floorplan_stats["bounding_box"]
            if floorplan_stats.get("cell_px"):
                debug_info["cell_px"] = floorplan_stats["cell_px"]
            debug_info["madori_info"] = floorplan_stats.get("madori_info", {})
            debug_info["grid_stats"] = {
                "cells_drawn": len(floorplan_stats.get("positions", {})),
                "cell_px": floorplan_stats.get("cell_px"),
                "bounding_box": floorplan_stats.get("bounding_box"),
                "grid_cells": floorplan_stats.get("grid_size")
            }

            rgb = cv2.cvtColor(out_img, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb), debug_info

        else:
            # ランダムアルファベットモード
            out_img, grid_stats = draw_grid_on_mask(
                image=out_bgr,
                final_mask=final_house,
                grid_mm=grid_mm,
                px_per_mm=px_per_mm
            )
            debug_info["grid_stats"] = grid_stats
            debug_info["grid_cells"] = grid_stats.get("grid_cells", {})
            debug_info["total_cells"] = grid_stats.get("total_cells_in_bbox", 0)
            if grid_stats.get("bounding_box"):
                debug_info["bounding_box"] = grid_stats["bounding_box"]
            if grid_stats.get("cell_px"):
                debug_info["cell_px"] = grid_stats["cell_px"]

            rgb = cv2.cvtColor(out_img, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb), debug_info

    except Exception as e:
        logger.error(f"画像処理中にエラー: {e}", exc_info=True)
        return None


def draw_grid_on_mask(
    image: np.ndarray,
    final_mask: np.ndarray,
    grid_mm: float,
    px_per_mm: float,
    fill_color=(255, 0, 0),
    alpha=0.4,
    line_color=(0, 0, 255),
    line_thickness=2
):
    """
    マスク内にだけマス目(セル)を描画し、セル中央にランダムアルファベットを配置
    """
    out = image.copy()
    grid_stats = {
        "cell_px": None,
        "bounding_box": None,
        "total_cells_in_bbox": 0,
        "cells_drawn": 0,
        "cells_skipped": 0,
        "reason_not_in_mask": 0,
        "alphabet_counts": {}
    }

    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        grid_stats["error"] = "マスクが空です"
        return out, grid_stats

    big_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(big_contour)
    grid_stats["bounding_box"] = {"x": x, "y": y, "width": w, "height": h}

    # マスク領域を半透明塗りつぶし
    overlay = out.copy()
    mask_area = np.zeros_like(out)
    mask_area[final_mask == 1] = fill_color
    cv2.addWeighted(mask_area, alpha, out, 1, 0, out)

    cell_px = 54  # 固定サイズ (約9.1mm相当)
    grid_stats["cell_px"] = cell_px

    grid_cols = w // cell_px
    grid_rows = h // cell_px
    grid_lines_cols = grid_cols + 1
    grid_lines_rows = grid_rows + 1

    grid_stats["grid_lines"] = {"rows": grid_lines_rows, "cols": grid_lines_cols}
    grid_stats["grid_cells"] = {"rows": grid_rows, "cols": grid_cols}
    total_cells_in_bbox = grid_rows * grid_cols
    grid_stats["total_cells_in_bbox"] = total_cells_in_bbox

    # アルファベット使用回数を初期化
    for letter in ALPHABET_LIST:
        grid_stats["alphabet_counts"][letter] = 0

    for row in range(grid_rows):
        cell_y1 = y + row * cell_px
        cell_y2 = cell_y1 + cell_px
        for col in range(grid_cols):
            cell_x1 = x + col * cell_px
            cell_x2 = cell_x1 + cell_px
            # マスク判定
            padding = max(1, line_thickness // 2)
            check_x1 = max(0, cell_x1 - padding)
            check_y1 = max(0, cell_y1 - padding)
            check_x2 = min(final_mask.shape[1] - 1, cell_x2 + padding)
            check_y2 = min(final_mask.shape[0] - 1, cell_y2 + padding)
            cell_roi = final_mask[check_y1:check_y2, check_x1:check_x2]

            if not np.all(cell_roi == 1):
                grid_stats["cells_skipped"] += 1
                grid_stats["reason_not_in_mask"] += 1
                continue

            # ランダムアルファベット
            cell_letter = random.choice(ALPHABET_LIST)
            grid_stats["alphabet_counts"][cell_letter] += 1

            # 枠線描画
            cv2.line(out, (cell_x1, cell_y1), (cell_x2, cell_y1), line_color, line_thickness)
            cv2.line(out, (cell_x1, cell_y2), (cell_x2, cell_y2), line_color, line_thickness)
            cv2.line(out, (cell_x1, cell_y1), (cell_x1, cell_y2), line_color, line_thickness)
            cv2.line(out, (cell_x2, cell_y1), (cell_x2, cell_y2), line_color, line_thickness)
            
            # 中心に文字を描画
            cell_center_x = (cell_x1 + cell_x2) // 2
            cell_center_y = (cell_y1 + cell_y2) // 2
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.0
            text_color = (0, 0, 0)
            text_thickness = 2
            text_size = cv2.getTextSize(cell_letter, font, font_scale, text_thickness)[0]
            text_x = cell_center_x - text_size[0] // 2
            text_y = cell_center_y + text_size[1] // 2

            cv2.putText(out, cell_letter, (text_x, text_y),
                        font, font_scale, text_color, text_thickness, cv2.LINE_AA)
            
            grid_stats["cells_drawn"] += 1

    return out, grid_stats


def draw_floorplan_on_mask_with_mask(
    base_image: np.ndarray,
    final_mask: np.ndarray,
    grid_mm: float,
    px_per_mm: float
):
    """
    間取り配置。最初からマスクの中だけ使うようにするバージョン。
    1) マスクから valid_grid_mask を生成
    2) Site(グリッド) を初期化 & arrange_rooms_with_constraints(valid_mask=...) で部屋を配置
    3) 結果をOpenCVで描画
    """
    out = base_image.copy()
    floorplan_stats = {
        "cell_px": None,
        "bounding_box": None,
        "grid_size": None,
        "madori_info": {},
        "positions": {},
        "cells_drawn": 0,
        "cells_skipped": 0,
        "reason_not_in_mask": 0
    }

    # マスク輪郭
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        floorplan_stats["error"] = "マスクが空です"
        return out, floorplan_stats

    big_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(big_contour)
    floorplan_stats["bounding_box"] = {"x": x, "y": y, "width": w, "height": h}

    cell_px = 54  # 約9.1mm相当
    floorplan_stats["cell_px"] = cell_px

    grid_cols = w // cell_px
    grid_rows = h // cell_px

    # valid_grid_mask
    valid_grid_mask = np.zeros((grid_rows, grid_cols), dtype=np.uint8)
    for i in range(grid_rows):
        for j in range(grid_cols):
            cell_x1 = x + j * cell_px
            cell_y1 = y + i * cell_px
            cell_x2 = cell_x1 + cell_px
            cell_y2 = cell_y1 + cell_px
            subroi = final_mask[cell_y1 : cell_y2, cell_x1 : cell_x2]
            if np.all(subroi == 1):
                valid_grid_mask[i, j] = 1
            else:
                floorplan_stats["cells_skipped"] += 1
                floorplan_stats["reason_not_in_mask"] += 1

    # Site作成
    site = Site(grid_cols, grid_rows)

    # 例として L,D,K,UT 可変。T=(1×2),E=(2×2)
    madori_dict = create_madori_odict(L_size=(4,3), D_size=(3,2), K_size=(2,2), UT_size=(2,2))
    site.set_madori_info(madori_dict)

    grid_data = site.init_grid()

    # 配置順
    order = ["E","L","K","D","B","UT","T"]

    # 部屋配置 (マスク内のみ)
    grid_data, positions = arrange_rooms_with_constraints(
        grid_data,
        site,
        order,
        valid_mask=valid_grid_mask
    )

    # 廊下で埋める
    grid_data = fill_corridor(grid_data, corridor_code=7)

    # 部屋ごとの色
    color_map = {
        'L': (144, 238, 144),
        'D': (255, 191, 0),
        'K': (147, 20, 255),
        'E': (102, 178, 255),
        'B': (95, 158, 160),
        'T': (180, 105, 255),
        'UT': (160, 190, 240),
        'C': (220, 220, 220)
    }

    # マスク領域を半透明塗り
    overlay = out.copy()
    mask_area = np.zeros_like(out)
    mask_area[final_mask == 1] = (255, 0, 0)
    cv2.addWeighted(mask_area, 0.4, out, 1, 0, out)

    # グリッド描画
    cells_drawn = 0
    for i in range(grid_rows):
        for j in range(grid_cols):
            code = grid_data[i, j]
            if code <= 0:
                continue
            cell_x1 = x + j * cell_px
            cell_y1 = y + i * cell_px
            cell_x2 = cell_x1 + cell_px
            cell_y2 = cell_y1 + cell_px

            # 色塗り
            found_name = None
            for nm, md in site.madori_info.items():
                if md.code == code:
                    found_name = nm
                    break
            c = color_map.get(found_name, (200, 200, 200))
            cv2.rectangle(out, (cell_x1, cell_y1), (cell_x2, cell_y2), c, -1)
            # 枠線
            cv2.rectangle(out, (cell_x1, cell_y1), (cell_x2, cell_y2), (100,100,100), 1)
            
            cells_drawn += 1

    # 部屋名を各部屋の中心に1回だけ表示
    for name, pos in positions.items():
        if name == 'C':  # 廊下は表示しない
            continue
        
        # 部屋の位置と大きさを取得
        room_x, room_y = pos
        room_width = site.madori_info[name].width
        room_height = site.madori_info[name].height
        
        # 部屋の中心座標を計算
        center_grid_x = room_x + room_width // 2
        center_grid_y = room_y + room_height // 2
        
        # グリッド座標からピクセル座標に変換
        center_px_x = x + center_grid_x * cell_px + cell_px // 2
        center_px_y = y + center_grid_y * cell_px + cell_px // 2
        
        # テキスト描画
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.2  # フォントサイズを大きく
        text_color = (0, 0, 0)  # 黒色
        text_thickness = 2
        
        # テキストサイズを取得
        text_size = cv2.getTextSize(name, font, font_scale, text_thickness)[0]
        text_x = center_px_x - text_size[0] // 2
        text_y = center_px_y + text_size[1] // 2
        
        # 白い背景を追加して読みやすくする
        bg_padding = 4
        bg_rect = (
            text_x - bg_padding, 
            text_y - text_size[1] - bg_padding,
            text_size[0] + bg_padding * 2, 
            text_size[1] + bg_padding * 2
        )
        cv2.rectangle(out, 
                     (bg_rect[0], bg_rect[1]), 
                     (bg_rect[0] + bg_rect[2], bg_rect[1] + bg_rect[3]), 
                     (255, 255, 255), 
                     -1)
        
        # テキスト描画
        cv2.putText(out, name, (text_x, text_y),
                    font, font_scale, text_color, text_thickness, cv2.LINE_AA)

    floorplan_stats["cells_drawn"] = cells_drawn
    floorplan_stats["grid_size"] = {"rows": grid_rows, "cols": grid_cols}

    # 部屋情報収集
    pos_dict = {}
    for name, pos in positions.items():
        m = site.madori_info[name]
        pos_dict[name] = {
            "x": pos[0],
            "y": pos[1],
            "grid_x": x + pos[0]*cell_px,
            "grid_y": y + pos[1]*cell_px
        }
        floorplan_stats["madori_info"][name] = {
            "name": name,
            "width": m.width,
            "height": m.height,
            "neighbor": m.neighbor_name
        }
    floorplan_stats["positions"] = pos_dict

    return out, floorplan_stats