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

    def get_madori_info(self):
        return self.madori_info.values()

    def reset_madori(self, grid, positions):
        """
        positions に基づき再配置。いったん全0にしてから再度コードを配置する
        """
        grid = self.init_grid()
        for madori_name, madori_pos in positions.items():
            madori_code = self.madori_info[madori_name].code
            madori_w = self.madori_info[madori_name].width
            madori_h = self.madori_info[madori_name].height
            madori_x, madori_y = madori_pos
            grid[madori_y : madori_y + madori_h, madori_x : madori_x + madori_w] = madori_code
        return grid

    def set_madori(
        self, 
        grid, 
        positions, 
        target_name: str, 
        neighbor_name=None, 
        madori_choices: dict=None,
        valid_mask: np.ndarray=None
    ):
        """
        指定した target_name の部屋を配置する。
        valid_maskがある場合は、配置しようとする領域がマスク内(=1)だけかどうかも判定する。
        """
        target_code = self.madori_info[target_name].code
        target_w = self.madori_info[target_name].width
        target_h = self.madori_info[target_name].height

        if neighbor_name is not None:
            neighbor_w = self.madori_info[neighbor_name].width
            neighbor_h = self.madori_info[neighbor_name].height
            neighbor_x, neighbor_y = positions[neighbor_name]

        if madori_choices is None or neighbor_name is None:
            # 最初の配置(玄関など)。四隅候補
            madori_choices = {}
            madori_choice_list = [
                (0, 0),
                (0, self.grid_h - target_h),
                (self.grid_w - target_w, 0),
                (self.grid_w - target_w, self.grid_h - target_h),
            ]
        elif target_name not in madori_choices:
            # neighborのまわりの候補を列挙
            madori_choice_list = []
            for x in range(self.grid_w):
                for y in range(self.grid_h):
                    # 左隣
                    if (x + target_w == neighbor_x 
                        and (neighbor_y - target_h) < y < (neighbor_y + neighbor_h)
                        and (y + target_h) <= self.grid_h):
                        madori_choice_list.append((x, y))
                    # 右隣
                    elif (x == neighbor_x + neighbor_w
                          and (neighbor_y - target_h) < y < (neighbor_y + neighbor_h)
                          and (y + target_h) <= self.grid_h
                          and (x + target_w) <= self.grid_w):
                        madori_choice_list.append((x, y))
                    # 上隣
                    elif (y + target_h == neighbor_y
                          and (neighbor_x - target_w) < x < (neighbor_x + neighbor_w)
                          and (x + target_w) <= self.grid_w):
                        madori_choice_list.append((x, y))
                    # 下隣
                    elif (y == neighbor_y + neighbor_h
                          and (neighbor_x - target_w) < x < (neighbor_x + neighbor_w)
                          and (x + target_w) <= self.grid_w
                          and (y + target_h) <= self.grid_h):
                        madori_choice_list.append((x, y))
        else:
            # 再配置時など
            madori_choice_list = madori_choices[target_name]

        # 候補地からランダム選択でトライ
        for _ in range(len(madori_choice_list)):
            choice_item = random.choice(madori_choice_list)
            madori_choice_list.remove(choice_item)
            cx, cy = choice_item
            # 配置領域が全部 0 かつ valid_mask があればその中も全部1かどうか確認
            region = grid[cy : cy+target_h, cx : cx+target_w]
            if np.any(region != 0):
                continue  # 既に使われている

            if valid_mask is not None:
                # 有効マスクかどうか
                submask = valid_mask[cy : cy+target_h, cx : cx+target_w]
                if np.any(submask != 1):
                    continue  # マスク外(=0)が混在している

            # ここまでOKなら配置
            grid[cy : cy+target_h, cx : cx+target_w] = target_code
            positions[target_name] = (cx, cy)
            madori_choices[target_name] = madori_choice_list
            return grid, positions, madori_choices

        # 候補が尽きた場合は前の部屋を置き直す
        prev_madori = next(reversed(positions))
        prev_neighbor_madori = self.madori_info[prev_madori].neighbor_name
        del positions[prev_madori]
        grid = self.reset_madori(grid, positions)
        grid, positions, madori_choices = self.set_madori(grid, positions, prev_madori, prev_neighbor_madori, madori_choices, valid_mask)
        # そしてまたターゲットをトライ
        grid, positions, madori_choices = self.set_madori(grid, positions, target_name, neighbor_name, madori_choices, valid_mask)
        return grid, positions, madori_choices

# 廊下（Corridor）用の定義
corridor = Madori(name='C', code=7, width=1, height=1, neighbor_name=None)

def create_madori_odict(L_size=(4,3), D_size=(3,2), K_size=(2,2), UT_size=(2,2)):
    """
    LDKのサイズを可変にした間取り情報を作成する。
    トイレ(T)は 幅1 x 高さ2 (2マス) で固定。
    """
    return OrderedDict(
        E=Madori('E', 1, 2, 2, None),         # 玄関（2×2固定）
        L=Madori('L', 2, L_size[0], L_size[1], 'E'),
        K=Madori('K', 4, K_size[0], K_size[1], 'L'), 
        D=Madori('D', 3, D_size[0], D_size[1], 'K'), 
        B=Madori('B', 5, 2, 2, 'L'),          # バスルーム (2×2)
        T=Madori('T', 6, 1, 2, 'B'),          # トイレ (1×2) ←2マスだけ
        UT=Madori('UT', 8, UT_size[0], UT_size[1], 'B'),
        C=corridor
    )

def arrange_rooms_in_rows(grid, site, order: list[str]):
    """
    左上から順に部屋を並べる簡易配置。
    """
    positions = OrderedDict()
    row_top = 0
    row_height = 0
    x_pos = 0
    remaining_rooms = list(order)

    grid_h, grid_w = grid.shape

    while remaining_rooms:
        placed_any = False

        for i, room_name in enumerate(remaining_rooms[:]):
            if room_name not in site.madori_info:
                remaining_rooms.remove(room_name)
                continue
            madori = site.madori_info[room_name]
            w = madori.width
            h = madori.height

            if x_pos + w <= grid_w and row_top + h <= grid_h:
                region = grid[row_top : row_top+h, x_pos : x_pos+w]
                if np.any(region != 0):
                    continue
                # 配置
                grid[row_top : row_top+h, x_pos : x_pos+w] = madori.code
                positions[room_name] = (x_pos, row_top)

                if h > row_height:
                    row_height = h
                x_pos += w

                remaining_rooms.remove(room_name)
                placed_any = True
                break

        if not placed_any:
            row_top += row_height
            x_pos = 0
            row_height = 0
            if row_top >= grid_h:
                break

    return grid, positions

def fill_corridor(grid, corridor_code=7):
    """
    空きスペースをすべて廊下コードで埋める
    """
    mask_empty = (grid == 0)
    grid[mask_empty] = corridor_code
    return grid

def process_large_corridors(grid, corridor_code=7, min_room_size=4):
    """
    廊下が大きく広がったエリアを追加部屋に変えるなどの処理
    """
    corridor_mask = (grid == corridor_code)
    if not np.any(corridor_mask):
        return grid, {}, 0

    labeled_array, num_features = ndimage.label(corridor_mask)
    new_room_count = 0
    new_rooms = {}

    for region_id in range(1, num_features + 1):
        region_mask = (labeled_array == region_id)
        region_size = np.sum(region_mask)
        if region_size >= min_room_size:
            y_indices, x_indices = np.where(region_mask)
            min_y, max_y = y_indices.min(), y_indices.max()
            min_x, max_x = x_indices.min(), x_indices.max()
            height = max_y - min_y + 1
            width = max_x - min_x + 1
            aspect_ratio = max(width / height, height / width)
            if aspect_ratio <= 3:
                new_room_count += 1
                new_code = 10 + new_room_count
                room_name = f"R{new_room_count}"
                new_rooms[room_name] = (min_y, min_x, height, width)
                grid[region_mask] = new_code

    return grid, new_rooms, new_room_count

def find_largest_empty_rectangle(grid):
    """
    グリッド内の最大の空の長方形を探す
    """
    grid_h, grid_w = grid.shape
    empty_mask = (grid == 0).astype(np.uint8)
    if not np.any(empty_mask):
        return None

    max_area = 0
    max_rect = None

    for y in range(grid_h):
        for x in range(grid_w):
            if empty_mask[y, x] == 1:
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

# サンプルの初期設定
madori_odict = OrderedDict(
    E=Madori('E', 1, 2, 2, None),   # 玄関
    L=Madori('L', 2, 5, 3, 'E'),
    K=Madori('K', 4, 2, 1, 'L'),
    D=Madori('D', 3, 3, 2, 'K'),
    B=Madori('B', 5, 2, 2, 'L'),
    # トイレを(1×2)=2マスで確定
    T=Madori('T', 6, 1, 2, 'B')
)

def arrange_rooms_with_constraints(grid, site, order: list[str], valid_mask=None):
    """
    建築学的な制約を考慮して部屋を配置し、さらにvalid_maskがあれば
    マスク外にはみ出さないようにする(=最初からマスク内セルだけで配置)。
    """
    positions = OrderedDict()
    grid_h, grid_w = grid.shape

    # 一旦、LやDなどは自由に大きさ変えてOK（ただしSiteが持つ madori_info に従う）
    # 玄関(E)をまず外周に(隅4箇所)配置
    placed_rooms = set()
    if "E" in site.madori_info:
        e_w = site.madori_info["E"].width
        e_h = site.madori_info["E"].height
        corners = [
            (0, grid_h - e_h),
            (grid_w - e_w, grid_h - e_h),
            (0, 0),
            (grid_w - e_w, 0)
        ]
        success = False
        for (cx, cy) in corners:
            if (cx >= 0 and cy >= 0 and 
                cx + e_w <= grid_w and cy + e_h <= grid_h):
                region = grid[cy : cy+e_h, cx : cx+e_w]
                if np.any(region != 0):
                    continue
                # mask判定
                if valid_mask is not None:
                    submask = valid_mask[cy : cy+e_h, cx : cx+e_w]
                    if np.any(submask != 1):
                        continue
                # OK
                grid[cy : cy+e_h, cx : cx+e_w] = site.madori_info["E"].code
                positions["E"] = (cx, cy)
                placed_rooms.add("E")
                success = True
                break

        if not success:
            # 強制配置
            x, y = 0, max(0, grid_h - e_h)
            grid[y : y+e_h, x : x+e_w] = site.madori_info["E"].code
            positions["E"] = (x, y)
            placed_rooms.add("E")

    # あとは順番に site.set_madori で配置
    madori_choices = dict()
    for name in order:
        if name == "E":
            continue  # 既に置いた
        neighbor = site.madori_info[name].neighbor_name if name in site.madori_info else None
        grid, positions, madori_choices = site.set_madori(
            grid, 
            positions, 
            name, 
            neighbor,
            madori_choices,
            valid_mask=valid_mask
        )
        placed_rooms.add(name)

    return grid, positions