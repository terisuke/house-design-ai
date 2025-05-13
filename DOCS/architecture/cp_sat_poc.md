# CP-SAT最小PoC実装

このドキュメントでは、間取り生成システムの制約ソルバーレイヤーで使用するCP-SAT（Google OR-Tools）の最小限のProof of Concept実装を提供します。このPoCは、910mmグリッドに準拠した基本的な間取りを生成し、建築基準法の基本的な制約を満たすことを検証します。

## CP-SAT最小PoCの主な目的

1. 910mmグリッドへのスナップ機能の検証
2. 基本的な建築制約の定式化と充足性の確認
3. 部屋間の隣接関係や空間配置の制御能力の検証
4. 解の探索時間と最適化能力の評価

## 実装サンプル

```python
from ortools.sat.python import cp_model
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, box

def create_basic_floor_plan_poc():
    """
    CP-SAT最小PoC - 3LDKの基本間取りを910mmグリッドで生成
    """
    # 定数定義
    GRID = 910                  # mmグリッド
    MM_TO_M = 1000.0            # mm→m変換
    width_grids = 10            # 敷地幅（グリッド数）
    height_grids = 8            # 敷地高さ（グリッド数）
    
    # モデル定義
    model = cp_model.CpModel()
    
    # 部屋変数の定義（グリッド単位）
    rooms = {
        'LDK': {
            'x': model.NewIntVar(0, width_grids - 4, 'ldk_x'),  # 左上X座標
            'y': model.NewIntVar(0, height_grids - 4, 'ldk_y'), # 左上Y座標
            'w': model.NewIntVar(4, 6, 'ldk_w'),                # 幅（横）
            'h': model.NewIntVar(4, 6, 'ldk_h'),                # 高さ（縦）
            'min_area': 16,                                     # 最小面積（グリッド^2）
            'color': 'skyblue'                                  # 可視化用
        },
        'BR1': {
            'x': model.NewIntVar(0, width_grids - 3, 'br1_x'),
            'y': model.NewIntVar(0, height_grids - 3, 'br1_y'),
            'w': model.NewIntVar(3, 4, 'br1_w'),
            'h': model.NewIntVar(3, 4, 'br1_h'),
            'min_area': 9,
            'color': 'pink'
        },
        'BR2': {
            'x': model.NewIntVar(0, width_grids - 3, 'br2_x'),
            'y': model.NewIntVar(0, height_grids - 3, 'br2_y'),
            'w': model.NewIntVar(3, 4, 'br2_w'), 
            'h': model.NewIntVar(3, 4, 'br2_h'),
            'min_area': 9,
            'color': 'lightgreen'
        },
        'WC': {
            'x': model.NewIntVar(0, width_grids - 2, 'wc_x'),
            'y': model.NewIntVar(0, height_grids - 2, 'wc_y'),
            'w': model.NewIntVar(2, 2, 'wc_w'),
            'h': model.NewIntVar(2, 2, 'wc_h'),
            'min_area': 4,
            'color': 'lightgray'
        },
        'UB': {
            'x': model.NewIntVar(0, width_grids - 2, 'ub_x'),
            'y': model.NewIntVar(0, height_grids - 2, 'ub_y'),
            'w': model.NewIntVar(2, 3, 'ub_w'),
            'h': model.NewIntVar(2, 2, 'ub_h'),
            'min_area': 4,
            'color': 'lavender'
        }
    }
    
    # 制約1: 敷地内に収まる
    for room_name, room in rooms.items():
        model.Add(room['x'] + room['w'] <= width_grids)
        model.Add(room['y'] + room['h'] <= height_grids)
        
        # 最小面積制約
        model.Add(room['w'] * room['h'] >= room['min_area'])
    
    # 制約2: 部屋が重ならない
    for r1_name, r1 in rooms.items():
        for r2_name, r2 in rooms.items():
            if r1_name < r2_name:  # 各ペアを一度だけチェック
                # 部屋間の非重複は、少なくとも以下の条件のいずれかが成立:
                # r1が右、r1が左、r1が下、r1が上
                b_right = model.NewBoolVar(f'b_right_{r1_name}_{r2_name}')
                b_left = model.NewBoolVar(f'b_left_{r1_name}_{r2_name}')
                b_below = model.NewBoolVar(f'b_below_{r1_name}_{r2_name}')
                b_above = model.NewBoolVar(f'b_above_{r1_name}_{r2_name}')
                
                model.Add(r1['x'] >= r2['x'] + r2['w']).OnlyEnforceIf(b_right)
                model.Add(r1['x'] + r1['w'] <= r2['x']).OnlyEnforceIf(b_left)
                model.Add(r1['y'] >= r2['y'] + r2['h']).OnlyEnforceIf(b_below)
                model.Add(r1['y'] + r1['h'] <= r2['y']).OnlyEnforceIf(b_above)
                
                model.AddBoolOr([b_right, b_left, b_below, b_above])
    
    # 制約3: 特定の隣接関係
    # 例: トイレと風呂は隣接させる（一辺を共有）
    wc_ub_adjacent = []
    
    # WC右 = UB左
    b1 = model.NewBoolVar('wc_ub_adj1')
    model.Add(rooms['WC']['x'] + rooms['WC']['w'] == rooms['UB']['x']).OnlyEnforceIf(b1)
    # Y方向で重なり
    model.Add(rooms['WC']['y'] < rooms['UB']['y'] + rooms['UB']['h']).OnlyEnforceIf(b1)
    model.Add(rooms['WC']['y'] + rooms['WC']['h'] > rooms['UB']['y']).OnlyEnforceIf(b1)
    wc_ub_adjacent.append(b1)
    
    # WC左 = UB右
    b2 = model.NewBoolVar('wc_ub_adj2')
    model.Add(rooms['WC']['x'] == rooms['UB']['x'] + rooms['UB']['w']).OnlyEnforceIf(b2)
    model.Add(rooms['WC']['y'] < rooms['UB']['y'] + rooms['UB']['h']).OnlyEnforceIf(b2)
    model.Add(rooms['WC']['y'] + rooms['WC']['h'] > rooms['UB']['y']).OnlyEnforceIf(b2)
    wc_ub_adjacent.append(b2)
    
    # WC下 = UB上
    b3 = model.NewBoolVar('wc_ub_adj3')
    model.Add(rooms['WC']['y'] + rooms['WC']['h'] == rooms['UB']['y']).OnlyEnforceIf(b3)
    model.Add(rooms['WC']['x'] < rooms['UB']['x'] + rooms['UB']['w']).OnlyEnforceIf(b3)
    model.Add(rooms['WC']['x'] + rooms['WC']['w'] > rooms['UB']['x']).OnlyEnforceIf(b3)
    wc_ub_adjacent.append(b3)
    
    # WC上 = UB下
    b4 = model.NewBoolVar('wc_ub_adj4')
    model.Add(rooms['WC']['y'] == rooms['UB']['y'] + rooms['UB']['h']).OnlyEnforceIf(b4)
    model.Add(rooms['WC']['x'] < rooms['UB']['x'] + rooms['UB']['w']).OnlyEnforceIf(b4)
    model.Add(rooms['WC']['x'] + rooms['WC']['w'] > rooms['UB']['x']).OnlyEnforceIf(b4)
    wc_ub_adjacent.append(b4)
    
    # 少なくとも1つの隣接条件を満たす
    model.AddBoolOr(wc_ub_adjacent)
    
    # 制約4: 採光条件 - LDKとBR1を南側（Y座標の小さい方）に配置
    # 南側を敷地のY=0とすると、Y座標が小さいほど南に位置する
    # 目的関数: LDKの北端のY座標を最小化
    model.Minimize(rooms['LDK']['y'])
    
    # 制約5: LDKは南側に窓がある（面する）
    model.Add(rooms['LDK']['y'] == 0)  # 敷地南端に接する
    
    # 制約6: BR1も採光を確保（壁1面以上が外気に面する）
    # 簡易化: BR1は敷地の端（東西南北いずれか）に接するとする
    south = model.NewBoolVar('br1_south')
    east = model.NewBoolVar('br1_east')
    north = model.NewBoolVar('br1_north')
    west = model.NewBoolVar('br1_west')
    
    model.Add(rooms['BR1']['y'] == 0).OnlyEnforceIf(south)  # 南
    model.Add(rooms['BR1']['x'] + rooms['BR1']['w'] == width_grids).OnlyEnforceIf(east)  # 東
    model.Add(rooms['BR1']['y'] + rooms['BR1']['h'] == height_grids).OnlyEnforceIf(north)  # 北
    model.Add(rooms['BR1']['x'] == 0).OnlyEnforceIf(west)  # 西
    
    model.AddBoolOr([south, east, north, west])  # いずれかの外壁に接する
    
    # ソルバー実行
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10  # 最大10秒
    status = solver.Solve(model)
    
    # 結果を取得し可視化
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"有効な間取りを生成しました (ステータス: {status})")
        
        # 結果を取得
        result = {}
        for room_name, room in rooms.items():
            x = solver.Value(room['x']) * GRID / MM_TO_M  # mに変換
            y = solver.Value(room['y']) * GRID / MM_TO_M
            w = solver.Value(room['w']) * GRID / MM_TO_M
            h = solver.Value(room['h']) * GRID / MM_TO_M
            
            result[room_name] = {
                'x': x, 'y': y, 'w': w, 'h': h,
                'area': w * h,
                'color': room['color']
            }
            
            print(f"{room_name}: 位置({x:.2f}m, {y:.2f}m), "
                 f"サイズ({w:.2f}m x {h:.2f}m), 面積: {w*h:.2f}m²")
        
        # 間取り図の可視化
        plt.figure(figsize=(10, 8))
        
        # 敷地境界
        site_width = width_grids * GRID / MM_TO_M
        site_height = height_grids * GRID / MM_TO_M
        plt.plot([0, site_width, site_width, 0, 0], 
                [0, 0, site_height, site_height, 0], 'k-', linewidth=2)
        
        # 部屋の描画
        for room_name, room in result.items():
            x, y, w, h = room['x'], room['y'], room['w'], room['h']
            plt.fill([x, x+w, x+w, x, x], [y, y, y+h, y+h, y], 
                    color=room['color'], alpha=0.7)
            plt.plot([x, x+w, x+w, x, x], [y, y, y+h, y+h, y], 'k-')
            
            # 部屋ラベルと面積
            plt.text(x + w/2, y + h/2, f"{room_name}\n{room['area']:.1f}m²", 
                    ha='center', va='center', fontsize=10)
        
        # グリッド線（910mmモジュール）の表示
        for i in range(width_grids + 1):
            x = i * GRID / MM_TO_M
            plt.plot([x, x], [0, site_height], 'k:', alpha=0.3)
        for j in range(height_grids + 1):
            y = j * GRID / MM_TO_M
            plt.plot([0, site_width], [y, y], 'k:', alpha=0.3)
        
        # 方位の表示
        plt.text(site_width / 2, -0.5, "南", fontsize=12, ha='center')
        plt.text(site_width + 0.5, site_height / 2, "東", fontsize=12, va='center')
        plt.text(site_width / 2, site_height + 0.5, "北", fontsize=12, ha='center')
        plt.text(-0.5, site_height / 2, "西", fontsize=12, va='center')
        
        plt.title('CP-SAT生成3LDK間取り（910mmグリッド）')
        plt.xlabel('X [m]')
        plt.ylabel('Y [m]')
        plt.axis('equal')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
        
        return result
    else:
        print(f"実行可能な間取りが見つかりませんでした。ステータス: {status}")
        return None
```

## CP-SATを用いた階段寸法制約の追加例

次の例では、階段の寸法制約を追加して、より建築基準法に沿った制約を実装します：

```python
def add_stair_constraints(model, rooms, grid_mm):
    """
    階段寸法に関する制約を追加
    
    Args:
        model: CP-SATモデル
        rooms: 部屋変数の辞書
        grid_mm: グリッドサイズ(mm)
    """
    # 階段がない場合はスキップ
    if 'STAIR' not in rooms:
        return
    
    stair = rooms['STAIR']
    
    # 階段の最小幅: 750mm以上
    min_width_grids = (750 + grid_mm - 1) // grid_mm  # 切り上げ除算
    model.Add(stair['w'] >= min_width_grids)
    
    # 階段の最小奥行き: 踏面240mm × 12段 = 2880mm以上
    min_depth_grids = (2880 + grid_mm - 1) // grid_mm
    model.Add(stair['h'] >= min_depth_grids)
    
    # 階段の面積制約: 最低限の階段面積
    min_area_grids = min_width_grids * min_depth_grids
    model.Add(stair['w'] * stair['h'] >= min_area_grids)
    
    # 階段が1階と2階で位置が一致する制約（2階建ての場合）
    if 'STAIR_1F' in rooms and 'STAIR_2F' in rooms:
        stair_1f = rooms['STAIR_1F']
        stair_2f = rooms['STAIR_2F']
        
        # X, Y座標が一致
        model.Add(stair_1f['x'] == stair_2f['x'])
        model.Add(stair_1f['y'] == stair_2f['y'])
        
        # 幅と高さも一致
        model.Add(stair_1f['w'] == stair_2f['w'])
        model.Add(stair_1f['h'] == stair_2f['h'])
```

## 採光条件の詳細な実装例

建築基準法における採光条件をより詳細に実装した例：

```python
def add_daylight_constraints(model, rooms, site_width, site_height):
    """
    採光条件に関する制約を追加
    建築基準法では、居室の窓面積は床面積の1/7以上が必要
    
    Args:
        model: CP-SATモデル
        rooms: 部屋変数の辞書
        site_width: 敷地幅（グリッド単位）
        site_height: 敷地高さ（グリッド単位）
    """
    # 居室リスト（採光条件が必要な部屋）
    living_rooms = ['LDK', 'BR1', 'BR2', 'BR3']
    
    for room_name in living_rooms:
        if room_name not in rooms:
            continue
            
        room = rooms[room_name]
        
        # 部屋の面積計算
        room_area = room['w'] * room['h']
        
        # 採光窓の条件
        # 簡易化: 窓は外壁に面する場合にのみ存在すると仮定
        window_area = model.NewIntVar(0, 100, f'{room_name}_window_area')
        
        # 少なくとも1つの壁が外壁に面しているか
        south_wall = model.NewBoolVar(f'{room_name}_south_wall')  # 南壁が外気に面する
        east_wall = model.NewBoolVar(f'{room_name}_east_wall')    # 東壁が外気に面する
        north_wall = model.NewBoolVar(f'{room_name}_north_wall')  # 北壁が外気に面する
        west_wall = model.NewBoolVar(f'{room_name}_west_wall')    # 西壁が外気に面する
        
        # 各壁が外壁に面する条件
        model.Add(room['y'] == 0).OnlyEnforceIf(south_wall)                     # 南端
        model.Add(room['x'] + room['w'] == site_width).OnlyEnforceIf(east_wall) # 東端
        model.Add(room['y'] + room['h'] == site_height).OnlyEnforceIf(north_wall) # 北端
        model.Add(room['x'] == 0).OnlyEnforceIf(west_wall)                      # 西端
        
        # 少なくとも1つの壁が外壁
        model.AddBoolOr([south_wall, east_wall, north_wall, west_wall])
        
        # 窓面積の計算（簡易化）
        # 南面する場合: 南側の壁の長さの80%を窓面積とする
        south_window = model.NewIntVar(0, 100, f'{room_name}_south_window')
        model.Add(south_window == room['w'] * 0.8).OnlyEnforceIf(south_wall)
        model.Add(south_window == 0).OnlyEnforceIf(south_wall.Not())
        
        # 東面する場合
        east_window = model.NewIntVar(0, 100, f'{room_name}_east_window')
        model.Add(east_window == room['h'] * 0.6).OnlyEnforceIf(east_wall)
        model.Add(east_window == 0).OnlyEnforceIf(east_wall.Not())
        
        # 北面する場合
        north_window = model.NewIntVar(0, 100, f'{room_name}_north_window')
        model.Add(north_window == room['w'] * 0.4).OnlyEnforceIf(north_wall)
        model.Add(north_window == 0).OnlyEnforceIf(north_wall.Not())
        
        # 西面する場合
        west_window = model.NewIntVar(0, 100, f'{room_name}_west_window')
        model.Add(west_window == room['h'] * 0.6).OnlyEnforceIf(west_wall)
        model.Add(west_window == 0).OnlyEnforceIf(west_wall.Not())
        
        # 総窓面積
        model.Add(window_area == south_window + east_window + north_window + west_window)
        
        # 採光条件: 窓面積 >= 床面積 / 7
        model.Add(window_area * 7 >= room_area)
```

## FreeCADへの出力連携例

生成された間取りをFreeCADに出力する例：

```python
def export_to_freecad(floor_plan, output_path):
    """
    CP-SATで生成された間取りをFreeCADフォーマットで出力
    
    Args:
        floor_plan: CP-SATで生成された間取り情報
        output_path: FCStd出力パス
    """
    import FreeCAD
    import Part
    
    # FreeCADドキュメント作成
    doc = FreeCAD.newDocument()
    
    # 壁の高さ
    wall_height = 2400  # mm
    
    # 各部屋の押し出し
    for room_name, room in floor_plan.items():
        # メートルからミリメートルに変換
        x = room['x'] * 1000
        y = room['y'] * 1000
        w = room['w'] * 1000
        h = room['h'] * 1000
        
        # 矩形の頂点座標
        points = [
            (x, y, 0),
            (x + w, y, 0),
            (x + w, y + h, 0),
            (x, y + h, 0)
        ]
        
        # ワイヤー作成
        wire = Part.makePolygon(points + [points[0]])
        face = Part.Face(wire)
        
        # 押し出し
        extrusion = face.extrude(FreeCAD.Vector(0, 0, wall_height))
        
        # オブジェクト追加
        obj = doc.addObject("Part::Feature", room_name)
        obj.Shape = extrusion
        
        # 部屋タイプに応じた色設定
        if room_name.startswith('LDK'):
            obj.ViewObject.ShapeColor = (0.8, 0.9, 1.0)  # 水色
        elif room_name.startswith('BR'):
            obj.ViewObject.ShapeColor = (1.0, 0.8, 0.8)  # ピンク
        elif room_name.startswith('WC'):
            obj.ViewObject.ShapeColor = (0.9, 0.9, 0.9)  # グレー
        elif room_name.startswith('UB'):
            obj.ViewObject.ShapeColor = (0.9, 0.8, 1.0)  # 薄紫
    
    # 保存
    doc.recompute()
    doc.saveAs(output_path)
    print(f"FreeCADファイルを保存しました: {output_path}")
```

## ユースケース例

このCP-SAT PoCは、以下のような用途に活用できます：

1. **基本的な3LDK間取り生成テスト**：
   - 910mmグリッドに準拠した基本的な間取りを生成
   - 各部屋の空間配置の検証

2. **建築基準法の主要制約の検証**：
   - 採光条件（居室の窓面積）
   - 階段寸法（幅と奥行き）
   - 部屋の最小面積

3. **CP-SATソルバーの性能評価**：
   - 複雑さの異なる制約セットでの解の探索時間の計測
   - 多様な制約下での解の存在確認

4. **FreeCADとの連携テスト**：
   - 生成された間取りの3Dモデル化
   - 建築モデルとしてのエクスポート検証

この最小PoCをベースに、より複雑な制約や多様な間取りパターンに拡張していくことで、本格的な間取り生成システムの制約ソルバーレイヤーを構築できます。
