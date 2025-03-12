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

    # サイドバー
    st.sidebar.header("パラメータ設定")

    # ★dpi, scale は削除し、 grid_mm のみ残す
    offset_near = st.sidebar.number_input("道路近接領域のオフセット(px)", 0, 5000, 296, 10)
    offset_far = st.sidebar.number_input("道路以外の領域のオフセット(px)", 0, 5000, 30, 10)
    grid_mm = st.sidebar.number_input("グリッド間隔(mm)", 0.1, 100.0, 9.1, 0.1)

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
    uploaded_file = st.file_uploader("建物・道路が写った画像を選択 (どんなサイズでもA3として処理)", type=["jpg", "jpeg", "png"])

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
                    process_result = process_image(
                        model=st.session_state.model,
                        image_file=uploaded_file,
                        near_offset_px=offset_near,
                        far_offset_px=offset_far,
                        grid_mm=grid_mm  # DPI, scale不要
                    )
                    
                    if process_result:
                        # 新旧両方の形式に対応: 新形式はタプル(Image, dict)、旧形式はImage単体
                        if isinstance(process_result, tuple) and len(process_result) == 2:
                            result_image, debug_info = process_result
                        else:
                            # 旧形式の場合はImageオブジェクトだけで、デバッグ情報は手動で作成
                            result_image = process_result
                            debug_info = {
                                "params": {
                                    "near_offset_px": offset_near,
                                    "far_offset_px": offset_far,
                                    "grid_mm": grid_mm
                                },
                                "image_size": {"width_px": result_image.width, "height_px": result_image.height},
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
                        
                        # デバッグ情報のセクションを追加（常に表示）
                        st.subheader("デバッグ情報")
                        
                        # リサイズ情報の表示
                        if debug_info.get("resized") and debug_info.get("original_size"):
                            orig_size = debug_info["original_size"]
                            st.write(f"🔄 **元の画像サイズ**: {orig_size['width_px']}px × {orig_size['height_px']}px")
                            
                            if debug_info.get("a3_size"):
                                a3_size = debug_info["a3_size"]
                                st.write(f"📄 **A3サイズ (150dpi)**: {a3_size['width_px']}px × {a3_size['height_px']}px")
                                st.info("すべての画像はA3サイズ(150dpi)にリサイズされ、同じスケールでグリッド線が描画されます。")
                        
                        # バウンディングボックス情報
                        if debug_info.get("bounding_box"):
                            bbox = debug_info["bounding_box"]
                            st.write(f"🔍 **バウンディングボックス**: (x={bbox['x']}, y={bbox['y']}, 幅={bbox['width']}, 高さ={bbox['height']})")
                            
                            # グリッドの行数と列数を計算して表示
                            if debug_info.get("cell_px"):
                                cell_px = debug_info["cell_px"]
                                grid_rows = bbox['height'] // cell_px
                                grid_cols = bbox['width'] // cell_px
                                st.write(f"📏 **グリッドサイズ**: {grid_rows}行 × {grid_cols}列")
                                
                                # グリッド統計情報の表示（新規追加）
                                if debug_info.get("grid_stats"):
                                    grid_stats = debug_info["grid_stats"]
                                    st.subheader("🧩 マス目生成の詳細")
                                    
                                    # マス目の統計情報
                                    st.write(f"- **バウンディングボックス内の全マス目数**: {grid_stats.get('total_cells_in_bbox', '不明')}")
                                    st.write(f"- **実際に描画されたマス目数**: {grid_stats.get('cells_drawn', '不明')}")
                                    st.write(f"- **スキップされたマス目数**: {grid_stats.get('cells_skipped', '不明')}")
                                    
                                    # 理論上の最大グリッドサイズ
                                    if grid_stats.get("theoretical_grid_size"):
                                        theoretical = grid_stats["theoretical_grid_size"]
                                        st.write(f"- **理論上の最大グリッドサイズ**: {theoretical.get('rows', '?')}行 × {theoretical.get('cols', '?')}列")
                                    
                                    # スキップ理由の内訳
                                    if grid_stats.get("reason_not_in_mask", 0) > 0:
                                        st.write(f"- **マスク外のためスキップ**: {grid_stats.get('reason_not_in_mask')}マス")
                                        
                                    # スキップされたマス目の割合
                                    if grid_stats.get("total_cells_in_bbox", 0) > 0:
                                        skip_ratio = grid_stats.get("cells_skipped", 0) / grid_stats.get("total_cells_in_bbox", 1) * 100
                                        st.write(f"- **スキップ率**: {skip_ratio:.1f}%")
                                        
                                        # 建物の形状に関する説明
                                        if skip_ratio > 50:
                                            st.info("👉 スキップ率が高いため、建物形状が不規則または複雑な形状であると考えられます。")
                                        elif skip_ratio > 20:
                                            st.info("👉 建物形状にある程度の凹凸があるため、一部のマス目がスキップされています。")
                                        else:
                                            st.info("👉 建物形状が比較的整っているため、多くのマス目が描画されています。")
                                            
                                    # グリッド描画に関する説明
                                    st.info("ℹ️ **「完全に収まるマス目だけを描画」モードを使用しています。**マス目の一部でもマスク外にはみ出す場合はそのマス目全体を描画しません。これにより整然としたグリッドが表示されます。")
                        
                        # セルサイズとフォールバック情報
                        if debug_info.get("cell_px"):
                            st.write(f"📊 **セルサイズ**: {debug_info['cell_px']}px")
                            
                            # px_per_mm情報
                            if debug_info.get("px_per_mm"):
                                st.write(f"📐 **ピクセル/mm変換比率**: {debug_info['px_per_mm']:.2f}px/mm")
                                st.write(f"📐 **理論上のセルサイズ計算**: {grid_mm}mm × {debug_info['px_per_mm']:.2f}px/mm = {grid_mm * debug_info['px_per_mm']:.2f}px")
                                
                                # 実物サイズの説明（1/100縮尺の場合）
                                real_size_mm = grid_mm * 100  # 1/100縮尺の場合
                                st.write(f"🏠 **実物相当サイズ (1/100縮尺)**: {grid_mm}mm × 100 = {real_size_mm}mm = {real_size_mm/1000:.2f}m")
                            
                            # フォールバック発動の場合は警告表示
                            if debug_info.get("fallback_activated"):
                                st.warning(f"⚠️ **フォールバック発動**: 元のセルサイズ({debug_info.get('original_cell_px')}px)がバウンディングボックスより大きいため、{debug_info.get('fallback_cell_px')}pxに調整されました。")
                        
                        # 画像サイズ情報
                        if debug_info.get("image_size"):
                            img_size = debug_info["image_size"]
                            st.write(f"🖼️ **処理後画像サイズ**: {img_size['width_px']}px × {img_size['height_px']}px")
                        
                        # 使用したパラメータを表示
                        st.write("🔧 **使用パラメータ**:")
                        params = debug_info.get("params", {})
                        st.write(f"- 道路近接オフセット: {params.get('near_offset_px')}px")
                        st.write(f"- その他領域オフセット: {params.get('far_offset_px')}px")
                        st.write(f"- グリッド間隔: {params.get('grid_mm')}mm")
                        
                        # エラー情報があれば表示
                        if debug_info.get("error"):
                            st.error(f"エラー: {debug_info['error']}")
                        elif debug_info.get("note"):
                            st.info(debug_info["note"])
                        
                        # メタデータを詳細表示するセクション
                        with st.expander("詳細デバッグ情報 (JSON)"):
                            st.json(debug_info)
                    else:
                        st.error("画像の処理に失敗しました。別の画像を試してください。")
                except Exception as e:
                    st.error(f"画像処理中にエラー: {str(e)}")
                    logger.error(f"画像処理エラー: {e}")

    st.markdown("---")
    st.markdown("U-DAKE (©2025)")

if __name__ == "__main__":
    main()