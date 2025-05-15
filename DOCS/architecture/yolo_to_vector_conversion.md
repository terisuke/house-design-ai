# YOLOアノテーション → ベクター/グラフJSON変換システム

## 概要

YOLOアノテーション → ベクター/グラフJSON変換システムは、YOLOモデルによって生成されたアノテーションデータを、間取り図生成に必要なベクターデータおよびグラフ構造のJSONに変換するシステムです。このシステムは、最終アーキテクチャの重要なコンポーネントとして、データ準備段階で使用されます。

## 主要機能

1. **YOLOアノテーションの読み込み**: YOLOフォーマットのアノテーションファイルを読み込み、解析します。
2. **部屋ポリゴンの生成**: アノテーションデータから各部屋のShapelyポリゴンを生成します。
3. **階情報の抽出**: 各部屋がどの階に属するかを判定します。
4. **隣接関係の抽出**: ポリゴン間の隣接関係を抽出し、NetworkXグラフとして表現します。
5. **910mmグリッドスナップ準備**: 建築基準に合わせたグリッドスナップのためのパラメータを計算します。
6. **方位情報の抽出**: 建物の方位情報を特定します。
7. **JSON形式でのシリアライズ**: データをJSON形式でシリアライズして保存します。
8. **視覚化**: 変換結果を視覚化して検証します。

## データ構造

変換後のJSONには以下の情報が含まれます：

- **メタデータ**: ソースファイル、画像サイズ、縮尺情報、グリッドサイズ、方位情報
- **敷地**: 敷地境界ポリゴン (WKT形式)
- **建物**: 建物外形ポリゴン (WKT形式)
- **部屋**: ID、ラベル、タイプID、階情報、ポリゴン形状(WKT形式)、バウンディングボックス
- **隣接グラフ**: NetworkXグラフのJSON表現（ノード:部屋ID、エッジ:隣接関係）

## 変換パイプライン

1. **YOLOアノテーション → バウンディングボックス**:
   - YOLOの検出結果（クラスID、中心座標、幅、高さ）から各部屋のバウンディングボックスを取得

2. **バウンディングボックス → Shapelyポリゴン**:
   - バウンディングボックスをShapelyポリゴン形式に変換
   - 必要に応じてポリゴンの形状を調整（L字型などの非矩形形状に対応）

3. **階情報の判定**:
   - アノテーションに階情報（1F/2F）がある場合はそれを使用
   - ない場合は建物内でのY座標位置から階情報を推定

4. **隣接グラフの構築**:
   - 部屋ポリゴン間の接触関係を検出
   - 接触長が一定以上の場合に隣接関係（エッジ）を設定
   - NetworkXグラフオブジェクトとして表現

5. **910mmグリッドへのスナップ準備**:
   - 実際の縮尺からグリッドサイズ（ピクセル単位）を計算
   - スナップ処理のためのパラメータ設定

6. **結果の構造化とJSON出力**:
   - 敷地境界、建物外形、部屋情報、隣接グラフを含む構造化データを生成
   - JSON形式で保存

## 実装サンプル

```python
import os
import json
import numpy as np
import pandas as pd
import networkx as nx
from shapely.geometry import Polygon, box, Point, LineString
import matplotlib.pyplot as plt
from collections import defaultdict

def convert_yolo_to_vector_graph(yolo_annotation_path, output_path, plot=False):
    """
    YOLOアノテーションファイルをベクターデータとグラフ構造に変換
    
    Args:
        yolo_annotation_path: YOLOアノテーションファイルのパス
        output_path: 出力JSONファイルのパス
        plot: 変換結果を可視化するかどうか
    
    Returns:
        変換結果の辞書
    """
    # YOLOラベルと部屋タイプのマッピング
    room_label_map = {
        0: 'LDK',
        1: 'BR1',
        2: 'BR2',
        3: 'BR3',
        4: 'WC',
        5: 'UB',
        6: 'CO',  # 廊下
        7: 'UP',  # 上り階段
        8: 'DN',  # 下り階段
        9: 'HOUSE', # 建物外形
        10: 'SITE'  # 敷地
    }
    
    # YOLOアノテーションの読み込み
    with open(yolo_annotation_path, 'r') as f:
        lines = f.readlines()
    
    # 画像サイズの取得（元画像の寸法が必要）
    image_path = yolo_annotation_path.replace('.txt', '.jpg')
    if os.path.exists(image_path):
        from PIL import Image
        img = Image.open(image_path)
        img_width, img_height = img.size
    else:
        # 画像がない場合はデフォルト値
        img_width, img_height = 1000, 1000
        print(f"Warning: Image {image_path} not found. Using default size.")
    
    # アノテーションをパース
    annotations = []
    for line in lines:
        parts = line.strip().split(' ')
        class_id = int(parts[0])
        x_center = float(parts[1]) * img_width
        y_center = float(parts[2]) * img_height
        width = float(parts[3]) * img_width
        height = float(parts[4]) * img_height
        
        # YOLOの中心座標＋幅高さから左上と右下の座標を計算
        x_min = x_center - width / 2
        y_min = y_center - height / 2
        x_max = x_center + width / 2
        y_max = y_center + height / 2
        
        # 部屋ラベルを取得
        label = room_label_map.get(class_id, f"unknown_{class_id}")
        
        annotations.append({
            'label': label,
            'class_id': class_id,
            'bbox': [x_min, y_min, x_max, y_max],
            'polygon': None,  # 後で設定
            'floor': None     # 後で設定
        })
    
    # 建物外形と敷地のポリゴンを特定
    house_poly = None
    site_poly = None
    
    for ann in annotations:
        if ann['label'] == 'HOUSE':
            x_min, y_min, x_max, y_max = ann['bbox']
            house_poly = box(x_min, y_min, x_max, y_max)
        elif ann['label'] == 'SITE':
            x_min, y_min, x_max, y_max = ann['bbox']
            site_poly = box(x_min, y_min, x_max, y_max)
    
    # 敷地境界がない場合は画像サイズから生成
    if site_poly is None:
        site_poly = box(0, 0, img_width, img_height)
        print("Warning: No SITE annotation found, using image bounds instead.")
    
    # 各部屋のポリゴンを生成
    rooms = []
    for ann in annotations:
        if ann['label'] not in ['HOUSE', 'SITE']:
            x_min, y_min, x_max, y_max = ann['bbox']
            polygon = box(x_min, y_min, x_max, y_max)
            
            # 部屋がどの階にあるか判定（あれば1F/2Fラベルから取得）
            floor = 'unknown'
            for floor_ann in annotations:
                if floor_ann['label'] in ['1F', '2F']:
                    floor_x_min, floor_y_min, floor_x_max, floor_y_max = floor_ann['bbox']
                    floor_poly = box(floor_x_min, floor_y_min, floor_x_max, floor_y_max)
                    
                    if polygon.intersects(floor_poly) and \
                       polygon.intersection(floor_poly).area / polygon.area > 0.5:
                        floor = floor_ann['label']
                        break
            
            # 階の情報がなければ、HOUSE内部のY座標から推定（下半分＝1F、上半分＝2F）
            if floor == 'unknown' and house_poly:
                y_relative = (y_center - house_poly.bounds[1]) / (house_poly.bounds[3] - house_poly.bounds[1])
                floor = '1F' if y_relative < 0.5 else '2F'
            
            ann['polygon'] = polygon
            ann['floor'] = floor
            
            rooms.append({
                'id': len(rooms),
                'label': ann['label'],
                'type_id': ann['class_id'],
                'floor': floor,
                'polygon': polygon.wkt,  # Well-Known Text形式で保存
                'bbox': ann['bbox']
            })
    
    # 隣接グラフの構築
    G = nx.Graph()
    
    # ノードの追加
    for room in rooms:
        G.add_node(room['id'], 
                  label=room['label'], 
                  type_id=room['type_id'], 
                  floor=room['floor'])
    
    # エッジの追加（隣接関係の検出）
    for i, room1 in enumerate(rooms):
        poly1 = Polygon.from_wkt(room1['polygon'])
        for j, room2 in enumerate(rooms):
            if i != j:
                poly2 = Polygon.from_wkt(room2['polygon'])
                
                # 隣接判定: 2つの部屋が接している場合
                if poly1.touches(poly2) or poly1.buffer(1).intersects(poly2):
                    # 隣接線の長さを計算
                    try:
                        # 境界の交差を取得
                        intersection = poly1.buffer(0.1).boundary.intersection(poly2.buffer(0.1).boundary)
                        
                        # 交差が線分である場合、その長さを計算
                        if isinstance(intersection, LineString):
                            edge_length = intersection.length
                        else:
                            # 複数の線分などの場合は合計長を計算
                            edge_length = sum(part.length for part in intersection.geoms if hasattr(part, 'length'))
                        
                        # 最小接続長より大きければ隣接と判定（小さな接触は無視）
                        min_contact_length = 10.0  # 最小接触長（ピクセル）
                        if edge_length > min_contact_length:
                            G.add_edge(room1['id'], room2['id'], weight=edge_length)
                            
                    except Exception as e:
                        print(f"Warning: Error calculating intersection between {room1['label']} and {room2['label']}: {e}")
    
    # 910mmグリッドへのスナップ準備
    # 実際の縮尺は図面によって異なるため、ここでは仮の変換係数を使用
    # 本番実装では、図面の実寸情報から変換係数を算出する必要がある
    def calculate_pixels_per_meter(drawing_data):
        """実際の図面の実世界寸法からスケーリング係数を動的に計算します"""
        # 図面データからスケールを抽出
        real_width_meters = drawing_data.get("width_meters", 20.0)  # デフォルト値
        image_width_pixels = drawing_data.get("width_pixels", 1000)  # デフォルト値
        
        return image_width_pixels / real_width_meters
    
    # 固定値 '50' の代わりに関数からの出力を使用
    pixels_per_meter = calculate_pixels_per_meter(drawing_data)
    grid_size_mm = 910     # グリッドサイズ（mm）
    grid_size_pixels = grid_size_mm / 1000 * pixels_per_meter
    
    # 結果の辞書構築
    result = {
        'metadata': {
            'source_file': os.path.basename(yolo_annotation_path),
            'image_width': img_width,
            'image_height': img_height,
            'pixels_per_meter': pixels_per_meter,
            'grid_size_mm': grid_size_mm,
            'grid_size_pixels': grid_size_pixels
        },
        'site': site_poly.wkt if site_poly else None,
        'house': house_poly.wkt if house_poly else None,
        'rooms': rooms,
        'adjacency_graph': nx.node_link_data(G)
    }
    
    # 方位情報の抽出（北向きマークなどが検出されていれば）
    north_indicator = next((ann for ann in annotations if ann['label'] == 'NORTH'), None)
    if north_indicator:
        # 北方向の角度を計算（x軸からの反時計回り、ラジアン）
        # 実際の実装では北方向マークの形状から方向を計算
        result['metadata']['north_angle'] = 0.0  # デフォルトは0（上が北）
    else:
        # デフォルトは上が北
        result['metadata']['north_angle'] = 0.0
    
    # JSONとして保存
    with open(output_path, 'w') as f:
        # Shapely objectは直接JSONにシリアライズできないため、
        # WKT (Well-Known Text)形式に変換して保存
        json.dump(result, f, indent=2)
    
    # 可視化（オプション）
    if plot:
        plt.figure(figsize=(10, 10))
        
        # 敷地の描画
        if site_poly:
            x, y = site_poly.exterior.xy
            plt.plot(x, y, 'k-', linewidth=2)
        
        # 建物外形の描画
        if house_poly:
            x, y = house_poly.exterior.xy
            plt.plot(x, y, 'r-', linewidth=1.5)
        
        # 部屋の描画
        colors = plt.cm.tab10(np.linspace(0, 1, len(rooms)))
        for i, room in enumerate(rooms):
            poly = Polygon.from_wkt(room['polygon'])
            x, y = poly.exterior.xy
            plt.fill(x, y, alpha=0.5, fc=colors[i])
            plt.plot(x, y, 'k-', linewidth=1)
            
            # 部屋ラベルの描画
            centroid = poly.centroid
            plt.text(centroid.x, centroid.y, room['label'], 
                    ha='center', va='center', fontsize=10)
        
        # グラフの描画
        pos = {room['id']: Polygon.from_wkt(room['polygon']).centroid.coords[0] for room in rooms}
        nx.draw_networkx_edges(G, pos, width=2, alpha=0.7)
        
        plt.axis('equal')
        plt.title('Floor Plan: Rooms and Adjacency Graph')
        plt.grid(True, alpha=0.3)
        plt.savefig(output_path.replace('.json', '.png'))
        plt.close()
    
    print(f"Conversion complete. Output saved to {output_path}")
    return result

def snap_to_grid(geometry, grid_size_pixels):
    """
    ジオメトリを指定されたグリッドサイズにスナップする
    
    Args:
        geometry: スナップするShapely Polygon/Point
        grid_size_pixels: グリッドサイズ（ピクセル単位）
    
    Returns:
        スナップされたジオメトリ
    """
    if hasattr(geometry, 'exterior'):
        # Polygon の場合
        coords = list(geometry.exterior.coords)
        snapped_coords = [(round(x / grid_size_pixels) * grid_size_pixels, 
                           round(y / grid_size_pixels) * grid_size_pixels) 
                         for x, y in coords]
        return Polygon(snapped_coords)
    elif hasattr(geometry, 'coords'):
        # Point/LineString の場合
        coords = list(geometry.coords)
        snapped_coords = [(round(x / grid_size_pixels) * grid_size_pixels, 
                           round(y / grid_size_pixels) * grid_size_pixels) 
                         for x, y in coords]
        if len(snapped_coords) == 1:
            return Point(snapped_coords[0])
        else:
            return LineString(snapped_coords)
    else:
        # その他の場合は変更なし
        return geometry

def process_dataset(input_dir, output_dir):
    """
    指定ディレクトリ内のすべてのYOLOアノテーションファイルを処理
    
    Args:
        input_dir: 入力YOLOアノテーションのディレクトリ
        output_dir: 出力JSONのディレクトリ
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 入力ディレクトリ内のすべてのtxtファイルを取得
    annotation_files = [f for f in os.listdir(input_dir) if f.endswith('.txt')]
    
    for i, file in enumerate(annotation_files):
        input_path = os.path.join(input_dir, file)
        output_path = os.path.join(output_dir, file.replace('.txt', '.json'))
        
        print(f"Processing file {i+1}/{len(annotation_files)}: {file}")
        convert_yolo_to_vector_graph(input_path, output_path, plot=True)
    
    print(f"All {len(annotation_files)} files processed successfully!")
```

## 主要機能の説明

### 1. YOLOアノテーションの解析

YOLOは中心座標と幅/高さで矩形を定義します。これを左上と右下の座標（バウンディングボックス）に変換し、さらにShapely Polygonオブジェクトに変換します。

```python
# YOLOの中心座標＋幅高さから左上と右下の座標を計算
x_min = x_center - width / 2
y_min = y_center - height / 2
x_max = x_center + width / 2
y_max = y_center + height / 2

# 矩形ポリゴンを生成
polygon = box(x_min, y_min, x_max, y_max)
```

### 2. 階情報の抽出

各部屋がどの階に属するかを判定します。アノテーションに1F/2Fのラベルがある場合はそれを利用し、ない場合は建物内でのY座標から推定します。

```python
# 階の情報がなければ、HOUSE内部のY座標から推定（下半分＝1F、上半分＝2F）
if floor == 'unknown' and house_poly:
    y_relative = (y_center - house_poly.bounds[1]) / (house_poly.bounds[3] - house_poly.bounds[1])
    floor = '1F' if y_relative < 0.5 else '2F'
```

### 3. 隣接グラフの構築

部屋間の隣接関係をNetworkXグラフとして構築します。二つのポリゴンが接しているか、または非常に近い場合、隣接していると判定します。

```python
# 隣接判定: 2つの部屋が接している場合
if poly1.touches(poly2) or poly1.buffer(1).intersects(poly2):
    # 隣接線の長さを計算
    intersection = poly1.buffer(0.1).boundary.intersection(poly2.buffer(0.1).boundary)
    
    # 交差が線分である場合、その長さを計算
    if isinstance(intersection, LineString):
        edge_length = intersection.length
    else:
        # 複数の線分などの場合は合計長を計算
        edge_length = sum(part.length for part in intersection.geoms if hasattr(part, 'length'))
    
    # 最小接続長より大きければ隣接と判定
    if edge_length > min_contact_length:
        G.add_edge(room1['id'], room2['id'], weight=edge_length)
```

### 4. 910mmグリッドへのスナップ

建築で標準的な910mmグリッドに全ての座標をスナップさせる機能を提供します。これにより、生成される間取りは実際の建築基準に合致しやすくなります。

```python
def snap_to_grid(geometry, grid_size_pixels):
    # ジオメトリをグリッドにスナップ
    coords = list(geometry.exterior.coords)
    snapped_coords = [(round(x / grid_size_pixels) * grid_size_pixels, 
                       round(y / grid_size_pixels) * grid_size_pixels) 
                     for x, y in coords]
    return Polygon(snapped_coords)
```

## 出力データ形式

処理結果はJSON形式で保存され、以下の情報を含みます：

1. **メタデータ**：
   - 元画像のサイズ
   - ピクセルと実寸の変換係数
   - グリッドサイズ情報
   - 方位情報

2. **敷地と建物**：
   - 敷地境界ポリゴン
   - 建物外形ポリゴン

3. **部屋情報**：
   - 部屋ラベル
   - 部屋タイプID
   - 階情報
   - ポリゴン形状（WKT形式）
   - バウンディングボックス

4. **隣接グラフ**：
   - NetworkXグラフのJSON表現
   - ノード：部屋ID、ラベル、タイプ、階
   - エッジ：隣接関係、接触長さ

## 使用例

```python
# 単一ファイルの処理
input_path = "data/raw/floor_plan_001.txt"
output_path = "data/processed/floor_plan_001.json"
result = convert_yolo_to_vector_graph(input_path, output_path, plot=True)

# データセット全体の処理
input_dir = "data/raw"
output_dir = "data/processed"
process_dataset(input_dir, output_dir)
```

## 注意点と改善方針

1. **正確な縮尺**：
   現在は仮の変換係数を使用していますが、実際には図面から正確な縮尺情報を抽出する必要があります。

2. **非矩形の部屋**：
   現在はすべての部屋を矩形として扱っていますが、L字型などの複雑な形状をサポートするには、矩形の結合や多角形への変換処理が必要です。

3. **方位情報**：
   現在は単純に「上=北」としていますが、実際には図面の北向きマークから正確な方位を計算する必要があります。

4. **隣接判定の精度**：
   現在の隣接判定は単純な交差テストに基づいていますが、より高度な「壁を共有している」などの判定ロジックを実装することで精度を向上できます。

## 実装状況

- ✅ データ構造の定義
- ✅ YOLOアノテーションの読み込み
- ✅ Shapelyポリゴンへの変換
- ✅ 階情報の抽出
- ✅ 隣接関係の抽出
- ✅ 910mmグリッドスナップ準備
- ✅ JSON形式でのシリアライズ
- ✅ 視覚化機能

## 今後の改善点

- 正確な縮尺情報の抽出
- 非矩形形状への対応拡充
- 方位情報の正確な抽出
- 隣接関係判定の精度向上
- パフォーマンスの最適化
- 大規模データセット処理の効率化
