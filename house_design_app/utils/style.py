"""
スタイル関連のユーティリティ
すべてのページで共通して使用するスタイル定義
"""

import streamlit as st
import base64
import os
from pathlib import Path

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
            background-color: white \\!important;
        }
        
        /* タイトルバーの背景を白に設定 */
        .st-emotion-cache-z5fcl4, [data-testid="stToolbar"] {
            background-color: white \\!important;
        }
        
        /* サイドバーのスタイル - 複数のセレクタを使用して確実に適用 */
        [data-testid="stSidebar"] {
            background-color: white \\!important;
        }
        [data-testid="stSidebar"] > div {
            background-color: white \\!important;
        }
        .css-1d391kg, .css-1lcbmhc, div[data-testid="stSidebar"], 
        .st-emotion-cache-1cypcdb, .st-emotion-cache-1gulkj5 {
            background-color: white \\!important;
        }
        
        /* サイドバーのスクロール部分 */
        .st-emotion-cache-uf99v8 {
            background-color: white \\!important;
        }
        
        /* サイドバーの開閉ボタン(矢印)を黒色に設定 */
        button[kind="header"] {
            color: black \\!important;
        }
        .st-emotion-cache-7oyrr6 {
            color: black \\!important;
        }
        [data-testid="collapsedControl"] {
            color: black \\!important;
        }
        [data-testid="baseButton-headerNoPadding"], svg[data-testid="chevronDownIcon"], svg[data-testid="chevronUpIcon"] {
            color: black \\!important;
            fill: black \\!important;
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
            background-color: #e50012 \\!important;
            color: white \\!important;
            border-color: #e50012 \\!important;
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
            color: white \\!important;
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
            color: white \\!important;
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
            background-color: #e50012 \\!important;
            color: white \\!important;
            border-radius: 5px;
            padding: 10px;
        }
        
        /* JSONビューア内のすべてのテキスト要素 */
        .element-container .stJson *, 
        [data-testid="stJson"] *,
        .streamlit-expanderContent .stJson * {
            color: white \\!important;
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

        /* カードスタイル */
        .card {
            border-radius: 5px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            padding: 20px;
            margin-bottom: 20px;
            background-color: #f9f9f9;
        }

        /* セクション分割線 */
        .section-divider {
            margin: 30px 0;
            border: 0;
            height: 1px;
            background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(229, 0, 18, 0.75), rgba(0, 0, 0, 0));
        }

        /* プログレスバー */
        .stProgress > div > div > div > div {
            background-color: #e50012;
        }

        /* タブのスタイル */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #f0f0f0;
            border-radius: 4px 4px 0 0;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #e50012 !important;
            color: #fff !important;
        }

        /* --- 1. サイドバーロゴ最上部配置用 --- */
        .sidebar-logo-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: 0;
            margin-bottom: 24px;
            padding: 0;
            width: 100%;
        }
        .sidebar-logo-container img {
            max-width: 90%;
            max-height: 80px;
            display: block;
            margin: 0 auto;
        }

        /* --- 2. 赤ボタンの文字色を白に強制 --- */
        .stButton>button,
        .stDownloadButton>button {
            background-color: #e50012 !important;
            color: #fff !important;
            border: none;
            font-weight: bold;
            padding: 0.5rem 1rem;
            border-radius: 5px;
        }
        .stButton>button:hover,
        .stDownloadButton>button:hover {
            background-color: #b3000e !important;
            color: #fff !important;
        }

        /* --- 3. タブ幅を統一 --- */
        .stTabs [data-baseweb="tab"] {
            min-width: 160px;
            max-width: 160px;
            width: 160px;
            text-align: center;
        }

        /* --- 4. サイドバーからmainを非表示 --- */
        /* サイドバーの最初のリスト項目（main）を非表示にする */
        div[data-testid="stSidebarNavItems"] > ul > li:first-child {
            display: none !important;
        }
        /* サイドバーのmainテキストも非表示にする */
        [data-testid="stSidebar"] ul li:first-child {
            display: none !important;
        }

        /* さらに強力にボタンの文字色を白に */
        button, .stButton>button, .stDownloadButton>button {
            color: #fff !important;
            background-color: #e50012 !important;
            border: none !important;
        }
        button:active, button:focus, button:hover, .stButton>button:active, .stButton>button:focus, .stButton>button:hover {
            color: #fff !important;
            background-color: #b3000e !important;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def display_logo():
    """サイドバーにロゴを表示(左上に配置)"""
    # ロゴのパスを取得
    try:
        # ディレクトリパスを取得
        file_path = Path(__file__)
        parent_dir = file_path.parent.parent
        logo_path = parent_dir / "logo.png"
        
        if logo_path.exists():
            with open(logo_path, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode()
                html = f"""
                <div style="text-align: left; margin-bottom: 20px; padding: 0;">
                    <img src="data:image/png;base64,{b64}" style="max-width: 100%; max-height: 80px;">
                </div>
                """
                st.sidebar.markdown(html, unsafe_allow_html=True)
        else:
            st.sidebar.warning("ロゴファイル (logo.png) が見つかりません。")
    except Exception as e:
        st.sidebar.warning(f"ロゴ表示エラー: {e}")

def display_footer():
    """フッターを表示"""
    footer_html = """
    <div style="position: fixed; bottom: 0; left: 0; width: 100%; background-color: white; text-align: center; padding: 10px; font-size: 14px; border-top: 1px solid #f0f0f0; z-index: 999;">
        © 2025 U-DAKE - 土地画像から間取りを生成するAIツール
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)

def card(content, key=None):
    """カードスタイルのコンテナを作成"""
    html = f"""
    <div class="card" id="{key if key else ''}">
        {content}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def section_divider():
    """セクション分割線を表示"""
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

def convert_to_2d_drawing(grid_data):
    """2D図面に変換する機能
    
    Args:
        grid_data (dict): グリッドデータ
        
    Returns:
        dict: 変換結果
    """
    import requests
    import os
    import tempfile
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # FreeCAD APIのエンドポイントを取得
        freecad_api_url = os.environ.get(
            "FREECAD_API_URL", "https://freecad-api-513507930971.asia-northeast1.run.app"
        )
        
        # APIリクエスト用のデータを作成
        api_data = {
            "grid": grid_data.get("grid", {}),
            "madori_info": grid_data.get("madori_info", {}),
            "options": {
                "drawing_type": "平面図",
                "scale": "1:100"
            }
        }
        
        # APIにリクエストを送信
        response = requests.post(
            f"{freecad_api_url}/convert/2d", 
            json=api_data,
            timeout=60
        )
        
        # レスポンスを確認
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"FreeCAD APIエラー: {response.status_code} - {response.text}")
            return {"success": False, "error": f"APIエラー: {response.status_code}"}
    
    except Exception as e:
        logger.error(f"2D図面変換エラー: {e}")
        return {"success": False, "error": str(e)}