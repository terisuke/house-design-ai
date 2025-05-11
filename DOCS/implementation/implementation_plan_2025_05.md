# 実装計画書 2025年5月

## 概要

本文書は、House Design AIプロジェクトの次期開発フェーズにおける実装計画を詳細に記述したものです。この計画は、以下の5つの主要コンポーネントの開発に焦点を当てています：

1. YOLOアノテーション → ベクター/グラフJSON変換システム
2. CP-SAT最小PoCの開発（3LDKの基本レイアウト生成と建築基準法制約の実装）
3. FreeCAD APIの完全実装と安定化
4. HouseDiffusion小規模実装と初期トレーニング
5. Streamlit UIの拡張

各コンポーネントの実装は、プロジェクトの全体的な目標である「土地の地図から自動的にCAD図面を生成するシステム」の実現に不可欠です。この計画は、Plan Bアーキテクチャに基づいており、HouseDiffusion（生成層）とCP-SAT（制約ソルバー層）の2層アーキテクチャを採用しています。

## 1. YOLOアノテーション → ベクター/グラフJSON変換システム

### 目的
YOLOモデルによって生成されたアノテーションデータを、間取り図生成に必要なベクターデータおよびグラフ構造のJSONに変換するシステムを構築します。

### 実装詳細

#### 1.1 データ構造の定義

```python
# src/processing/yolo_to_vector.py

from typing import List, Dict, Tuple, Optional, Union
import numpy as np
import json
from pydantic import BaseModel

class Point(BaseModel):
    x: float
    y: float

class Line(BaseModel):
    start: Point
    end: Point
    type: str = "wall"  # wall, window, door, etc.

class Room(BaseModel):
    id: str
    name: str
    points: List[Point]
    area: float
    neighbors: List[str] = []
    room_type: str = "other"  # living, bedroom, kitchen, etc.

class Building(BaseModel):
    rooms: List[Room]
    walls: List[Line]
    windows: List[Line] = []
    doors: List[Line] = []
    
class Site(BaseModel):
    building: Building
    boundary: List[Point]
    road_access: List[Line] = []
    north_direction: float = 0.0  # 北方向（ラジアン）
```

#### 1.2 変換パイプラインの実装

- YOLOアノテーション → マスク画像への変換
- マスク画像 → 輪郭抽出（OpenCV contour detection）
- 輪郭 → ベクターデータ（ポリゴン単純化）
- ベクターデータ → グラフ構造（隣接関係の抽出）
- グラフ構造 → JSON出力（Pydanticモデルを使用）

#### 1.3 主要機能

- `convert_yolo_to_vector()`: YOLOの検出結果をベクターデータに変換
- `convert_vector_to_graph()`: ベクターデータをグラフ構造に変換
- `serialize_to_json()`: データをJSON形式でシリアライズして保存
- `visualize_vector_data()`: 変換結果を視覚化して検証

### テスト計画

1. 単体テスト：各関数の入出力と境界条件のテスト
2. 統合テスト：YOLOの出力から最終JSONまでの一連の処理のテスト
3. 視覚的検証：変換結果を視覚化して人間が確認

### 成功基準

- YOLOの検出結果から正確なベクターデータへの変換率 > 95%
- 生成されたJSONが定義されたスキーマに100%準拠
- 処理時間 < 2秒/画像

## 2. CP-SAT最小PoCの開発

### 目的
Google OR-ToolsのCP-SATソルバーを使用して、3LDKの基本レイアウトを生成し、日本の建築基準法に準拠した制約を実装します。

### 実装詳細

#### 2.1 基本データモデル

```python
# src/optimization/cp_sat_solver.py

from typing import List, Dict, Tuple, Optional
from ortools.sat.python import cp_model
import numpy as np

class Room:
    def __init__(self, name: str, min_area: float, preferred_ratio: float = 1.0):
        self.name = name
        self.min_area = min_area  # 最小面積（m²）
        self.preferred_ratio = preferred_ratio  # 望ましい縦横比
        
        # CP-SAT変数（後で初期化）
        self.x = None  # x座標
        self.y = None  # y座標
        self.width = None  # 幅
        self.height = None  # 高さ
        self.area = None  # 面積

class BuildingConstraints:
    def __init__(self):
        # 建築基準法の制約
        self.min_room_size = 4.5  # 居室の最小面積（m²）
        self.min_ceiling_height = 2.1  # 最小天井高（m）
        self.min_corridor_width = 0.78  # 最小廊下幅（m）
        self.min_door_width = 0.75  # 最小ドア幅（m）
        self.wall_thickness = 0.12  # 壁の厚さ（m）
        self.first_floor_height = 2.9  # 1階の高さ（m）
        self.second_floor_height = 2.8  # 2階の高さ（m）
```

#### 2.2 主要機能

- `create_3ldk_model()`: 3LDKの間取りを生成するためのCP-SATモデルを構築
- `add_adjacency_constraint()`: 2つの部屋が隣接していることを保証する制約を追加
- `solve_and_convert()`: CP-SATモデルを解いて結果をJSON形式に変換
- `visualize_layout()`: 生成された間取りを視覚化

#### 2.3 実装する制約

1. **部屋の基本制約**
   - 最小面積要件
   - 望ましい縦横比
   - 部屋が敷地内に収まる

2. **部屋間の関係制約**
   - 部屋同士が重ならない
   - 特定の部屋間の隣接関係（例：LDKと玄関、浴室とトイレ）
   - 動線の最適化（玄関からの距離）

3. **建築基準法の制約**
   - 建蔽率・容積率の遵守
   - 最小居室面積の確保
   - 最小天井高の確保
   - 最小廊下幅の確保

### テスト計画

1. 単体テスト：各制約関数のテスト
2. 統合テスト：様々な敷地サイズと制約条件での解の検証
3. 視覚的検証：生成された間取りの視覚化と建築基準法への適合性確認

### 成功基準

- 3LDKの基本レイアウトが正常に生成される
- すべての部屋が最小面積要件を満たす
- 建築基準法の制約（建蔽率、容積率など）を100%遵守
- 解の生成時間 < 30秒

## 3. FreeCAD APIの完全実装と安定化

### 目的
FreeCAD APIを完全に実装し、安定化させることで、生成された間取りデータから正確な3Dモデルを作成できるようにします。

### 実装詳細

#### 3.1 FreeCAD APIの基本構造

```python
# freecad_api/freecad_wrapper.py

import os
import sys
import tempfile
import json
import logging
from typing import Dict, List, Optional, Tuple, Union

# FreeCADのインポート
try:
    import FreeCAD
    import Part
    import Draft
    import Arch
    FREECAD_AVAILABLE = True
except ImportError:
    logging.warning("FreeCADのインポートに失敗しました: No module named 'FreeCAD'")
    FREECAD_AVAILABLE = False

class FreeCADWrapper:
    def __init__(self):
        self.document = None
        self.wall_thickness = 120  # mm
        self.first_floor_height = 2900  # mm
        self.second_floor_height = 2800  # mm
        
        if FREECAD_AVAILABLE:
            self.document = FreeCAD.newDocument("House")
```

#### 3.2 主要機能

- `create_wall()`: 壁を作成する機能
- `create_room()`: 部屋を作成する機能
- `create_model_from_json()`: JSON形式のデータから3Dモデルを作成
- `export_model()`: 3Dモデルをエクスポート（fcstd, step, stl, obj, gltf）
- `create_2d_drawing()`: 3Dモデルから2D図面を生成（PDF, SVG）

#### 3.3 エラー処理とフォールバック

- FreeCADが利用できない場合のフォールバック処理
- 例外処理と適切なエラーメッセージ
- ログ機能の強化

#### 3.4 パフォーマンス最適化

- 大規模モデル生成時のメモリ使用量の最適化
- 処理速度の向上（キャッシュの活用など）
- 並列処理の検討

### テスト計画

1. 単体テスト：各APIメソッドの機能テスト
2. 統合テスト：JSONから3Dモデル生成までの一連の処理のテスト
3. エラー処理テスト：様々なエラーケースでの動作確認
4. パフォーマンステスト：大規模なモデル生成時の性能評価

### 成功基準

- FreeCADのインポートエラーが解消される
- JSONから正確な3Dモデルへの変換率 > 95%
- 2D図面の生成が正常に機能する
- エラー発生時の適切なフォールバック処理の実装
- 処理時間の最適化（中規模モデルで < 10秒）

## 4. HouseDiffusion小規模実装と初期トレーニング

### 目的
HouseDiffusionモデルの小規模実装と初期トレーニングを行い、間取り図の生成能力を検証します。

### 実装詳細

#### 4.1 基本モデル構造

```python
# src/models/house_diffusion.py

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional
import numpy as np

class UNet(nn.Module):
    def __init__(self, in_channels, out_channels, time_emb_dim=256):
        super().__init__()
        
        # Time embedding
        self.time_mlp = nn.Sequential(
            nn.Linear(1, time_emb_dim),
            nn.ReLU(),
            nn.Linear(time_emb_dim, time_emb_dim)
        )
        
        # Encoder
        self.enc1 = ResidualBlock(in_channels, 64)
        self.enc2 = ResidualBlock(64, 128)
        self.enc3 = ResidualBlock(128, 256)
        self.enc4 = ResidualBlock(256, 512)
        
        # Decoder
        self.dec4 = ResidualBlock(512 + 512, 256)
        self.dec3 = ResidualBlock(256 + 256, 128)
        self.dec2 = ResidualBlock(128 + 128, 64)
        self.dec1 = ResidualBlock(64 + 64, 64)
        
        # Final layer
        self.final = nn.Conv2d(64, out_channels, 1)
```

#### 4.2 主要機能

- `forward()`: 訓練用のフォワードパス
- `add_noise()`: 指定されたタイムステップでノイズを追加
- `sample()`: サンプリングによる間取り生成
- `save_model()`: モデルの保存
- `load_model()`: モデルの読み込み

#### 4.3 データセット準備

- 間取り図データセットの収集と前処理
- データ拡張（回転、反転、スケーリングなど）
- 敷地境界と間取り図のペアの作成

#### 4.4 トレーニングパイプライン

- 損失関数の定義
- 最適化アルゴリズムの選択
- 学習率スケジューリング
- 早期停止とモデル選択

### テスト計画

1. 単体テスト：各モデルコンポーネントのテスト
2. 統合テスト：トレーニングとサンプリングの一連の流れのテスト
3. 生成結果の評価：生成された間取り図の品質評価

### 成功基準

- モデルが収束し、意味のある間取り図を生成できる
- 敷地境界の制約を考慮した間取り図の生成
- 生成された間取り図の多様性
- 推論時間 < 10秒/サンプル

## 5. Streamlit UIの拡張

### 目的
新アーキテクチャに対応したユーザーインターフェースを構築し、ユーザーが簡単に間取り図を生成、編集、評価できるようにします。

### 実装詳細

#### 5.1 UIコンポーネント

```python
# house_design_app/pages/2_間取り生成.py

import streamlit as st
import numpy as np
import pandas as pd
import json
import requests
from PIL import Image
import io
import matplotlib.pyplot as plt
import time

def generate_layout_page():
    st.title("間取り生成")
    
    # サイドバー：パラメータ設定
    st.sidebar.header("パラメータ設定")
    
    # 敷地情報
    st.sidebar.subheader("敷地情報")
    site_width = st.sidebar.slider("敷地幅 (m)", 10.0, 30.0, 15.0, 0.5)
    site_depth = st.sidebar.slider("敷地奥行き (m)", 10.0, 30.0, 20.0, 0.5)
    
    # 間取り要件
    st.sidebar.subheader("間取り要件")
    num_bedrooms = st.sidebar.slider("寝室数", 1, 5, 3)
    has_ldk = st.sidebar.checkbox("LDK", value=True)
    has_bathroom = st.sidebar.checkbox("浴室", value=True)
    has_toilet = st.sidebar.checkbox("トイレ", value=True)
    
    # 生成方法
    st.sidebar.subheader("生成方法")
    generation_method = st.sidebar.radio(
        "生成方法",
        ["HouseDiffusion", "CP-SAT", "HouseDiffusion + CP-SAT"]
    )
    
    # 生成ボタン
    if st.sidebar.button("間取り生成"):
        with st.spinner("間取りを生成中..."):
            # 実際の実装では、バックエンドAPIを呼び出す
            time.sleep(3)  # シミュレーション
            
            # 結果表示（ダミーデータ）
            st.success("間取りが生成されました！")
            
            # タブで結果表示
            tab1, tab2, tab3 = st.tabs(["2D間取り", "3Dモデル", "詳細情報"])
            
            with tab1:
                st.image("dummy_floorplan.png", caption="生成された間取り図")
                
            with tab2:
                st.write("3Dモデルビューア（実装予定）")
                
            with tab3:
                st.write("部屋情報")
                room_data = {
                    "部屋名": ["LDK", "主寝室", "寝室2", "寝室3", "浴室", "トイレ"],
                    "面積 (m²)": [25.5, 12.3, 8.7, 8.5, 3.2, 1.8]
                }
                st.dataframe(pd.DataFrame(room_data))
                
                st.write("建築基準法チェック")
                check_data = {
                    "項目": ["建蔽率", "容積率", "居室面積", "天井高"],
                    "結果": ["適合", "適合", "適合", "適合"]
                }
                st.dataframe(pd.DataFrame(check_data))
```

#### 5.2 主要機能

- 土地画像のアップロードと処理（既存機能の拡張）
- 間取り生成パラメータの設定と実行
- 生成された間取りの表示と編集
- 3Dモデルの表示と操作
- 建築基準法チェック結果の表示
- 生成結果のエクスポート（JSON, PDF, 3Dモデル）

#### 5.3 バックエンドAPI連携

- YOLOアノテーション変換APIの呼び出し
- CP-SATソルバーAPIの呼び出し
- HouseDiffusionモデルAPIの呼び出し
- FreeCAD APIの呼び出し

#### 5.4 ユーザーエクスペリエンス向上

- 処理状況の進捗表示
- エラーメッセージの改善
- ヘルプテキストとツールチップの追加
- レスポンシブデザインの改善

### テスト計画

1. 単体テスト：各UIコンポーネントの機能テスト
2. 統合テスト：エンドツーエンドのユーザーフローテスト
3. ユーザビリティテスト：実際のユーザーによる操作テスト

### 成功基準

- すべての新機能がUIから利用可能
- 処理時間とフィードバックの適切な表示
- エラー発生時の適切なフォールバック処理
- 直感的な操作性の実現

## 実装スケジュール

| 週 | YOLOアノテーション変換 | CP-SAT PoC | FreeCAD API | HouseDiffusion | Streamlit UI |
|----|----------------------|------------|------------|---------------|-------------|
| 1  | データ構造定義         | 基本モデル構築 | 基本構造実装   | モデル構造実装   | -            |
| 2  | 変換パイプライン実装    | 制約実装     | 壁・部屋作成機能 | データセット準備 | -            |
| 3  | グラフ構造変換         | ソルバー実装  | JSONからの変換 | 初期トレーニング | UI設計       |
| 4  | テストと最適化         | テストと最適化 | エクスポート機能 | 評価と改善     | コンポーネント実装 |
| 5  | -                    | -          | 2D図面生成   | -            | バックエンド連携 |
| 6  | -                    | -          | テストと最適化 | -            | テストと最適化  |

## リスクと対策

| リスク | 影響度 | 対策 |
|-------|-------|-----|
| FreeCADのインポートエラーが解消できない | 高 | Dockerコンテナでの実行環境の整備、代替ライブラリの検討 |
| CP-SATソルバーが現実的な時間で解を見つけられない | 中 | 問題の分割、ヒューリスティックの導入、制約の緩和 |
| HouseDiffusionモデルの学習が収束しない | 中 | モデル構造の単純化、データ拡張、事前学習モデルの活用 |
| YOLOアノテーションからの変換精度が低い | 中 | 後処理アルゴリズムの改善、手動修正インターフェースの提供 |
| Streamlit UIのパフォーマンスが低下 | 低 | コンポーネントの最適化、非同期処理の導入、キャッシュの活用 |

## 結論

本実装計画は、House Design AIプロジェクトの次期開発フェーズにおける5つの主要コンポーネントの実装詳細を提供しています。YOLOアノテーション変換システム、CP-SAT最小PoC、FreeCAD API、HouseDiffusion、Streamlit UIの各コンポーネントが連携することで、土地の地図から自動的にCAD図面を生成するという全体目標の実現に近づきます。

実装は段階的に進め、各コンポーネントの基本機能を早期に実装し、その後機能拡張と最適化を行います。また、定期的なテストと評価を通じて、品質と性能を確保します。

最終的には、ユーザーが簡単に操作できるインターフェースを通じて、建築基準法に準拠した高品質な間取り図と3Dモデルを生成できるシステムを目指します。
