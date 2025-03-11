"""
建物・道路セグメンテーションとグリッド生成のためのStreamlitアプリ
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

# 自作モジュールをインポート
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
            # ローカルのモデルをロード
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
                    # デフォルトモデルの使用を試みる
                    try:
                        from ultralytics import YOLO
                        st.session_state.model = YOLO("yolov8m-seg.pt")
                        st.warning("デフォルトのYOLOv8mセグメンテーションモデルを使用します")
                    except Exception as e:
                        st.error(f"デフォルトモデルのロードに失敗: {e}")
            except Exception as e:
                st.error(f"モデルロードエラー: {e}")


def main():
    """Streamlitアプリのメインエントリーポイント"""
    st.title("建物セグメンテーション＆グリッド生成")
    
    # サイドバーの設定
    st.sidebar.header("パラメータ設定")
    
    # モデルのロード
    with st.spinner("モデルをロード中..."):
        load_yolo_model()
    
    if "model" not in st.session_state or st.session_state.model is None:
        st.error("モデルのロードに失敗しました。アプリを再起動してください。")
        return
    
    # 処理パラメータの設定
    offset_near = st.sidebar.number_input("道路近接領域のオフセット(px)", 0, 5000, 100, 10)
    offset_far = st.sidebar.number_input("道路以外の領域のオフセット(px)", 0, 5000, 50, 10)
    grid_mm = st.sidebar.number_input("グリッド間隔(mm)", 1.0, 10000.0, 910.0, 10.0)
    dpi_val = st.sidebar.number_input("DPI", 1.0, 1200.0, 300.0, 1.0)
    scale_val = st.sidebar.number_input("スケール", 0.01, 10.0, 1.0, 0.01)
    
    # ヘルプセクション
    with st.sidebar.expander("ヘルプ"):
        st.markdown("""
        ### パラメータ説明
        
        - **道路近接領域のオフセット**: 道路に近い建物境界からのオフセット距離(ピクセル)
        - **道路以外の領域のオフセット**: その他の建物境界からのオフセット距離(ピクセル)
        - **グリッド間隔**: グリッド線の間隔(ミリメートル)
        - **DPI**: 画像の解像度(1インチあたりのドット数)
        - **スケール**: 追加の倍率係数
        
        ### 使用方法
        1. 画像をアップロードします
        2. パラメータを調整します
        3. 処理された画像が表示されます
        4. 結果をダウンロードできます
        """)
    
    # 画像アップロードセクション
    st.header("画像アップロード")
    uploaded_file = st.file_uploader("建物・道路が写った画像を選択", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        # 2カラムレイアウト
        col1, col2 = st.columns(2)
        
        # 左カラム: 元の画像
        with col1:
            st.subheader("元の画像")
            st.image(uploaded_file, use_container_width=True)
        
        # 右カラム: 処理結果
        with col2:
            st.subheader("処理結果")
            with st.spinner("画像を処理中..."):
                result = process_image(
                    model=st.session_state.model,
                    image_file=uploaded_file,
                    near_offset_px=offset_near,
                    far_offset_px=offset_far,
                    grid_mm=grid_mm,
                    dpi=dpi_val,
                    scale=scale_val
                )
                
                if result:
                    st.image(result, use_container_width=True)
                    
                    # ダウンロードボタン
                    buf = io.BytesIO()
                    result.save(buf, format="PNG")
                    st.download_button(
                        label="結果をダウンロード",
                        data=buf.getvalue(),
                        file_name="result.png",
                        mime="image/png"
                    )
                    
                    # メタデータ表示
                    with st.expander("処理メタデータ"):
                        st.json({
                            "元画像サイズ": f"{result.width}x{result.height}",
                            "パラメータ": {
                                "道路近接領域のオフセット": offset_near,
                                "道路以外の領域のオフセット": offset_far,
                                "グリッド間隔(mm)": grid_mm,
                                "DPI": dpi_val,
                                "スケール": scale_val
                            }
                        })
                else:
                    st.error("画像の処理中にエラーが発生しました")
    
    # フッター
    st.markdown("---")
    st.markdown("U-DAKE")


if __name__ == "__main__":
    main()