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

def arrange_rooms_with_constraints(grid, site: Site, order: list[str]):
    """
    建築学的な制約を考慮した間取り配置を行う。
    特に水回りは外周（窓側）に配置し、部屋の用途に応じた配置を行う。
    
    Args:
        grid: 2次元numpy配列
        site: Siteオブジェクト
        order: 配置する部屋名のリスト
        
    Returns:
        配置後の grid, positions(OrderedDict)
    """
    positions = OrderedDict()
    grid_h, grid_w = grid.shape
    
    # まだ配置していない部屋のリスト
    remaining_rooms = list(order)
    
    # 1. まず玄関(E)を左下または右下に配置
    if "E" in remaining_rooms:
        # 玄関の候補位置（左下・右下）
        entry_positions = [(0, grid_h-2), (grid_w-2, grid_h-2)]
        
        for pos in entry_positions:
            x, y = pos
            if "E" in site.madori_info:
                madori = site.madori_info["E"]
                w, h = madori.width, madori.height
                
                # グリッド範囲内に収まるか確認
                if x + w <= grid_w and y + h <= grid_h:
                    # このセルが未使用か確認
                    if np.all(grid[y:y+h, x:x+w] == 0):
                        grid[y:y+h, x:x+w] = madori.code
                        positions["E"] = (x, y)
                        remaining_rooms.remove("E")
                        break
    
    # 2. リビング(L)をグリッドの中央付近に配置
    if "L" in remaining_rooms:
        # リビングの配置候補（中央付近を優先）
        center_x, center_y = grid_w // 2 - 2, grid_h // 2 - 2
        living_positions = [
            (center_x, center_y),
            (center_x - 1, center_y),
            (center_x + 1, center_y),
            (center_x, center_y - 1),
            (center_x, center_y + 1)
        ]
        
        for pos in living_positions:
            x, y = pos
            if "L" in site.madori_info:
                madori = site.madori_info["L"]
                w, h = madori.width, madori.height
                
                # グリッド範囲内に収まるか確認
                if x >= 0 and x + w <= grid_w and y >= 0 and y + h <= grid_h:
                    # このセルが未使用か確認
                    if np.all(grid[y:y+h, x:x+w] == 0):
                        grid[y:y+h, x:x+w] = madori.code
                        positions["L"] = (x, y)
                        remaining_rooms.remove("L")
                        break
    
    # 3. キッチン(K)とダイニング(D)をリビングの近くに配置
    # まずキッチンを配置
    if "K" in remaining_rooms and "L" in positions:
        lx, ly = positions["L"]
        l_madori = site.madori_info["L"]
        lw, lh = l_madori.width, l_madori.height
        
        # キッチンの候補位置（リビングの周辺を優先）
        k_positions = [
            (lx + lw, ly),          # リビングの右
            (lx - site.madori_info["K"].width, ly),  # リビングの左
            (lx, ly - site.madori_info["K"].height), # リビングの上
            (lx, ly + lh)           # リビングの下
        ]
        
        for pos in k_positions:
            x, y = pos
            if "K" in site.madori_info:
                madori = site.madori_info["K"]
                w, h = madori.width, madori.height
                
                # グリッド範囲内に収まるか確認
                if x >= 0 and x + w <= grid_w and y >= 0 and y + h <= grid_h:
                    # このセルが未使用か確認
                    if np.all(grid[y:y+h, x:x+w] == 0):
                        grid[y:y+h, x:x+w] = madori.code
                        positions["K"] = (x, y)
                        remaining_rooms.remove("K")
                        break
    
    # 次にダイニングを配置（キッチンの隣）
    if "D" in remaining_rooms and "K" in positions:
        kx, ky = positions["K"]
        k_madori = site.madori_info["K"]
        kw, kh = k_madori.width, k_madori.height
        
        # ダイニングの候補位置（キッチンの周辺を優先）
        d_positions = [
            (kx + kw, ky),          # キッチンの右
            (kx - site.madori_info["D"].width, ky),  # キッチンの左
            (kx, ky - site.madori_info["D"].height), # キッチンの上
            (kx, ky + kh)           # キッチンの下
        ]
        
        for pos in d_positions:
            x, y = pos
            if "D" in site.madori_info:
                madori = site.madori_info["D"]
                w, h = madori.width, madori.height
                
                # グリッド範囲内に収まるか確認
                if x >= 0 and x + w <= grid_w and y >= 0 and y + h <= grid_h:
                    # このセルが未使用か確認
                    if np.all(grid[y:y+h, x:x+w] == 0):
                        grid[y:y+h, x:x+w] = madori.code
                        positions["D"] = (x, y)
                        remaining_rooms.remove("D")
                        break
    
    # 4. 水回り（バス、トイレ、脱衣所）を外周に配置
    water_rooms = [r for r in remaining_rooms if r in ["B", "T", "UT"]]
    
    # 外周の座標候補（外側のエッジに沿う）
    edge_positions = []
    
    # 左端
    for y in range(1, grid_h - 2):
        edge_positions.append((0, y))
    
    # 右端
    for y in range(1, grid_h - 2):
        edge_positions.append((grid_w - 2, y))
    
    # 上端
    for x in range(1, grid_w - 2):
        edge_positions.append((x, 0))
    
    # 下端
    for x in range(1, grid_w - 2):
        edge_positions.append((x, grid_h - 2))
    
    # 水回りの部屋を外周に配置
    for room_name in water_rooms:
        if room_name in site.madori_info:
            madori = site.madori_info[room_name]
            w, h = madori.width, madori.height
            
            # 外周の候補位置を試す
            for pos in edge_positions:
                x, y = pos
                
                # グリッド範囲内に収まるか確認
                if x + w <= grid_w and y + h <= grid_h:
                    # このセルが未使用か確認
                    if np.all(grid[y:y+h, x:x+w] == 0):
                        grid[y:y+h, x:x+w] = madori.code
                        positions[room_name] = (x, y)
                        remaining_rooms.remove(room_name)
                        break
    
    # 5. 残りの部屋を配置（通常の配置ロジック）
    # 左上から順に配置
    row_top = 0
    row_height = 0
    x_pos = 0
    
    while remaining_rooms:
        placed_any = False
        
        for room_name in remaining_rooms[:]:
            if room_name not in site.madori_info:
                remaining_rooms.remove(room_name)
                continue
                
            madori = site.madori_info[room_name]
            w = madori.width
            h = madori.height
            
            if x_pos + w <= grid_w and row_top + h <= grid_h:
                # このセルが未使用か確認
                if np.all(grid[row_top:row_top+h, x_pos:x_pos+w] == 0):
                    grid[row_top:row_top+h, x_pos:x_pos+w] = madori.code
                    positions[room_name] = (x_pos, row_top)
                    
                    if h > row_height:
                        row_height = h
                    
                    x_pos += w
                    remaining_rooms.remove(room_name)
                    placed_any = True
                    break
                else:
                    # このセルは使用済み、次のx位置を試す
                    x_pos += 1
                    if x_pos + w > grid_w:
                        break
            
        if not placed_any:
            row_top += row_height if row_height > 0 else 1
            x_pos = 0
            row_height = 0
            
            if row_top >= grid_h:
                break
    
    return grid, positions

# 間取り情報 (間取り名, 間取り番号, 幅, 高さ, 隣接間取り名)
madori_odict = OrderedDict(
    E=Madori('E', 1, 2, 2, None), # 玄関
    L=Madori('L', 2, 5, 3, 'E'),
    K=Madori('K', 4, 2, 1, 'L'),  # キッチン：最低2マス (2×1=2マス)、リビングに隣接
    D=Madori('D', 3, 3, 2, 'K'),  # ダイニング：最低4マス (3×2=6マス)、キッチンに隣接
    B=Madori('B', 5, 2, 2, 'L'),
    T=Madori('T', 6, 1, 2, 'B')
)

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