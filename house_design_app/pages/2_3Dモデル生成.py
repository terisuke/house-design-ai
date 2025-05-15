"""
3Dモデル生成ページ
間取り情報からFreeCAD APIを使って3Dモデルを生成します。
"""

import io
import logging
import os
import streamlit as st
import tempfile
import requests
import json
from PIL import Image
import numpy as np
import sys
from pathlib import Path
import torch
import streamlit.components.v1 as components
from utils.style import apply_custom_css, display_logo, display_footer, convert_to_2d_drawing

# 親ディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# ユーティリティをインポート
try:
    from house_design_app.utils.style import apply_custom_css, display_logo, display_footer, convert_to_2d_drawing
except ImportError as e:
    st.error(f"スタイルユーティリティのインポート失敗: {e}")

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit-app-3d-model")

# タイトルと説明
# st.set_page_config() # メインページで設定済み

# カスタムCSSを適用
try:
    apply_custom_css()
except Exception as e:
    st.error(f"スタイルの適用に失敗: {e}")

# ロゴを表示
with st.sidebar:
    display_logo()

# メインタイトルとコンテンツ
st.title("3Dモデル生成")
st.markdown("""
このページでは、土地画像から生成された間取り情報をもとに3Dモデルを生成します。  
メインページで間取り画像を生成した後、このページで3Dモデルを作成できます。
""")

# セッションステートで間取り情報を確認
if "debug_info" not in st.session_state or "result_image" not in st.session_state:
    st.warning("まだ間取り情報が生成されていません。最初にメインページで土地画像をアップロードして間取りを生成してください。")
    st.info("メインページに戻るには、左側のサイドバーの「Home」をクリックしてください。")
    
    # サンプル画像を使用するオプション
    st.subheader("サンプルデータを使用")
    if st.button("サンプルデータをロード"):
        # サンプルの間取り情報をロード
        try:
            # サンプルの間取り情報を生成
            sample_madori_info = {
                "E": {"width": 2, "height": 2, "position": [0, 0]},
                "L": {"width": 4, "height": 3, "position": [2, 0]},
                "D": {"width": 3, "height": 2, "position": [2, 3]},
                "K": {"width": 2, "height": 2, "position": [0, 2]},
                "B": {"width": 2, "height": 2, "position": [6, 0]},
                "T": {"width": 1, "height": 1, "position": [6, 2]},
                "UT": {"width": 2, "height": 1, "position": [5, 3]}
            }
            
            # 画像サイズの設定
            img_width = 800
            img_height = 600
            sample_image = Image.new("RGB", (img_width, img_height), color=(255, 255, 255))
            
            # 画像をセッションステートに保存
            st.session_state.result_image = sample_image
            st.session_state.debug_info = {
                "madori_info": sample_madori_info,
                "params": {
                    "global_setback_mm": 5.0,
                    "road_setback_mm": 50.0,
                    "grid_mm": 9.1,
                    "floorplan_mode": True
                },
                "bounding_box": {"x": 100, "y": 100, "width": 600, "height": 400},
                "cell_px": 54,
                "px_per_mm": 5.9,
                "grid": {"width": 8, "height": 6},
                "grid_stats": {"cells_drawn": 30, "cells_skipped": 0}
            }
            
            st.success("サンプルデータをロードしました！")
            st.rerun()
        except Exception as e:
            st.error(f"サンプルデータのロード中にエラーが発生しました: {e}")
    
    # メインページへのボタン
    st.button("メインページへ戻る", on_click=lambda: st.rerun())
    
    # フッターを表示
    try:
        display_footer()
    except Exception as e:
        st.markdown(
            """
            <div style="position: fixed; bottom: 0; left: 0; width: 100%; background-color: white; text-align: center; padding: 10px; font-size: 14px; border-top: 1px solid #f0f0f0; z-index: 999;">
                © 2025 U-DAKE - 土地画像から間取りを生成するAIツール
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.stop()

# 間取り情報の表示
st.subheader("間取り情報")

# 前のページで生成した画像を表示
st.image(st.session_state.result_image, use_column_width=True, caption="生成された間取り図")

# 間取り情報を表示（テーブル形式）
debug_info = st.session_state.debug_info
madori_info = debug_info.get("madori_info", {})

if madori_info:
    madori_descriptions = {
        "E": "玄関",
        "L": "リビング",
        "D": "ダイニング",
        "K": "キッチン",
        "B": "バスルーム",
        "T": "トイレ",
        "UT": "脱衣所",
    }
    
    # 間取りデータをテーブル形式で表示
    madori_data = []
    for madori_name, info in madori_info.items():
        description = madori_descriptions.get(madori_name, "")
        width = info.get("width", 0)
        height = info.get("height", 0)
        area = width * height * 910 * 910 / 1000000  # 1グリッド = 910mm x 910mm
        madori_data.append({
            "記号": madori_name,
            "名称": description,
            "幅": f"{width}マス",
            "高さ": f"{height}マス",
            "床面積": f"{area:.2f}㎡",
        })
    
    # DataFrameに変換して表示
    if madori_data:
        import pandas as pd
        df = pd.DataFrame(madori_data)
        st.dataframe(df)
        
        # 合計面積の表示
        total_area = sum(float(item["床面積"].replace("㎡", "")) for item in madori_data)
        st.info(f"総床面積: {total_area:.2f}㎡")

# 3Dモデル生成のためのFreeCAD API設定
st.subheader("3Dモデル生成")
with st.expander("詳細設定", expanded=True):
    freecad_api_url = st.text_input(
        "FreeCAD API URL",
        value=os.environ.get("FREECAD_API_URL", "https://freecad-api-513507930971.asia-northeast1.run.app"),
        help="FreeCAD APIのエンドポイントURL"
    )
    
    # グリッドサイズの設定（mm）
    grid_size = 910  # 1グリッド = 910mm

    # 壁の高さ設定
    wall_height = 2500  # 壁の高さ（mm）

    # 部屋の高さ設定
    room_height = 2800  # 部屋の高さ（mm）

    include_furniture = st.checkbox(
        "家具を含める",
        value=True,
        help="3Dモデルに基本的な家具を含めます"
    )

# 3Dモデル生成ボタン
if st.button("3Dモデルを生成", key="generate_3d_model"):
    with st.spinner("3Dモデルを生成中..."):
        try:
            # 間取り情報からグリッドデータを作成
            rooms = []
            walls = []
            room_id = 1
            
            # 間取り情報からルームデータを作成
            for madori_name, info in madori_info.items():
                width = info.get("width", 0) * 910  # グリッドサイズを実寸（mm）に変換
                height = info.get("height", 0) * 910
                pos_x = info.get("position", [0, 0])[0] * 910
                pos_y = info.get("position", [0, 0])[1] * 910
                
                # 部屋の寸法を計算
                room_width = width  # mm (already converted to mm)
                room_height = height  # mm (already converted to mm)
                room_area = room_width * room_height  # mm²

                # 部屋の情報を表示
                st.write(f"部屋の寸法: {room_width:.1f}mm × {room_height:.1f}mm")
                st.write(f"部屋の面積: {room_area:.1f}mm²")
                
                # 部屋データを追加
                rooms.append({
                    "id": room_id,
                    "dimensions": [width, height],
                    "position": [pos_x, pos_y],
                    "label": madori_descriptions.get(madori_name, madori_name)
                })
                
                # 部屋の周囲に壁を作成
                walls.extend([
                    {"start": [pos_x, pos_y], "end": [pos_x + width, pos_y], "height": wall_height},
                    {"start": [pos_x + width, pos_y], "end": [pos_x + width, pos_y + height], "height": wall_height},
                    {"start": [pos_x + width, pos_y + height], "end": [pos_x, pos_y + height], "height": wall_height},
                    {"start": [pos_x, pos_y + height], "end": [pos_x, pos_y], "height": wall_height}
                ])
                
                room_id += 1
            
            # グリッドデータオブジェクトを作成
            grid_data_obj = {
                "rooms": rooms,
                "walls": walls,
                "wall_thickness": 0.12,  # 壁の厚さ120mm
                "include_furniture": include_furniture,
                    "grid_stats": {},
                "grid_stats": debug_info.get("grid_stats", {})
            }
            
            # グリッドデータが空の場合はサンプルデータを使用
            if len(rooms) == 0:
                st.warning("間取り情報から有効なデータが生成できませんでした。サンプルデータを使用します。")
                grid_data_obj = {
                    "rooms": [
                        {
                            "id": 1,
                            "dimensions": [10.0, 10.0],
                            "position": [0.0, 0.0],
                            "label": "Main Room"
                        }
                    ],
                    "walls": [
                        {"start": [0.0, 0.0], "end": [10.0, 0.0], "height": wall_height},
                        {"start": [10.0, 0.0], "end": [10.0, 10.0], "height": wall_height},
                        {"start": [10.0, 10.0], "end": [0.0, 10.0], "height": wall_height},
                        {"start": [0.0, 10.0], "end": [0.0, 0.0], "height": wall_height}
                    ],
                    "wall_thickness": 0.12,
                    "include_furniture": include_furniture,
                    "grid_stats": {},
                "grid_stats": debug_info.get("grid_stats", {})
                }
            
            # APIリクエストを送信
            response = requests.post(
                f"{freecad_api_url}/process/grid",
                json=grid_data_obj,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            response.raise_for_status()
            cad_model_result = response.json()
            logger.info(f"APIレスポンス: {cad_model_result}")
            
            if "url" in cad_model_result:
                st.session_state.cad_model_url = cad_model_result["url"]
                st.success("3Dモデルの生成に成功しました")
                st.markdown(f"モデルURL: {cad_model_result['url']}")
                
                if "preview_url" in cad_model_result:
                    st.image(cad_model_result["preview_url"], use_column_width=True, caption="3Dモデルプレビュー")
                
                # FCStdファイルを自動的にSTL経由でglTFに変換してWebで表示
                with st.spinner("3Dモデルをブラウザ表示用に変換中..."):
                    try:
                        # FCStdファイルのURLを取得
                        fcstd_url = cad_model_result["url"]
                        st.session_state.fcstd_url = fcstd_url
                        
                        # FCStdファイルをダウンロード
                        r = requests.get(fcstd_url)
                        r.raise_for_status()
                        
                        # FCStdファイルをSTLに変換
                        files = {'file': ('model.fcstd', r.content)}
                        convert_response = requests.post(
                            f"{freecad_api_url}/convert/3d",
                            files=files,
                            timeout=180
                        )
                        convert_response.raise_for_status()
                        stl_result = convert_response.json()
                        
                        if "url" in stl_result:
                            st.session_state.stl_url = stl_result["url"]
                            
                            stl_response = requests.get(stl_result["url"])
                            stl_response.raise_for_status()
                            
                            # STLファイルをglTFに変換
                            files = {'file': ('model.stl', stl_response.content)}
                            gltf_convert_response = requests.post(
                                f"{freecad_api_url}/convert/stl-to-gltf",
                                files=files,
                                timeout=180
                            )
                            gltf_convert_response.raise_for_status()
                            gltf_result = gltf_convert_response.json()
                            
                            if "url" in gltf_result:
                                st.session_state.gltf_url = gltf_result["url"]
                                st.session_state.gltf_format = gltf_result.get("format", "gltf")
                                st.success("3Dモデルの表示準備ができました")
                                
                                # 3Dビューアーの表示
                                st.markdown("### 3Dモデルプレビュー")
                                
                                # model-viewerコンポーネントで表示（拡張オプション付き）
                                components.html(f'''
                                <model-viewer src="{st.session_state.gltf_url}" alt="3D model" 
                                    auto-rotate camera-controls 
                                    style="width: 100%; height: 500px;" 
                                    shadow-intensity="1" 
                                    environment-image="neutral" 
                                    exposure="0.5"
                                    camera-orbit="45deg 60deg 3m"
                                    ar ar-modes="webxr scene-viewer quick-look">
                                </model-viewer>
                                <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
                                ''', height=520)
                                
                                # ダウンロードリンク
                                st.subheader("3Dモデルのダウンロード")
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.markdown(f"[FCStd形式]({st.session_state.fcstd_url})")
                                    st.caption("FreeCADで編集可能")
                                
                                with col2:
                                    st.markdown(f"[STL形式]({st.session_state.stl_url})")
                                    st.caption("3Dプリント用")
                                
                                with col3:
                                    file_format = st.session_state.gltf_format.upper()
                                    st.markdown(f"[{file_format}形式]({st.session_state.gltf_url})")
                                    st.caption("ウェブ表示用")
                            else:
                                st.warning("STLからglTFへの変換に失敗しました")
                                st.markdown(f"[3Dモデルをダウンロード (STL形式)]({st.session_state.stl_url})")
                        else:
                            st.warning("FCStdからSTLへの変換には成功しましたが、glTF変換に失敗しました")
                            st.markdown(f"[3Dモデルをダウンロード (FCStd形式)]({cad_model_result['url']})")
                    except Exception as e:
                        st.warning(f"3Dモデルの表示準備中にエラーが発生しました: {str(e)}")
                        logger.exception(f"3Dモデル変換エラー: {e}")
                        if "fcstd_url" in st.session_state:
                            st.markdown(f"[3Dモデルをダウンロード (FCStd形式)]({st.session_state.fcstd_url})")
                        else:
                            st.markdown(f"[3Dモデルをダウンロード (FCStd形式)]({cad_model_result['url']})")
            else:
                st.error(f"3Dモデル生成エラー: {cad_model_result.get('error', '不明なエラー')}")
        except requests.exceptions.RequestException as e:
            st.error(f"APIリクエストエラー: {str(e)}")
            logger.error(f"APIリクエストエラー: {e}")
        except Exception as e:
            st.error(f"3Dモデル生成中にエラーが発生しました: {str(e)}")
            logger.exception(f"3Dモデル生成エラー: {e}")

# 2D図面生成部分
if "cad_model_url" in st.session_state:
    st.subheader("2D図面生成")
    st.info("3Dモデルから2D図面を生成します。建築図面として利用できるPDF形式で出力されます。")
    
    # 図面タイプの選択
    drawing_type = st.selectbox(
        "図面タイプ",
        options=["平面図", "立面図", "断面図", "アイソメトリック"],
        index=0,
        help="生成する図面の種類を選択します"
    )
    
    drawing_scale = st.selectbox(
        "縮尺",
        options=["1:50", "1:100", "1:200"],
        index=1,
        help="図面の縮尺を選択します"
    )
    
    # 2D図面生成ボタン
    if st.button("2D図面を生成"):
        with st.spinner("2D図面を生成中..."):
            try:
                # FreeCAD APIに2D図面生成リクエストを送信
                response = requests.post(
                    f"{freecad_api_url}/process/drawing",
                    json={
                        "model_url": st.session_state.cad_model_url,
                        "drawing_type": drawing_type,
                        "scale": drawing_scale
                    },
                    timeout=60
                )
                response.raise_for_status()
                drawing_result = response.json()
                
                if "url" in drawing_result:
                    st.success("2D図面の生成に成功しました")
                    st.markdown(f"[2D図面をダウンロード]({drawing_result['url']})")
                    
                    # プレビュー画像がある場合は表示
                    if "preview_url" in drawing_result:
                        st.image(drawing_result["preview_url"], use_column_width=True, caption="2D図面プレビュー")
                else:
                    st.error(f"2D図面生成エラー: {drawing_result.get('error', '不明なエラー')}")
            except Exception as e:
                st.error(f"2D図面生成中にエラーが発生しました: {str(e)}")
                logger.exception(f"2D図面生成エラー: {e}")

# 3Dモデル生成後のglTFプレビュー機能
if "cad_model_url" in st.session_state and "gltf_url" not in st.session_state:
    st.subheader("3DモデルWebプレビュー")
    st.info("モデル生成後に自動的にブラウザ表示用の変換が行われなかった場合、ここから手動で変換できます。")
    
    if st.button("3Dプレビューを生成", key="generate_gltf_preview"):
        with st.spinner("3Dモデルをブラウザ表示用に変換中..."):
            try:
                # FCStdファイルのURLを取得
                fcstd_url = st.session_state.cad_model_url
                st.session_state.fcstd_url = fcstd_url
                
                # FCStdファイルをダウンロード
                r = requests.get(fcstd_url)
                r.raise_for_status()
                
                # FCStdファイルをSTLに変換
                files = {'file': ('model.fcstd', r.content)}
                convert_response = requests.post(
                    f"{freecad_api_url}/convert/3d",
                    files=files,
                    timeout=180
                )
                convert_response.raise_for_status()
                stl_result = convert_response.json()
                
                if "url" in stl_result:
                    st.session_state.stl_url = stl_result["url"]
                    
                    # STLファイルをダウンロード
                    stl_response = requests.get(stl_result["url"])
                    stl_response.raise_for_status()
                    
                    # STLファイルをglTFに変換
                    files = {'file': ('model.stl', stl_response.content)}
                    gltf_convert_response = requests.post(
                        f"{freecad_api_url}/convert/stl-to-gltf",
                        files=files,
                        timeout=180
                    )
                    gltf_convert_response.raise_for_status()
                    gltf_result = gltf_convert_response.json()
                    
                    if "url" in gltf_result:
                        st.session_state.gltf_url = gltf_result["url"]
                        st.session_state.gltf_format = gltf_result.get("format", "gltf")
                        st.success("3Dモデルの表示準備ができました")
                        
                        # 3Dビューアーの表示
                        st.markdown("### 3Dモデルプレビュー")
                        
                        # model-viewerコンポーネントで表示（拡張オプション付き）
                        components.html(f'''
                        <model-viewer src="{st.session_state.gltf_url}" alt="3D model" 
                            auto-rotate camera-controls 
                            style="width: 100%; height: 500px;" 
                            shadow-intensity="1" 
                            environment-image="neutral" 
                            exposure="0.5"
                            camera-orbit="45deg 60deg 3m"
                            ar ar-modes="webxr scene-viewer quick-look">
                        </model-viewer>
                        <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
                        ''', height=520)
                        
                        # ダウンロードリンク
                        st.subheader("3Dモデルのダウンロード")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown(f"[FCStd形式]({st.session_state.fcstd_url})")
                            st.caption("FreeCADで編集可能")
                        
                        with col2:
                            st.markdown(f"[STL形式]({st.session_state.stl_url})")
                            st.caption("3Dプリント用")
                        
                        with col3:
                            file_format = st.session_state.gltf_format.upper()
                            st.markdown(f"[{file_format}形式]({st.session_state.gltf_url})")
                            st.caption("ウェブ表示用")
                    else:
                        st.warning("STLからglTFへの変換に失敗しました")
                        st.markdown(f"[3Dモデルをダウンロード (STL形式)]({st.session_state.stl_url})")
                else:
                    st.warning("FCStdからSTLへの変換には成功しましたが、glTF変換に失敗しました")
                    st.markdown(f"[3Dモデルをダウンロード (FCStd形式)]({st.session_state.fcstd_url})")
            except Exception as e:
                st.error(f"3Dモデル変換中にエラーが発生しました: {str(e)}")
                logger.exception(f"3Dモデル変換エラー: {e}")
                if "fcstd_url" in st.session_state:
                    st.markdown(f"[3Dモデルをダウンロード (FCStd形式)]({st.session_state.fcstd_url})")

# フッターを表示
try:
    display_footer()
except Exception as e:
    st.markdown(
        """
        <div style="position: fixed; bottom: 0; left: 0; width: 100%; background-color: white; text-align: center; padding: 10px; font-size: 14px; border-top: 1px solid #f0f0f0; z-index: 999;">
            © 2025 U-DAKE - 土地画像から間取りを生成するAIツール
        </div>
        """,
        unsafe_allow_html=True
    )
