"""
セグメンテーションマスクの処理と操作のためのユーティリティ関数
(マスク外の不要グリッドを非表示にする修正版)
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
    fill_corridor,
    process_large_corridors,
)

logger = logging.getLogger(__name__)

# data.yaml を読み込み
with open('config/data.yaml', 'r') as f:
    data_config = yaml.safe_load(f)
class_names = data_config['names']

HOUSE_CLASS_ID = class_names.index('House') if 'House' in class_names else None
ROAD_CLASS_ID = class_names.index('Road') if 'Road' in class_names else None

A3_WIDTH_PX  = 2481
A3_HEIGHT_PX = 1754
A3_WIDTH_MM  = 420.0

ALPHABET_LIST = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def offset_mask_by_distance(mask: np.ndarray, offset_px: int) -> np.ndarray:
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
    画像を推論し、マスク処理・レイアウト生成(またはランダムアルファベット表示)を行う。
    """
    try:
        # 古いパラメータ(near_offset_px, far_offset_px)の互換処理
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

        # 画像を読み込み (ファイルorURLorStreamlitUploader対応)
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

        # 元のサイズを記録
        orig_h, orig_w = orig.shape[:2]
        debug_info["original_size"] = {"width_px": orig_w, "height_px": orig_h}

        # A3サイズ(150dpi想定)にリサイズ
        resized = cv2.resize(orig, (A3_WIDTH_PX, A3_HEIGHT_PX), interpolation=cv2.INTER_LINEAR)
        debug_info["resized"] = True
        debug_info["a3_size"] = {"width_px": A3_WIDTH_PX, "height_px": A3_HEIGHT_PX}

        # 推論用に一時ファイルに保存
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            is_success, buffer = cv2.imencode(".jpg", resized)
            if not is_success:
                logger.error("Failed to encode resized image")
                return None
            tmp.write(buffer)
            tmp.close()
            results = model(tmp.name, task="segment")
            os.unlink(tmp.name)

        # 推論後の画像(リサイズ済み)をコピー
        a3_img = resized.copy()
        h, w = a3_img.shape[:2]
        debug_info["image_size"] = {"width_px": w, "height_px": h}

        # House,Roadマスクの合成
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

        # マスク可視化用(緑=House, マゼンタ=Road)
        out_bgr = a3_img.copy()
        overlay_house = out_bgr.copy()
        overlay_house[house_mask == 1] = (0, 255, 0)
        cv2.addWeighted(overlay_house, 0.3, out_bgr, 0.7, 0, out_bgr)

        overlay_road = out_bgr.copy()
        overlay_road[road_mask == 1] = (255, 0, 255)
        cv2.addWeighted(overlay_road, 0.3, out_bgr, 0.7, 0, out_bgr)

        # px_per_mm算出
        px_per_mm = w / A3_WIDTH_MM
        debug_info["px_per_mm"] = px_per_mm

        # グローバルセットバック
        global_setback_px = int(round(global_setback_mm * px_per_mm))
        debug_info["global_setback_px"] = global_setback_px
        house_global = offset_mask_by_distance(house_mask, global_setback_px)

        # 道路近接セットバック
        road_setback_px = int(round(road_setback_mm * px_per_mm))
        debug_info["road_setback_px"] = road_setback_px

        # 距離変換: 道路近いところだけさらに収縮
        road_bin = (road_mask > 0).astype(np.uint8)
        dist_map = cv2.distanceTransform(1 - road_bin, cv2.DIST_L2, 5)
        near_road = (dist_map < road_setback_px).astype(np.uint8)

        house_near = (house_global & near_road)
        house_far  = (house_global & (1 - near_road))

        house_near_offset = offset_mask_by_distance(house_near, road_setback_px)
        final_house = np.maximum(house_far, house_near_offset)

        # 旗竿形状(細すぎる領域)を除去: 最大連結成分のみ残す
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

        # 極端に細長い旗竿形状も除去(アスペクト比>5 かつ面積小さい)
        contours, _ = cv2.findContours(final_house, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            rx, ry, rw, rh = cv2.boundingRect(contour)
            aspect_ratio = max(rw / rh, rh / rw)
            area = rw * rh
            if aspect_ratio > 5.0 and area < (h * w * 0.2):
                cv2.fillPoly(final_house, [contour], 0)

        if np.sum(final_house) == 0:
            logger.warning("オフセット後の住居領域が見つかりません")
            debug_info["error"] = "オフセット後の住居領域が見つかりません"
            rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb), debug_info

        # 間取りモード or ランダムアルファベットモード
        if floorplan_mode:
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
    「ランダムアルファベット」モード用の描画:
    マスク内にだけセルを描画し、各セル中心にランダムアルファベットを配置。
    マスク外にあるグリッドは表示しない。
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

    # マスク輪郭からバウンディングボックス取得
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        grid_stats["error"] = "マスクが空です"
        return out, grid_stats

    big_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(big_contour)
    grid_stats["bounding_box"] = {"x": x, "y": y, "width": w, "height": h}

    # マスク領域を半透明塗り
    overlay = out.copy()
    mask_area = np.zeros_like(out)
    mask_area[final_mask == 1] = fill_color
    cv2.addWeighted(mask_area, alpha, out, 1, 0, out)

    # セルサイズ固定(約9.1mm→54px)
    cell_px = 54
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

    # 各セルごとにマスク内かどうかチェックして描画
    for row in range(grid_rows):
        cell_y1 = y + row * cell_px
        cell_y2 = cell_y1 + cell_px
        for col in range(grid_cols):
            cell_x1 = x + col * cell_px
            cell_x2 = cell_x1 + cell_px

            # セルが全てマスク内にあるか確認
            cell_roi = final_mask[cell_y1:cell_y2, cell_x1:cell_x2]
            if not np.all(cell_roi == 1):
                grid_stats["cells_skipped"] += 1
                grid_stats["reason_not_in_mask"] += 1
                continue

            # ランダムアルファベット
            cell_letter = random.choice(ALPHABET_LIST)
            grid_stats["alphabet_counts"][cell_letter] += 1

            # セル枠線描画
            cv2.line(out, (cell_x1, cell_y1), (cell_x2, cell_y1), line_color, line_thickness)
            cv2.line(out, (cell_x1, cell_y2), (cell_x2, cell_y2), line_color, line_thickness)
            cv2.line(out, (cell_x1, cell_y1), (cell_x1, cell_y2), line_color, line_thickness)
            cv2.line(out, (cell_x2, cell_y1), (cell_x2, cell_y2), line_color, line_thickness)

            # 中心にテキスト
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
    間取り表示モード:
     1) マスクの範囲だけを有効とする valid_grid_mask を作成
     2) Site(グリッド)に部屋(E,L,D,K,B,UT,T)を配置
     3) 空きスペースを廊下(C)で埋める→さらに大きい廊下をR部屋化
     4) valid_grid_mask=0(=マスク外)のセルに関しては間取りを描画しない
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

    # 最大輪郭のバウンディングボックス
    big_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(big_contour)
    floorplan_stats["bounding_box"] = {"x": x, "y": y, "width": w, "height": h}

    # マスク領域を半透明着色(青)
    overlay = out.copy()
    mask_area = np.zeros_like(out)
    mask_area[final_mask == 1] = (255, 0, 0)
    cv2.addWeighted(mask_area, 0.4, out, 1, 0, out)

    # セルサイズ (約9.1mm→54px)
    cell_px = 54
    floorplan_stats["cell_px"] = cell_px

    grid_cols = w // cell_px
    grid_rows = h // cell_px
    floorplan_stats["grid_size"] = {"rows": grid_rows, "cols": grid_cols}

    # マスク内セル(=1)だけを有効にするvalid_grid_mask
    valid_grid_mask = np.zeros((grid_rows, grid_cols), dtype=np.uint8)
    for i in range(grid_rows):
        for j in range(grid_cols):
            cell_x1 = x + j * cell_px
            cell_y1 = y + i * cell_px
            cell_x2 = cell_x1 + cell_px
            cell_y2 = cell_y1 + cell_px

            subroi = final_mask[cell_y1:cell_y2, cell_x1:cell_x2]
            if np.all(subroi == 1):
                valid_grid_mask[i, j] = 1
            else:
                floorplan_stats["cells_skipped"] += 1
                floorplan_stats["reason_not_in_mask"] += 1

    # Site作成 & 間取り情報セット
    site = Site(grid_cols, grid_rows)
    madori_dict = create_madori_odict(
        L_size=(4,3),
        D_size=(3,2),
        K_size=(2,2),
        UT_size=(2,2)
    )
    site.set_madori_info(madori_dict)
    grid_data = site.init_grid()

    # 部屋配置(玄関E→L→K→D→B→UT→T)
    order = ["E","L","K","D","B","UT","T"]
    grid_data, positions = arrange_rooms_with_constraints(
        grid_data,
        site,
        order,
        valid_mask=valid_grid_mask
    )

    # 空きスペースを廊下(C=7)で埋める
    grid_data = fill_corridor(grid_data, corridor_code=7)

    # 大きな廊下領域をR部屋化
    grid_data, new_rooms, new_room_count = process_large_corridors(
        grid_data,
        corridor_code=7,
        min_room_size=4
    )

    # 部屋ごとに色を割り当て
    color_map = {
        'E': (102, 178, 255),   # 玄関
        'L': (144, 238, 144),   # リビング
        'D': (255, 191, 0),     # ダイニング
        'K': (147, 20, 255),    # キッチン
        'B': (95, 158, 160),    # バスルーム
        'T': (180, 105, 255),   # トイレ
        'UT': (160, 190, 240),  # 脱衣所
        'C': (220, 220, 220)    # 廊下
    }

    # グリッドを描画(但し valid_grid_mask=1 のセルだけ)
    cells_drawn = 0
    for i in range(grid_rows):
        for j in range(grid_cols):
            code = grid_data[i, j]
            if code <= 0:
                continue
            # マスク外=0 のセルは間取りを描画しない
            if valid_grid_mask[i, j] == 0:
                continue

            cell_x1 = x + j * cell_px
            cell_y1 = y + i * cell_px
            cell_x2 = cell_x1 + cell_px
            cell_y2 = cell_y1 + cell_px

            # コード→部屋名
            found_name = None
            for nm, md in site.madori_info.items():
                if md.code == code:
                    found_name = nm
                    break
            # R(追加部屋)判定
            if (found_name is None) and (code >= 10):
                rid = code - 10
                found_name = f"R{rid}"

            # 色決定
            c = color_map.get(found_name, (200,200,200))

            # 塗りつぶし＋枠線
            cv2.rectangle(out, (cell_x1, cell_y1), (cell_x2, cell_y2), c, -1)
            cv2.rectangle(out, (cell_x1, cell_y1), (cell_x2, cell_y2), (100,100,100), 1)
            cells_drawn += 1

    # 主要部屋(E,L,K,D,B,UT,T)のラベルを描画
    for name, pos in positions.items():
        if name == 'C':
            continue
        m = site.madori_info.get(name, None)
        if m is None:
            continue
        room_x, room_y = pos
        w_ = m.width
        h_ = m.height
        center_x = room_x + w_//2
        center_y = room_y + h_//2
        px_x = x + center_x*cell_px + cell_px//2
        px_y = y + center_y*cell_px + cell_px//2

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.2
        text_color = (0, 0, 0)
        text_thickness = 2
        text_size = cv2.getTextSize(name, font, font_scale, text_thickness)[0]
        text_x = px_x - text_size[0] // 2
        text_y = px_y + text_size[1] // 2

        bg_padding = 4
        bg_rect = (
            text_x - bg_padding,
            text_y - text_size[1] - bg_padding,
            text_size[0] + bg_padding*2,
            text_size[1] + bg_padding*2
        )
        cv2.rectangle(out,
                      (bg_rect[0], bg_rect[1]),
                      (bg_rect[0] + bg_rect[2], bg_rect[1] + bg_rect[3]),
                      (255,255,255),
                      -1)
        cv2.putText(out, name, (text_x, text_y), font,
                    font_scale, text_color, text_thickness, cv2.LINE_AA)

    # R部屋(R1,R2...)のラベル描画
    labeled_corr, n_labels_corr = cv2.connectedComponents((grid_data >= 10).astype(np.uint8))
    if isinstance(n_labels_corr, np.ndarray):
        if n_labels_corr.size == 1:
            n_labels_corr = n_labels_corr.item()
        else:
            n_labels_corr = int(np.max(n_labels_corr)) + 1
    for lbl in range(1, n_labels_corr):
        region_mask = (labeled_corr == lbl)
        codes_in_region = grid_data[region_mask]
        code_vals, counts = np.unique(codes_in_region, return_counts=True)
        if len(code_vals) == 0:
            continue
        r_code = code_vals[np.argmax(counts)]
        rid = r_code - 10
        r_name = f"R{rid}"

        ys, xs = np.where(region_mask)
        miny, maxy = ys.min(), ys.max()
        minx, maxx = xs.min(), xs.max()
        w_ = maxx-minx+1
        h_ = maxy-miny+1

        # 追加部屋情報
        floorplan_stats["madori_info"][r_name] = {
            "name": r_name,
            "width": w_,
            "height": h_,
            "neighbor": None
        }

        cy = int(np.mean(ys))
        cx = int(np.mean(xs))
        px_x = x + cx*cell_px + cell_px//2
        px_y = y + cy*cell_px + cell_px//2

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.2
        text_color = (0, 0, 0)
        text_thickness = 2
        text_size = cv2.getTextSize(r_name, font, font_scale, text_thickness)[0]
        text_x = px_x - text_size[0] // 2
        text_y = px_y + text_size[1] // 2

        bg_padding = 4
        bg_rect = (
            text_x - bg_padding,
            text_y - text_size[1] - bg_padding,
            text_size[0] + bg_padding*2,
            text_size[1] + bg_padding*2
        )
        cv2.rectangle(out,
                      (bg_rect[0], bg_rect[1]),
                      (bg_rect[0]+bg_rect[2], bg_rect[1]+bg_rect[3]),
                      (255,255,255),
                      -1)
        cv2.putText(out, r_name, (text_x, text_y), font,
                    font_scale, text_color, text_thickness, cv2.LINE_AA)

    floorplan_stats["cells_drawn"] = cells_drawn

    # 間取り情報(positions & R部屋含む)
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

    if isinstance(n_labels_corr, np.ndarray):
        if n_labels_corr.size == 1:
            n_labels_corr = n_labels_corr.item()
        else:
            n_labels_corr = int(np.max(n_labels_corr)) + 1

    for lbl in range(1, n_labels_corr):
        region_mask = (labeled_corr == lbl)
        codes_in_region = grid_data[region_mask]
        code_vals, counts = np.unique(codes_in_region, return_counts=True)
        if len(code_vals) == 0:
            continue
        r_code = code_vals[np.argmax(counts)]
        rid = r_code - 10
        r_name = f"R{rid}"

        ys, xs = np.where(region_mask)
        miny, maxy = ys.min(), ys.max()
        minx, maxx = xs.min(), xs.max()
        w_ = maxx-minx+1
        h_ = maxy-miny+1
        floorplan_stats["madori_info"][r_name] = {
            "name": r_name,
            "width": w_,
            "height": h_,
            "neighbor": None
        }
        pos_dict[r_name] = {
            "x": minx,
            "y": miny,
            "grid_x": x + minx*cell_px,
            "grid_y": y + miny*cell_px
        }

    floorplan_stats["positions"] = pos_dict

    return out, floorplan_stats