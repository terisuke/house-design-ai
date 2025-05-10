# 間取り生成システム: 最終実装アプローチ

## 最終結論と実装戦略

複数のAIによる意見を統合し、既存システムを活かしながら最も効率的に実用フェーズに進める最適な方法を提案します。

### コア戦略: 「生成と制約の明確な分離」

```
YOLO (データ抽出)  →  Diffusion/GNN (創造性)  →  CP-SAT (厳密制約)  →  出力・評価
```

この分離アプローチにより、創造性と法的制約の両立が可能となり、GANで遭遇した「全ての条件を満たせない」問題を解決します。

## 詳細実装計画

### 1. データ整備フェーズ (1週目)

**目標**: YOLOアノテーションデータをベクターデータ+グラフ構造に変換

```python
# YOLOアノテーション → ベクター/グラフデータ変換
def convert_annotations_to_vector(annotations_path, output_path):
    import shapely.geometry as sg
    import networkx as nx
    import json
    
    annotations = load_yolo_annotations(annotations_path)
    
    # 部屋ポリゴンの抽出
    rooms = []
    for ann in annotations:
        if ann['label'] in ['L', 'D', 'K', 'R1', 'R2', 'WC', 'UB', 'CO', 'UP', 'DN']:
            bbox = ann['bbox']  # [x, y, w, h]
            polygon = sg.box(bbox[0]-bbox[2]/2, bbox[1]-bbox[3]/2, 
                             bbox[0]+bbox[2]/2, bbox[1]+bbox[3]/2)
            rooms.append({
                'label': ann['label'],
                'polygon': polygon.wkt,  # WKT形式で保存
                'floor': '1F' if any(a['label'] == '1F' and is_inside(bbox, a['bbox']) 
                                   for a in annotations) else '2F'
            })
    
    # 隣接グラフの構築
    adjacency_graph = nx.Graph()
    for room in rooms:
        adjacency_graph.add_node(room['label'])
    
    for i, room1 in enumerate(rooms):
        poly1 = sg.loads(room1['polygon'])
        for j, room2 in enumerate(rooms):
            if i != j:
                poly2 = sg.loads(room2['polygon'])
                if poly1.touches(poly2) or poly1.distance(poly2) < 0.01:  # 近接判定
                    adjacency_graph.add_edge(room1['label'], room2['label'])
    
    # House, Space, 方位の抽出
    house_poly = next((sg.loads(ann['bbox_to_polygon'](ann['bbox'])).wkt 
                      for ann in annotations if ann['label'] == 'House'), None)
    space_poly = next((sg.loads(ann['bbox_to_polygon'](ann['bbox'])).wkt 
                      for ann in annotations if ann['label'] == 'Space'), None)
    direction = next((ann['label'] for ann in annotations 
                     if ann['label'] in ['North', 'South']), None)
    
    # 結果の保存
    result = {
        'rooms': rooms,
        'adjacency_graph': nx.node_link_data(adjacency_graph),
        'house': house_poly,
        'space': space_poly,
        'direction': direction
    }
    
    with open(output_path, 'w') as f:
        json.dump(result, f)
```

**重要ポイント**:
- 910mmグリッドは「属性」として保持し、生成後にスナップさせる方式を採用
- 建築基準法のためのメタデータ（窓の位置、方位など）も抽出

### 2. 一次生成レイヤー (2-4週目)

**目標**: 敷地条件と部屋要件から多様な間取り案を大量生成

```python
# HouseDiffusion実装例（PyTorch）
class HouseDiffusionModel(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.encoder = VectorEncoder(config)
        self.diffusion = DiffusionModel(config)
        self.decoder = VectorDecoder(config)
        
    def forward(self, site_boundary, requirements, time_step):
        # 敷地境界と要件をエンコード
        encoded = self.encoder(site_boundary, requirements)
        # 拡散モデルで部屋配置を生成
        diffused = self.diffusion(encoded, time_step)
        # 部屋ポリゴンとして復号
        room_polygons = self.decoder(diffused)
        return room_polygons
    
    def generate(self, site_boundary, requirements, num_samples=100):
        # 条件付き生成プロセス
        samples = []
        for _ in range(num_samples):
            noise = torch.randn(1, self.config.latent_dim)
            for t in reversed(range(self.config.diffusion_steps)):
                time_step = torch.tensor([t])
                with torch.no_grad():
                    denoised = self.denoise_step(noise, time_step, site_boundary, requirements)
                    noise = denoised
            
            # 最終的な潜在表現を部屋ポリゴンにデコード
            room_polygons = self.decoder(noise)
            samples.append(room_polygons)
        
        return samples
```

**実装優先順位**:
1. **◎ HouseDiffusion** (敷地形状→部屋ポリゴン直接生成)
   - 10K枚のデータで訓練可能
   - 非直交形状にも対応可能

2. **○ Graph2Plan / Graph-Transformer** (補完的役割)
   - 部屋リストや隣接条件が明確な場合に有効
   - 「LDKと階段を隣接させる」などの制約が指定できる

### 3. 制約ソルバレイヤー (4-6週目)

**目標**: 生成された間取り案を建築基準法とグリッド要件に適合させる

```python
# Google OR-Tools CP-SATを利用した制約ソルバー
from ortools.sat.python import cp_model

def optimize_floor_plan(generated_room_polygons, site_boundary, requirements):
    model = cp_model.CpModel()
    
    # 各部屋の位置・寸法変数を定義（910mmグリッドに合わせる）
    room_vars = {}
    for i, room in enumerate(generated_room_polygons):
        # 各部屋の左上と右下座標をグリッド単位で変数化
        room_vars[i] = {
            'x1': model.NewIntVar(0, max_grid_x, f'x1_{i}'),
            'y1': model.NewIntVar(0, max_grid_y, f'y1_{i}'),
            'x2': model.NewIntVar(0, max_grid_x, f'x2_{i}'),
            'y2': model.NewIntVar(0, max_grid_y, f'y2_{i}')
        }
        
        # 部屋サイズ制約（910mm単位）
        model.Add(room_vars[i]['x2'] - room_vars[i]['x1'] >= min_width[room['label']])
        model.Add(room_vars[i]['y2'] - room_vars[i]['y1'] >= min_height[room['label']])
    
    # 建築基準法の制約
    
    # 1. 採光条件
    for i, room in enumerate(generated_room_polygons):
        if room['label'] in living_room_types:  # 居室のみ適用
            window_area = model.NewIntVar(0, 100000, f'window_area_{i}')
            room_area = (room_vars[i]['x2'] - room_vars[i]['x1']) * (room_vars[i]['y2'] - room_vars[i]['y1'])
            # 窓面積 >= 居室面積 / 7
            model.Add(window_area * 7 >= room_area)
    
    # 2. 階段寸法
    for i, room in enumerate(generated_room_polygons):
        if room['label'] in ['UP', 'DN']:
            # 階段幅は910mm以上
            model.Add(room_vars[i]['x2'] - room_vars[i]['x1'] >= 1)  # 1グリッド = 910mm
    
    # 3. 1F/2F整合性（階段・荷重壁）
    if '2F' in requirements:
        stairs_1f = next((i for i, r in enumerate(generated_room_polygons) 
                         if r['label'] == 'UP' and r['floor'] == '1F'), None)
        stairs_2f = next((i for i, r in enumerate(generated_room_polygons) 
                         if r['label'] == 'DN' and r['floor'] == '2F'), None)
        
        if stairs_1f is not None and stairs_2f is not None:
            # 階段のXY座標を一致させる
            model.Add(room_vars[stairs_1f]['x1'] == room_vars[stairs_2f]['x1'])
            model.Add(room_vars[stairs_1f]['y1'] == room_vars[stairs_2f]['y1'])
            model.Add(room_vars[stairs_1f]['x2'] == room_vars[stairs_2f]['x2'])
            model.Add(room_vars[stairs_1f]['y2'] == room_vars[stairs_2f]['y2'])
    
    # 荷重壁の整合性はペナルティ最小化として扱う
    wall_penalties = []
    # ...荷重壁整合ロジック...
    
    # 目的関数: ペナルティの最小化 + 原案からの変更を最小化
    objective_terms = wall_penalties + [...]
    model.Minimize(sum(objective_terms))
    
    # ソルバー実行
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # 解を取得して返す
        optimized_plan = extract_solution(solver, room_vars, generated_room_polygons)
        return optimized_plan
    else:
        return None  # 解なし
```

**主要制約条件**:
- 910mmグリッドへのスナップ
- 採光条件 (窓面積 ≥ 居室面積/7)
- 階段寸法（幅 ≥ 750mm）
- 廊下幅 (≥ 750mm)
- 1F/2F階段の一致
- 2Fの荷重壁が1Fの壁の上にあること（ソフト制約）

### 4. ポストプロセスと出力 (6-8週目)

```python
# FreeCAD出力例
def export_to_freecad(optimized_floor_plan, output_path):
    import FreeCAD
    import Part
    
    doc = FreeCAD.newDocument()
    
    # 各階のモデリング
    for floor in ['1F', '2F']:
        z_offset = 0 if floor == '1F' else 3000  # 2Fは3m上
        
        # 各部屋の押し出し
        floor_rooms = [r for r in optimized_floor_plan['rooms'] if r['floor'] == floor]
        for room in floor_rooms:
            poly = sg.loads(room['polygon'])
            points = [(p[0], p[1], z_offset) for p in poly.exterior.coords]
            
            # FreeCADオブジェクト作成
            wire = Part.makePolygon(points)
            face = Part.Face(wire)
            extrusion = face.extrude(FreeCAD.Vector(0, 0, 2400))  # 高さ2.4m
            
            obj = doc.addObject("Part::Feature", room['label'])
            obj.Shape = extrusion
            
            # 部屋タイプに応じた色設定
            obj.ViewObject.ShapeColor = room_colors.get(room['label'], (0.8, 0.8, 0.8))
    
    # IFC変換のための追加属性
    for obj in doc.Objects:
        if hasattr(obj, "Label"):
            if obj.Label in ["L", "D", "K"]:
                obj.addProperty("App::PropertyString", "IfcType").IfcType = "IfcSpace"
                obj.addProperty("App::PropertyString", "Description").Description = "Living Space"
    
    doc.recompute()
    doc.saveAs(output_path)
    
    # IFC出力（オプション）
    if output_path.endswith('.FCStd'):
        ifc_path = output_path.replace('.FCStd', '.ifc')
        import exportIFC
        exportIFC.export(doc.Objects, ifc_path)
```

**出力フォーマット**:
- FreeCAD (.FCStd)
- IFC (.ifc) - 構造解析ソフトウェアとの連携用
- SVG (.svg) - 2D図面
- JSON - メタデータ（部屋面積、窓位置など）

### 5. 評価・選定システム (7-8週目)

```python
# 生成された間取りの評価スコアリング
def evaluate_floor_plan(floor_plan):
    scores = {}
    
    # 1. 採光率スコア
    scores['natural_light'] = calculate_natural_light_score(floor_plan)
    
    # 2. 動線効率スコア
    scores['circulation'] = calculate_circulation_score(floor_plan)
    
    # 3. 空間効率スコア（無駄スペース最小化）
    scores['space_efficiency'] = calculate_space_efficiency(floor_plan)
    
    # 4. 1F/2F整合性スコア
    scores['floor_consistency'] = calculate_floor_consistency(floor_plan)
    
    # 総合スコア（重み付け）
    weights = {
        'natural_light': 0.3,
        'circulation': 0.3,
        'space_efficiency': 0.2,
        'floor_consistency': 0.2
    }
    
    total_score = sum(score * weights[key] for key, score in scores.items())
    scores['total'] = total_score
    
    return scores
```

## 最適な実装ステップ（8週間計画）

### 週1-2: データ整備とCP-SAT PoC
1. YOLOアノテーション → ベクター/グラフJSON変換システム構築
2. CP-SAT最小PoC開発
   - 3LDKの基本的な間取りを生成・制約遵守を検証
   - 910mmグリッド + 採光条件 + 階段寸法の基本制約を実装

### 週3-4: HouseDiffusionモデル開発
1. HouseDiffusion実装・小規模データセットで初期トレーニング
2. 敷地形状と方位条件の埋め込みメカニズム実装
3. FreeCAD出力基本システム構築

### 週5-6: 制約ソルバー完成と統合
1. CP-SATソルバーの完全実装
   - 採光、階段、1F/2F整合性など全制約条件の実装
2. Diffusionモデルと制約ソルバーの統合
3. ベンチマークテスト（100案生成→制約チェック→最適化）

### 週7-8: UI開発と最終調整
1. Streamlit/Three.js UIの開発
2. 評価システム完成
3. パフォーマンス最適化
4. 実際の敷地データでのエンドツーエンドテスト

## 実装の要点と優位性

1. **モジュール分離によるリスク低減**
   - 生成と制約を完全分離し、それぞれが得意な役割に専念
   - 一方が失敗しても、別モジュールで補完可能な柔軟性

2. **YOLOの効果的活用**
   - 間取り生成ではなく「教師データ抽出」と「評価」に特化
   - 既存資産（アノテーション）を最大限活用

3. **拡散モデル(HouseDiffusion)の優先採用**
   - ベクター座標を直接出力可能で非マンハッタン形状も扱える
   - 10K規模のデータセットで十分な性能が期待できる

4. **CP-SATによる厳密制約の担保**
   - 建築基準法100%準拠を保証
   - 910mmモジュール化を最適化のプロセスとして実現

5. **実装複雑性のコントロール**
   - GAよりも管理しやすいCP-SATを主要最適化エンジンとして採用
   - バックアップアプローチとしてGraph2Planを準備

## CP-SAT最小PoC例（初週で実装すべきコード）

```python
from ortools.sat.python import cp_model
import numpy as np
import matplotlib.pyplot as plt

def create_basic_floor_plan(width_grids, height_grids, room_requirements):
    """
    最小限のCP-SAT PoC - 3LDKの基本レイアウトを910mmグリッドで最適化
    
    Args:
        width_grids: 敷地幅（グリッド単位）
        height_grids: 敷地高さ（グリッド単位）
        room_requirements: 部屋要件辞書 {部屋タイプ: 最小面積(グリッド単位)}
    
    Returns:
        最適化された間取り（各部屋の座標とサイズ）
    """
    model = cp_model.CpModel()
    
    # 部屋変数の定義
    rooms = {}
    for room_type in room_requirements:
        # 各部屋の左上座標と幅・高さを変数化
        rooms[room_type] = {
            'x': model.NewIntVar(0, width_grids - 1, f'x_{room_type}'),
            'y': model.NewIntVar(0, height_grids - 1, f'y_{room_type}'),
            'w': model.NewIntVar(1, width_grids, f'w_{room_type}'),
            'h': model.NewIntVar(1, height_grids, f'h_{room_type}')
        }
        
        # 部屋が敷地内に収まる制約
        model.Add(rooms[room_type]['x'] + rooms[room_type]['w'] <= width_grids)
        model.Add(rooms[room_type]['y'] + rooms[room_type]['h'] <= height_grids)
        
        # 最小面積制約
        min_area = room_requirements[room_type]
        model.Add(rooms[room_type]['w'] * rooms[room_type]['h'] >= min_area)
    
    # 部屋同士が重ならない制約
    for r1 in rooms:
        for r2 in rooms:
            if r1 < r2:  # 重複チェックを避けるため
                # r1とr2が重ならない条件: 
                # r1の右端 <= r2の左端 または r1の左端 >= r2の右端 または
                # r1の下端 <= r2の上端 または r1の上端 >= r2の下端
                b1 = model.NewBoolVar(f'b1_{r1}_{r2}')
                b2 = model.NewBoolVar(f'b2_{r1}_{r2}')
                b3 = model.NewBoolVar(f'b3_{r1}_{r2}')
                b4 = model.NewBoolVar(f'b4_{r1}_{r2}')
                
                model.Add(rooms[r1]['x'] + rooms[r1]['w'] <= rooms[r2]['x']).OnlyEnforceIf(b1)
                model.Add(rooms[r1]['x'] >= rooms[r2]['x'] + rooms[r2]['w']).OnlyEnforceIf(b2)
                model.Add(rooms[r1]['y'] + rooms[r1]['h'] <= rooms[r2]['y']).OnlyEnforceIf(b3)
                model.Add(rooms[r1]['y'] >= rooms[r2]['y'] + rooms[r2]['h']).OnlyEnforceIf(b4)
                
                model.AddBoolOr([b1, b2, b3, b4])
    
    # 隣接制約の例（LとDKを隣接させる）
    if 'L' in rooms and 'DK' in rooms:
        # 隣接 = 少なくとも一辺が接している
        b_adj1 = model.NewBoolVar('b_adj_L_DK_1')
        b_adj2 = model.NewBoolVar('b_adj_L_DK_2')
        b_adj3 = model.NewBoolVar('b_adj_L_DK_3')
        b_adj4 = model.NewBoolVar('b_adj_L_DK_4')
        
        # L.右 = DK.左
        model.Add(rooms['L']['x'] + rooms['L']['w'] == rooms['DK']['x']).OnlyEnforceIf(b_adj1)
        model.Add(rooms['L']['y'] < rooms['DK']['y'] + rooms['DK']['h']).OnlyEnforceIf(b_adj1)
        model.Add(rooms['L']['y'] + rooms['L']['h'] > rooms['DK']['y']).OnlyEnforceIf(b_adj1)
        
        # L.左 = DK.右
        model.Add(rooms['L']['x'] == rooms['DK']['x'] + rooms['DK']['w']).OnlyEnforceIf(b_adj2)
        model.Add(rooms['L']['y'] < rooms['DK']['y'] + rooms['DK']['h']).OnlyEnforceIf(b_adj2)
        model.Add(rooms['L']['y'] + rooms['L']['h'] > rooms['DK']['y']).OnlyEnforceIf(b_adj2)
        
        # L.下 = DK.上
        model.Add(rooms['L']['y'] + rooms['L']['h'] == rooms['DK']['y']).OnlyEnforceIf(b_adj3)
        model.Add(rooms['L']['x'] < rooms['DK']['x'] + rooms['DK']['w']).OnlyEnforceIf(b_adj3)
        model.Add(rooms['L']['x'] + rooms['L']['w'] > rooms['DK']['x']).OnlyEnforceIf(b_adj3)
        
        # L.上 = DK.下
        model.Add(rooms['L']['y'] == rooms['DK']['y'] + rooms['DK']['h']).OnlyEnforceIf(b_adj4)
        model.Add(rooms['L']['x'] < rooms['DK']['x'] + rooms['DK']['w']).OnlyEnforceIf(b_adj4)
        model.Add(rooms['L']['x'] + rooms['L']['w'] > rooms['DK']['x']).OnlyEnforceIf(b_adj4)
        
        model.AddBoolOr([b_adj1, b_adj2, b_adj3, b_adj4])
    
    # 採光条件の例（Lは南側に配置）
    if 'L' in rooms:
        # 南側 = y座標が大きい方が南
        model.Maximize(rooms['L']['y'])
    
    # ソルバー実行
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    # 結果を取得
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        result = {}
        for room_type in rooms:
            result[room_type] = {
                'x': solver.Value(rooms[room_type]['x']),
                'y': solver.Value(rooms[room_type]['y']),
                'w': solver.Value(rooms[room_type]['w']),
                'h': solver.Value(rooms[room_type]['h'])
            }
        return result
    else:
        return None

# 使用例
def main():
    # 敷地サイズ（グリッド単位、1グリッド = 910mm）
    width = 10  # 約9.1m
    height = 8  # 約7.3m
    
    # 部屋要件（最小面積、グリッド単位）
    room_requirements = {
        'L': 6,    # リビング: 約5m²
        'DK': 6,   # ダイニング・キッチン: 約5m²
        'R1': 4,   # 寝室1: 約3.3m²
        'R2': 4,   # 寝室2: 約3.3m²
        'WC': 1,   # トイレ: 約0.8m²
        'UB': 2    # 風呂: 約1.7m²
    }
    
    # 間取り生成
    floor_plan = create_basic_floor_plan(width, height, room_requirements)
    
    if floor_plan:
        # 間取り図の描画
        plt.figure(figsize=(10, 8))
        ax = plt.gca()
        
        # 敷地境界
        plt.plot([0, width, width, 0, 0], [0, 0, height, height, 0], 'k-')
        
        # 部屋の描画
        colors = {'L': 'skyblue', 'DK': 'lightgreen', 'R1': 'pink', 
                 'R2': 'lavender', 'WC': 'lightgray', 'UB': 'lightcyan'}
        
        for room, pos in floor_plan.items():
            x, y, w, h = pos['x'], pos['y'], pos['w'], pos['h']
            ax.add_patch(plt.Rectangle((x, y), w, h, 
                                     facecolor=colors.get(room, 'white'),
                                     edgecolor='black', 
                                     alpha=0.7))
            plt.text(x + w/2, y + h/2, room, 
                    ha='center', va='center', fontsize=12)
        
        # グリッド線（910mmモジュール）
        for i in range(width + 1):
            plt.plot([i, i], [0, height], 'k:', alpha=0.3)
        for j in range(height + 1):
            plt.plot([0, width], [j, j], 'k:', alpha=0.3)
        
        plt.title('CP-SAT生成3LDK間取り（910mmグリッド）')
        plt.xlabel('X (グリッド単位 = 910mm)')
        plt.ylabel('Y (グリッド単位 = 910mm)')
        plt.axis('equal')
        plt.xlim(-0.5, width + 0.5)
        plt.ylim(-0.5, height + 0.5)
        plt.grid(True, linestyle=':', alpha=0.3)
        plt.show()
        
        # 部屋の情報を出力
        for room, pos in floor_plan.items():
            area = pos['w'] * pos['h'] * 0.91 * 0.91  # m²単位
            print(f"{room}: 位置({pos['x']*0.91:.2f}m, {pos['y']*0.91:.2f}m), "
                 f"サイズ({pos['w']*0.91:.2f}m x {pos['h']*0.91:.2f}m), "
                 f"面積: {area:.2f}m²")
    else:
        print("実行可能な間取りが見つかりませんでした。制約を緩和してください。")

if __name__ == "__main__":
    main()
```

## 結論: 実装への最短パス

本提案の実装アプローチは、既存のYOLOデータを最大限に活用しつつ、HouseDiffusionとCP-SATという現実的に実装しやすい技術を組み合わせた「現実解」です。重要なのは「生成と制約の分離」という設計思想で、これによって:

1. 生成モデルは「部屋の配置案」という創造的な役割に専念
2. CP-SATは「建築基準法とグリッド適合」という厳密な役割に専念
3. それぞれが得意なことに注力できるため、実装リスクが大幅に低減

まずは第1週目にCP-SATの最小PoCを実装し、「本当に制約を全部通せるか」を検証することから始めるのが最も効率的です。そこから着実にモジュールを拡張していくことで、8週間以内に実用的なシステムを構築できると考えられます。