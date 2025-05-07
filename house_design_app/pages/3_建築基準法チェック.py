"""
建築基準法チェックページ
生成された間取りデータに対して建築基準法のチェックを行います。
"""

import logging
import streamlit as st
import numpy as np
import pandas as pd
import sys
from pathlib import Path
from PIL import Image

# 親ディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# ユーティリティをインポート
try:
    from house_design_app.utils.style import apply_custom_css, display_logo, display_footer, section_divider
except ImportError as e:
    st.error(f"スタイルユーティリティのインポート失敗: {e}")

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit-app-building-code")

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
st.title("建築基準法チェック")
st.markdown("""
このページでは、生成された間取りデータが建築基準法に準拠しているかをチェックします。
主な確認項目として、容積率や建ぺい率、採光や通風の要件などをチェックします。
""")

# セッションステートで間取り情報を確認
if "debug_info" not in st.session_state or "result_image" not in st.session_state:
    st.warning("まだ間取り情報が生成されていません。最初にメインページで土地画像をアップロードして間取りを生成してください。")
    st.info("メインページに戻るには、左側のサイドバーの「Home」をクリックしてください。")
    
    # サンプルデータを使用するオプション
    st.subheader("サンプルデータを使用")
    if st.button("サンプルデータをロード"):
        # サンプルの間取り情報を生成
        sample_madori_info = {
            "E": {"width": 2, "height": 2, "position": [0, 0]},
            "L": {"width": 4, "height": 3, "position": [2, 0]},
            "D": {"width": 3, "height": 2, "position": [2, 3]},
            "K": {"width": 2, "height": 2, "position": [0, 2]},
            "B": {"width": 2, "height": 2, "position": [6, 0]},
            "T": {"width": 1, "height": 1, "position": [6, 2]},
            "UT": {"width": 2, "height": 1, "position": [5, 3]}
        }
        
        # 画像サイズの設定
        img_width = 800
        img_height = 600
        sample_image = Image.new("RGB", (img_width, img_height), color=(255, 255, 255))
        
        # 画像をセッションステートに保存
        st.session_state.result_image = sample_image
        st.session_state.debug_info = {
            "madori_info": sample_madori_info,
            "params": {
                "global_setback_mm": 5.0,
                "road_setback_mm": 50.0,
                "grid_mm": 9.1,
                "floorplan_mode": True
            },
            "bounding_box": {"x": 100, "y": 100, "width": 600, "height": 400},
            "cell_px": 54,
            "px_per_mm": 5.9,
            "grid": {"width": 8, "height": 6},
            "grid_stats": {"cells_drawn": 30, "cells_skipped": 0}
        }
        
        st.success("サンプルデータをロードしました！")
        st.experimental_rerun()
    
    # メインページへのボタン
    st.button("メインページへ戻る", on_click=lambda: st._rerun())
    
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
    
    st.stop()

# 前のページで生成した画像を表示
st.subheader("生成された間取り図")
col1, col2 = st.columns([1, 1])
with col1:
    st.image(st.session_state.result_image, use_column_width=True, caption="生成された間取り図")

# 間取り情報を表示
debug_info = st.session_state.debug_info
madori_info = debug_info.get("madori_info", {})

# 土地情報入力
with col2:
    st.subheader("土地情報")
    
    col2_1, col2_2 = st.columns(2)
    with col2_1:
        land_area = st.number_input(
            "敷地面積（㎡）",
            min_value=50.0,
            max_value=2000.0,
            value=200.0,
            step=10.0,
            help="敷地の総面積を入力してください"
        )
        
        max_building_coverage = st.number_input(
            "建ぺい率（%）",
            min_value=30,
            max_value=80,
            value=60,
            step=5,
            help="地域の建ぺい率制限を入力してください"
        )
    
    with col2_2:
        land_width = st.number_input(
            "間口（m）",
            min_value=5.0,
            max_value=50.0,
            value=10.0,
            step=1.0,
            help="道路に面した土地の幅を入力してください"
        )
        
        max_floor_area_ratio = st.number_input(
            "容積率（%）",
            min_value=50,
            max_value=400,
            value=200,
            step=10,
            help="地域の容積率制限を入力してください"
        )
    
    land_zone = st.selectbox(
        "用途地域",
        options=["第一種低層住居専用地域", "第二種低層住居専用地域", "第一種中高層住居専用地域", 
                "第二種中高層住居専用地域", "第一種住居地域", "第二種住居地域", "準住居地域",
                "近隣商業地域", "商業地域", "準工業地域", "工業地域", "工業専用地域"],
        index=0,
        help="地域の用途地域を選択してください"
    )
    
    st.subheader("建築条件")
    north_side_restriction = st.checkbox(
        "北側斜線制限あり",
        value=True,
        help="北側斜線制限の有無"
    )
    
    daylight_factor = st.slider(
        "採光率",
        min_value=0.0,
        max_value=1.0,
        value=0.14,
        step=0.01,
        help="採光率の最低基準値"
    )

# チェックボタン
st.subheader("建築基準法チェック")
if st.button("建築基準法チェックを実行"):
    with st.spinner("建築基準法に基づくチェックを実行中..."):
        # 間取りの床面積を計算
        total_floor_area = 0
        building_coverage = 0
        
        for room_name, room_info in madori_info.items():
            width = room_info.get("width", 0)
            height = room_info.get("height", 0)
            room_area = width * height * 0.91 * 0.91  # 1グリッド = 0.91m x 0.91m
            total_floor_area += room_area
            
            # 1階の部屋の場合は建ぺい率の計算に含める
            # 仮に全ての部屋を1階と仮定
            building_coverage += room_area
        
        # 建ぺい率のチェック
        building_coverage_ratio = (building_coverage / land_area) * 100
        building_coverage_ok = building_coverage_ratio <= max_building_coverage
        
        # 容積率のチェック
        floor_area_ratio = (total_floor_area / land_area) * 100
        floor_area_ratio_ok = floor_area_ratio <= max_floor_area_ratio
        
        # 部屋ごとの採光チェック
        daylight_rooms = ["L", "D", "K"]  # 居室と見なす部屋
        daylight_checks = {}
        
        for room_name, room_info in madori_info.items():
            if room_name in daylight_rooms:
                width = room_info.get("width", 0)
                height = room_info.get("height", 0)
                room_area = width * height * 0.91 * 0.91
                
                # 仮の採光面積（部屋の面積の10%と仮定）
                window_area = room_area * 0.1
                actual_daylight_factor = window_area / room_area
                
                daylight_checks[room_name] = {
                    "室面積": f"{room_area:.2f}㎡",
                    "必要採光面積": f"{room_area * daylight_factor:.2f}㎡",
                    "想定採光面積": f"{window_area:.2f}㎡",
                    "採光基準": "適合" if actual_daylight_factor >= daylight_factor else "不適合"
                }
        
        # 結果の表示
        st.subheader("チェック結果")
        
        # 一般情報の表示
        col_result1, col_result2 = st.columns(2)
        
        with col_result1:
            st.info(f"### 建築面積\n{building_coverage:.2f}㎡（敷地面積の{building_coverage_ratio:.1f}%）")
            st.info(f"### 延床面積\n{total_floor_area:.2f}㎡（敷地面積の{floor_area_ratio:.1f}%）")
        
        with col_result2:
            # 建ぺい率チェック結果
            if building_coverage_ok:
                st.success(f"### 建ぺい率チェック\n制限値: {max_building_coverage}% / 計画値: {building_coverage_ratio:.1f}% ✅")
            else:
                st.error(f"### 建ぺい率チェック\n制限値: {max_building_coverage}% / 計画値: {building_coverage_ratio:.1f}% ❌")
            
            # 容積率チェック結果
            if floor_area_ratio_ok:
                st.success(f"### 容積率チェック\n制限値: {max_floor_area_ratio}% / 計画値: {floor_area_ratio:.1f}% ✅")
            else:
                st.error(f"### 容積率チェック\n制限値: {max_floor_area_ratio}% / 計画値: {floor_area_ratio:.1f}% ❌")
        
        # 採光チェック結果
        st.subheader("採光チェック結果")
        if daylight_checks:
            df = pd.DataFrame.from_dict(daylight_checks, orient='index')
            st.dataframe(df)
        else:
            st.warning("採光チェック対象の部屋がありません。")
        
        # 総合判定
        st.subheader("総合判定")
        all_checks_passed = building_coverage_ok and floor_area_ratio_ok and all(
            check["採光基準"] == "適合" for check in daylight_checks.values()
        )
        
        if all_checks_passed:
            st.success("### 建築基準法に適合しています ✅")
        else:
            st.error("### 建築基準法に不適合の項目があります ❌")
            
            # 不適合項目の詳細
            st.subheader("不適合項目の詳細")
            if not building_coverage_ok:
                st.error(f"- 建ぺい率が制限値（{max_building_coverage}%）を超過しています")
            if not floor_area_ratio_ok:
                st.error(f"- 容積率が制限値（{max_floor_area_ratio}%）を超過しています")
            for room_name, check in daylight_checks.items():
                if check["採光基準"] == "不適合":
                    st.error(f"- {room_name}の採光基準を満たしていません")

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