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
    Houseマスクの輪郭からバウンディングボックスを取得し、
    「セル全体がマスク内に完全に収まる」マス目だけを描画する。

    Args:
        image: 描画対象のBGR画像
        final_mask: グリッドを描画する対象のマスク(0 or 1)
        grid_mm: 紙上(mm)単位のグリッド間隔
        px_per_mm: mmあたりのピクセル数(A3横420mm想定)
        fill_color: セル塗りつぶし色 (BGR)
        alpha: 塗りつぶしの透明度(0~1)
        line_color: グリッド線の色 (BGR)
        line_thickness: グリッド線の太さ(px)
    Returns:
        Tuple[グリッド描画後の画像(BGR), 描画情報の辞書]
    """
    out = image.copy()
    
    # 統計情報
    grid_stats = {
        "total_cells_in_bbox": 0,
        "cells_drawn": 0,
        "cells_skipped": 0,
        "reason_not_in_mask": 0,
    }

    # 1) final_maskから輪郭・バウンディングボックスを取得
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

    # grid_mm を pxに変換
    cell_px = int(round(grid_mm * px_per_mm))
    grid_stats["cell_px"] = cell_px
    grid_stats["bounding_box"] = {"x": x, "y": y, "width": w, "height": h}

    # セルが領域より大きすぎる場合はfallback
    if cell_px > w or cell_px > h:
        fallback = max(1, min(w, h) // 5)
        logger.warning(f"セルサイズ {cell_px}px が領域より大きいため、{fallback}px に調整します")
        cell_px = fallback
        grid_stats["fallback_cell_px"] = fallback
        grid_stats["original_cell_px"] = cell_px
        grid_stats["fallback_activated"] = True
    else:
        grid_stats["fallback_activated"] = False

    # ここから「四辺すべてがバウンディングボックスに収まる」かつ
    # 「セル全体がマスク内に収まる」セルだけ線を描画する
    x_end = x + w
    y_end = y + h

    # 理論上のグリッドサイズを計算（バウンディングボックス内の最大マス目数）
    grid_cols = w // cell_px
    grid_rows = h // cell_px
    grid_stats["theoretical_grid_size"] = {"rows": grid_rows, "cols": grid_cols}
    
    # バウンディングボックス内の総セル数
    total_cells_in_bbox = grid_rows * grid_cols
    grid_stats["total_cells_in_bbox"] = total_cells_in_bbox

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
            
            # バウンディングボックス内のセル数をカウント
            grid_stats["total_cells_in_bbox"] += 1
            
            # セル領域全体がマスク内に収まっているか確認
            # 境界線の太さを考慮して少し内側を確認する
            padding = max(1, line_thickness // 2)
            check_x1 = max(0, cell_x1 - padding)
            check_y1 = max(0, cell_y1 - padding)
            check_x2 = min(final_mask.shape[1] - 1, cell_x2 + padding)
            check_y2 = min(final_mask.shape[0] - 1, cell_y2 + padding)
            
            # マスクのセル領域の範囲を抽出
            cell_roi = final_mask[check_y1:check_y2, check_x1:check_x2]
            
            # セル領域のピクセルがすべて1（マスク内）かどうかチェック
            if not np.all(cell_roi == 1):
                # 部分的にでもマスク外ならこのセルはスキップ
                grid_stats["cells_skipped"] += 1
                grid_stats["reason_not_in_mask"] += 1
                col += 1
                continue
            
            # ===== マスの四隅 (cell_x1, cell_y1) → (cell_x2, cell_y2) =====
            # 四辺をそれぞれ描画（マスク内かのチェックは不要になった）

            # 上辺
            cv2.line(out, (cell_x1, cell_y1), (cell_x2, cell_y1), line_color, line_thickness)

            # 下辺
            cv2.line(out, (cell_x1, cell_y2), (cell_x2, cell_y2), line_color, line_thickness)

            # 左辺
            cv2.line(out, (cell_x1, cell_y1), (cell_x1, cell_y2), line_color, line_thickness)

            # 右辺
            cv2.line(out, (cell_x2, cell_y1), (cell_x2, cell_y2), line_color, line_thickness)

            # 描画したセルをカウント
            grid_stats["cells_drawn"] += 1
            col += 1
        
        row += 1

    return out, grid_stats

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
    far_offset_px: Optional[int] = None
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
                "grid_mm": grid_mm
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
            # House内部だけにグリッド描画
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
            
            # バウンディングボックス情報をデバッグ情報に追加
            if grid_stats.get("bounding_box"):
                debug_info["bounding_box"] = grid_stats["bounding_box"]
            
            # セルサイズ情報をデバッグ情報に追加
            if grid_stats.get("cell_px"):
                debug_info["cell_px"] = grid_stats["cell_px"]
                
            # fallback情報をデバッグ情報に追加
            if grid_stats.get("fallback_activated"):
                debug_info["fallback_activated"] = grid_stats["fallback_activated"]
                debug_info["original_cell_px"] = grid_stats.get("original_cell_px")
                debug_info["fallback_cell_px"] = grid_stats.get("fallback_cell_px")
        else:
            logger.warning("オフセット後の住居領域が見つかりません")
            debug_info["error"] = "オフセット後の住居領域が見つかりません"

        # BGR→RGB変換してPIL画像化
        rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb), debug_info

    except Exception as e:
        logger.error(f"画像処理中にエラー: {e}", exc_info=True)
        return None