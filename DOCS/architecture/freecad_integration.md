# FreeCAD 連携実装

このドキュメントでは、間取り生成システムの「ポストプロセス／出力」段階で使用するFreeCAD連携の実装について説明します。CP-SATソルバーによって生成および最適化された間取りを、3Dモデルとして出力するための機能を提供します。

## 連携の目的と概要

FreeCAD連携には以下の主要な目的があります：

1. **3Dモデル化**: 平面的な間取り情報を立体的な3Dモデルに変換する
2. **構造的な表現**: 壁、床、天井などの建築要素を正確に表現する
3. **IFC出力**: 建築業界標準のIFCフォーマットでエクスポートする
4. **視覚化**: 施主や設計者が直感的に理解できる3D表示を提供する

この連携により、生成された間取りを実際の建築プロセスや他のCADソフトウェアと統合することが可能になります。

## 実装サンプル

```python
import os
import json
import FreeCAD
import Part
import Draft
import Arch
import ImportIFC
import exportIFC
from FreeCAD import Vector
from shapely.geometry import Polygon, mapping
from math import pi

def export_to_freecad(floor_plan_json, output_path, wall_height=2400, wall_thickness=100):
    """
    間取りJSONをFreeCADモデルとして出力
    
    Args:
        floor_plan_json: 間取りデータを含むJSONファイルのパス
        output_path: 出力FCStdファイルのパス
        wall_height: 壁の高さ (mm)
        wall_thickness: 壁の厚さ (mm)
    
    Returns:
        bool: 変換が成功した場合はTrue、失敗した場合はFalse
    
    Raises:
        ImportError: FreeCADのインポートに失敗した場合
        ValueError: 入力JSONが無効な場合
        IOError: ファイルの読み書きに失敗した場合
    """
    # JSONの読み込み
    with open(floor_plan_json, 'r') as f:
        data = json.load(f)
    
    # 必要なデータを抽出
    rooms = data['rooms']
    metadata = data.get('metadata', {})
    adjacency_graph = data.get('adjacency_graph', {})
    
    # mm単位に変換する係数
    # metadata内にpixels_per_meterがあれば使用
    pixels_per_meter = metadata.get('pixels_per_meter', 50)
    pixel_to_mm = 1000 / pixels_per_meter
    
    # FreeCADドキュメントを作成
    doc = FreeCAD.newDocument("FloorPlan")
    
    # 階ごとにレイヤーを作成
    floors = set(room['floor'] for room in rooms)
    floor_heights = {
        '1F': 0,
        '2F': wall_height + 200,  # 2階は1階の壁高さ + 床厚 (mm)
    }
    
    # 各部屋の処理
    room_objects = {}
    for room in rooms:
        # 部屋データの取得
        room_id = room['id']
        label = room['label']
        floor = room['floor']
        polygon_wkt = room['polygon']
        
        # Shapelyポリゴンを解析
        room_poly = Polygon.from_wkt(polygon_wkt)
        
        # 階の高さオフセットを取得
        z_offset = floor_heights.get(floor, 0)
        
        # FreeCADオブジェクトを作成
        create_room_in_freecad(doc, room_poly, label, z_offset, wall_height, wall_thickness, pixel_to_mm)
        
        # 出力フォーマットに応じた追加処理
        if output_path.endswith('.ifc'):
            # IFC属性を設定
            obj = doc.getObject(label)
            if obj:
                ifc_type = get_ifc_type_for_room(label)
                obj.IfcType = ifc_type
    
    # ドキュメントの保存
    doc.recompute()
    
    if output_path.endswith('.FCStd'):
        doc.saveAs(output_path)
        print(f"FreeCAD file saved: {output_path}")
    elif output_path.endswith('.ifc'):
        # IFCとして出力
        export_ifc(doc, output_path)
        print(f"IFC file exported: {output_path}")
    elif output_path.endswith('.svg'):
        # SVGとして出力（2D図面）
        export_svg(doc, output_path)
        print(f"SVG file exported: {output_path}")
    
    return doc

def create_room_in_freecad(doc, room_poly, label, z_offset, wall_height, wall_thickness, pixel_to_mm):
    """
    Shapelyポリゴンから部屋のFreeCADオブジェクトを作成
    
    Args:
        doc: FreeCADドキュメント
        room_poly: 部屋のShapelyポリゴン
        label: 部屋ラベル
        z_offset: Z軸オフセット (高さ) (mm)
        wall_height: 壁の高さ (mm)
        wall_thickness: 壁の厚さ (mm)
        pixel_to_mm: ピクセルからmmへの変換係数
    
    Returns:
        作成された部屋オブジェクト
    """
    # 部屋タイプに基づく色の定義
    room_colors = {
        'LDK': (0.8, 0.9, 1.0),  # 水色
        'BR': (1.0, 0.8, 0.8),   # ピンク
        'WC': (0.9, 0.9, 0.9),   # グレー
        'UB': (0.9, 0.8, 1.0),   # 薄紫
        'CO': (1.0, 1.0, 0.8),   # 薄黄色
        'UP': (1.0, 0.7, 0.7),   # 薄赤（上り階段）
        'DN': (0.7, 0.7, 1.0)    # 薄青（下り階段）
    }
    
    # ポリゴンの座標をmm単位に変換
    coords = list(room_poly.exterior.coords)
    points_mm = [(x * pixel_to_mm, y * pixel_to_mm, z_offset) for x, y in coords[:-1]]  # 最後の点は最初と同じなので除外
    
    # FreeCADのポリラインを作成
    polyline = Draft.make_wire(points_mm, closed=True, face=True)
    polyline.Label = label
    
    # 壁の押し出し
    # 内側に壁の厚さ分だけオフセットしたポリゴンを作成
    inner_poly = room_poly.buffer(-wall_thickness / pixel_to_mm)
    
    # 内側ポリゴンの座標をmm単位に変換
    inner_coords = list(inner_poly.exterior.coords)
    inner_points_mm = [(x * pixel_to_mm, y * pixel_to_mm, z_offset) for x, y in inner_coords[:-1]]
    
    # 内側ポリラインを作成
    inner_polyline = Draft.make_wire(inner_points_mm, closed=True, face=True)
    inner_polyline.Label = f"{label}_inner"
    
    # 壁と床を作成
    extrusion = Arch.makeWall(polyline, height=wall_height, width=wall_thickness, align="Center")
    extrusion.Label = f"{label}_wall"
    
    # 床を作成
    floor = Arch.makeFloor([inner_polyline])
    floor.Label = f"{label}_floor"
    floor.Height = 100  # 床の厚さ (mm)
    
    # 色を設定
    color = None
    for key, value in room_colors.items():
        if key in label:
            color = value
            break
    
    if color:
        extrusion.ViewObject.ShapeColor = color
        floor.ViewObject.ShapeColor = tuple(c * 0.8 for c in color)  # 床は少し暗く
    
    # 部屋空間を作成（IfcSpace用）
    space = Arch.makeSpace([inner_polyline])
    space.Label = label
    space.Height = wall_height - 100  # 天井までの高さ
    
    return space

def get_ifc_type_for_room(label):
    """
    部屋ラベルに基づいてIFCタイプを取得
    
    Args:
        label: 部屋ラベル
    
    Returns:
        IFCタイプ文字列
    """
    ifc_mapping = {
        'LDK': 'IfcSpace',
        'BR': 'IfcSpace',
        'WC': 'IfcSpace',
        'UB': 'IfcSpace',
        'CO': 'IfcSpace',
        'UP': 'IfcStair',
        'DN': 'IfcStair'
    }
    
    for key, value in ifc_mapping.items():
        if key in label:
            return value
    
    return 'IfcSpace'  # デフォルト

def export_ifc(doc, output_path):
    """
    FreeCADドキュメントをIFCとしてエクスポート
    
    Args:
        doc: FreeCADドキュメント
        output_path: 出力IFCファイルのパス
    """
    # IFCエクスポート設定
    prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Arch")
    prefs.SetBool("ExportIFCObjects", True)
    prefs.SetBool("ExportIFC2DElements", False)
    
    # エクスポート実行
    exportIFC.export(doc.Objects, output_path)

def export_svg(doc, output_path):
    """
    FreeCADドキュメントをSVGとしてエクスポート（2D平面図）
    
    Args:
        doc: FreeCADドキュメント
        output_path: 出力SVGファイルのパス
    """
    import importSVG
    
    # ビューの設定
    page = FreeCAD.activeDocument().addObject('TechDraw::DrawPage', 'Page')
    template = FreeCAD.activeDocument().addObject('TechDraw::DrawSVGTemplate', 'Template')
    template.Template = FreeCAD.getResourceDir() + 'Mod/TechDraw/Templates/A3_Landscape_blank.svg'
    page.Template = template
    
    # 平面図の作成
    view = FreeCAD.activeDocument().addObject('TechDraw::DrawViewPart', 'View')
    page.addView(view)
    view.Source = doc.Objects
    view.Direction = Vector(0, 0, 1)  # 上からの視点
    
    # SVGとしてエクスポート
    importSVG.export([page], output_path)
```

## 階段の処理例

階段は特別な処理が必要な要素です。以下は階段を作成する追加のコード例です：

```python
def create_stair_in_freecad(doc, stair_poly, label, z_offset, floor_height, pixel_to_mm):
    """
    階段のFreeCADオブジェクトを作成
    
    Args:
        doc: FreeCADドキュメント
        stair_poly: 階段のShapelyポリゴン
        label: 階段ラベル
        z_offset: Z軸オフセット (高さ) (mm)
        floor_height: 階高 (mm)
        pixel_to_mm: ピクセルからmmへの変換係数
    
    Returns:
        作成された階段オブジェクト
    """
    # ポリゴンの座標をmm単位に変換
    coords = list(stair_poly.exterior.coords)
    points_mm = [(x * pixel_to_mm, y * pixel_to_mm, z_offset) for x, y in coords[:-1]]
    
    # FreeCADのポリラインを作成
    polyline = Draft.make_wire(points_mm, closed=True, face=True)
    polyline.Label = f"{label}_outline"
    
    # 階段の各種パラメータを計算
    stair_length = stair_poly.bounds[2] - stair_poly.bounds[0]
    stair_width = stair_poly.bounds[3] - stair_poly.bounds[1]
    
    # mm単位に変換
    stair_length_mm = stair_length * pixel_to_mm
    stair_width_mm = stair_width * pixel_to_mm
    
    # 階段の段数を計算（階高を踏面高さで割る）
    riser_height = 170  # 蹴上高さ (mm)
    tread_depth = 250   # 踏面奥行 (mm)
    
    num_steps = int(floor_height / riser_height)
    
    # 階段オブジェクトの作成
    stair = Arch.makeStairs(
        baseobj=polyline,
        length=stair_length_mm,
        width=stair_width_mm,
        height=floor_height,
        steps=num_steps
    )
    
    stair.Label = label
    
    # 上り/下りで色を変える
    if 'UP' in label:
        stair.ViewObject.ShapeColor = (1.0, 0.7, 0.7)  # 薄赤
    elif 'DN' in label:
        stair.ViewObject.ShapeColor = (0.7, 0.7, 1.0)  # 薄青
    
    return stair
```

## 窓とドアの追加例

間取りデータから窓とドアを検出し、追加するコード例：

```python
def add_windows_and_doors(doc, room_objects, adjacency_graph, wall_height, pixel_to_mm):
    """
    部屋間の接続関係から窓とドアを追加
    
    Args:
        doc: FreeCADドキュメント
        room_objects: 部屋オブジェクトの辞書 {room_id: obj}
        adjacency_graph: 隣接グラフデータ
        wall_height: 壁の高さ (mm)
        pixel_to_mm: ピクセルからmmへの変換係数
    """
    # グラフからリンクを抽出
    links = adjacency_graph.get('links', [])
    
    for link in links:
        source_id = link.get('source')
        target_id = link.get('target')
        
        if source_id in room_objects and target_id in room_objects:
            source_obj = room_objects[source_id]
            target_obj = room_objects[target_id]
            
            # 部屋タイプを取得
            source_label = source_obj.Label
            target_label = target_obj.Label
            
            # 接続部分を計算
            source_wall = doc.getObject(f"{source_label}_wall")
            target_wall = doc.getObject(f"{target_label}_wall")
            
            if source_wall and target_wall:
                # 2つの壁の交差部分を計算
                intersection = source_wall.Shape.common(target_wall.Shape)
                
                if not intersection.isNull():
                    # 交差部分の中心を計算
                    center = intersection.CenterOfMass
                    
                    # ドアか窓かを判断
                    # LDKと廊下の間はドア、その他はケースバイケース
                    is_door = False
                    if ('LDK' in source_label and 'CO' in target_label) or \
                       ('LDK' in target_label and 'CO' in source_label) or \
                       ('BR' in source_label and 'CO' in target_label) or \
                       ('BR' in target_label and 'CO' in source_label):
                        is_door = True
                    
                    # 外部に面する壁には窓を設置
                    is_external = False
                    if source_id == 'exterior' or target_id == 'exterior':
                        is_external = True
                    
                    # オブジェクト作成
                    if is_door:
                        create_door(doc, center, wall_height, pixel_to_mm)
                    elif is_external:
                        create_window(doc, center, wall_height, pixel_to_mm)

def create_door(doc, position, wall_height, pixel_to_mm):
    """ドアを作成"""
    door_width = 800  # ドア幅 (mm)
    door_height = 2000  # ドア高さ (mm)
    
    # ドアの基準面を作成
    x, y, z = position.x, position.y, position.z
    points = [
        Vector(x - door_width/2, y, z),
        Vector(x + door_width/2, y, z),
        Vector(x + door_width/2, y, z + door_height),
        Vector(x - door_width/2, y, z + door_height)
    ]
    
    # ワイヤーを作成
    wire = Draft.makeWire(points, closed=True, face=True)
    
    # ドアオブジェクトを作成
    door = Arch.makeDoor(wire)
    door.Normal = Vector(0, 1, 0)  # ドアの向き
    
    return door

def create_window(doc, position, wall_height, pixel_to_mm):
    """窓を作成"""
    window_width = 1200  # 窓幅 (mm)
    window_height = 1200  # 窓高さ (mm)
    sill_height = 900    # 窓台高さ (mm)
    
    # 窓の基準面を作成
    x, y, z = position.x, position.y, position.z
    points = [
        Vector(x - window_width/2, y, z + sill_height),
        Vector(x + window_width/2, y, z + sill_height),
        Vector(x + window_width/2, y, z + sill_height + window_height),
        Vector(x - window_width/2, y, z + sill_height + window_height)
    ]
    
    # ワイヤーを作成
    wire = Draft.makeWire(points, closed=True, face=True)
    
    # 窓オブジェクトを作成
    window = Arch.makeWindow(wire)
    window.Normal = Vector(0, 1, 0)  # 窓の向き
    
    return window
```

## CP-SATソルバー出力とFreeCAD連携の例

以下は、CP-SATソルバーの出力をFreeCADモデルに変換する完全な例です：

```python
def cpsat_to_freecad(cpsat_output_json, output_path):
    """
    CP-SATソルバーの出力をFreeCADモデルに変換
    
    Args:
        cpsat_output_json: CP-SATソルバーの出力JSONファイルパス
        output_path: 出力FCStdファイルパス
    """
    # JSONを読み込む
    with open(cpsat_output_json, 'r') as f:
        data = json.load(f)
    
    # CP-SAT出力から部屋データを抽出
    rooms = []
    wall_thickness = 120  # mm
    
    for room_id, room_data in data['rooms'].items():
        # 91cmグリッド座標をメートルに変換
        x1 = room_data['x'] * 0.91
        y1 = room_data['y'] * 0.91
        x2 = x1 + room_data['w'] * 0.91
        y2 = y1 + room_data['h'] * 0.91
        
        # 部屋ラベルを取得
        label = room_data.get('label', f"Room_{room_id}")
        floor = room_data.get('floor', '1F')
        
        # 四角形ポリゴンを作成
        polygon = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
        
        rooms.append({
            'id': room_id,
            'label': label,
            'polygon': polygon.wkt,
            'floor': floor
        })
    
    # 隣接関係の取得
    adjacency_graph = data.get('adjacency_graph', {'nodes': [], 'links': []})
    
    # FreeCADモデルを生成
    doc = export_to_freecad_internal(rooms, adjacency_graph, output_path)
    
    return doc

def export_to_freecad_internal(rooms, adjacency_graph, output_path, 
                              wall_height=2900, wall_thickness=120):
    """内部実装：部屋データからFreeCADモデルを生成"""
    # FreeCADドキュメントを作成
    doc = FreeCAD.newDocument("FloorPlan")
    
    # 階ごとの高さ設定
    floor_heights = {
        '1F': 0,
        '2F': wall_height + 200,  # 2階は1階の壁高さ + 床厚
    }
    
    # 各部屋のオブジェクトを作成
    room_objects = {}
    for room in rooms:
        room_id = room['id']
        label = room['label']
        floor = room['floor']
        polygon_wkt = room['polygon']
        
        # Shapelyポリゴンを解析
        room_poly = Polygon.from_wkt(polygon_wkt)
        
        # 階の高さオフセットを取得
        z_offset = floor_heights.get(floor, 0)
        
        # 部屋の高さ設定（1階と2階で変える）
        height = 2900 if floor == '1F' else 2800  # mm
        
        # 部屋オブジェクトを作成
        room_obj = create_room_in_freecad(doc, room_poly, label, z_offset, height, wall_thickness, 1000)
        room_objects[room_id] = room_obj
    
    # 窓とドアを追加
    add_windows_and_doors(doc, room_objects, adjacency_graph, wall_height, 1000)
    
    # ドキュメントを保存
    doc.recompute()
    doc.saveAs(output_path)
    
    return doc
```

## 使用例

以下は、間取りデータからFreeCADモデルを生成し、各種形式でエクスポートする使用例です：

```python
# FreeCADモデル出力
json_path = "data/processed/floor_plan_001.json"

# FCStdとして保存
freecad_path = "output/floor_plan_001.FCStd"
doc = export_to_freecad(json_path, freecad_path)

# IFCとして出力
ifc_path = "output/floor_plan_001.ifc"
export_to_freecad(json_path, ifc_path)

# SVG（2D図面）として出力
svg_path = "output/floor_plan_001.svg"
export_to_freecad(json_path, svg_path)
```

## 910mmグリッドへのスナップ機能

建築標準の910mmグリッドに合わせてモデルを調整する機能：

```python
def snap_to_grid(doc, grid_size=910):
    """
    ドキュメント内のすべてのオブジェクトを指定されたグリッドサイズにスナップ
    
    Args:
        doc: FreeCADドキュメント
        grid_size: グリッドサイズ (mm)、デフォルトは910mm
    """
    for obj in doc.Objects:
        if hasattr(obj, "Placement"):
            # 現在の位置を取得
            pos = obj.Placement.Base
            
            # グリッドにスナップ
            new_x = round(pos.x / grid_size) * grid_size
            new_y = round(pos.y / grid_size) * grid_size
            new_z = round(pos.z / grid_size) * grid_size
            
            # 新しい位置を設定
            obj.Placement.Base = Vector(new_x, new_y, new_z)

def snap_polygon_to_grid(polygon, grid_size_mm):
    """
    Shapelyポリゴンをグリッドにスナップ
    
    Args:
        polygon: Shapelyポリゴン
        grid_size_mm: グリッドサイズ (mm)
        
    Returns:
        スナップされたポリゴン
    """
    # 座標を取得
    coords = list(polygon.exterior.coords)
    
    # 各点をグリッドにスナップ
    snapped_coords = []
    for x, y in coords:
        # mmに変換
        x_mm = x * 1000
        y_mm = y * 1000
        
        # グリッドにスナップ
        x_snapped = round(x_mm / grid_size_mm) * grid_size_mm
        y_snapped = round(y_mm / grid_size_mm) * grid_size_mm
        
        # メートルに戻す
        snapped_coords.append((x_snapped / 1000, y_snapped / 1000))
    
    # 新しいポリゴンを作成
    return Polygon(snapped_coords)
```

## FreeCAD APIの主な機能

FreeCADのAPIでは以下の主要機能が利用可能です：

1. **ジオメトリ操作**
   - 基本形状（点、線、面、立体）の作成
   - ブーリアン演算（和、差、積）
   - 変換（移動、回転、スケール）

2. **アーキテクチャ要素**
   - 壁、床、柱、屋根の作成
   - 窓、ドアの作成
   - 階段の作成

3. **ファイル入出力**
   - FCStd（FreeCADネイティブ形式）
   - STEP、IGES（CAD交換形式）
   - IFC（建築BIM形式）
   - STL、OBJ（3Dメッシュ形式）
   - SVG、DXF（2D図面形式）

## 注意点と最適化のポイント

1. **パフォーマンス最適化**
   - 複雑な形状は簡略化して処理速度を向上
   - 大量のオブジェクトはグループ化

2. **スケーリングと単位**
   - FreeCADはミリメートル単位で動作
   - 910mmグリッドとの整合性に注意

3. **IFCエクスポート**
   - 適切なIFCタイプを設定
   - 構造関係を正確に定義

## システム連携のアーキテクチャ

```
CP-SAT出力JSON
      ↓
FreeCAD変換モジュール
      ↓
┌───────────────┐
│ FCStd (3Dモデル)│
└───────────────┘
      ↓
┌─────────┬─────────┬────────┐
│IFC (BIM) │ SVG (2D) │ STL (3D)│
└─────────┴─────────┴────────┘
```

このFreeCAD連携により、間取り生成システムの出力を実際の建築設計や3D表示に活用することが可能になります。特に、910mmモジュールに対応した3Dモデル生成や、IFCフォーマットでの出力により、専門的な建築設計ソフトウェアとの連携も実現します。
