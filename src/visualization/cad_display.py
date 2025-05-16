"""
FreeCADを使用した間取り図のCAD風表示のためのStreamlitコンポーネント
"""
import streamlit as st
import os
import sys
import tempfile
import numpy as np
import cv2
from PIL import Image
import io
import logging
import base64
import requests

# FreeCADの環境設定をインポート
from src.utils.setup_freecad import setup_freecad_environment

# FreeCAD APIの設定
FREECAD_API_URL = os.getenv(
    "FREECAD_API_URL", "https://freecad-api-513507930971.asia-northeast1.run.app"
)

logger = logging.getLogger(__name__)

def create_cad_display(grid_data):
    """CAD風の表示を作成する関数
    
    Args:
        grid_data (dict): グリッドデータ
        
    Returns:
        dict: 表示データ
    """
    try:
        # FreeCAD APIにリクエストを送信
        response = requests.post(
            f"{FREECAD_API_URL}/process/grid",
            json=grid_data,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"FreeCAD APIエラー: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"CAD表示の作成中にエラーが発生しました: {e}")
        return None

def display_cad_floorplan(floorplan_image, floorplan_stats, show_dimensions=True, show_furniture=True):
    """
    CAD風の間取り図を表示するStreamlitコンポーネント
    """
    # 間取り図の表示
    st.image(floorplan_image, caption="CAD風間取り図", use_column_width=True)
    
    # 寸法情報の表示
    if show_dimensions and "madori_info" in floorplan_stats:
        st.subheader("部屋の寸法情報")
        
        # 部屋ごとの寸法情報を表形式で表示
        room_data = []
        for name, info in floorplan_stats["madori_info"].items():
            # 1マス = 910mm (91.0cm)として計算
            width_mm = info.get("width", 0) * 910
            height_mm = info.get("height", 0) * 910
            area_sqm = (width_mm / 1000) * (height_mm / 1000)  # m²に変換
            
            # 畳数計算（1畳 = 約1.62m²）
            tatami = area_sqm / 1.62
            
            room_data.append({
                "部屋": name,
                "幅 (mm)": f"{width_mm:.0f}",
                "奥行き (mm)": f"{height_mm:.0f}",
                "面積 (m²)": f"{area_sqm:.2f}",
                "畳数": f"{tatami:.1f}"
            })
        
        # データフレームとして表示
        import pandas as pd
        df = pd.DataFrame(room_data)
        st.dataframe(df)
    
    # 3Dビューの表示
    if show_furniture:
        st.subheader("3D間取りビュー")
        
        try:
            # FreeCAD APIを使用して3Dモデルを生成
            response = requests.post(
                f"{FREECAD_API_URL}/process/grid",
                json=floorplan_stats,
                timeout=60
            )
            
            if response.status_code == 200:
                model_data = response.json()
                if "model_url" in model_data:
                    st.image(model_data["model_url"], caption="3D間取りビュー", use_column_width=True)
                else:
                    st.warning("3DモデルのURLが見つかりませんでした")
            else:
                st.warning(f"3Dモデルの生成に失敗しました: {response.status_code}")
                
        except Exception as e:
            st.warning(f"3Dビューの生成に失敗しました: {e}")

def display_floorplan_details(floorplan_stats):
    """間取り図の詳細情報を表示"""
    st.subheader("間取り詳細情報")
    
    # 部屋情報
    if "madori_info" in floorplan_stats:
        st.write("### 部屋情報")
        
        # 部屋ごとの情報を表示
        for name, info in floorplan_stats["madori_info"].items():
            width = info.get("width", 0)
            height = info.get("height", 0)
            neighbor = info.get("neighbor", "なし")
            
            # 1マス = 910mm (91.0cm)として計算
            width_mm = width * 910
            height_mm = height * 910
            area_sqm = (width_mm / 1000) * (height_mm / 1000)  # m²に変換
            
            # 畳数計算（1畳 = 約1.62m²）
            tatami = area_sqm / 1.62
            
            st.write(f"**{name}**: {width_mm:.0f}mm × {height_mm:.0f}mm ({area_sqm:.2f}m² ≈ {tatami:.1f}畳)")
    
    # グリッド情報
    if "grid_size" in floorplan_stats:
        rows = floorplan_stats["grid_size"].get("rows", 0)
        cols = floorplan_stats["grid_size"].get("cols", 0)
        st.write(f"### グリッドサイズ: {rows} × {cols}")
    
    # セルサイズ
    if "cell_px" in floorplan_stats:
        cell_px = floorplan_stats["cell_px"]
        st.write(f"### セルサイズ: {cell_px}px (≈ 910mm)")
    
    # 描画統計
    cells_drawn = floorplan_stats.get("cells_drawn", 0)
    cells_skipped = floorplan_stats.get("cells_skipped", 0)
    st.write(f"### 描画セル数: {cells_drawn} (スキップ: {cells_skipped})")

def export_floorplan_to_dxf(floorplan_stats):
    """間取り図をDXF形式でエクスポート"""
    try:
        # FreeCAD APIを使用してDXFを生成
        response = requests.post(
            f"{FREECAD_API_URL}/process/drawing",
            json={
                "grid_data": floorplan_stats,
                "drawing_type": "平面図",
                "scale": "1:100"
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            if "file_url" in data:
                # DXFファイルをダウンロード
                dxf_response = requests.get(data["file_url"])
                if dxf_response.status_code == 200:
                    return dxf_response.content
                else:
                    logger.error(f"DXFファイルのダウンロードに失敗しました: {dxf_response.status_code}")
            else:
                logger.error("DXFファイルのURLが見つかりませんでした")
        else:
            logger.error(f"DXFの生成に失敗しました: {response.status_code}")
        
        return None
        
    except Exception as e:
        logger.error(f"DXFエクスポートに失敗しました: {e}")
        return None

def display_download_options(floorplan_image, floorplan_stats):
    """ダウンロードオプションを表示"""
    st.subheader("ダウンロードオプション")
    
    # PNG画像としてダウンロード
    img_bytes = io.BytesIO()
    if isinstance(floorplan_image, np.ndarray):
        # OpenCV画像をPIL形式に変換
        pil_img = Image.fromarray(cv2.cvtColor(floorplan_image, cv2.COLOR_BGR2RGB))
        pil_img.save(img_bytes, format='PNG')
    else:
        # すでにPIL形式の場合
        floorplan_image.save(img_bytes, format='PNG')
    
    img_bytes.seek(0)
    st.download_button(
        label="PNG画像としてダウンロード",
        data=img_bytes,
        file_name="floorplan.png",
        mime="image/png"
    )
    
    # DXF形式でダウンロード
    dxf_data = export_floorplan_to_dxf(floorplan_stats)
    if dxf_data:
        st.download_button(
            label="DXF形式でダウンロード（CADソフト用）",
            data=dxf_data,
            file_name="floorplan.dxf",
            mime="application/dxf"
        )
