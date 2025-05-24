"""
設定ページ
アプリケーションとパラメータの設定を変更できます
"""

import logging
import streamlit as st
import sys
import os
from pathlib import Path

# 親ディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# ユーティリティをインポート
try:
    from utils.style import apply_custom_css, display_logo, display_footer
except ImportError as e:
    st.error(f"スタイルユーティリティのインポート失敗: {e}")

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit-app-settings")

# ページ設定はメインページで設定済み
# st.set_page_config()

# カスタムCSSを適用
try:
    apply_custom_css()
except Exception as e:
    st.error(f"スタイルの適用に失敗: {e}")

# ロゴを表示
with st.sidebar:
    display_logo()

# タイトルと説明
st.title("設定")
st.markdown("""
アプリケーションの設定とパラメータを変更できます。設定はブラウザセッション中に保存されます。
""")

# タブで設定をグループ化
tab1, tab2, tab3 = st.tabs(["パラメータ設定", "表示設定", "API設定"])

with tab1:
    st.subheader("間取り生成パラメータ")
    
    # 既存の設定値を取得（セッションステートから）
    if "params" not in st.session_state:
        st.session_state.params = {
            "near_offset_px": 295,
            "far_offset_px": 30,
            "grid_mm": 9.1,
            "floorplan_mode": True,
            "cad_style": True,
            "show_dimensions": True,
            "show_furniture": True,
        }
    
    params = st.session_state.params
    
    offset_near = st.number_input(
        "道路近接領域のオフセット(px)",
        min_value=0,
        max_value=5000,
        value=params["near_offset_px"],
        step=10,
        help="道路に近い住居境界から内側に収縮させる距離"
    )
    
    offset_far = st.number_input(
        "道路以外の領域のオフセット(px)",
        min_value=0,
        max_value=5000,
        value=params["far_offset_px"],
        step=10,
        help="道路以外の住居境界から内側に収縮させる距離"
    )
    
    grid_mm = st.number_input(
        "グリッド間隔(mm)",
        min_value=0.1,
        max_value=100.0,
        value=params["grid_mm"],
        step=0.1,
        help="間取りグリッドの間隔 (A3横で9.1mm = 実物910mm)"
    )
    
    # 間取り表示オプション
    st.subheader("表示オプション")
    
    floorplan_mode = st.checkbox(
        "間取り表示モード",
        value=params["floorplan_mode"],
        help="オンにすると、ランダムアルファベットの代わりに間取り（LDKなど）を表示します"
    )
    
    cad_style = st.checkbox(
        "CAD風表示",
        value=params["cad_style"],
        help="オンにすると、CAD風の間取り図を表示します"
    )
    
    # CAD表示の詳細オプション
    if cad_style:
        show_dimensions = st.checkbox(
            "寸法情報を表示", 
            value=params["show_dimensions"],
            help="CAD表示で寸法情報を表示します"
        )
        show_furniture = st.checkbox(
            "家具・設備を表示", 
            value=params["show_furniture"],
            help="CAD表示で家具・設備を表示します"
        )
    else:
        show_dimensions = params["show_dimensions"]
        show_furniture = params["show_furniture"]

with tab2:
    st.subheader("表示設定")

    # テーマ設定
    theme_options = ["ライト", "ダーク"]
    selected_theme = st.selectbox(
        "テーマ",
        options=theme_options,
        index=0,
        help="アプリケーションの表示テーマを選択します"
    )
    
    # 表示モード設定
    display_mode_options = ["標準", "詳細", "開発者"]
    selected_display_mode = st.selectbox(
        "表示モード",
        options=display_mode_options,
        index=0,
        help="表示する情報の詳細度を選択します"
    )
    
    # フォントサイズ設定
    font_size = st.slider(
        "フォントサイズ倍率",
        min_value=0.8,
        max_value=1.5,
        value=1.0,
        step=0.1,
        help="文字の大きさを調整します"
    )

with tab3:
    st.subheader("API設定")
    
    # YOLOモデルの選択
    yolo_model_options = ["YOLO v11n", "YOLO v11s", "YOLO v11m (デフォルト)", "YOLO v11l", "YOLO v11x"]
    selected_yolo_model = st.selectbox(
        "YOLOモデル",
        options=yolo_model_options,
        index=2,
        help="使用するYOLOモデルを選択します。高性能なモデルほど精度が高くなりますが、処理に時間がかかります。"
    )
    
    # APIエンドポイント設定
    freecad_api_url = st.text_input(
        "FreeCAD API URL",
        value=os.environ.get("FREECAD_API_URL", "https://your-freecad-api-endpoint.com"),
        help="FreeCAD APIのエンドポイントURLを設定します"
    )

# 設定の保存と適用ボタン
if st.button("設定を保存", type="primary"):
    # パラメータ設定を保存
    st.session_state.params = {
        "near_offset_px": offset_near,
        "far_offset_px": offset_far,
        "grid_mm": grid_mm,
        "floorplan_mode": floorplan_mode,
        "cad_style": cad_style,
        "show_dimensions": show_dimensions,
        "show_furniture": show_furniture,
    }
    
    # 表示設定を保存
    st.session_state.display_settings = {
        "theme": selected_theme,
        "display_mode": selected_display_mode,
        "font_size": font_size,
    }
    
    # API設定を保存
    st.session_state.api_settings = {
        "yolo_model": selected_yolo_model,
        "freecad_api_url": freecad_api_url,
    }
    
    # 環境変数を設定（セッション内のみ）
    os.environ["FREECAD_API_URL"] = freecad_api_url
    
    st.success("設定を保存しました。設定はブラウザセッション中のみ有効です。")
    st.info("一部の設定は次回のページ読み込み時に適用されます。")

# 設定のリセット
if st.button("設定をリセット"):
    # セッションステートから設定を削除
    if "params" in st.session_state:
        del st.session_state.params
    if "display_settings" in st.session_state:
        del st.session_state.display_settings
    if "api_settings" in st.session_state:
        del st.session_state.api_settings
    
    st.success("設定をデフォルトに戻しました。")
    st.experimental_rerun()

# 現在の設定を表示
with st.expander("現在の設定一覧"):
    st.subheader("パラメータ設定")
    st.json(st.session_state.get("params", {}))
    
    st.subheader("表示設定")
    st.json(st.session_state.get("display_settings", {}))
    
    st.subheader("API設定")
    st.json(st.session_state.get("api_settings", {}))

# 詳細情報
with st.expander("詳細情報"):
    st.subheader("アプリケーション情報")
    st.markdown("""
    - バージョン: 1.0.0
    - 最終更新日: 2025年5月7日
    - 開発者: U-DAKE チーム
    """)
    
    st.subheader("システム情報")
    st.markdown(f"""
    - Python バージョン: {sys.version.split(' ')[0]}
    - Streamlit バージョン: {st.__version__}
    - 実行環境: {'デプロイ環境' if os.environ.get('DEPLOYED') else 'ローカル環境'}
    """)

# パラメータ説明
with st.expander("パラメータ説明"):
    st.markdown("""
    ### パラメータ設定
    - **道路近接領域のオフセット(px)**: 道路に近い住居境界から内側に何ピクセル収縮するか
    - **道路以外の領域のオフセット(px)**: その他の住居境界から内側に何ピクセル収縮するか
    - **グリッド間隔(mm)**: A3横420mm図面での紙上のマス目サイズ(例: 9.1mm = 実物910mmの1/100)
    
    ### 表示オプション
    - **間取り表示モード**: オンにすると、ランダムアルファベットの代わりにLDK等の間取りを配置します
    - **CAD風表示**: オンにすると、FreeCADを使用したCAD風の間取り図を表示します
    - **寸法情報を表示**: CAD表示で寸法情報を表示します
    - **家具・設備を表示**: CAD表示で家具・設備を表示します
    """)

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
