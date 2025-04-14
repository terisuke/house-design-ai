# streamlit/app.py
"""
建物・道路セグメンテーションとグリッド生成のためのStreamlitアプリ
(2025-03-12 修正版: A3横向き換算でマス目描画)
(2025-03-27 修正版: FreeCADを使用したCAD風間取り図の生成機能を追加)
(2025-04-05 修正版: FreeCAD APIとの連携機能を追加)
"""

import base64
import io
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import requests
import streamlit as st
from ultralytics import YOLO

from src.cloud.storage import (
    download_dataset,
    download_model_from_gcs,
    initialize_gcs_client,
    upload_to_gcs,
)

# ロギング設定を最初に行う
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit-app")

__all__ = [
    "process_image",
    "load_yolo_model",
    "generate_grid",
    "send_to_freecad_api",
    "convert_to_2d_drawing",
]

# アプリの設定（必ず最初のStreamlitコマンドにする）
st.set_page_config(
    page_title="U-DAKE", page_icon="🏠", layout="wide", initial_sidebar_state="expanded"
)


# カスタムCSSでアプリのスタイルを設定
def apply_custom_css():
    """アプリケーションに白基調のカスタムCSSを適用"""
    css = """
    <style>
        /* 全体の背景色を白に設定 */
        .stApp {
            background-color: white;
        }
        
        /* ヘッダー部分の背景を白に設定 */
        header, [data-testid="stHeader"], .st-emotion-cache-1avcm0n, .st-emotion-cache-18ni7ap {
            background-color: white !important;
        }
        
        /* タイトルバーの背景を白に設定 */
        .st-emotion-cache-z5fcl4, [data-testid="stToolbar"] {
            background-color: white !important;
        }
        
        /* サイドバーのスタイル - 複数のセレクタを使用して確実に適用 */
        [data-testid="stSidebar"] {
            background-color: white !important;
        }
        [data-testid="stSidebar"] > div {
            background-color: white !important;
        }
        .css-1d391kg, .css-1lcbmhc, div[data-testid="stSidebar"], 
        .st-emotion-cache-1cypcdb, .st-emotion-cache-1gulkj5 {
            background-color: white !important;
        }
        
        /* サイドバーのスクロール部分 */
        .st-emotion-cache-uf99v8 {
            background-color: white !important;
        }
        
        /* サイドバーの開閉ボタン(矢印)を黒色に設定 */
        button[kind="header"] {
            color: black !important;
        }
        .st-emotion-cache-7oyrr6 {
            color: black !important;
        }
        [data-testid="collapsedControl"] {
            color: black !important;
        }
        [data-testid="baseButton-headerNoPadding"], svg[data-testid="chevronDownIcon"], svg[data-testid="chevronUpIcon"] {
            color: black !important;
            fill: black !important;
        }
        
        /* メインコンテンツのスタイル */
        .css-18e3th9, .st-emotion-cache-18e3th9 {
            background-color: white;
        }
        
        /* 基本テキストの色を黒に設定 */
        .stApp, .stApp p, .stApp div, .stApp span, .stApp label, .stApp .stMarkdown {
            color: black;
        }
        
        /* サイドバー内のテキスト色を黒に設定 */
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] div, 
        [data-testid="stSidebar"] span, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] .st-emotion-cache-16idsys p {
            color: black;
        }
        
        /* 入力ウィジェットのラベル文字色 */
        .st-emotion-cache-16idsys p, .st-emotion-cache-ue6h4q p {
            color: black;
        }
        
        /* ファイルアップローダーの領域を赤背景・白文字に */
        [data-testid="stFileUploader"], 
        [data-testid="stFileUploader"] > div,
        [data-testid="stFileUploader"] label span p,
        .st-emotion-cache-1erivf3, .st-emotion-cache-1gulkj5 > section {
            background-color: #e50012 !important;
            color: white !important;
            border-color: #e50012 !important;
            padding: 10px;
            border-radius: 5px;
        }
        
        /* ファイルアップローダー内の「Browse files」ボタン */
        [data-testid="stFileUploader"] button {
            background-color: white;
            color: #e50012;
            border: 1px solid white;
        }
        
        /* ファイルアップローダー内のテキスト */
        [data-testid="stFileUploader"] p,
        [data-testid="stFileUploader"] div,
        [data-testid="stFileUploader"] span {
            color: white !important;
        }
        
        /* ボタンを赤背景、白文字に設定 */
        .stButton>button {
            background-color: #e50012;
            color: white;
            border: none;
            font-weight: bold;
            padding: 0.5rem 1rem;
            border-radius: 5px;
        }
        
        /* ボタンホバー時のエフェクト */
        .stButton>button:hover {
            background-color: #b3000e;
            color: white;
        }
        
        /* ダウンロードボタンのスタイル */
        .stDownloadButton>button {
            background-color: #e50012;
            color: white;
            border: none;
            font-weight: bold;
            border-radius: 5px;
        }
        
        /* ダウンロードボタン内のテキスト色を白色に強制 */
        .stDownloadButton button p, 
        .stDownloadButton button span,
        .stDownloadButton button div,
        [data-testid="stDownloadButton"] p,
        [data-testid="stDownloadButton"] span,
        [data-testid="stDownloadButton"] div,
        .st-emotion-cache-1ekf6i8 p {
            color: white !important;
        }
        
        /* ダウンロードボタンホバー時のエフェクト */
        .stDownloadButton>button:hover {
            background-color: #b3000e;
            color: white;
        }
        
        /* JSONビューア（詳細デバッグ情報）のスタイル */
        .element-container .stJson, 
        [data-testid="stJson"],
        .streamlit-expanderContent .stJson {
            background-color: #e50012 !important;
            color: white !important;
            border-radius: 5px;
            padding: 10px;
        }
        
        /* JSONビューア内のすべてのテキスト要素 */
        .element-container .stJson *, 
        [data-testid="stJson"] *,
        .streamlit-expanderContent .stJson * {
            color: white !important;
        }
        
        /* JSONビューアのキー（プロパティ名） */
        .element-container .stJson span.json-key, 
        [data-testid="stJson"] span.json-key,
        .streamlit-expanderContent .stJson span.json-key,
        .react-json-view .string-value,
        .react-json-view .variable-value,
        div[style*="position: relative"] .variable-value,
        div[style*="position: relative"] .string-value {
            color: white !important;
        }
        
        /* JSONビューアの値 */
        .element-container .stJson span.json-value, 
        [data-testid="stJson"] span.json-value,
        .streamlit-expanderContent .stJson span.json-value,
        .react-json-view .variable-row {
            color: white !important;
        }
        
        /* JSONの展開/折りたたみアイコン */
        .react-json-view svg {
            fill: white !important;
            color: white !important;
        }
        
        /* ヘッダーテキストの色 */
        h1, h2, h3, h4, h5, h6 {
            color: #222222;
        }
        
        /* フッタースタイル */
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: white;
            text-align: center;
            padding: 10px;
            font-size: 14px;
            border-top: 1px solid #f0f0f0;
            z-index: 999;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# 画像を表示する関数
def display_logo():
    """サイドバーにロゴを表示"""
    logo_path = Path(__file__).parent / "logo.png"

    if logo_path.exists():
        with open(logo_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            html = f"""
            <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                <img src="data:image/png;base64,{b64}" style="max-width: 100%; height: auto;">
            </div>
            """
            st.sidebar.markdown(html, unsafe_allow_html=True)
    else:
        st.sidebar.warning("ロゴファイル (logo.png) が見つかりません。")
        logger.warning(f"ロゴファイル不見: {logo_path}")


# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# OpenCVとその他の依存関係のインポートをエラーハンドリングする
cv2_available = False
import_errors = []

try:
    import cv2

    cv2_available = True
except ImportError as e:
    error_msg = f"OpenCVのインポートに失敗しました: {e}"
    logger.error(error_msg)
    import_errors.append(error_msg)

# 自作モジュールのインポート
modules_available = False
try:
    from src.cloud.storage import download_model_from_gcs
    from src.processing.mask import process_image

    modules_available = True
except ImportError as e:
    error_msg = f"モジュールのインポートに失敗しました: {e}"
    logger.error(error_msg)
    import_errors.append(error_msg)

# CAD表示モジュールのインポート
cad_display_available = False
try:
    from src.visualization.cad_display import (
        display_cad_floorplan,
        display_download_options,
        display_floorplan_details,
    )

    cad_display_available = True
except ImportError as e:
    error_msg = f"CAD表示モジュールのインポートに失敗しました: {e}"
    logger.error(error_msg)
    import_errors.append(error_msg)


def load_yolo_model(model_path: Optional[str] = None) -> YOLO:
    """YOLOモデルを読み込む

    Args:
        model_path (Optional[str]): モデルファイルのパス。Noneの場合はCloud Storageからダウンロード

    Returns:
        YOLO: 読み込まれたYOLOモデル
    """
    if model_path is None:
        from src.cloud.storage import download_model_from_gcs

        model_path = download_model_from_gcs()

    from ultralytics import YOLO

    model = YOLO(model_path)
    return model


def process_image(model: YOLO, image_path: str) -> List[Dict[str, Any]]:
    """画像を処理して建物を検出する

    Args:
        model (YOLO): YOLOモデル
        image_path (str): 画像ファイルのパス

    Returns:
        List[Dict[str, Any]]: 検出された建物のリスト
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    results = model.predict(image_path)

    buildings = []
    for detection in results[0].boxes.data:
        x1, y1, x2, y2, conf, cls = detection.tolist()
        buildings.append(
            {"bbox": [x1, y1, x2, y2], "confidence": conf, "class": int(cls)}
        )
    return buildings


def generate_grid(buildings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """建物データからグリッドを生成する

    Args:
        buildings (List[Dict[str, Any]]): 検出された建物のリスト

    Returns:
        Dict[str, Any]: 生成されたグリッドデータ
    """
    grid = {"rooms": [], "walls": []}

    for i, building in enumerate(buildings):
        bbox = building["bbox"]
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        # 部屋を追加
        room = {
            "id": i + 1,
            "dimensions": [width, height],
            "position": [bbox[0], bbox[1]],
            "label": f"Room {i + 1}",
        }
        grid["rooms"].append(room)

        # 壁を追加
        walls = [
            {
                "start": [bbox[0], bbox[1]],
                "end": [bbox[2], bbox[1]],
                "height": 2.5,
            },  # 上壁
            {
                "start": [bbox[2], bbox[1]],
                "end": [bbox[2], bbox[3]],
                "height": 2.5,
            },  # 右壁
            {
                "start": [bbox[2], bbox[3]],
                "end": [bbox[0], bbox[3]],
                "height": 2.5,
            },  # 下壁
            {
                "start": [bbox[0], bbox[3]],
                "end": [bbox[0], bbox[1]],
                "height": 2.5,
            },  # 左壁
        ]
        grid["walls"].extend(walls)

    return grid


def send_to_freecad_api(grid_data: Dict[str, Any]) -> Dict[str, Any]:
    """グリッドデータをFreeCAD APIに送信する

    Args:
        grid_data (Dict[str, Any]): グリッドデータ

    Returns:
        Dict[str, Any]: APIレスポンス
    """
    try:
        # FreeCAD APIのエンドポイントを取得
        freecad_api_url = os.environ.get(
            "FREECAD_API_URL", "http://freecad-api-service:8080"
        )

        # グリッドデータをFreeCAD APIの形式に変換
        rooms = []
        walls = []

        # グリッドデータから部屋情報を抽出
        if "madori_info" in grid_data:
            for i, (room_name, room_info) in enumerate(
                grid_data["madori_info"].items()
            ):
                width = room_info.get("width", 0)
                height = room_info.get("height", 0)
                position = room_info.get("position", [0, 0])

                # 寸法をメートル単位に変換（1グリッド = 0.91m）
                width_m = width * 0.91
                height_m = height * 0.91

                rooms.append(
                    {
                        "id": i,
                        "dimensions": [width_m, height_m],
                        "position": position,
                        "label": room_name,
                    }
                )

        # 壁の情報を抽出（簡易的な実装）
        if "grid" in grid_data and "grid_stats" in grid_data:
            grid_stats = grid_data.get("grid_stats", {})
            if "boundaries" in grid_stats:
                for boundary in grid_stats["boundaries"]:
                    walls.append(
                        {
                            "start": boundary.get("start", [0, 0]),
                            "end": boundary.get("end", [0, 0]),
                            "height": 2.5,
                        }
                    )

        # APIリクエスト用のデータを作成
        api_data = {"rooms": rooms, "walls": walls}

        # APIにリクエストを送信
        response = requests.post(
            f"{freecad_api_url}/process/grid", json=api_data, timeout=60
        )

        # レスポンスを確認
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"FreeCAD APIエラー: {response.status_code} - {response.text}")
            return {"success": False, "error": f"APIエラー: {response.status_code}"}

    except Exception as e:
        logger.error(f"FreeCAD API呼び出しエラー: {e}")
        return {"success": False, "error": str(e)}


def convert_to_2d_drawing(grid_data: Dict[str, Any]) -> Dict[str, Any]:
    """2D図面を生成する

    Args:
        grid_data (Dict[str, Any]): グリッドデータ

    Returns:
        Dict[str, Any]: APIレスポンス
    """
    try:
        # FreeCAD APIのエンドポイントを取得
        freecad_api_url = os.environ.get(
            "FREECAD_API_URL", "http://freecad-api-service:8080"
        )

        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False) as temp_file:
            temp_file_path = temp_file.name

            # モデルファイルをダウンロード
            if "url" in grid_data:
                model_url = grid_data["url"]

                # Cloud Storageからファイルをダウンロード
                bucket_name = os.environ.get("BUCKET_NAME", "house-design-ai-data")
                file_name = model_url.split("/")[-1]

                # Google Cloud Storageからダウンロード
                storage_client = storage.Client()
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(f"models/{file_name}")
                blob.download_to_filename(temp_file_path)

                # ファイルをアップロードして2D変換をリクエスト
                with open(temp_file_path, "rb") as f:
                    files = {"file": (file_name, f, "application/octet-stream")}
                    response = requests.post(
                        f"{freecad_api_url}/convert/2d", files=files, timeout=60
                    )

                # 一時ファイルを削除
                os.unlink(temp_file_path)

                # レスポンスを確認
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        f"FreeCAD APIエラー: {response.status_code} - {response.text}"
                    )
                    return {
                        "success": False,
                        "error": f"APIエラー: {response.status_code}",
                    }
            else:
                logger.error("モデルURLが指定されていません")
                return {"success": False, "error": "モデルURLが指定されていません"}

    except Exception as e:
        logger.error(f"2D図面生成エラー: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Streamlitアプリのメインエントリーポイント"""

    # カスタムCSSを適用
    apply_custom_css()

    # ロゴを表示
    display_logo()

    # インポートエラーがあればここで表示
    if import_errors:
        st.error("### システムライブラリエラー")
        for error in import_errors:
            st.error(error)
        st.error(
            "アプリケーションの依存関係が正しくインストールされていません。管理者に連絡してください。"
        )
        st.info(
            "必要なライブラリ: libgl1-mesa-glx, libglib2.0-0, opencv-python-headless等"
        )
        return  # 重大なエラーなので、ここで処理を中断

    st.title("土地画像アップロード")

    # ──────────────────────────────────────────────
    # 1) パラメータ表示を mm*100 の数値に変更し、デフォルトを 5000, 500, 910 にする
    #    ラベルに「(mm*100)」と付けることで表示だけ大きい値で設定する
    # ──────────────────────────────────────────────
    st.sidebar.header("パラメータ設定")

    offset_near = st.sidebar.number_input(
        "道路近接領域のオフセット(px)",  # 元のラベルに戻す
        min_value=0,
        max_value=5000,
        value=295,  # 元の値に戻す
        step=10,
    )

    offset_far = st.sidebar.number_input(
        "道路以外の領域のオフセット(px)",  # 元のラベルに戻す
        min_value=0,
        max_value=5000,
        value=30,  # 元の値に戻す
        step=10,
    )

    grid_mm = st.sidebar.number_input(
        "グリッド間隔(mm)",  # 元のラベルに戻す
        min_value=0.1,
        max_value=100.0,
        value=9.1,  # 元の値に戻す
        step=0.1,
    )

    # 間取り表示モードの選択オプション
    floorplan_mode = st.sidebar.checkbox(
        "間取り表示モード",
        value=True,  # デフォルトでオン
        help="オンにすると、ランダムアルファベットの代わりに間取り（LDKなど）を表示します",
    )

    # CAD風表示のオプション
    cad_style = st.sidebar.checkbox(
        "CAD風表示",
        value=True,  # デフォルトでオン
        help="オンにすると、CAD風の間取り図を表示します",
    )

    # CAD表示の詳細オプション
    if cad_style and cad_display_available:
        with st.sidebar.expander("CAD表示オプション"):
            show_dimensions = st.checkbox("寸法情報を表示", value=True)
            show_furniture = st.checkbox("家具・設備を表示", value=True)

    with st.sidebar.expander("ヘルプ"):
        st.markdown(
            """
        ### パラメータ説明
        - **道路近接領域のオフセット(px)**: 道路に近い住居境界から内側に何ピクセル収縮するか
        - **道路以外の領域のオフセット(px)**: その他の住居境界から内側に何ピクセル収縮するか
        - **グリッド間隔(mm)**: A3横420mm図面での紙上のマス目サイズ(例: 9.1mm = 実物910mmの1/100)
        - **間取り表示モード**: オンにすると、ランダムアルファベットの代わりにLDK等の間取りを配置します
        - **CAD風表示**: オンにすると、FreeCADを使用したCAD風の間取り図を表示します
        """
        )

    # モデルロード
    with st.spinner("モデルをロード中..."):
        load_yolo_model()

    if "model" not in st.session_state or st.session_state.model is None:
        st.error("モデルのロードに失敗しました。アプリを再起動してください。")
        return

    # 画像アップロード
    uploaded_file = st.file_uploader(
        "建物・道路が写った画像を選択", type=["jpg", "jpeg", "png"]
    )

    if uploaded_file:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("元の画像")
            try:
                file_bytes = uploaded_file.getvalue()
                st.image(file_bytes, use_column_width=True)
            except Exception as e:
                st.error(f"画像の表示中にエラー: {str(e)}")
                logger.error(f"画像表示エラー: {e}")

        with col2:
            st.subheader("処理結果")
            with st.spinner("画像を処理中..."):
                try:
                    actual_near_offset_px = offset_near  # px扱い
                    actual_far_offset_px = offset_far  # px扱い
                    actual_grid_mm = grid_mm

                    process_result = process_image(
                        model=st.session_state.model,
                        image_file=uploaded_file,
                        near_offset_px=actual_near_offset_px,
                        far_offset_px=actual_far_offset_px,
                        grid_mm=actual_grid_mm,
                        floorplan_mode=floorplan_mode,
                    )

                    if process_result:
                        if (
                            isinstance(process_result, tuple)
                            and len(process_result) == 2
                        ):
                            result_image, debug_info = process_result
                        else:
                            result_image = process_result
                            debug_info = {
                                "params": {
                                    "near_offset_px": actual_near_offset_px,
                                    "far_offset_px": actual_far_offset_px,
                                    "grid_mm": actual_grid_mm,
                                },
                                "image_size": {
                                    "width_px": result_image.width,
                                    "height_px": result_image.height,
                                },
                                "note": "基本デバッグ情報のみ（旧バージョンのprocess_image関数使用中）",
                            }

                        # CAD風表示が有効で、CAD表示モジュールが利用可能な場合
                        if cad_style and cad_display_available and floorplan_mode:
                            # 通常の結果画像を表示
                            st.image(
                                result_image, use_column_width=True, caption="標準表示"
                            )

                            # CAD風の間取り図を表示
                            st.subheader("CAD風間取り図")
                            display_cad_floorplan(
                                result_image,
                                debug_info,
                                show_dimensions=show_dimensions,
                                show_furniture=show_furniture,
                            )

                            # 間取り詳細情報を表示
                            display_floorplan_details(debug_info)

                            # ダウンロードオプションを表示
                            display_download_options(result_image, debug_info)
                        else:
                            # 通常の結果画像を表示
                            st.image(result_image, use_column_width=True)

                            # 通常のダウンロードボタン
                            buf = io.BytesIO()
                            result_image.save(buf, format="PNG")
                            st.download_button(
                                label="結果をダウンロード",
                                data=buf.getvalue(),
                                file_name="result.png",
                                mime="image/png",
                            )

                        # デバッグ情報のセクション

                        # ──────────────────────────────────────────────
                        # デバッグ情報の安全な取得 (NoneTypeエラー対策)
                        # ──────────────────────────────────────────────
                        # debug_infoがNone、またはgrid_statsキーがない場合に備える
                        grid_stats = {}
                        cells_drawn = "不明"

                        if debug_info is not None:
                            grid_stats = debug_info.get("grid_stats", {}) or {}
                            cells_drawn = grid_stats.get("cells_drawn", "不明")

                        # 間取りモードの場合は間取り情報を表示（CAD風表示が無効の場合のみ）
                        if (
                            floorplan_mode
                            and debug_info is not None
                            and not (cad_style and cad_display_available)
                        ):
                            madori_info = debug_info.get("madori_info", {})
                            if madori_info:
                                st.subheader("間取り情報")
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
                                    description = madori_descriptions.get(
                                        madori_name, ""
                                    )
                                    width = info.get("width", 0)
                                    height = info.get("height", 0)
                                    area = (
                                        width * height * 0.91 * 0.91
                                    )  # 1グリッド = 0.91m x 0.91m
                                    madori_data.append(
                                        {
                                            "記号": madori_name,
                                            "名称": description,
                                            "幅": f"{width}マス",
                                            "高さ": f"{height}マス",
                                            "床面積": f"{area:.2f}㎡",
                                        }
                                    )

                                # DataFrameに変換して表示
                                if madori_data:
                                    import pandas as pd

                                    df = pd.DataFrame(madori_data)
                                    st.dataframe(df)

                                # FreeCAD APIとの連携
                                st.subheader("CADモデル生成")
                                if st.button("3Dモデルを生成"):
                                    with st.spinner("3Dモデルを生成中..."):
                                        # グリッドデータを準備
                                        grid_data = {
                                            "grid": grid_data,
                                            "madori_info": madori_info,
                                            "params": debug_info.get("params", {}),
                                        }

                                        # FreeCAD APIに送信
                                        cad_model_url = send_to_freecad_api(grid_data)

                                        if cad_model_url:
                                            st.success("3Dモデルの生成に成功しました")
                                            st.info(f"モデルURL: {cad_model_url}")

                                            # 3Dモデルをダウンロード
                                            with st.spinner(
                                                "3Dモデルをダウンロード中..."
                                            ):
                                                try:
                                                    # Cloud Storageからファイルをダウンロード
                                                    bucket_name = os.environ.get(
                                                        "BUCKET_NAME",
                                                        "house-design-ai-data",
                                                    )
                                                    file_name = cad_model_url.split(
                                                        "/"
                                                    )[-1]

                                                    # 一時ファイルとして保存
                                                    with tempfile.NamedTemporaryFile(
                                                        suffix=".fcstd", delete=False
                                                    ) as temp_file:
                                                        temp_file_path = temp_file.name

                                                    # Google Cloud Storageからダウンロード
                                                    from google.cloud import storage

                                                    storage_client = storage.Client()
                                                    bucket = storage_client.bucket(
                                                        bucket_name
                                                    )
                                                    blob = bucket.blob(
                                                        f"cad_models/{file_name}"
                                                    )
                                                    blob.download_to_filename(
                                                        temp_file_path
                                                    )

                                                    # 2D図面の生成
                                                    if st.button("2D図面を生成"):
                                                        with st.spinner(
                                                            "2D図面を生成中..."
                                                        ):
                                                            # FreeCAD APIに2D変換をリクエスト
                                                            drawing_url = (
                                                                convert_to_2d_drawing(
                                                                    temp_file_path
                                                                )
                                                            )

                                                            if drawing_url:
                                                                st.success(
                                                                    "2D図面の生成に成功しました"
                                                                )
                                                                st.info(
                                                                    f"図面URL: {drawing_url}"
                                                                )

                                                                # 図面を表示
                                                                st.markdown(
                                                                    f"### 2D図面"
                                                                )
                                                                st.markdown(
                                                                    f"![2D図面]({drawing_url})"
                                                                )
                                                            else:
                                                                st.error(
                                                                    "2D図面の生成に失敗しました"
                                                                )

                                                    # 一時ファイルを削除
                                                    os.unlink(temp_file_path)
                                                except Exception as e:
                                                    st.error(
                                                        f"3Dモデルのダウンロード中にエラーが発生しました: {str(e)}"
                                                    )
                                                    logger.error(
                                                        f"3Dモデルダウンロードエラー: {e}"
                                                    )
                                        else:
                                            st.error("3Dモデルの生成に失敗しました")

                        # 詳細デバッグ情報（エキスパートモード）
                        with st.expander("詳細デバッグ情報"):
                            st.json(debug_info)

                            # 処理パラメータ
                            st.subheader("処理パラメータ")
                            params = debug_info.get("params", {})
                            st.write(
                                f"- 道路近接領域オフセット: {params.get('road_setback_mm', '不明')}mm"
                            )
                            st.write(
                                f"- その他領域オフセット: {params.get('global_setback_mm', '不明')}mm"
                            )
                            st.write(
                                f"- グリッド間隔: {params.get('grid_mm', '不明')}mm"
                            )
                            st.write(
                                f"- 間取りモード: {'有効' if params.get('floorplan_mode', False) else '無効'}"
                            )

                            # 画像サイズ情報
                            st.subheader("画像サイズ情報")
                            original_size = debug_info.get("original_size", {})
                            image_size = debug_info.get("image_size", {})
                            st.write(
                                f"- 元画像: {original_size.get('width_px', '不明')}px × {original_size.get('height_px', '不明')}px"
                            )
                            st.write(
                                f"- 処理画像: {image_size.get('width_px', '不明')}px × {image_size.get('height_px', '不明')}px"
                            )

                            # グリッド情報
                            st.subheader("グリッド情報")
                            st.write(f"- 描画セル数: {cells_drawn}")
                            st.write(
                                f"- スキップセル数: {grid_stats.get('cells_skipped', '不明')}"
                            )
                            st.write(
                                f"- マスク外理由: {grid_stats.get('reason_not_in_mask', '不明')}"
                            )

                except Exception as e:
                    st.error(f"画像処理中にエラーが発生しました: {str(e)}")
                    logger.exception(f"画像処理エラー: {e}")

        # フッター
        st.markdown(
            """
            <div class="footer">
                © 2025 U-DAKE - 土地画像から間取りを生成するAIツール
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
