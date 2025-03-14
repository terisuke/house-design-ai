import random
import numpy as np
import pandas as pd
from collections import OrderedDict
from scipy import ndimage

from dataclasses import dataclass

@dataclass
class Madori:
    name: str
    code: int
    width: int
    height: int
    neighbor_name: str

class Site:
    def __init__(self, grid_w, grid_h):
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.madori_info = OrderedDict()    # Madoriデータクラス

    def init_grid(self):
        grid = np.zeros(shape=(self.grid_h, self.grid_w), dtype=int)
        return grid

    def set_madori_info(self, madori_info: OrderedDict):
        self.madori_info = madori_info

    def get_madori_info(self) -> OrderedDict:
        return self.madori_info.values()

    # positionsに基づいて間取り配置
    def reset_madori(self, grid, positions):
        grid = self.init_grid()
        for madori_name, madori_pos in positions.items():
            madori_code = self.madori_info[madori_name].code
            madori_w, madori_h = self.madori_info[madori_name].width, self.madori_info[madori_name].height
            madori_x, madori_y = madori_pos[0], madori_pos[1]
            grid[madori_y:madori_y + madori_h, madori_x:madori_x + madori_w] = madori_code

        return grid

    # 配置可能な場所を探して配置
    def set_madori(self, grid, positions, target_name: str, neighbor_name = None, madori_choices: dict = None):
        target_code = self.madori_info[target_name].code
        target_w, target_h = self.madori_info[target_name].width, self.madori_info[target_name].height

        if neighbor_name is not None:
            neighbor_code = self.madori_info[neighbor_name].code
            neighbor_w, neighbor_h = self.madori_info[neighbor_name].width, self.madori_info[neighbor_name].height
            neighbor_x, neighbor_y = positions[neighbor_name][0], positions[neighbor_name][1]

        if madori_choices is None or neighbor_name is None:
            # 配置候補が全く何も無いとき→四隅に配置 (最初に玄関を配置する想定)
            madori_choices = dict()
            madori_choice_list = [(0, 0), (0, self.grid_h - target_h), (self.grid_w - target_w, 0), (self.grid_w - target_w, self.grid_h - target_h)]
        elif target_name not in madori_choices:
            # 今回対象とする間取りの配置候補が無いとき→候補を作る
            madori_choice_list = []
            for x in range(self.grid_w):
                for y in range(self.grid_h):
                    if x + target_w == neighbor_x and neighbor_y - target_h < y < neighbor_y + neighbor_h and y + target_h <= self.grid_h:
                        # 左
                        madori_choice_list.append((x, y))
                    elif x == neighbor_x + neighbor_w and neighbor_y - target_h < y < neighbor_y + neighbor_h and y + target_h <= self.grid_h and x + target_w <= self.grid_w:
                        # 右
                        madori_choice_list.append((x, y))
                    elif y + target_h == neighbor_y and neighbor_x - target_w < x < neighbor_x + neighbor_w and x + target_w <= self.grid_w:
                        # 上
                        madori_choice_list.append((x, y))
                    elif y == neighbor_y + neighbor_h and neighbor_x - target_w < x < neighbor_x + neighbor_w and x + target_w <= self.grid_w and y + target_h <= self.grid_h:
                        # 下
                        madori_choice_list.append((x, y))
        else:
            # 配置候補があるとき (再配置)
            madori_choice_list = madori_choices[target_name]

        # 候補地リストからランダム選択
        for _ in range(len(madori_choice_list)):
            choice_item = random.choice(madori_choice_list)
            madori_choice_list.remove(choice_item)
            # 左上～右下の矩形が全て0 (未配置) なら配置可能
            if grid[choice_item[1]:choice_item[1] + target_h, choice_item[0]:choice_item[0] + target_w].sum() == 0:
                grid[choice_item[1]:choice_item[1] + target_h, choice_item[0]:choice_item[0] + target_w] = target_code
                # 配置情報を記録
                positions[target_name] = choice_item
                # 残りの候補地も控えておく (再配置時に使用)
                madori_choices[target_name] = madori_choice_list
                return grid, positions, madori_choices
                break

        # 候補リストを使い尽くしたら、1つ前の間取りからやり直す
        prev_madori = next(reversed(positions))
        prev_neighbor_madori = self.madori_info[prev_madori].neighbor_name
        del positions[prev_madori]
        grid = self.reset_madori(grid, positions)
        grid, positions, madori_choices = self.set_madori(grid, positions, prev_madori, prev_neighbor_madori, madori_choices)
        # 本来置こうとした物を配置
        grid, positions, madori_choices = self.set_madori(grid, positions, target_name, neighbor_name, madori_choices)
        return grid, positions, madori_choices

# 廊下（Corridor）用のMadori定義を追加
corridor = Madori(name='C', code=7, width=1, height=1, neighbor_name=None)

# LDKサイズを柔軟に設定できる関数
def create_madori_odict(L_size=(4,3), D_size=(3,2), K_size=(2,2), UT_size=(2,2)):
    """
    LDKのサイズを可変にした間取り情報を作成する。
    E, B, Tは固定サイズ。UTは脱衣所。
    
    Args:
        L_size: リビングのサイズ (width, height)
        D_size: ダイニングのサイズ (width, height)
        K_size: キッチンのサイズ (width, height)
        UT_size: 脱衣所のサイズ (width, height)
    
    Returns:
        間取り情報のOrderedDict
    """
    return OrderedDict(
        E=Madori('E', 1, 2, 2, None),       # 玄関（固定）
        L=Madori('L', 2, L_size[0], L_size[1], 'E'),
        K=Madori('K', 4, K_size[0], K_size[1], 'L'),  # キッチンはリビングに隣接
        D=Madori('D', 3, D_size[0], D_size[1], 'K'),  # ダイニングはキッチンに隣接（変更）
        B=Madori('B', 5, 2, 2, 'L'),        # バスルーム（固定）
        T=Madori('T', 6, 1, 2, 'B'),        # トイレ（固定）
        UT=Madori('UT', 8, UT_size[0], UT_size[1], 'B'),  # 脱衣所（バスルームに隣接）
        C=corridor                           # 廊下
    )

def arrange_rooms_in_rows(grid, site: Site, order: list[str]):
    """
    左上を起点に、指定した順番(order)で効率的に部屋を配置する。
    横方向に配置していき、スペース不足なら次の行へ移る。
    
    縦方向のスペースも最大限活用するために、各行を埋めてから次の行へ進む。
    
    Args:
        grid: 2次元numpy配列 (site.init_grid() した後のもの)
        site: Siteオブジェクト
        order: 配置する部屋名のリスト (例: ["L","D","K","E","B","T"])
    
    Returns:
        配置後の grid, positions(OrderedDict)
    """
    positions = OrderedDict()
    row_top = 0
    row_height = 0
    x_pos = 0  # 左端から開始
    
    # まだ配置していない部屋のリスト
    remaining_rooms = list(order)
    
    # グリッドサイズを取得
    grid_h, grid_w = grid.shape
    
    # すべての部屋が配置されるまで繰り返す
    while remaining_rooms:
        # 現在の行に配置できる部屋を探す
        placed_any = False
        
        # 配置できる部屋を探す
        for i, room_name in enumerate(remaining_rooms[:]):  # コピーを使ってループ
            if room_name not in site.madori_info:
                remaining_rooms.remove(room_name)  # 無効な部屋名はスキップ
                continue
                
            madori = site.madori_info[room_name]
            w = madori.width
            h = madori.height
            
            # 現在の行に置けるかチェック
            if x_pos + w <= grid_w and row_top + h <= grid_h:
                # 配置
                start_x = x_pos
                start_y = row_top
                end_x = x_pos + w
                end_y = row_top + h
                
                # すでに埋まっているか確認
                if np.any(grid[start_y:end_y, start_x:end_x] != 0):
                    # 次の部屋を試す
                    continue
                
                grid[start_y:end_y, start_x:end_x] = madori.code
                positions[room_name] = (start_x, start_y)
                
                # row_heightを更新
                if h > row_height:
                    row_height = h
                
                # x_posを進める
                x_pos += w
                
                # 配置した部屋をリストから削除
                remaining_rooms.remove(room_name)
                placed_any = True
                break
        
        # 現在の行にどの部屋も配置できなかった場合
        if not placed_any:
            # 次の行へ移動
            row_top += row_height
            x_pos = 0
            row_height = 0
            
            # もし全部の行を試しても配置できない場合はループを抜ける
            if row_top >= grid_h:
                break

    return grid, positions

def fill_corridor(grid, corridor_code=7):
    """
    空きスペース（0）を廊下コードで埋める
    
    Args:
        grid: 配置済みの2次元numpy配列
        corridor_code: 廊下のコード
    
    Returns:
        廊下埋め込み後のgrid
    """
    mask_empty = (grid == 0)
    grid[mask_empty] = corridor_code
    return grid

def process_large_corridors(grid, corridor_code=7, min_room_size=4):
    """
    広い廊下領域を見つけて追加部屋（R1, R2など）に変換し、
    残りの部分を1マス幅の廊下にする
    
    Args:
        grid: 部屋と廊下が配置されたグリッド
        corridor_code: 廊下に使用されるコード
        min_room_size: 部屋とみなす最小サイズ（セル数）
    
    Returns:
        更新されたグリッド、新しい部屋の辞書、新しい部屋の数
    """
    # 廊下領域を見つける
    corridor_mask = (grid == corridor_code)
    
    # 廊下がない場合は変更なし
    if not np.any(corridor_mask):
        return grid, {}, 0
    
    # 連結領域を見つける
    labeled_array, num_features = ndimage.label(corridor_mask)
    
    # 各領域を処理
    new_room_count = 0
    new_rooms = {}
    
    for region_id in range(1, num_features + 1):
        region_mask = (labeled_array == region_id)
        region_size = np.sum(region_mask)
        
        if region_size >= min_room_size:
            # 寸法を計算
            y_indices, x_indices = np.where(region_mask)
            min_y, max_y = y_indices.min(), y_indices.max()
            min_x, max_x = x_indices.min(), x_indices.max()
            height = max_y - min_y + 1
            width = max_x - min_x + 1
            
            # 変換する価値があるか確認（極端に細長くない）
            aspect_ratio = max(width / height, height / width)
            if aspect_ratio <= 3:  # あまり細長くない場合
                new_room_count += 1
                new_room_code = 10 + new_room_count
                room_name = f"R{new_room_count}"
                
                # 部屋情報を保存
                new_rooms[room_name] = (min_y, min_x, height, width)
                
                # グリッドを更新
                grid[region_mask] = new_room_code
    
    return grid, new_rooms, new_room_count

def find_largest_empty_rectangle(grid):
    """
    グリッド内の最大の空の長方形を見つける
    
    Args:
        grid: 2次元numpy配列
    
    Returns:
        (x, y, width, height) または None
    """
    grid_h, grid_w = grid.shape
    empty_mask = (grid == 0).astype(np.uint8)
    
    if not np.any(empty_mask):
        return None
    
    # 左上から探索
    max_area = 0
    max_rect = None
    
    for y in range(grid_h):
        for x in range(grid_w):
            if empty_mask[y, x] == 1:
                # この位置から最大の長方形を探す
                max_w = 1
                while x + max_w < grid_w and empty_mask[y, x + max_w] == 1:
                    max_w += 1
                
                max_h = 1
                valid = True
                while y + max_h < grid_h and valid:
                    for dx in range(max_w):
                        if empty_mask[y + max_h, x + dx] == 0:
                            valid = False
                            break
                    if valid:
                        max_h += 1
                
                area = max_w * max_h
                if area > max_area:
                    max_area = area
                    max_rect = (x, y, max_w, max_h)
    
    return max_rect

# 間取り情報 (間取り名, 間取り番号, 幅, 高さ, 隣接間取り名)
madori_odict = OrderedDict(
    E=Madori('E', 1, 2, 2, None), # 玄関
    L=Madori('L', 2, 5, 3, 'E'),
    K=Madori('K', 4, 2, 1, 'L'),  # キッチン：最低2マス (2×1=2マス)、リビングに隣接
    D=Madori('D', 3, 3, 2, 'K'),  # ダイニング：最低4マス (3×2=6マス)、キッチンに隣接
    B=Madori('B', 5, 2, 2, 'L'),
    T=Madori('T', 6, 1, 2, 'B')
)

# arrange_rooms_with_constraints関数を追加
def arrange_rooms_with_constraints(grid, site: Site, order: list[str]):
    """
    建築学的な制約を考慮した間取り配置を行う。
    特に水回りは外周（窓側）に配置し、部屋の用途に応じた配置を行う。
    敷地形状に関わらず、必ずすべての部屋を配置するように努める。
    
    Args:
        grid: 2次元numpy配列
        site: Siteオブジェクト
        order: 配置する部屋名のリスト
        
    Returns:
        配置後の grid, positions(OrderedDict)
    """
    positions = OrderedDict()
    grid_h, grid_w = grid.shape
    
    # 各部屋のサイズを明示的に確認
    room_sizes = {}
    for room_name, madori in site.madori_info.items():
        if room_name == 'C':  # 廊下はスキップ
            continue
        room_sizes[room_name] = (madori.width, madori.height)
    
    # グリッドが部屋を配置するのに十分な大きさかチェック
    min_grid_size_needed = sum(w * h for w, h in room_sizes.values())
    actual_grid_size = grid_h * grid_w
    scale_factor = 1.0
    
    # グリッドが小さすぎる場合、部屋サイズを縮小（ただし最小2x2は保持）
    if actual_grid_size < min_grid_size_needed:
        print(f"グリッドサイズ({actual_grid_size})が必要なサイズ({min_grid_size_needed})より小さいです。部屋を縮小します。")
        scale_factor = min(0.8, actual_grid_size / min_grid_size_needed)  # 最大20%まで縮小
        
        # サイズ調整（最小2x2を保持）
        for room_name in room_sizes:
            if room_name in ['T', 'E']:  # 玄関とトイレは最小サイズの例外
                continue
            w, h = room_sizes[room_name]
            new_w = max(2, int(w * scale_factor))
            new_h = max(2, int(h * scale_factor))
            
            # サイズを更新
            if room_name in site.madori_info:
                room = site.madori_info[room_name]
                site.madori_info[room_name] = Madori(
                    room.name, room.code, new_w, new_h, room.neighbor_name
                )
    
    # 既に配置された部屋を記録
    placed_rooms = set()
    
    # 玄関(E)を必ず最初に配置
    if "E" in site.madori_info:
        e_w = site.madori_info["E"].width
        e_h = site.madori_info["E"].height
        
        # 左下、右下、左上、右上の順で試行
        entry_positions = [
            (0, grid_h - e_h),                # 左下
            (grid_w - e_w, grid_h - e_h),     # 右下
            (0, 0),                           # 左上
            (grid_w - e_w, 0)                 # 右上
        ]
        
        for pos in entry_positions:
            x, y = pos
            if x >= 0 and y >= 0 and x + e_w <= grid_w and y + e_h <= grid_h:
                if np.all(grid[y:y+e_h, x:x+e_w] == 0):
                    grid[y:y+e_h, x:x+e_w] = site.madori_info["E"].code
                    positions["E"] = (x, y)
                    placed_rooms.add("E")
                    break
        
        # どの位置にも配置できなかった場合は強制的に左下に配置
        if "E" not in placed_rooms:
            x, y = 0, max(0, grid_h - e_h)
            grid[y:min(y+e_h, grid_h), x:min(x+e_w, grid_w)] = site.madori_info["E"].code
            positions["E"] = (x, y)
            placed_rooms.add("E")
    
    # リビング(L)を配置
    if "L" in site.madori_info and "L" not in placed_rooms:
        l_w = site.madori_info["L"].width
        l_h = site.madori_info["L"].height
        
        # 玄関の近くに配置
        if "E" in positions:
            ex, ey = positions["E"]
            e_w = site.madori_info["E"].width
            e_h = site.madori_info["E"].height
            
            # リビングの候補位置
            living_positions = [
                (ex + e_w, ey),          # 玄関の右
                (ex - l_w, ey),          # 玄関の左
                (ex, ey - l_h),          # 玄関の上
                (ex, ey + e_h)           # 玄関の下
            ]
            
            for pos in living_positions:
                x, y = pos
                # グリッド内かつ未使用領域かチェック
                if (x >= 0 and y >= 0 and 
                    x + l_w <= grid_w and y + l_h <= grid_h and
                    np.all(grid[y:y+l_h, x:x+l_w] == 0)):
                    grid[y:y+l_h, x:x+l_w] = site.madori_info["L"].code
                    positions["L"] = (x, y)
                    placed_rooms.add("L")
                    break
        
        # どこにも配置できなかった場合は中央付近に強制配置
        if "L" not in placed_rooms:
            center_x = max(0, (grid_w - l_w) // 2)
            center_y = max(0, (grid_h - l_h) // 2)
            
            # 中央から外側に探索
            for offset in range(max(grid_w, grid_h)):
                for dx in range(-offset, offset+1):
                    for dy in range(-offset, offset+1):
                        if abs(dx) + abs(dy) != offset:  # 特定の距離にあるマスのみ
                            continue
                        
                        x = center_x + dx
                        y = center_y + dy
                        
                        if (x >= 0 and y >= 0 and 
                            x + l_w <= grid_w and y + l_h <= grid_h and
                            np.all(grid[y:y+l_h, x:x+l_w] == 0)):
                            grid[y:y+l_h, x:x+l_w] = site.madori_info["L"].code
                            positions["L"] = (x, y)
                            placed_rooms.add("L")
                            break
                    if "L" in placed_rooms:
                        break
                if "L" in placed_rooms:
                    break
            
            # それでも配置できない場合は強制的に配置
            if "L" not in placed_rooms:
                for y in range(grid_h - l_h + 1):
                    for x in range(grid_w - l_w + 1):
                        if np.sum(grid[y:y+l_h, x:x+l_w]) == 0:  # 完全に空いているエリア
                            grid[y:y+l_h, x:x+l_w] = site.madori_info["L"].code
                            positions["L"] = (x, y)
                            placed_rooms.add("L")
                            break
                    if "L" in placed_rooms:
                        break
    
    # LDK関連の配置（Dを先に配置し、次にKを配置）
    # ダイニング(D)を配置 - リビングに隣接
    if "D" in site.madori_info and "D" not in placed_rooms and "L" in positions:
        lx, ly = positions["L"]
        l_w = site.madori_info["L"].width
        l_h = site.madori_info["L"].height
        d_w = site.madori_info["D"].width
        d_h = site.madori_info["D"].height
        
        # ダイニングの候補位置（リビングの隣接）
        dining_positions = [
            (lx + l_w, ly),          # リビングの右
            (lx - d_w, ly),          # リビングの左
            (lx, ly - d_h),          # リビングの上
            (lx, ly + l_h)           # リビングの下
        ]
        
        for pos in dining_positions:
            x, y = pos
            if (x >= 0 and y >= 0 and 
                x + d_w <= grid_w and y + d_h <= grid_h and
                np.all(grid[y:y+d_h, x:x+d_w] == 0)):
                grid[y:y+d_h, x:x+d_w] = site.madori_info["D"].code
                positions["D"] = (x, y)
                placed_rooms.add("D")
                break
        
        # 隣接配置できない場合は最も近い空きエリアを探す
        if "D" not in placed_rooms:
            best_distance = float('inf')
            best_pos = None
            
            for y in range(grid_h - d_h + 1):
                for x in range(grid_w - d_w + 1):
                    if np.all(grid[y:y+d_h, x:x+d_w] == 0):
                        dist = abs(x - lx) + abs(y - ly)  # マンハッタン距離
                        if dist < best_distance:
                            best_distance = dist
                            best_pos = (x, y)
            
            if best_pos:
                x, y = best_pos
                grid[y:y+d_h, x:x+d_w] = site.madori_info["D"].code
                positions["D"] = (x, y)
                placed_rooms.add("D")
    
    # キッチン(K)を配置 - ダイニングに隣接、または次善としてリビングに隣接
    if "K" in site.madori_info and "K" not in placed_rooms:
        k_w = site.madori_info["K"].width
        k_h = site.madori_info["K"].height
        
        # ダイニングがある場合はダイニングに隣接
        if "D" in positions:
            dx, dy = positions["D"]
            d_w = site.madori_info["D"].width
            d_h = site.madori_info["D"].height
            
            kitchen_positions = [
                (dx + d_w, dy),          # ダイニングの右
                (dx - k_w, dy),          # ダイニングの左
                (dx, dy - k_h),          # ダイニングの上
                (dx, dy + d_h)           # ダイニングの下
            ]
            
            # 玄関から遠い位置を優先
            if "E" in positions:
                ex, ey = positions["E"]
                kitchen_positions.sort(key=lambda pos: -((pos[0]-ex)**2 + (pos[1]-ey)**2))
            
            for pos in kitchen_positions:
                x, y = pos
                if (x >= 0 and y >= 0 and 
                    x + k_w <= grid_w and y + k_h <= grid_h and
                    np.all(grid[y:y+k_h, x:x+k_w] == 0)):
                    grid[y:y+k_h, x:x+k_w] = site.madori_info["K"].code
                    positions["K"] = (x, y)
                    placed_rooms.add("K")
                    break
        
        # ダイニングがないか隣接できない場合はリビングに隣接
        if "K" not in placed_rooms and "L" in positions:
            lx, ly = positions["L"]
            l_w = site.madori_info["L"].width
            l_h = site.madori_info["L"].height
            
            kitchen_positions = [
                (lx + l_w, ly),          # リビングの右
                (lx - k_w, ly),          # リビングの左
                (lx, ly - k_h),          # リビングの上
                (lx, ly + l_h)           # リビングの下
            ]
            
            # 玄関から遠い位置を優先
            if "E" in positions:
                ex, ey = positions["E"]
                kitchen_positions.sort(key=lambda pos: -((pos[0]-ex)**2 + (pos[1]-ey)**2))
            
            for pos in kitchen_positions:
                x, y = pos
                if (x >= 0 and y >= 0 and 
                    x + k_w <= grid_w and y + k_h <= grid_h and
                    np.all(grid[y:y+k_h, x:x+k_w] == 0)):
                    grid[y:y+k_h, x:x+k_w] = site.madori_info["K"].code
                    positions["K"] = (x, y)
                    placed_rooms.add("K")
                    break
        
        # どこにも配置できない場合は空いているところに配置
        if "K" not in placed_rooms:
            for y in range(grid_h - k_h + 1):
                for x in range(grid_w - k_w + 1):
                    if np.all(grid[y:y+k_h, x:x+k_w] == 0):
                        grid[y:y+k_h, x:x+k_w] = site.madori_info["K"].code
                        positions["K"] = (x, y)
                        placed_rooms.add("K")
                        break
                if "K" in placed_rooms:
                    break
    
    # 水回り（バス、トイレ、脱衣所）をまとめて外周に配置
    # まずバスルーム(B)を配置
    if "B" in site.madori_info and "B" not in placed_rooms:
        b_w = site.madori_info["B"].width
        b_h = site.madori_info["B"].height
        
        # 外周位置の候補を生成（窓が必要な部屋用）
        perimeter_positions = []
        
        # 左端
        for y in range(grid_h - b_h + 1):
            perimeter_positions.append((0, y))
        
        # 右端
        for y in range(grid_h - b_h + 1):
            perimeter_positions.append((grid_w - b_w, y))
        
        # 上端
        for x in range(grid_w - b_w + 1):
            perimeter_positions.append((x, 0))
        
        # 下端
        for x in range(grid_w - b_w + 1):
            perimeter_positions.append((x, grid_h - b_h))
        
        # 外周をランダムに試す
        random.shuffle(perimeter_positions)
        for pos in perimeter_positions:
            x, y = pos
            if np.all(grid[y:y+b_h, x:x+b_w] == 0):
                grid[y:y+b_h, x:x+b_w] = site.madori_info["B"].code
                positions["B"] = (x, y)
                placed_rooms.add("B")
                break
        
        # 外周に配置できない場合は任意の場所に配置
        if "B" not in placed_rooms:
            for y in range(grid_h - b_h + 1):
                for x in range(grid_w - b_w + 1):
                    if np.all(grid[y:y+b_h, x:x+b_w] == 0):
                        grid[y:y+b_h, x:x+b_w] = site.madori_info["B"].code
                        positions["B"] = (x, y)
                        placed_rooms.add("B")
                        break
                if "B" in placed_rooms:
                    break
    
    # 脱衣所(UT)を配置 - バスルームに隣接
    if "UT" in site.madori_info and "UT" not in placed_rooms:
        ut_w = site.madori_info["UT"].width
        ut_h = site.madori_info["UT"].height
        
        # バスルームに隣接配置
        if "B" in positions:
            bx, by = positions["B"]
            b_w = site.madori_info["B"].width
            b_h = site.madori_info["B"].height
            
            ut_positions = [
                (bx + b_w, by),          # バスルームの右
                (bx - ut_w, by),         # バスルームの左
                (bx, by - ut_h),         # バスルームの上
                (bx, by + b_h)           # バスルームの下
            ]
            
            for pos in ut_positions:
                x, y = pos
                if (x >= 0 and y >= 0 and 
                    x + ut_w <= grid_w and y + ut_h <= grid_h and
                    np.all(grid[y:y+ut_h, x:x+ut_w] == 0)):
                    grid[y:y+ut_h, x:x+ut_w] = site.madori_info["UT"].code
                    positions["UT"] = (x, y)
                    placed_rooms.add("UT")
                    break
        
        # バスルームに隣接できない場合は任意の場所に配置
        if "UT" not in placed_rooms:
            for y in range(grid_h - ut_h + 1):
                for x in range(grid_w - ut_w + 1):
                    if np.all(grid[y:y+ut_h, x:x+ut_w] == 0):
                        grid[y:y+ut_h, x:x+ut_w] = site.madori_info["UT"].code
                        positions["UT"] = (x, y)
                        placed_rooms.add("UT")
                        break
                if "UT" in placed_rooms:
                    break
    
    # トイレ(T)を配置 - バスルームまたは脱衣所の近くに
    if "T" in site.madori_info and "T" not in placed_rooms:
        t_w = site.madori_info["T"].width
        t_h = site.madori_info["T"].height
        
        # バスルームに隣接
        if "B" in positions:
            bx, by = positions["B"]
            b_w = site.madori_info["B"].width
            b_h = site.madori_info["B"].height
            
            toilet_positions = [
                (bx + b_w, by),          # バスルームの右
                (bx - t_w, by),          # バスルームの左
                (bx, by - t_h),          # バスルームの上
                (bx, by + b_h)           # バスルームの下
            ]
            
            for pos in toilet_positions:
                x, y = pos
                if (x >= 0 and y >= 0 and 
                    x + t_w <= grid_w and y + t_h <= grid_h and
                    np.all(grid[y:y+t_h, x:x+t_w] == 0)):
                    grid[y:y+t_h, x:x+t_w] = site.madori_info["T"].code
                    positions["T"] = (x, y)
                    placed_rooms.add("T")
                    break
        
        # バスルームに隣接できない場合は脱衣所に隣接
        if "T" not in placed_rooms and "UT" in positions:
            utx, uty = positions["UT"]
            ut_w = site.madori_info["UT"].width
            ut_h = site.madori_info["UT"].height
            
            toilet_positions = [
                (utx + ut_w, uty),       # 脱衣所の右
                (utx - t_w, uty),        # 脱衣所の左
                (utx, uty - t_h),        # 脱衣所の上
                (utx, uty + ut_h)        # 脱衣所の下
            ]
            
            for pos in toilet_positions:
                x, y = pos
                if (x >= 0 and y >= 0 and 
                    x + t_w <= grid_w and y + t_h <= grid_h and
                    np.all(grid[y:y+t_h, x:x+t_w] == 0)):
                    grid[y:y+t_h, x:x+t_w] = site.madori_info["T"].code
                    positions["T"] = (x, y)
                    placed_rooms.add("T")
                    break
        
        # 両方に隣接できない場合は任意の場所に配置
        if "T" not in placed_rooms:
            for y in range(grid_h - t_h + 1):
                for x in range(grid_w - t_w + 1):
                    if np.all(grid[y:y+t_h, x:x+t_w] == 0):
                        grid[y:y+t_h, x:x+t_w] = site.madori_info["T"].code
                        positions["T"] = (x, y)
                        placed_rooms.add("T")
                        break
                if "T" in placed_rooms:
                    break
    
    # 残りの大きい部屋（R1, R2など）を配置 - 必ず四角形にする
    # グリッドに配置されていない部屋名のリストを作成
    remaining_rooms = set(site.madori_info.keys()) - placed_rooms - {"C"}
    
    # 部屋R1, R2を追加（必要なら）
    room_count = 1
    while room_count <= 2:  # R1とR2のみサポート
        room_name = f"R{room_count}"
        
        # すでに部屋が存在するならスキップ
        if room_name in site.madori_info:
            room_count += 1
            continue
        
        # まだ大きな空きスペースがあるか確認
        max_rect = find_largest_empty_rectangle(grid)
        if max_rect:
            x, y, width, height = max_rect
            
            # 最低2×2サイズを確保
            if width >= 2 and height >= 2:
                room_code = 10 + room_count
                grid[y:y+height, x:x+width] = room_code
                
                # 新しい部屋を追加
                site.madori_info[room_name] = Madori(room_name, room_code, width, height, None)
                positions[room_name] = (x, y)
                placed_rooms.add(room_name)
        
        room_count += 1
    
    return grid, positions

if __name__ == "__main__":
    # @title 敷地の縦横を設定
    site_w = 10 # @param {"type":"integer","placeholder":"敷地幅"}
    site_h = 10 # @param {"type":"integer","placeholder":"敷地高さ"}

    # 敷地を引く (縦・横マス数)
    site = Site(site_w, site_h)
    site.set_madori_info(madori_odict)

    # マス目と位置情報
    grid = site.init_grid()
    positions = OrderedDict()

    # 間取りを配置
    madori_choices = dict()
    for madori in site.get_madori_info():
        madori_name = madori.name
        neighbor_name = madori.neighbor_name
        grid, positions, madori_choices = site.set_madori(grid, positions, madori_name, neighbor_name, madori_choices)

    # 間取り確認
    print(grid)
    print(positions)
    print(madori_choices)

    # コード→名前に変換
    replace_dict = {}
    for madori in site.get_madori_info():
        replace_dict[madori.code] = madori.name
    replace_dict[0] = ' '
    replace_dict

    df_grid = pd.DataFrame(grid)
    df_grid.replace(replace_dict, inplace=True)
    df_grid

    # 新しい配置方法をテスト
    print("\n新しい右上整列配置方法のテスト:")
    # L, D, K だけ柔軟に大きさ変更 (Dは最低4マス、Kは最低2マスに設定)
    my_madori_odict = create_madori_odict(L_size=(4,3), D_size=(3,2), K_size=(2,1))
    site.set_madori_info(my_madori_odict)

    # 初期化
    new_grid = site.init_grid()

    # 配置順は例えば E -> L -> K -> D -> B -> T
    order = ["E","L","K","D","B","T"]  # KとDが隣接するよう順序変更

    new_grid, new_positions = arrange_rooms_with_constraints(new_grid, site, order)
    
    # 余白を廊下(C)で埋める
    new_grid = fill_corridor(new_grid, corridor_code=7)

    # 可視化のためにDataFrame化
    # コード→名前変換
    new_replace_dict = {}
    for madori_name, madori in site.madori_info.items():
        new_replace_dict[madori.code] = madori.name
    new_replace_dict[0] = ' '
    
    new_df_grid = pd.DataFrame(new_grid)
    new_df_grid.replace(new_replace_dict, inplace=True)
    print(new_df_grid)
    print(new_positions)

    # 各間取りの矩形情報を取得
    madori_rects = {}
    for madori_name, pos in positions.items():
        madori = site.madori_info[madori_name]
        x, y = pos
        madori_rects[madori_name] = (x, y, madori.width, madori.height, madori_name)

    # 画像サイズを設定
    fig, ax = plt.subplots(figsize=(site.grid_w, site.grid_h))

    # 各部屋の色を設定
    colors = {'E': 'lightcoral',
              'L': 'lightblue',
              'D': 'lightgreen',
              'K': 'lightyellow',
              'B': 'lightpink',
              'T': 'lightgray'}

    # 座標系を左上に変更
    ax.set_xlim(0, site.grid_w)
    ax.set_ylim(site.grid_h, 0) # y軸を反転

    for madori_name, rect_info in madori_rects.items():
        x, y, width, height, label = rect_info
        rect = patches.Rectangle((x, y), width, height, linewidth=2, edgecolor='black', facecolor=colors.get(madori_name, 'lightblue')) # 色分けを適用
        ax.add_patch(rect)
        ax.text(x + width / 2, y + height / 2, label, ha='center', va='center', fontsize=24)

    # 軸目盛りと補助線を非表示にする
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')

    # 画像を表示
    plt.show()