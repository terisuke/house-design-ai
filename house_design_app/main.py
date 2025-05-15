"""
House Design AI メインアプリケーション
マルチページアプリのエントリーポイント
"""

import streamlit as st
import sys
import asyncio
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# アプリの設定
st.set_page_config(
    page_title="U-DAKE",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# サイドバーのメインページ表示を非表示にする
st.markdown(
    """
    <style>
    [data-testid="collapsedControl"] {
        display: none;
    }
    #MainMenu {
        visibility: hidden;
    }
    div[data-testid="stSidebarNavItems"] {
        padding-top: 0rem;
    }
    div[data-testid="stSidebarNavItems"] > ul {
        padding-top: 0.5rem;
    }
    div[data-testid="stSidebarNavItems"] > ul > li:first-child {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# イベントループの設定
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# 画像アップロードページにリダイレクト
st.switch_page("pages/1_画像アップロード.py")