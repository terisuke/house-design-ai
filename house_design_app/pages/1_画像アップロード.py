"""
画像アップロードページ
土地画像をアップロードして間取りを自動生成します
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

# PyTorchのクラスパス問題を解決
import torch
from PIL import Image
from ultralytics import YOLO

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ユーティリティをインポート
try:
    from house_design_app.utils.style import apply_custom_css, display_logo, display_footer, section_divider
except ImportError as e:
    # フォールバックとしてカスタムCSSを直接適用する関数を定義
    def apply_custom_css():
        """アプリケーションに白基調のカスタムCSSを適用"""
        css = """
        <style>
            /* 全体の背景色を白に設定 */
            .stApp {
                background-color: white;
            }
            
            /* その他のスタイル設定は省略 */
            
            /* ボタンを赤背景、白文字に設定 */
            .stButton>button {
                background-color: #e50012;
                color: white;
                border: none;
                font-weight: bold;
                padding: 0.5rem 1rem;
                border-radius: 5px;
            }
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    
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
    
    def display_footer():
        """フッターを表示"""
        footer_html = """
        <div style="position: fixed; bottom: 0; left: 0; width: 100%; background-color: white; text-align: center; padding: 10px; font-size: 14px; border-top: 1px solid #f0f0f0; z-index: 999;">
            © 2025 U-DAKE - 土地画像から間取りを生成するAIツール
        </div>
        """
        st.markdown(footer_html, unsafe_allow_html=True)
    
    def section_divider():
        """セクション分割線を表示"""
        st.markdown('<hr style="margin: 30px 0; border: 0; height: 1px; background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(229, 0, 18, 0.75), rgba(0, 0, 0, 0));">', unsafe_allow_html=True)

def convert_to_2d_drawing(grid_data: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """2D図面を生成する

    Args:
        grid_data (Union[Dict[str, Any], str]): グリッドデータまたはFreeCADファイルのパス

    Returns:
        Dict[str, Any]: APIレスポンス
    """
    # グローバル変数 freecad_api_available をチェック
    if not globals().get('freecad_api_available', False):
        logger.warning("FreeCAD APIが利用できないため、2D図面生成をスキップします")
        return {
            "success": False,
            "error": "FreeCAD APIが利用できません。APIモードのみをサポートしています。"
        }
    
    if isinstance(grid_data, str) and os.path.exists(grid_data):
        file_path = grid_data
        grid_data = {"file_path": file_path}
    try:
        # FreeCAD APIのエンドポイントを取得
        freecad_api_url = os.environ.get(
            "FREECAD_API_URL", "http://freecad-api-service:8080"
        )
        logger.info(f"FreeCAD API URL: {freecad_api_url}")

        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False) as temp_file:
            temp_file_path = temp_file.name

            # モデルファイルをダウンロード
            if isinstance(grid_data, dict) and "url" in grid_data:
                model_url = grid_data["url"]

                # Cloud Storageからファイルをダウンロード
                bucket_name = os.environ.get("BUCKET_NAME", "house-design-ai-data")
                file_name = model_url.split("/")[-1]

                # Google Cloud Storageからダウンロード
                try:
                    import google.cloud.storage as gcs_storage

                    storage_client = gcs_storage.Client()
                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(f"models/{file_name}")
                except ImportError:
                    logger.error(
                        "Google Cloud Storageライブラリのインポートに失敗しました"
                    )
                    return {
                        "success": False,
                        "error": "Google Cloud Storageライブラリのインポートに失敗しました",
                    }
                blob.download_to_filename(temp_file_path)

                # ファイルをアップロードして2D変換をリクエスト
                with open(temp_file_path, "rb") as f:
                    files = {"file": (file_name, f, "application/octet-stream")}
                    
                    try:
                        response = requests.post(
                            f"{freecad_api_url}/convert/2d", files=files, timeout=60
                        )
                    except requests.exceptions.RequestException as e:
                        logger.error(f"FreeCAD APIリクエストエラー: {e}")
                        return {
                            "success": False,
                            "error": f"APIリクエストエラー: {e}",
                        }

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
        import traceback
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}

# CAD表示モジュールのインポート
try:
    from src.visualization.cad_display import (
        display_cad_floorplan,
        display_download_options,
        display_floorplan_details,
    )
    cad_display_available = True
except ImportError as e:
    cad_display_available = False
    logger.warning(f"CAD表示モジュールのインポートに失敗しました: {e}")

# FreeCAD APIクライアントの設定
try:
    # FreeCADのインポートは試みず、APIクライアントの設定のみ行う
    logger.info("FreeCAD APIに接続できました")
    freecad_api_available = True
except Exception as e:
    logger.warning(f"FreeCADのインポートに失敗しました: {e}")
    freecad_api_available = False

from src.cloud.storage import (
    download_dataset,
    download_model_from_gcs,
    initialize_gcs_client,
    upload_to_gcs,
)

# ロギング設定を最初に行う
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit-app")

# PyTorchとStreamlitの互換性問題の解決
import torch
if not hasattr(torch, 'classes'):
    torch.classes = type('', (), {'__path__': []})()
else:
    if not hasattr(torch.classes, '__path__'):
        torch.classes.__path__ = []

# アプリの設定はメインページで設定済み
# st.set_page_config()

# カスタムCSSを適用
apply_custom_css()

# ロゴを表示
with st.sidebar:
    display_logo()

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
    from src.processing.mask import process_image
    modules_available = True
except ImportError as e:
    error_msg = f"モジュールのインポートに失敗しました: {e}"
    logger.error(error_msg)
    import_errors.append(error_msg)

def load_yolo_model(model_path: Optional[str] = None):
    """YOLOモデルを読み込む

    Args:
        model_path (Optional[str]): モデルファイルのパス。Noneの場合はCloud Storageからダウンロード

    Returns:
        YOLO: 読み込まれたYOLOモデル
    """
    if model_path is None:
        from src.cloud.storage import download_model_from_gcs
        model_path = download_model_from_gcs()

    try:
        # PyTorch 2.6以降での安全なグローバルの登録
        try:
            torch.serialization.add_safe_globals(['ultralytics.nn.tasks.SegmentationModel'])
        except AttributeError:
            logger.warning("PyTorch 2.6未満のバージョンでは add_safe_globals は利用できません")
        
        # モデルロード時にweights_only=Falseを指定
        from ultralytics import YOLO
        model = YOLO(model_path)
        # モデルをセッションステートに保存
        st.session_state.model = model
        return model
    except Exception as e:
        logger.error(f"YOLOモデルのロード中にエラーが発生しました: {e}")
        return None

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
            "FREECAD_API_URL", "https://freecad-api-513507930971.asia-northeast1.run.app"
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

                # 寸法をmm単位に変換（1グリッド = 910mm）
                width_mm = width * 910
                height_mm = height * 910

                rooms.append(
                    {
                        "id": i,
                        "dimensions": [width_mm, height_mm],
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
                            "height": 2500,  # 壁の高さ（mm）
                        }
                    )

        # APIリクエスト用のデータを作成
        api_data = {"rooms": rooms, "walls": walls}

        # FreeCAD APIにリクエストを送信
        response = requests.post(
            f"{freecad_api_url}/generate",
            json=api_data,  # 必要に応じてtest_freecad_api.pyの形式に合わせてください
            headers={"Content-Type": "application/json"},
            timeout=60
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

def main():
    """Streamlitアプリのメインエントリーポイント"""

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

    st.title("画像アップロード")
    st.markdown("""
    土地の画像をアップロードして、建物と道路を検出し、自動で間取りを生成します。
    アップロードした画像から建物と道路の領域を検出し、建築可能エリアにグリッドを適用します。
    """)

    # サイドバーにパラメータ設定へのリンクを追加
    st.sidebar.header("パラメータ設定")
    st.sidebar.info("パラメータ設定は設定ページで行えます。")
    if st.sidebar.button("設定ページへ"):
        st.switch_page("pages/4_設定.py")

    # メインコンテンツエリア
    # タブでメイン機能を分割
    tab1, tab2 = st.tabs(["📷 画像アップロード", "📊 処理結果"])

    with tab1:
        # 画像アップロードの説明
        st.markdown("""
        ### 画像アップロードの手順
        1. 土地の画像（空撮写真、地図、図面など）をアップロードします
        2. 建物と道路の領域が自動的に検出されます
        3. 設定に基づいて間取りが自動生成されます
        """)

        # 画像アップロードエリア
        model_loaded = "model" in st.session_state
        uploaded_file = st.file_uploader(
            "建物・道路が写った画像を選択", 
            type=["jpg", "jpeg", "png"], 
            key="image_upload",
            help="上空から見た土地の画像や図面をアップロードしてください"
        )
        
        # サンプル画像を使用するオプション
        st.markdown("### または")
        use_sample = st.checkbox("サンプル画像を使用", value=False)
        
        if use_sample:
            # サンプル画像を表示（複数から選べるようにする）
            sample_options = ["サンプル1（住宅地）", "サンプル2（郊外）", "サンプル3（都市部）"]
            selected_sample = st.selectbox("サンプル画像を選択", sample_options)
            
            # サンプル画像のパスを設定（実際には存在する画像パスに置き換える）
            sample_path = Path(__file__).parent / "samples" / "sample1.jpg"
            
            st.image("https://placehold.jp/800x600.png", caption=f"選択中: {selected_sample}", use_column_width=True)
            
            if st.button("このサンプルを使用"):
                # サンプル画像をアップロードファイルとして設定（実装では実際のファイルパスを使用）
                st.info("サンプルをロード中...")
                # サンプル画像が実際に存在する場合のコード
                # with open(sample_path, "rb") as f:
                #     uploaded_file = io.BytesIO(f.read())
                
                # 画像が存在しない場合、ダミーデータを作成
                uploaded_file = io.BytesIO()
                Image.new("RGB", (800, 600), color=(255, 255, 255)).save(uploaded_file, format="JPEG")
                uploaded_file.seek(0)
                
                st.success("サンプルがロードされました。「処理結果」タブに移動して結果を確認してください。")
        
        if uploaded_file and not model_loaded:
            with st.spinner("モデルをロード中..."):
                load_yolo_model()

        if uploaded_file and (
            "model" not in st.session_state or st.session_state.model is None
        ):
            st.error("モデルのロードに失敗しました。アプリを再起動してください。")
            return

    with tab2:
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
                        # セッションステートからパラメータを取得
                        if "params" in st.session_state:
                            params = st.session_state.params
                            actual_near_offset_px = params["near_offset_px"]
                            actual_far_offset_px = params["far_offset_px"]
                            actual_grid_mm = params["grid_mm"]
                            floorplan_mode = params["floorplan_mode"]
                            cad_style = params["cad_style"]
                            show_dimensions = params["show_dimensions"]
                            show_furniture = params["show_furniture"]
                        else:
                            # デフォルト値
                            actual_near_offset_px = 295
                            actual_far_offset_px = 30
                            actual_grid_mm = 9.1
                            floorplan_mode = True
                            cad_style = True
                            show_dimensions = True
                            show_furniture = True

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

                            # 結果をセッションステートに保存（他のページで使用するため）
                            st.session_state.result_image = result_image
                            st.session_state.debug_info = debug_info

                            # CAD風表示が有効で、CAD表示モジュールが利用可能な場合
                            if cad_style and cad_display_available and floorplan_mode:
                                # CAD表示オプションをセッションステートから取得
                                show_dimensions = st.session_state.params.get('show_dimensions', True) if 'params' in st.session_state else True
                                show_furniture = st.session_state.params.get('show_furniture', True) if 'params' in st.session_state else True

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

                            # 次のステップの説明
                            st.success("間取り生成が完了しました。次のステップに進みましょう！")
                            st.markdown("""
                            ### 次のステップ:
                            1. **3Dモデル生成:** サイドバーの「3Dモデル生成」をクリックして、自動生成された間取りから3Dモデルを作成します。
                            2. **建築基準法チェック:** 「建築基準法チェック」ページで、生成された間取りが建築基準法に準拠しているかを確認します。
                            3. **PDF図面出力:** 3Dモデルから2D図面を生成し、建築確認申請用のPDF図面を出力できます。
                            """)

                            # デバッグ情報のセクション
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

                    except Exception as e:
                        st.error(f"画像処理中にエラーが発生しました: {str(e)}")
                        logger.exception(f"画像処理エラー: {e}")
        else:
            st.info("画像がアップロードされていません。左側の「画像アップロード」タブで画像をアップロードしてください。")
            # 使用例を表示
            st.subheader("使用例")
            st.markdown("""
            1. 「画像アップロード」タブで土地の画像をアップロードします
            2. 「処理結果」タブで自動生成された間取りを確認します
            3. サイドバーのパラメータを調整して、結果を最適化します
            4. 「3Dモデル生成」ページで3Dモデルを作成します
            5. 建築基準法チェックで法的要件への準拠を確認します
            """)

    # フッターを表示
    display_footer()

if __name__ == "__main__":
    main()
