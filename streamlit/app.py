# streamlit/app.py
"""
建物・道路セグメンテーションとグリッド生成のためのStreamlitアプリ
(2025-03-12 修正版: A3横向き換算でマス目描画)
"""

import streamlit as st
import os
import tempfile
import io
from typing import Optional, Tuple, Dict, Any, Union
from pathlib import Path
import logging
import sys
import base64

# ロギング設定を最初に行う
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit-app")

# アプリの設定（必ず最初のStreamlitコマンドにする）
st.set_page_config(
    page_title="U-DAKE",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
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

def load_yolo_model() -> None:
    """YOLOモデルをロード・初期化"""
    if "model" not in st.session_state or st.session_state.model is None:
        # 環境変数からモデルパスをチェック
        model_path = os.environ.get("YOLO_MODEL_PATH")

        if model_path and os.path.exists(model_path):
            from ultralytics import YOLO
            st.session_state.model = YOLO(model_path)
            st.success(f"ローカルモデルをロードしました: {model_path}")
        else:
            # Google Cloud Storageからモデルをダウンロード
            try:
                model_path = download_model_from_gcs(
                    bucket_name="yolo-v11-training",
                    blob_name="runs/segment/train_20250311-143512/weights/best.pt"
                )
                if model_path:
                    from ultralytics import YOLO
                    st.session_state.model = YOLO(model_path)
                    st.success("クラウドストレージからモデルをロードしました")
                else:
                    st.error("モデルのダウンロードに失敗しました")
                    # デフォルトモデルを試す
                    try:
                        from ultralytics import YOLO
                        st.session_state.model = YOLO("yolov8m-seg.pt")
                        st.warning("デフォルトYOLOv8mセグメンテーションモデルを使用します")
                    except Exception as e:
                        st.error(f"デフォルトモデルのロードにも失敗: {e}")
            except Exception as e:
                st.error(f"モデルロードエラー: {e}")

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
        st.error("アプリケーションの依存関係が正しくインストールされていません。管理者に連絡してください。")
        st.info("必要なライブラリ: libgl1-mesa-glx, libglib2.0-0, opencv-python-headless等")
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
        step=10
    )

    offset_far = st.sidebar.number_input(
        "道路以外の領域のオフセット(px)",  # 元のラベルに戻す
        min_value=0,
        max_value=5000,
        value=30,   # 元の値に戻す
        step=10
    )

    grid_mm = st.sidebar.number_input(
        "グリッド間隔(mm)",  # 元のラベルに戻す
        min_value=0.1,
        max_value=100.0,
        value=9.1,   # 元の値に戻す
        step=0.1
    )

    with st.sidebar.expander("ヘルプ"):
        st.markdown("""
        ### パラメータ説明
        - **道路近接領域のオフセット(px)**: 道路に近い住居境界から内側に何ピクセル収縮するか
        - **道路以外の領域のオフセット(px)**: その他の住居境界から内側に何ピクセル収縮するか
        - **グリッド間隔(mm)**: A3横420mm図面での紙上のマス目サイズ(例: 9.1mm = 実物910mmの1/100)
        """)

    # モデルロード
    with st.spinner("モデルをロード中..."):
        load_yolo_model()

    if "model" not in st.session_state or st.session_state.model is None:
        st.error("モデルのロードに失敗しました。アプリを再起動してください。")
        return

    # 画像アップロード
    uploaded_file = st.file_uploader(
        "建物・道路が写った画像を選択",
        type=["jpg", "jpeg", "png"]
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
                    actual_far_offset_px = offset_far    # px扱い
                    actual_grid_mm = grid_mm

                    process_result = process_image(
                        model=st.session_state.model,
                        image_file=uploaded_file,
                        near_offset_px=actual_near_offset_px,
                        far_offset_px=actual_far_offset_px,
                        grid_mm=actual_grid_mm
                    )
                    
                    if process_result:
                        if isinstance(process_result, tuple) and len(process_result) == 2:
                            result_image, debug_info = process_result
                        else:
                            result_image = process_result
                            debug_info = {
                                "params": {
                                    "near_offset_px": actual_near_offset_px,
                                    "far_offset_px": actual_far_offset_px,
                                    "grid_mm": actual_grid_mm
                                },
                                "image_size": {
                                    "width_px": result_image.width,
                                    "height_px": result_image.height
                                },
                                "note": "基本デバッグ情報のみ（旧バージョンのprocess_image関数使用中）"
                            }
                            
                        st.image(result_image, use_column_width=True)

                        buf = io.BytesIO()
                        result_image.save(buf, format="PNG")
                        st.download_button(
                            label="結果をダウンロード",
                            data=buf.getvalue(),
                            file_name="result.png",
                            mime="image/png"
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
                        
                        # ここで「実際に描画されたマス目数」を「マス目数」として表示
                        st.write(f"**マス目数**: {cells_drawn}")
                        
                        # グリッドサイズと床面積の計算
                        actual_grid_rows = grid_stats.get("actual_grid_rows")
                        actual_grid_cols = grid_stats.get("actual_grid_cols")
                        
                        # バウンディングボックスから行数・列数を推定（actual_grid_rows/colsがない場合）
                        if actual_grid_rows is None and actual_grid_cols is None and debug_info is not None:
                            if debug_info.get("bounding_box") and debug_info.get("cell_px"):
                                bbox = debug_info.get("bounding_box", {})
                                cell_px = debug_info.get("cell_px")
                                if bbox and cell_px and cell_px > 0:
                                    actual_grid_rows = bbox.get("height", 0) // cell_px
                                    actual_grid_cols = bbox.get("width", 0) // cell_px
                        
                        if (actual_grid_rows is not None) and (actual_grid_cols is not None):
                            st.write(f"**グリッドサイズ**: {actual_grid_rows} 行 × {actual_grid_cols} 列")
                        else:
                            # グリッドを最終的に何行何列描いたかを
                            # まとめていない実装の場合は推測不可なので「(不明)」を表示
                            st.write("**グリッドサイズ**: 不明(行×列)")
                            
                        # 床面積計算
                        one_cell_area_m2 = 0.91 * 0.91  # = 0.8281
                        if isinstance(cells_drawn, int) and cells_drawn > 0:
                            total_area_m2 = cells_drawn * one_cell_area_m2
                            st.write(f"**床面積**: 約 {total_area_m2:.2f} m² (910mmグリッド換算)")
                        else:
                            st.write("**床面積**: 面積計算不可")
                        
                        # メタデータ(JSON)
                        with st.expander("デバッグ情報 (JSON)"):
                            if debug_info is not None:
                                st.json(debug_info)
                            else:
                                st.write("デバッグ情報が利用できません")
                    else:
                        st.error("画像の処理に失敗しました。別の画像を試してください。")
                except Exception as e:
                    st.error(f"画像処理中にエラー: {str(e)}")
                    logger.error(f"画像処理エラー: {e}")

    # フッターの追加
    st.markdown(
        """
        <div class="footer" style="font-size: 24px; font-weight: bold;">
            U-DAKE (©2025)
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()