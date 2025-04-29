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

# FreeCADのパスを追加
sys.path.append('/usr/lib/freecad-python3/lib')

# FreeCADの利用可能性をチェック
try:
    import FreeCAD
    import Part
    import Draft
    import Sketcher
    import Arch
    FREECAD_AVAILABLE = True
except ImportError as e:
    logging.warning(f"FreeCADのインポートに失敗しました: {e}")
    FREECAD_AVAILABLE = False

logger = logging.getLogger(__name__)

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
    
    # 3Dビューの表示（FreeCADが利用可能な場合）
    if FREECAD_AVAILABLE and show_furniture:
        st.subheader("3D間取りビュー")
        
        try:
            # 一時的なFreeCADドキュメントを作成
            doc = create_temp_3d_floorplan(floorplan_stats)
            
            if doc:
                # 3Dビューを画像として保存
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp_path = tmp.name
                
                # ビューを設定して3D図を作成
                FreeCAD.Gui.ActiveDocument = FreeCAD.getDocument(doc.Name)
                FreeCAD.Gui.ActiveDocument.ActiveView.viewIsometric()
                FreeCAD.Gui.ActiveDocument.ActiveView.fitAll()
                
                # 画像として保存
                FreeCAD.Gui.ActiveDocument.ActiveView.saveImage(tmp_path, 800, 600, 'White')
                
                # 画像を表示
                st.image(tmp_path, caption="3D間取りビュー", use_column_width=True)
                
                # 一時ファイルを削除
                os.unlink(tmp_path)
        except Exception as e:
            st.warning(f"3Dビューの生成に失敗しました: {e}")

def create_temp_3d_floorplan(floorplan_stats):
    """一時的な3D間取り図を作成"""
    if not FREECAD_AVAILABLE:
        return None
    
    try:
        # FreeCADドキュメントを作成
        doc = FreeCAD.newDocument("TempFloorPlan")
        
        # 部屋情報を取得
        madori_info = floorplan_stats.get("madori_info", {})
        positions = floorplan_stats.get("positions", {})
        
        # 壁の高さ
        wall_height = 2500  # mm
        
        # 各部屋を作成
        for name, info in madori_info.items():
            width = info.get("width", 0) * 910  # mm
            height = info.get("height", 0) * 910  # mm
            
            # 部屋の位置を取得
            pos = positions.get(name, (0, 0))
            x = pos[0] * 910
            y = pos[1] * 910
            
            # 部屋の床を作成
            floor = doc.addObject("Part::Box", f"Floor_{name}")
            floor.Length = width
            floor.Width = height
            floor.Height = 100  # 床の厚さ
            floor.Placement = FreeCAD.Placement(
                FreeCAD.Vector(x, y, 0),
                FreeCAD.Rotation(0, 0, 0, 1)
            )
            
            # 部屋の壁を作成
            # 前壁
            front_wall = doc.addObject("Part::Box", f"FrontWall_{name}")
            front_wall.Length = width
            front_wall.Width = 100  # 壁の厚さ
            front_wall.Height = wall_height
            front_wall.Placement = FreeCAD.Placement(
                FreeCAD.Vector(x, y, 0),
                FreeCAD.Rotation(0, 0, 0, 1)
            )
            
            # 後壁
            back_wall = doc.addObject("Part::Box", f"BackWall_{name}")
            back_wall.Length = width
            back_wall.Width = 100
            back_wall.Height = wall_height
            back_wall.Placement = FreeCAD.Placement(
                FreeCAD.Vector(x, y + height - 100, 0),
                FreeCAD.Rotation(0, 0, 0, 1)
            )
            
            # 左壁
            left_wall = doc.addObject("Part::Box", f"LeftWall_{name}")
            left_wall.Length = 100
            left_wall.Width = height
            left_wall.Height = wall_height
            left_wall.Placement = FreeCAD.Placement(
                FreeCAD.Vector(x, y, 0),
                FreeCAD.Rotation(0, 0, 0, 1)
            )
            
            # 右壁
            right_wall = doc.addObject("Part::Box", f"RightWall_{name}")
            right_wall.Length = 100
            right_wall.Width = height
            right_wall.Height = wall_height
            right_wall.Placement = FreeCAD.Placement(
                FreeCAD.Vector(x + width - 100, y, 0),
                FreeCAD.Rotation(0, 0, 0, 1)
            )
            
            # 部屋タイプに応じた家具を追加
            if name == 'E':  # 玄関
                # 玄関ドア
                door_width = min(width * 0.4, 910)
                door_x = x + width - door_width
                door_y = y
                door = doc.addObject("Part::Box", f"Door_{name}")
                door.Length = door_width
                door.Width = 100
                door.Height = 2100  # ドアの高さ
                door.Placement = FreeCAD.Placement(
                    FreeCAD.Vector(door_x, door_y, 0),
                    FreeCAD.Rotation(0, 0, 0, 1)
                )
                
            elif name == 'L':  # リビング
                # ソファ
                sofa_width = width * 0.6
                sofa_height = height * 0.2
                sofa_x = x + (width - sofa_width) / 2
                sofa_y = y + height * 0.1
                sofa = doc.addObject("Part::Box", f"Sofa_{name}")
                sofa.Length = sofa_width
                sofa.Width = sofa_height
                sofa.Height = 800  # ソファの高さ
                sofa.Placement = FreeCAD.Placement(
                    FreeCAD.Vector(sofa_x, sofa_y, 0),
                    FreeCAD.Rotation(0, 0, 0, 1)
                )
                
                # テーブル
                table_size = min(width, height) * 0.3
                table_x = x + (width - table_size) / 2
                table_y = y + height * 0.4
                table = doc.addObject("Part::Box", f"Table_{name}")
                table.Length = table_size
                table.Width = table_size
                table.Height = 400  # テーブルの高さ
                table.Placement = FreeCAD.Placement(
                    FreeCAD.Vector(table_x, table_y, 0),
                    FreeCAD.Rotation(0, 0, 0, 1)
                )
                
            elif name == 'K':  # キッチン
                # キッチンカウンター
                counter_width = width * 0.8
                counter_height = height * 0.3
                counter_x = x + (width - counter_width) / 2
                counter_y = y + height * 0.6
                counter = doc.addObject("Part::Box", f"Counter_{name}")
                counter.Length = counter_width
                counter.Width = counter_height
                counter.Height = 850  # カウンターの高さ
                counter.Placement = FreeCAD.Placement(
                    FreeCAD.Vector(counter_x, counter_y, 0),
                    FreeCAD.Rotation(0, 0, 0, 1)
                )
                
            elif name == 'B':  # バスルーム
                # 浴槽
                bath_width = width * 0.7
                bath_height = height * 0.6
                bath_x = x + (width - bath_width) / 2
                bath_y = y + (height - bath_height) / 2
                bath = doc.addObject("Part::Box", f"Bath_{name}")
                bath.Length = bath_width
                bath.Width = bath_height
                bath.Height = 600  # 浴槽の高さ
                bath.Placement = FreeCAD.Placement(
                    FreeCAD.Vector(bath_x, bath_y, 0),
                    FreeCAD.Rotation(0, 0, 0, 1)
                )
                
            elif name == 'T':  # トイレ
                # トイレ
                toilet_size = min(width, height) * 0.4
                toilet_x = x + (width - toilet_size) / 2
                toilet_y = y + height * 0.6
                toilet = doc.addObject("Part::Box", f"Toilet_{name}")
                toilet.Length = toilet_size
                toilet.Width = toilet_size
                toilet.Height = 400  # トイレの高さ
                toilet.Placement = FreeCAD.Placement(
                    FreeCAD.Vector(toilet_x, toilet_y, 0),
                    FreeCAD.Rotation(0, 0, 0, 1)
                )
        
        # ドキュメントを更新
        doc.recompute()
        return doc
        
    except Exception as e:
        logger.error(f"3D間取り図の作成に失敗しました: {e}")
        return None

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
    if not FREECAD_AVAILABLE:
        st.warning("FreeCADが利用できないため、DXFエクスポートができません。")
        return None
    
    try:
        # FreeCADドキュメントを作成
        doc = FreeCAD.newDocument("ExportFloorPlan")
        
        # 部屋情報を取得
        madori_info = floorplan_stats.get("madori_info", {})
        positions = floorplan_stats.get("positions", {})
        
        # 各部屋を作成
        for name, info in madori_info.items():
            width = info.get("width", 0) * 910  # mm
            height = info.get("height", 0) * 910  # mm
            
            # 部屋の位置を取得
            pos = positions.get(name, (0, 0))
            x = pos[0] * 910
            y = pos[1] * 910
            
            # 部屋の輪郭を作成
            sketch = doc.addObject('Sketcher::SketchObject', f'Sketch_{name}')
            sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x, y, 0), FreeCAD.Vector(x+width, y, 0)))
            sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x+width, y, 0), FreeCAD.Vector(x+width, y+height, 0)))
            sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x+width, y+height, 0), FreeCAD.Vector(x, y+height, 0)))
            sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x, y+height, 0), FreeCAD.Vector(x, y, 0)))
            
            # 部屋名をテキストとして追加
            label = Draft.makeText([name], FreeCAD.Vector(x + width/2, y + height/2, 0))
        
        # ドキュメントを更新
        doc.recompute()
        
        # DXFとしてエクスポート
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp:
            dxf_path = tmp.name
        
        import importDXF
        importDXF.export([obj for obj in doc.Objects], dxf_path)
        
        # DXFファイルを読み込み
        with open(dxf_path, 'rb') as f:
            dxf_data = f.read()
        
        # 一時ファイルを削除
        os.unlink(dxf_path)
        
        return dxf_data
        
    except Exception as e:
        st.error(f"DXFエクスポートに失敗しました: {e}")
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
    
    # DXF形式でダウンロード（FreeCADが利用可能な場合）
    if FREECAD_AVAILABLE:
        dxf_data = export_floorplan_to_dxf(floorplan_stats)
        if dxf_data:
            st.download_button(
                label="DXF形式でダウンロード（CADソフト用）",
                data=dxf_data,
                file_name="floorplan.dxf",
                mime="application/dxf"
            )
