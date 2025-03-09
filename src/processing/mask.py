"""
セグメンテーションマスクの処理と操作のためのユーティリティ関数
"""
import numpy as np
import cv2
import tempfile
import io
from typing import Optional, Tuple, Dict, Any, Union
from PIL import Image
import logging
import yaml

# ロギング設定
logger = logging.getLogger(__name__)

# data.yamlからクラス名を取得
with open('config/data.yaml', 'r') as f:
    data_config = yaml.safe_load(f)
    class_names = data_config['names']

# クラス名からIDを取得
HOUSE_CLASS_ID = class_names.index('House') if 'House' in class_names else None
ROAD_CLASS_ID = class_names.index('Road') if 'Road' in class_names else None


def offset_mask_by_distance(mask: np.ndarray, offset_px: int) -> np.ndarray:
    """
    マスクを距離変換して内側にオフセットしたバイナリマスクを返します。
    
    Args:
        mask: オフセットするバイナリマスク
        offset_px: オフセットする距離（ピクセル単位）
        
    Returns:
        内側にオフセットされたバイナリマスク
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
    grid_mm: float = 910.0,
    dpi: float = 300.0,
    scale: float = 1.0,
    fill_color: Tuple[int, int, int] = (255, 0, 0),
    alpha: float = 0.4,
    line_color: Tuple[int, int, int] = (0, 0, 255),
    line_thickness: int = 2
) -> np.ndarray:
    """
    長方形領域に半透明の塗りつぶしとグリッドを描画します。
    
    Args:
        image: 描画対象の画像
        rect: 長方形領域 (x, y, width, height)
        grid_mm: グリッド間隔（ミリメートル単位）
        dpi: 解像度（DPI）
        scale: スケールファクター
        fill_color: 塗りつぶし色 (BGR形式)
        alpha: 塗りつぶしの透明度 (0.0〜1.0)
        line_color: グリッド線の色 (BGR形式)
        line_thickness: グリッド線の太さ
        
    Returns:
        グリッドが描画された画像
    """
    out = image.copy()
    x, y, width, height = rect
    x2, y2 = x + width, y + height
    
    # 半透明の塗りつぶし
    overlay = out.copy()
    cv2.rectangle(overlay, (x, y), (x2, y2), fill_color, cv2.FILLED)
    cv2.addWeighted(overlay, alpha, out, 1 - alpha, 0, out)
    
    # 外枠
    cv2.rectangle(out, (x, y), (x2, y2), line_color, line_thickness)
    
    # ミリメートルをピクセルに変換
    def mm_to_px(mm: float) -> int:
        inch = mm / 25.4  # 1インチ = 25.4mm
        px = inch * dpi * scale
        return int(round(px))
    
    cell_px = mm_to_px(grid_mm)
    
    # セルサイズが大きすぎる場合のフォールバック
    if cell_px > width or cell_px > height:
        fallback = max(1, min(width, height) // 5)
        logger.warning(f"セルサイズ {cell_px}px が大きすぎるため、{fallback}px に調整します")
        cell_px = fallback
    
    # 水平グリッド線
    for gy in range(y, y2, cell_px):
        cv2.line(out, (x, gy), (x2, gy), line_color, line_thickness)
    
    # 垂直グリッド線
    for gx in range(x, x2, cell_px):
        cv2.line(out, (gx, y), (gx, y2), line_color, line_thickness)
    
    return out


def process_image(
    model,
    image_file,
    near_offset_px: int = 100,
    far_offset_px: int = 50,
    grid_mm: float = 910.0,
    dpi: float = 300.0,
    scale: float = 1.0
) -> Optional[Image.Image]:
    """
    画像を処理して、セグメンテーション、マスク操作、グリッド生成を行います。
    
    プロセス:
    1. YOLOセグメンテーションで "House" と "Road" マスクを生成
    2. 道路に近い住居領域と遠い領域で異なるオフセットを適用
    3. 処理後のマスクに対してバウンディングボックスを計算
    4. バウンディングボックス内にグリッドを描画
    5. 元の住居マスクを緑色半透明で表示
    
    Args:
        model: 推論に使用するYOLOモデル
        image_file: 入力画像ファイル（Streamlitのアップロードファイル）
        near_offset_px: 道路近くの領域に適用するオフセット（ピクセル単位）
        far_offset_px: その他の領域に適用するオフセット（ピクセル単位）
        grid_mm: グリッド間隔（ミリメートル単位）
        dpi: 解像度（DPI）
        scale: スケールファクター
        
    Returns:
        処理後のPIL Image、エラー時はNone
    """
    try:
        image_bytes = image_file.getvalue()
        
        # 一時ファイルに保存して推論を実行
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp.close()
            results = model(tmp.name, task="segment")
            import os
            os.unlink(tmp.name)  # 一時ファイルを削除
        
        # 元の画像を取得
        orig = results[0].orig_img
        if orig is None:
            logger.error("Original image not found in results")
            return None
        
        # 画像の寸法を取得
        h, w = orig.shape[:2]
        
        # マスクを初期化
        house_mask = np.zeros((h, w), dtype=np.uint8)
        road_mask = np.zeros((h, w), dtype=np.uint8)
        
        # セグメンテーションマスクを合成
        if results[0].masks is not None:
            for seg_data, cls_id in zip(results[0].masks.data, results[0].boxes.cls):
                m = seg_data.cpu().numpy().astype(np.uint8)
                
                # YOLOの出力マスクを元の画像サイズにリサイズ
                resized = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
                
                if int(cls_id) == HOUSE_CLASS_ID:
                    house_mask = np.maximum(house_mask, resized)
                elif int(cls_id) == ROAD_CLASS_ID:
                    road_mask = np.maximum(road_mask, resized)
        
        # 住居マスクを緑色半透明で表示
        out_bgr = orig.copy()
        overlay = out_bgr.copy()
        overlay[house_mask == 1] = (0, 255, 0)  # BGR形式
        cv2.addWeighted(overlay, 0.3, out_bgr, 0.7, 0, out_bgr)
        
        # 道路からの距離に基づいて異なるオフセットを適用
        bin_road = (road_mask > 0).astype(np.uint8)
        dist_road = cv2.distanceTransform(bin_road, cv2.DIST_L2, 5)
        near_threshold = 20
        near_road = (dist_road < near_threshold).astype(np.uint8)
        
        near_house = (house_mask & near_road)
        far_house = (house_mask & (1 - near_road))
        
        shrunk_near = offset_mask_by_distance(near_house, near_offset_px)
        shrunk_far = offset_mask_by_distance(far_house, far_offset_px)
        final_house = np.maximum(shrunk_near, shrunk_far)
        
        # バウンディングボックスを取得してグリッドを描画
        contours, _ = cv2.findContours(final_house, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            logger.warning("オフセット適用後の住居領域が見つかりませんでした")
        else:
            # 最大の輪郭を取得
            big_contour = max(contours, key=cv2.contourArea)
            x, y, wc, hc = cv2.boundingRect(big_contour)
            
            # グリッドを描画
            out_bgr = draw_grid_on_rect(
                image=out_bgr,
                rect=(x, y, wc, hc),
                grid_mm=grid_mm,
                dpi=dpi,
                scale=scale,
                fill_color=(255, 0, 0),
                alpha=0.4,
                line_color=(0, 0, 255),
                line_thickness=2
            )
        
        # BGR -> RGB変換してPIL Imageとして返す
        rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
    
    except Exception as e:
        logger.error(f"画像処理エラー: {e}", exc_info=True)
        return None