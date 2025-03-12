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

# ロギング設定を最初に行う
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit-app")

# アプリの設定（必ず最初のStreamlitコマンドにする）
st.set_page_config(
    page_title="建物セグメンテーション＆グリッド生成",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    
    # インポートエラーがあればここで表示
    if import_errors:
        st.error("### システムライブラリエラー")
        for error in import_errors:
            st.error(error)
        st.error("アプリケーションの依存関係が正しくインストールされていません。管理者に連絡してください。")
        st.info("必要なライブラリ: libgl1-mesa-glx, libglib2.0-0, opencv-python-headless等")
        return  # 重大なエラーなので、ここで処理を中断
        
    st.title("建物セグメンテーション＆グリッド生成 (A3横向き)")

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

        ### 補足
        - すべての画像はA3サイズ(150dpi: 2481x1754px)に自動リサイズされて処理されます。
        - これにより、どのような画像でも同じスケールで一貫したグリッドが描画されます。
        - グリッド間隔は「紙上のmm単位」で指定します。例えば：
          - 9.1mm → 実物で910mm (1/100縮尺)
          - 10mm → 実物で1000mm (1/100縮尺)
        """)

    # モデルロード
    with st.spinner("モデルをロード中..."):
        load_yolo_model()

    if "model" not in st.session_state or st.session_state.model is None:
        st.error("モデルのロードに失敗しました。アプリを再起動してください。")
        return

    # 画像アップロード
    st.header("画像アップロード")
    st.info("アップロードされた画像は自動的にA3サイズ(150dpi: 2481x1754px)にリサイズされ処理されます。")
    uploaded_file = st.file_uploader(
        "建物・道路が写った画像を選択 (どんなサイズでもA3として処理)",
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
            st.subheader("処理結果 (A3サイズにリサイズ)")
            with st.spinner("画像を処理中..."):
                try:
                    # ─────────────────────────────────────────────────────
                    # 1) mm*100で入力された値を「px」として使っていた旧仕様を踏襲するため
                    #    いったん「近接オフセット(px)」「その他オフセット(px)」として渡す
                    #    => near_offset_px, far_offset_px
                    # 2) グリッド間隔は mm で受け取っていたが、今回は mm*100 になっているので
                    #    9.1 mm 相当なら 910 → 910 / 100 = 9.1 (float)
                    # ─────────────────────────────────────────────────────
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
                        st.subheader("デバッグ情報")
                        
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
                        with st.expander("詳細デバッグ情報 (JSON)"):
                            if debug_info is not None:
                                st.json(debug_info)
                            else:
                                st.write("デバッグ情報が利用できません")
                    else:
                        st.error("画像の処理に失敗しました。別の画像を試してください。")
                except Exception as e:
                    st.error(f"画像処理中にエラー: {str(e)}")
                    logger.error(f"画像処理エラー: {e}")

    st.markdown("---")
    st.markdown("U-DAKE (©2025)")

if __name__ == "__main__":
    main()