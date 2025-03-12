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
    A3(横420mm)想定で「grid_mm」をピクセル換算し、等間隔のグリッドを引く。

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
    x2, y2 = x + w, y + h

    # まず半透明塗りつぶし
    overlay = out.copy()
    cv2.rectangle(overlay, (x, y), (x2, y2), fill_color, cv2.FILLED)
    cv2.addWeighted(overlay, alpha, out, 1 - alpha, 0, out)

    # 矩形の外枠
    cv2.rectangle(out, (x, y), (x2, y2), line_color, line_thickness)

    # A3横420mm→画面幅image_width_pxより1mm→(image_width_px/420)px
    px_per_mm = image_width_px / A3_WIDTH_MM

    # grid_mm（紙上のmm）をピクセル換算
    cell_px = int(round(grid_mm * px_per_mm))

    # セルが領域より大きすぎる場合はfallback
    if cell_px > w or cell_px > h:
        fallback = max(1, min(w, h) // 5)
        logger.warning(f"セルサイズ {cell_px}px が領域より大きいため、{fallback}px に調整します")
        cell_px = fallback

    # 等間隔の水平線
    for gy in range(y, y2, cell_px):
        cv2.line(out, (x, gy), (x2, gy), line_color, line_thickness)

    # 等間隔の垂直線
    for gx in range(x, x2, cell_px):
        cv2.line(out, (gx, y), (gx, y2), line_color, line_thickness)

    return out

def process_image(
    model,
    image_file,
    near_offset_px: int = 100,
    far_offset_px: int = 50,
    grid_mm: float = 9.1
) -> Optional[Tuple[Image.Image, Dict[str, Any]]]:
    """
    画像を処理して、セグメンテーション・マスク操作・グリッド生成を行う。
    
    すべての画像をA3サイズ(150dpi: 2481x1754px)にリサイズして処理するため、
    どんな画像でも常に同じスケールでグリッドが描画される。
    
    Args:
        model: YOLO推論モデル(YOLOクラスなど)
        image_file: 入力画像(アップローダ等のファイルオブジェクトやパス)
        near_offset_px: 道路近くの住居領域をどれだけ内側にオフセットするか(px)
        far_offset_px: その他の住居領域をどれだけ内側にオフセットするか(px)
        grid_mm: 紙上のグリッド間隔(mm) (例: 9.1mm = 実物910mmの1/100)
    Returns:
        Tuple[処理後のPIL画像, デバッグ情報の辞書] または None (失敗時)
    """
    try:
        # デバッグ情報を格納する辞書
        debug_info = {
            "params": {
                "near_offset_px": near_offset_px,
                "far_offset_px": far_offset_px,
                "grid_mm": grid_mm
            },
            "fallback_activated": False,
            "bounding_box": None,
            "cell_px": None,
            "px_per_mm": None,
            "image_size": None,
            "resized": False,
            "original_size": None
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
        processed_img = resized.copy()
        
        # 画像サイズを取得 (h,w) - A3サイズになっているはず
        h, w = processed_img.shape[:2]
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

        # 住居マスクを半透明(緑)で描画
        out_bgr = processed_img.copy()
        overlay = out_bgr.copy()
        overlay[house_mask == 1] = (0, 255, 0)  # BGR
        cv2.addWeighted(overlay, 0.3, out_bgr, 0.7, 0, out_bgr)

        # 道路からの距離を算出して、近接/遠隔住居を分ける
        bin_road = (road_mask > 0).astype(np.uint8)
        dist_road = cv2.distanceTransform(bin_road, cv2.DIST_L2, 5)
        near_threshold = 20
        near_road = (dist_road < near_threshold).astype(np.uint8)

        near_house = (house_mask & near_road)
        far_house = (house_mask & (1 - near_road))

        # それぞれの領域を指定オフセットだけ収縮
        shrunk_near = offset_mask_by_distance(near_house, near_offset_px)
        shrunk_far = offset_mask_by_distance(far_house, far_offset_px)

        # 結合して最終住居マスク
        final_house = np.maximum(shrunk_near, shrunk_far)

        # バウンディングボックスを求めてグリッド描画
        contours, _ = cv2.findContours(final_house, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            logger.warning("オフセット後の住居領域が見つかりません")
            debug_info["error"] = "オフセット後の住居領域が見つかりません"
        else:
            # 最大輪郭を取得
            big_contour = max(contours, key=cv2.contourArea)
            x, y, wc, hc = cv2.boundingRect(big_contour)
            debug_info["bounding_box"] = {"x": x, "y": y, "width": wc, "height": hc}
            
            # A3のピクセル/mm変換比を計算
            px_per_mm = A3_WIDTH_PX / A3_WIDTH_MM
            cell_px = int(round(grid_mm * px_per_mm))
            debug_info["px_per_mm"] = px_per_mm
            debug_info["cell_px"] = cell_px
            
            # フォールバックチェック
            if cell_px > wc or cell_px > hc:
                fallback = max(1, min(wc, hc) // 5)
                logger.warning(f"セルサイズ {cell_px}px が領域より大きいため、{fallback}px に調整します")
                debug_info["fallback_activated"] = True
                debug_info["original_cell_px"] = cell_px
                debug_info["fallback_cell_px"] = fallback
                cell_px = fallback

            # A3サイズでグリッド描画（常に同じスケール）
            out_bgr = draw_grid_on_rect(
                image=out_bgr,
                rect=(x, y, wc, hc),
                grid_mm=grid_mm,
                image_width_px=A3_WIDTH_PX,  # 横幅は固定のA3幅
                fill_color=(255, 0, 0),
                alpha=0.4,
                line_color=(0, 0, 255),
                line_thickness=2
            )

        # BGR→RGB変換してPIL画像化
        rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb), debug_info

    except Exception as e:
        logger.error(f"画像処理中にエラー: {e}", exc_info=True)
        return None