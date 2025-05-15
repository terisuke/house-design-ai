# Graph-to-Plan モデル実装サンプル

このドキュメントでは、間取り生成システムの中核となるGraph-to-Planモデルの概要と簡略化した実装例を提供します。このアプローチは、HouseDiffusionの商用利用制限を回避しつつ、効果的な間取り生成を可能にします。

## 基本的なアーキテクチャ

Graph-to-Planモデルは以下の3つの主要コンポーネントで構成されます：

1. **グラフエンコーダ**: 部屋の関係性グラフを処理
2. **空間トランスフォーマー**: 部屋の空間的配置を生成
3. **ポリゴンデコーダ**: 各部屋の具体的な形状を生成

## 実装サンプル（簡略版）

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
import networkx as nx
import numpy as np
from shapely.geometry import Polygon

class GraphToPlanModel(nn.Module):
    """部屋グラフから間取り図を生成するモデル"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        # グラフエンコーダ
        self.node_embedding = nn.Embedding(config.num_room_types, config.hidden_dim)
        self.graph_conv = nn.Linear(config.hidden_dim, config.hidden_dim)
        
        # 空間トランスフォーマー
        self.site_encoder = nn.Sequential(
            nn.Linear(config.site_feature_dim, config.hidden_dim),
            nn.ReLU()
        )
        self.attention = nn.MultiheadAttention(
            embed_dim=config.hidden_dim, 
            num_heads=4,
            dropout=0.1
        )
        
        # ポリゴンデコーダ
        self.position_predictor = nn.Sequential(
            nn.Linear(config.hidden_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, 4)  # x, y, width, height
        )
        
    def forward(self, room_types, adjacency_matrix, site_features):
        """
        順伝播でグラフから部屋ポリゴンを生成
        
        Args:
            room_types: 各ノードの部屋タイプ [batch_size, num_nodes]
            adjacency_matrix: 隣接行列 [batch_size, num_nodes, num_nodes]
            site_features: 敷地の特徴量 [batch_size, site_feature_dim]
        """
        # 部屋タイプの埋め込み
        node_features = self.node_embedding(room_types)  # [batch_size, num_nodes, hidden_dim]
        
        # グラフ畳み込み
        x = node_features
        for _ in range(3):
            # メッセージパッシング
            x_j = torch.bmm(adjacency_matrix, x)
            x = F.relu(self.graph_conv(x_j)) + x
            
        # 敷地情報の組み込み
        site_encoding = self.site_encoder(site_features).unsqueeze(1)
        
        # 部屋の空間配置を生成
        query = x.permute(1, 0, 2)  # [num_nodes, batch_size, hidden_dim]
        key = value = query
        attn_output, _ = self.attention(query, key, value)
        spatial_features = attn_output.permute(1, 0, 2)  # [batch_size, num_nodes, hidden_dim]
        
        # 各部屋の位置・サイズを予測
        positions = self.position_predictor(spatial_features)  # [batch_size, num_nodes, 4]
        x, y, w, h = torch.split(positions, 1, dim=-1)
        
        # 部屋のポリゴン形状に変換
        room_polygons = []
        for b in range(node_features.shape[0]):
            batch_shapes = []
            for n in range(node_features.shape[1]):
                # 基本矩形の座標
                x_val, y_val = x[b, n, 0].item(), y[b, n, 0].item()
                w_val, h_val = w[b, n, 0].item(), h[b, n, 0].item()
                
                # 矩形の頂点座標
                rectangle = [
                    (x_val, y_val),
                    (x_val + w_val, y_val),
                    (x_val + w_val, y_val + h_val),
                    (x_val, y_val + h_val)
                ]
                batch_shapes.append(rectangle)
            room_polygons.append(batch_shapes)
            
        return room_polygons
    
    def generate(self, room_graph, site_boundary, num_samples=10):
        """
        複数の候補間取りを生成
        
        Args:
            room_graph: 部屋の関係性グラフ (NetworkX形式)
            site_boundary: 敷地境界ポリゴン
            num_samples: 生成するサンプル数
        """
        # グラフをテンソル形式に変換
        adjacency_matrix, room_types = self._prepare_graph_input(room_graph)
        
        # 敷地特徴量を抽出
        site_features = self._extract_site_features(site_boundary)
        
        # 候補生成
        samples = []
        for _ in range(num_samples):
            with torch.no_grad():
                room_polygons = self.forward(room_types, adjacency_matrix, site_features)
                samples.append(room_polygons[0])  # バッチサイズ1の最初の要素
            
        return samples
```

## CP-SATとの連携（簡略版）

```python
from ortools.sat.python import cp_model

def optimize_floor_plan_with_cpsat(floor_plan, site_boundary):
    """
    Graph-to-Planで生成された間取りをCP-SATで最適化
    """
    model = cp_model.CpModel()
    
    # 各部屋の位置・寸法変数（910mmグリッドに合わせる）
    room_vars = {}
    max_grid = 100  # 最大グリッド数
    
    for i, room_polygon in enumerate(floor_plan):
        # バウンディングボックスの計算
        points = np.array(room_polygon)
        min_x, min_y = points.min(axis=0)
        max_x, max_y = points.max(axis=0)
        
        # グリッド座標に変換（四捨五入）
        grid_min_x = round(min_x / 0.91)
        grid_min_y = round(min_y / 0.91)
        grid_max_x = round(max_x / 0.91)
        grid_max_y = round(max_y / 0.91)
        
        # CP-SAT変数の定義
        room_vars[i] = {
            'x1': model.NewIntVar(0, max_grid, f'x1_{i}'),
            'y1': model.NewIntVar(0, max_grid, f'y1_{i}'),
            'x2': model.NewIntVar(0, max_grid, f'x2_{i}'),
            'y2': model.NewIntVar(0, max_grid, f'y2_{i}')
        }
        
        # 初期値から大きく離れないよう制約
        model.Add(room_vars[i]['x1'] >= grid_min_x - 2)
        model.Add(room_vars[i]['y1'] >= grid_min_y - 2)
        model.Add(room_vars[i]['x2'] <= grid_max_x + 2)
        model.Add(room_vars[i]['y2'] <= grid_max_y + 2)
        
        # 最小面積制約
        model.Add((room_vars[i]['x2'] - room_vars[i]['x1']) * 
                 (room_vars[i]['y2'] - room_vars[i]['y1']) >= 4)  # 最小4グリッド
    
    # 部屋が重ならない制約
    for i in range(len(floor_plan)):
        for j in range(i + 1, len(floor_plan)):
            b1 = model.NewBoolVar(f'b1_{i}_{j}')
            b2 = model.NewBoolVar(f'b2_{i}_{j}')
            b3 = model.NewBoolVar(f'b3_{i}_{j}')
            b4 = model.NewBoolVar(f'b4_{i}_{j}')
            
            model.Add(room_vars[i]['x2'] <= room_vars[j]['x1']).OnlyEnforceIf(b1)
            model.Add(room_vars[j]['x2'] <= room_vars[i]['x1']).OnlyEnforceIf(b2)
            model.Add(room_vars[i]['y2'] <= room_vars[j]['y1']).OnlyEnforceIf(b3)
            model.Add(room_vars[j]['y2'] <= room_vars[i]['y1']).OnlyEnforceIf(b4)
            
            model.AddBoolOr([b1, b2, b3, b4])
    
    # ソルバー実行
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    status = solver.Solve(model)
    
    # 解が見つかった場合
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        optimized_plan = []
        for i in range(len(floor_plan)):
            x1 = solver.Value(room_vars[i]['x1']) * 0.91  # グリッド→メートル変換
            y1 = solver.Value(room_vars[i]['y1']) * 0.91
            x2 = solver.Value(room_vars[i]['x2']) * 0.91
            y2 = solver.Value(room_vars[i]['y2']) * 0.91
            
            # 矩形の部屋形状
            polygon = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
            optimized_plan.append(polygon)
        
        return optimized_plan
    else:
        return None  # 解なし
```

## 使用例

```python
def generate_floor_plan_example():
    """間取り生成パイプラインの使用例"""
    import matplotlib.pyplot as plt
    from shapely.geometry import box
    
    # モデル設定
    class ModelConfig:
        def __init__(self):
            self.num_room_types = 10
            self.hidden_dim = 128
            self.site_feature_dim = 32
    
    # 敷地設定
    site = box(0, 0, 10, 8)  # 10m x 8m
    
    # 部屋グラフの構築
    G = nx.Graph()
    
    # 部屋タイプ
    room_types = {
        'LDK': 0, 'BR1': 1, 'BR2': 2, 'WC': 3, 'UB': 4
    }
    
    # ノード追加
    for i, (room_type, type_id) in enumerate(room_types.items()):
        G.add_node(i, type=room_type, type_id=type_id)
    
    # エッジ追加（隣接関係）
    # LDKと全部屋を接続
    for i in range(1, len(room_types)):
        G.add_edge(0, i)  # LDKは0番
    
    # トイレと風呂を接続
    G.add_edge(3, 4)  # WC-UB
    
    # モデルの初期化
    config = ModelConfig()
    model = GraphToPlanModel(config)
    
    # 間取り生成
    candidates = model.generate(G, site, num_samples=5)
    
    # CP-SATによる最適化
    optimized = optimize_floor_plan_with_cpsat(candidates[0], site)
    
    # 可視化
    plt.figure(figsize=(10, 8))
    
    # 敷地
    x, y = site.exterior.xy
    plt.plot(x, y, 'k-', linewidth=2)
    
    # 部屋の色
    colors = ['skyblue', 'pink', 'lightgreen', 'lightgray', 'lavender']
    
    # 最適化された間取りを描画
    for i, room in enumerate(optimized):
        poly = Polygon(room)
        x, y = poly.exterior.xy
        
        room_type = list(room_types.keys())[i]
        plt.fill(x, y, color=colors[i], alpha=0.7)
        plt.plot(x, y, 'k-')
        
        # 部屋ラベル
        centroid = poly.centroid
        plt.text(centroid.x, centroid.y, room_type, ha='center', va='center')
    
    plt.axis('equal')
    plt.title('Generated and Optimized Floor Plan')
    plt.show()
```

## VAEアプローチ（代替案）

Graph-to-Planが課題に直面した場合の代替として、VAEベースの簡略化実装:

```python
class FloorPlanVAE(nn.Module):
    """間取り生成のための変分オートエンコーダ（簡略版）"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        # エンコーダ
        self.encoder = nn.Sequential(
            nn.Linear(config.input_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, config.hidden_dim * 2)
        )
        
        # 条件エンコーダ
        self.condition_encoder = nn.Sequential(
            nn.Linear(config.condition_dim, config.hidden_dim),
            nn.ReLU()
        )
        
        # デコーダ
        self.decoder = nn.Sequential(
            nn.Linear(config.latent_dim + config.hidden_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, config.output_dim)
        )
        
    def encode(self, x, condition):
        """入力と条件から潜在変数を得る"""
        h = self.encoder(x)
        mu, logvar = torch.chunk(h, 2, dim=-1)
        return mu, logvar
        
    def decode(self, z, condition):
        """潜在変数と条件から間取りを生成"""
        c = self.condition_encoder(condition)
        z_c = torch.cat([z, c], dim=1)
        return self.decoder(z_c)
        
    def generate(self, condition, num_samples=10):
        """条件付きでサンプル生成"""
        with torch.no_grad():
            c = self.condition_encoder(condition)
            samples = []
            
            for _ in range(num_samples):
                z = torch.randn(1, self.config.latent_dim)
                z_c = torch.cat([z, c], dim=1)
                output = self.decoder(z_c)
                floor_plan = self._output_to_floor_plan(output)
                samples.append(floor_plan)
                
            return samples
```

## CP-SAT最小PoC

CP-SATソルバーの検証用最小実装例:

```python
def create_basic_floor_plan_poc():
    """
    CP-SAT最小PoC - 3LDKの基本間取りを910mmグリッドで生成（簡略版）
    """
    from ortools.sat.python import cp_model
    import matplotlib.pyplot as plt
    
    # 設定
    GRID_SIZE = 910  # mm
    width_grids = 10  # 約9.1m
    height_grids = 8  # 約7.3m
    
    # モデル定義
    model = cp_model.CpModel()
    
    # 部屋変数（グリッド単位）- 簡略化のためLDKと2寝室のみ
    rooms = {
        'LDK': {
            'x': model.NewIntVar(0, width_grids - 4, 'ldk_x'),
            'y': model.NewIntVar(0, height_grids - 4, 'ldk_y'),
            'w': model.NewIntVar(4, width_grids, 'ldk_w'),
            'h': model.NewIntVar(4, height_grids, 'ldk_h'),
            'min_area': 20,
            'color': 'skyblue'
        },
        'BR1': {
            'x': model.NewIntVar(0, width_grids - 3, 'br1_x'),
            'y': model.NewIntVar(0, height_grids - 3, 'br1_y'),
            'w': model.NewIntVar(3, width_grids, 'br1_w'),
            'h': model.NewIntVar(3, height_grids, 'br1_h'),
            'min_area': 9,
            'color': 'pink'
        },
        'BR2': {
            'x': model.NewIntVar(0, width_grids - 3, 'br2_x'),
            'y': model.NewIntVar(0, height_grids - 3, 'br2_y'),
            'w': model.NewIntVar(3, width_grids, 'br2_w'),
            'h': model.NewIntVar(3, height_grids, 'br2_h'),
            'min_area': 9,
            'color': 'lightgreen'
        }
    }
    
    # 基本制約をここに追加
    # 1. 敷地内に収まる
    # 2. 部屋同士が重ならない
    # 3. 最小面積を満たす
    # 4. 部屋の隣接関係
    
    # ソルバー実行
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    # 結果の可視化
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # 結果を取得して描画
        plt.figure(figsize=(10, 8))
        
        # 各部屋を描画
        for room_name, room in rooms.items():
            x = solver.Value(room['x']) * GRID_SIZE / 1000  # mに変換
            y = solver.Value(room['y']) * GRID_SIZE / 1000
            w = solver.Value(room['w']) * GRID_SIZE / 1000
            h = solver.Value(room['h']) * GRID_SIZE / 1000
            
            # 部屋を描画
            plt.fill([x, x+w, x+w, x, x], [y, y, y+h, y+h, y], 
                    color=room['color'], alpha=0.7)
            plt.text(x + w/2, y + h/2, room_name, ha='center', va='center')
        
        plt.title('CP-SAT生成基本間取り')
        plt.axis('equal')
        plt.grid(True, alpha=0.3)
        plt.show()
```

これらの簡略化されたコード例は、実際の実装の基礎となるものです。実際のシステムではより詳細な制約条件や機能拡張が必要ですが、ここで示した基本構造を元に段階的に開発を進めていくことができます。
