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

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# 自作モジュールのインポート
from src.cloud.storage import download_model_from_gcs
from src.processing.mask import process_image

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit-app")

# アプリの設定
st.set_page_config(
    page_title="建物セグメンテーション＆グリッド生成",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    st.title("建物セグメンテーション＆グリッド生成 (A3横向き)")

    # サイドバー
    st.sidebar.header("パラメータ設定")

    # ★dpi, scale は削除し、 grid_mm のみ残す
    offset_near = st.sidebar.number_input("道路近接領域のオフセット(px)", 0, 5000, 100, 10)
    offset_far = st.sidebar.number_input("道路以外の領域のオフセット(px)", 0, 5000, 50, 10)
    grid_mm = st.sidebar.number_input("グリッド間隔(mm)", 0.1, 100.0, 9.1, 0.1)

    with st.sidebar.expander("ヘルプ"):
        st.markdown("""
        ### パラメータ説明
        - **道路近接領域のオフセット(px)**: 道路に近い住居境界から内側に何ピクセル収縮するか
        - **道路以外の領域のオフセット(px)**: その他の住居境界から内側に何ピクセル収縮するか
        - **グリッド間隔(mm)**: A3横420mm図面での紙上のマス目サイズ(例: 9.1mm)

        ### 補足
        本アプリでは常に「画像の横幅(px) → 420mm」という比率で換算します。
        """)

    # モデルロード
    with st.spinner("モデルをロード中..."):
        load_yolo_model()

    if "model" not in st.session_state or st.session_state.model is None:
        st.error("モデルのロードに失敗しました。アプリを再起動してください。")
        return

    # 画像アップロード
    st.header("画像アップロード")
    uploaded_file = st.file_uploader("建物・道路が写った画像を選択 (A3横向き想定)", type=["jpg", "jpeg", "png"])

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
                    result = process_image(
                        model=st.session_state.model,
                        image_file=uploaded_file,
                        near_offset_px=offset_near,
                        far_offset_px=offset_far,
                        grid_mm=grid_mm  # DPI, scale不要
                    )
                    if result:
                        st.image(result, use_column_width=True)

                        buf = io.BytesIO()
                        result.save(buf, format="PNG")
                        st.download_button(
                            label="結果をダウンロード",
                            data=buf.getvalue(),
                            file_name="result.png",
                            mime="image/png"
                        )

                        with st.expander("処理メタデータ"):
                            st.json({
                                "元画像サイズ(px)": f"{result.width}x{result.height}",
                                "パラメータ": {
                                    "道路近接領域のオフセット(px)": offset_near,
                                    "道路以外の領域のオフセット(px)": offset_far,
                                    "グリッド間隔(mm)": grid_mm
                                }
                            })
                    else:
                        st.error("画像の処理に失敗しました。別の画像を試してください。")
                except Exception as e:
                    st.error(f"画像処理中にエラー: {str(e)}")
                    logger.error(f"画像処理エラー: {e}")

    st.markdown("---")
    st.markdown("U-DAKE (©2025)")

if __name__ == "__main__":
    main()