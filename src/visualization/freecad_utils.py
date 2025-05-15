"""
FreeCADを使用して間取り図をCAD風に描画するためのユーティリティ関数
"""
import os
import sys
import tempfile
import numpy as np
import cv2
from PIL import Image
import logging
import io

# FreeCADのパスを追加
sys.path.append('/usr/lib/freecad-python3/lib')

try:
    import FreeCAD
    import Part
    import Draft
    import Sketcher
    import Arch
    FREECAD_AVAILABLE = True
except ImportError as e:
    logging.warning(f"FreeCADのインポートに失敗しました: {e}")
    FREECAD_AVAILABLE = False

logger = logging.getLogger(__name__)

# 部屋タイプごとの色定義
ROOM_COLORS = {
    'E': (102, 178, 255),   # 玄関
    'L': (144, 238, 144),   # リビング
    'D': (255, 191, 0),     # ダイニング
    'K': (147, 20, 255),    # キッチン
    'B': (95, 158, 160),    # バスルーム
    'T': (180, 105, 255),   # トイレ
    'UT': (160, 190, 240),  # 脱衣所
    'C': (220, 220, 220),   # 廊下
    'R': (200, 200, 200)    # その他の部屋
}

# 部屋タイプごとの家具・設備の定義
ROOM_FURNITURE = {
    'E': ['玄関ドア', '下駄箱'],
    'L': ['ソファ', 'テーブル', 'テレビ'],
    'D': ['ダイニングテーブル', '椅子'],
    'K': ['キッチン', '冷蔵庫'],
    'B': ['浴槽', 'シャワー'],
    'T': ['トイレ', '洗面台'],
    'UT': ['洗濯機', '洗面台']
}

def create_freecad_document(name="FloorPlan"):
    """FreeCADドキュメントを作成"""
    if not FREECAD_AVAILABLE:
        return None
    
    doc = FreeCAD.newDocument(name)
    return doc

def create_room(doc, name, x, y, width, height, room_type='L'):
    """部屋を作成"""
    if not FREECAD_AVAILABLE or doc is None:
        return None
    
    # 部屋の輪郭を作成
    sketch = doc.addObject('Sketcher::SketchObject', f'Sketch_{name}')
    sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x, y, 0), FreeCAD.Vector(x+width, y, 0)))
    sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x+width, y, 0), FreeCAD.Vector(x+width, y+height, 0)))
    sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x+width, y+height, 0), FreeCAD.Vector(x, y+height, 0)))
    sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x, y+height, 0), FreeCAD.Vector(x, y, 0)))
    
    # 部屋オブジェクトを作成
    room = Arch.makeSpace(sketch, height=0.1, name=name)
    
    # 部屋の色を設定
    color = ROOM_COLORS.get(room_type, ROOM_COLORS['R'])
    r, g, b = color
    room.ViewObject.ShapeColor = (r/255.0, g/255.0, b/255.0)
    
    # 部屋のラベルを追加
    label = Draft.makeText([name], FreeCAD.Vector(x + width/2, y + height/2, 0))
    label.ViewObject.TextColor = (0, 0, 0)
    
    return room

def add_furniture(doc, room, room_type, x, y, width, height):
    """部屋に家具を追加"""
    if not FREECAD_AVAILABLE or doc is None:
        return
    
    furniture_list = ROOM_FURNITURE.get(room_type, [])
    
    if not furniture_list:
        return
    
    # 部屋のサイズに基づいて家具を配置
    if room_type == 'E':  # 玄関
        # 玄関ドア
        door_width = min(width * 0.4, 1.0)
        door_x = x + width - door_width
        door_y = y
        door = Arch.makeWall(
            [FreeCAD.Vector(door_x, door_y, 0), FreeCAD.Vector(door_x + door_width, door_y, 0)],
            width=0.1, height=0.1, name=f"Door_{room.Name}"
        )
        door.ViewObject.LineColor = (0.3, 0.3, 0.3)
        
    elif room_type == 'L':  # リビング
        # ソファ
        sofa_width = width * 0.6
        sofa_height = height * 0.2
        sofa_x = x + (width - sofa_width) / 2
        sofa_y = y + height * 0.1
        sofa = doc.addObject('Part::Box', f"Sofa_{room.Name}")
        sofa.Length = sofa_width
        sofa.Width = sofa_height
        sofa.Height = 0.05
        sofa.Placement = FreeCAD.Placement(
            FreeCAD.Vector(sofa_x, sofa_y, 0),
            FreeCAD.Rotation(0, 0, 0, 1)
        )
        sofa.ViewObject.ShapeColor = (0.8, 0.8, 0.6)
        
        # テーブル
        table_size = min(width, height) * 0.3
        table_x = x + (width - table_size) / 2
        table_y = y + height * 0.4
        table = doc.addObject('Part::Box', f"Table_{room.Name}")
        table.Length = table_size
        table.Width = table_size
        table.Height = 0.05
        table.Placement = FreeCAD.Placement(
            FreeCAD.Vector(table_x, table_y, 0),
            FreeCAD.Rotation(0, 0, 0, 1)
        )
        table.ViewObject.ShapeColor = (0.6, 0.4, 0.2)
        
    elif room_type == 'K':  # キッチン
        # キッチンカウンター
        counter_width = width * 0.8
        counter_height = height * 0.3
        counter_x = x + (width - counter_width) / 2
        counter_y = y + height * 0.6
        counter = doc.addObject('Part::Box', f"Counter_{room.Name}")
        counter.Length = counter_width
        counter.Width = counter_height
        counter.Height = 0.05
        counter.Placement = FreeCAD.Placement(
            FreeCAD.Vector(counter_x, counter_y, 0),
            FreeCAD.Rotation(0, 0, 0, 1)
        )
        counter.ViewObject.ShapeColor = (0.7, 0.7, 0.7)
        
    elif room_type == 'B':  # バスルーム
        # 浴槽
        bath_width = width * 0.7
        bath_height = height * 0.6
        bath_x = x + (width - bath_width) / 2
        bath_y = y + (height - bath_height) / 2
        bath = doc.addObject('Part::Box', f"Bath_{room.Name}")
        bath.Length = bath_width
        bath.Width = bath_height
        bath.Height = 0.05
        bath.Placement = FreeCAD.Placement(
            FreeCAD.Vector(bath_x, bath_y, 0),
            FreeCAD.Rotation(0, 0, 0, 1)
        )
        bath.ViewObject.ShapeColor = (0.8, 0.8, 1.0)
        
    elif room_type == 'T':  # トイレ
        # トイレ
        toilet_size = min(width, height) * 0.4
        toilet_x = x + (width - toilet_size) / 2
        toilet_y = y + height * 0.6
        toilet = doc.addObject('Part::Box', f"Toilet_{room.Name}")
        toilet.Length = toilet_size
        toilet.Width = toilet_size
        toilet.Height = 0.05
        toilet.Placement = FreeCAD.Placement(
            FreeCAD.Vector(toilet_x, toilet_y, 0),
            FreeCAD.Rotation(0, 0, 0, 1)
        )
        toilet.ViewObject.ShapeColor = (1.0, 1.0, 1.0)

def render_freecad_floorplan(grid_data, positions, madori_info, cell_px, x, y):
    """FreeCADを使用して間取り図をレンダリング"""
    if not FREECAD_AVAILABLE:
        return None, None
    
    # FreeCADドキュメントを作成
    doc = create_freecad_document("FloorPlan")
    
    # 各部屋を作成
    rooms = {}
    for name, pos in positions.items():
        if name == 'C':  # 廊下はスキップ
            continue
            
        room_x, room_y = pos
        m = madori_info.get(name)
        if m is None:
            continue
            
        # 部屋のサイズと位置を計算
        width = m.width * cell_px
        height = m.height * cell_px
        pos_x = x + room_x * cell_px
        pos_y = y + room_y * cell_px
        
        # 部屋を作成
        room = create_room(doc, name, pos_x, pos_y, width, height, room_type=name)
        rooms[name] = room
        
        # 家具を追加
        add_furniture(doc, room, name, pos_x, pos_y, width, height)
    
    # R部屋（追加部屋）を処理
    labeled_corr, n_labels_corr = cv2.connectedComponents((grid_data >= 10).astype(np.uint8))
    if isinstance(n_labels_corr, np.ndarray):
        if n_labels_corr.size == 1:
            n_labels_corr = n_labels_corr.item()
        else:
            n_labels_corr = int(np.max(n_labels_corr)) + 1
            
    for lbl in range(1, n_labels_corr):
        region_mask = (labeled_corr == lbl)
        codes_in_region = grid_data[region_mask]
        code_vals, counts = np.unique(codes_in_region, return_counts=True)
        if len(code_vals) == 0:
            continue
            
        r_code = code_vals[np.argmax(counts)]
        rid = r_code - 10
        r_name = f"R{rid}"
        
        ys, xs = np.where(region_mask)
        miny, maxy = ys.min(), ys.max()
        minx, maxx = xs.min(), xs.max()
        width = (maxx - minx + 1) * cell_px
        height = (maxy - miny + 1) * cell_px
        
        pos_x = x + minx * cell_px
        pos_y = y + miny * cell_px
        
        # R部屋を作成
        room = create_room(doc, r_name, pos_x, pos_y, width, height, room_type='R')
        rooms[r_name] = room
    
    # 廊下を処理
    corridor_mask = (grid_data == 7)
    labeled_corr, n_labels_corr = cv2.connectedComponents(corridor_mask.astype(np.uint8))
    
    for lbl in range(1, n_labels_corr):
        region_mask = (labeled_corr == lbl)
        ys, xs = np.where(region_mask)
        if len(ys) == 0:
            continue
            
        miny, maxy = ys.min(), ys.max()
        minx, maxx = xs.min(), xs.max()
        
        # 廊下の各セルを個別に処理
        for i in range(minx, maxx + 1):
            for j in range(miny, maxy + 1):
                if grid_data[j, i] == 7:  # 廊下コード
                    pos_x = x + i * cell_px
                    pos_y = y + j * cell_px
                    width = cell_px
                    height = cell_px
                    
                    # 廊下セルを作成
                    c_name = f"C_{i}_{j}"
                    room = create_room(doc, c_name, pos_x, pos_y, width, height, room_type='C')
    
    # 一時ファイルに保存してレンダリング
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name
    
    # ビューを設定して上から見た図を作成
    FreeCAD.Gui.ActiveDocument = FreeCAD.getDocument(doc.Name)
    FreeCAD.Gui.ActiveDocument.ActiveView.viewTop()
    FreeCAD.Gui.ActiveDocument.ActiveView.fitAll()
    
    # 画像として保存
    FreeCAD.Gui.ActiveDocument.ActiveView.saveImage(tmp_path, 1920, 1080, 'White')
    
    # 画像を読み込み
    img = cv2.imread(tmp_path)
    os.unlink(tmp_path)  # 一時ファイルを削除
    
    # PILイメージに変換
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_img)
    
    return pil_img, doc

def generate_cad_floorplan(grid_data, positions, madori_info, cell_px, x, y, base_image=None):
    """CAD風の間取り図を生成"""
    if not FREECAD_AVAILABLE:
        # FreeCADが利用できない場合は代替の描画方法を使用
        return fallback_cad_style_drawing(grid_data, positions, madori_info, cell_px, x, y, base_image)
    
    try:
        # FreeCADを使用して間取り図をレンダリング
        pil_img, doc = render_freecad_floorplan(grid_data, positions, madori_info, cell_px, x, y)
        
        if pil_img is None:
            # レンダリングに失敗した場合は代替の描画方法を使用
            return fallback_cad_style_drawing(grid_data, positions, madori_info, cell_px, x, y, base_image)
        
        # OpenCV形式に変換
        img = np.array(pil_img)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # ベース画像がある場合は合成
        if base_image is not None:
            # ベース画像のサイズを取得
            h, w = base_image.shape[:2]
            
            # レンダリングした画像をリサイズ
            img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
            
            # マスク領域を作成
            mask = np.zeros((h, w), dtype=np.uint8)
            for name, pos in positions.items():
                if name == 'C':  # 廊下はスキップ
                    continue
                    
                room_x, room_y = pos
                m = madori_info.get(name)
                if m is None:
                    continue
                    
                # 部屋の領域をマスクに追加
                rx1 = x + room_x * cell_px
                ry1 = y + room_y * cell_px
                rx2 = rx1 + m.width * cell_px
                ry2 = ry1 + m.height * cell_px
                
                cv2.rectangle(mask, (rx1, ry1), (rx2, ry2), 255, -1)
            
            # マスク領域に合成
            mask_inv = cv2.bitwise_not(mask)
            img_bg = cv2.bitwise_and(base_image, base_image, mask=mask_inv)
            img_fg = cv2.bitwise_and(img, img, mask=mask)
            img = cv2.add(img_bg, img_fg)
        
        return img
        
    except Exception as e:
        logger.error(f"CAD風間取り図の生成に失敗しました: {e}")
        # エラーが発生した場合は代替の描画方法を使用
        return fallback_cad_style_drawing(grid_data, positions, madori_info, cell_px, x, y, base_image)

def fallback_cad_style_drawing(grid_data, positions, madori_info, cell_px, x, y, base_image=None):
    """FreeCADが利用できない場合の代替CAD風描画"""
    # ベース画像のコピーを作成
    if base_image is not None:
        out = base_image.copy()
    else:
        # ベース画像がない場合は新しい画像を作成
        h, w = grid_data.shape
        out = np.ones((h * cell_px, w * cell_px, 3), dtype=np.uint8) * 255
    
    # 部屋ごとに色を割り当て
    for name, pos in positions.items():
        if name == 'C':  # 廊下はスキップ
            continue
            
        room_x, room_y = pos
        m = madori_info.get(name)
        if m is None:
            continue
            
        # 部屋の領域を描画
        rx1 = x + room_x * cell_px
        ry1 = y + room_y * cell_px
        rx2 = rx1 + m.width * cell_px
        ry2 = ry1 + m.height * cell_px
        
        # 部屋の色を取得
        color = ROOM_COLORS.get(name, ROOM_COLORS['R'])
        
        # 部屋を塗りつぶし
        cv2.rectangle(out, (rx1, ry1), (rx2, ry2), color, -1)
        
        # 部屋の枠線を描画（太め）
        cv2.rectangle(out, (rx1, ry1), (rx2, ry2), (50, 50, 50), 2)
        
        # 部屋名を描画
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        text_color = (0, 0, 0)
        text_thickness = 2
        text_size = cv2.getTextSize(name, font, font_scale, text_thickness)[0]
        text_x = rx1 + (m.width * cell_px - text_size[0]) // 2
        text_y = ry1 + (m.height * cell_px + text_size[1]) // 2
        
        # テキスト背景
        bg_padding = 4
        bg_rect = (
            text_x - bg_padding,
            text_y - text_size[1] - bg_padding,
            text_size[0] + bg_padding*2,
            text_size[1] + bg_padding*2
        )
        cv2.rectangle(out,
                    (bg_rect[0], bg_rect[1]),
                    (bg_rect[0] + bg_rect[2], bg_rect[1] + bg_rect[3]),
                    (255, 255, 255),
                    -1)
        cv2.putText(out, name, (text_x, text_y), font,
                    font_scale, text_color, text_thickness, cv2.LINE_AA)
        
        # CAD風の家具や設備を追加
        if name == 'E':  # 玄関
            # 玄関ドア
            door_width = min(m.width * cell_px * 0.4, cell_px)
            door_x = rx1 + m.width * cell_px - door_width
            door_y = ry1
            cv2.rectangle(out, (int(door_x), door_y), (int(door_x + door_width), door_y + 5), (50, 50, 50), -1)
            
        elif name == 'L':  # リビング
            # ソファ
            sofa_width = m.width * cell_px * 0.6
            sofa_height = m.height * cell_px * 0.2
            sofa_x = rx1 + (m.width * cell_px - sofa_width) / 2
            sofa_y = ry1 + m.height * cell_px * 0.1
            cv2.rectangle(out, (int(sofa_x), int(sofa_y)), 
                        (int(sofa_x + sofa_width), int(sofa_y + sofa_height)), 
                        (204, 204, 153), -1)
            cv2.rectangle(out, (int(sofa_x), int(sofa_y)), 
                        (int(sofa_x + sofa_width), int(sofa_y + sofa_height)), 
                        (50, 50, 50), 1)
            
            # テーブル
            table_size = min(m.width, m.height) * cell_px * 0.3
            table_x = rx1 + (m.width * cell_px - table_size) / 2
            table_y = ry1 + m.height * cell_px * 0.4
            cv2.rectangle(out, (int(table_x), int(table_y)), 
                        (int(table_x + table_size), int(table_y + table_size)), 
                        (153, 102, 51), -1)
            cv2.rectangle(out, (int(table_x), int(table_y)), 
                        (int(table_x + table_size), int(table_y + table_size)), 
                        (50, 50, 50), 1)
            
        elif name == 'K':  # キッチン
            # キッチンカウンター
            counter_width = m.width * cell_px * 0.8
            counter_height = m.height * cell_px * 0.3
            counter_x = rx1 + (m.width * cell_px - counter_width) / 2
            counter_y = ry1 + m.height * cell_px * 0.6
            cv2.rectangle(out, (int(counter_x), int(counter_y)), 
                        (int(counter_x + counter_width), int(counter_y + counter_height)), 
                        (179, 179, 179), -1)
            cv2.rectangle(out, (int(counter_x), int(counter_y)), 
                        (int(counter_x + counter_width), int(counter_y + counter_height)), 
                        (50, 50, 50), 1)
            
            # シンク
            sink_size = min(counter_width, counter_height) * 0.3
            sink_x = counter_x + counter_width * 0.7
            sink_y = counter_y + (counter_height - sink_size) / 2
            cv2.rectangle(out, (int(sink_x), int(sink_y)), 
                        (int(sink_x + sink_size), int(sink_y + sink_size)), 
                        (200, 200, 200), -1)
            cv2.rectangle(out, (int(sink_x), int(sink_y)), 
                        (int(sink_x + sink_size), int(sink_y + sink_size)), 
                        (50, 50, 50), 1)
            
        elif name == 'B':  # バスルーム
            # 浴槽
            bath_width = m.width * cell_px * 0.7
            bath_height = m.height * cell_px * 0.6
            bath_x = rx1 + (m.width * cell_px - bath_width) / 2
            bath_y = ry1 + (m.height * cell_px - bath_height) / 2
            cv2.rectangle(out, (int(bath_x), int(bath_y)), 
                        (int(bath_x + bath_width), int(bath_y + bath_height)), 
                        (204, 204, 255), -1)
            cv2.rectangle(out, (int(bath_x), int(bath_y)), 
                        (int(bath_x + bath_width), int(bath_y + bath_height)), 
                        (50, 50, 50), 1)
            
        elif name == 'T':  # トイレ
            # トイレ
            toilet_size = min(m.width, m.height) * cell_px * 0.4
            toilet_x = rx1 + (m.width * cell_px - toilet_size) / 2
            toilet_y = ry1 + m.height * cell_px * 0.6
            cv2.ellipse(out, 
                      (int(toilet_x + toilet_size/2), int(toilet_y + toilet_size/2)), 
                      (int(toilet_size/2), int(toilet_size/3)), 
                      0, 0, 360, (255, 255, 255), -1)
            cv2.ellipse(out, 
                      (int(toilet_x + toilet_size/2), int(toilet_y + toilet_size/2)), 
                      (int(toilet_size/2), int(toilet_size/3)), 
                      0, 0, 360, (50, 50, 50), 1)
    
    # R部屋（追加部屋）を処理
    labeled_corr, n_labels_corr = cv2.connectedComponents((grid_data >= 10).astype(np.uint8))
    if isinstance(n_labels_corr, np.ndarray):
        if n_labels_corr.size == 1:
            n_labels_corr = n_labels_corr.item()
        else:
            n_labels_corr = int(np.max(n_labels_corr)) + 1
            
    for lbl in range(1, n_labels_corr):
        region_mask = (labeled_corr == lbl)
        codes_in_region = grid_data[region_mask]
        code_vals, counts = np.unique(codes_in_region, return_counts=True)
        if len(code_vals) == 0:
            continue
            
        r_code = code_vals[np.argmax(counts)]
        rid = r_code - 10
        r_name = f"R{rid}"
        
        ys, xs = np.where(region_mask)
        miny, maxy = ys.min(), ys.max()
        minx, maxx = xs.min(), xs.max()
        
        # R部屋の領域を描画
        rx1 = x + minx * cell_px
        ry1 = y + miny * cell_px
        rx2 = x + (maxx + 1) * cell_px
        ry2 = y + (maxy + 1) * cell_px
        
        # R部屋の色
        color = ROOM_COLORS['R']
        
        # R部屋を塗りつぶし
        cv2.rectangle(out, (rx1, ry1), (rx2, ry2), color, -1)
        
        # R部屋の枠線を描画（太め）
        cv2.rectangle(out, (rx1, ry1), (rx2, ry2), (50, 50, 50), 2)
        
        # R部屋名を描画
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        text_color = (0, 0, 0)
        text_thickness = 2
        text_size = cv2.getTextSize(r_name, font, font_scale, text_thickness)[0]
        text_x = rx1 + (rx2 - rx1 - text_size[0]) // 2
        text_y = ry1 + (ry2 - ry1 + text_size[1]) // 2
        
        # テキスト背景
        bg_padding = 4
        bg_rect = (
            text_x - bg_padding,
            text_y - text_size[1] - bg_padding,
            text_size[0] + bg_padding*2,
            text_size[1] + bg_padding*2
        )
        cv2.rectangle(out,
                    (bg_rect[0], bg_rect[1]),
                    (bg_rect[0] + bg_rect[2], bg_rect[1] + bg_rect[3]),
                    (255, 255, 255),
                    -1)
        cv2.putText(out, r_name, (text_x, text_y), font,
                    font_scale, text_color, text_thickness, cv2.LINE_AA)
    
    # 廊下を処理
    corridor_mask = (grid_data == 7)
    for i in range(grid_data.shape[1]):
        for j in range(grid_data.shape[0]):
            if grid_data[j, i] == 7:  # 廊下コード
                rx1 = x + i * cell_px
                ry1 = y + j * cell_px
                rx2 = rx1 + cell_px
                ry2 = ry1 + cell_px
                
                # 廊下の色
                color = ROOM_COLORS['C']
                
                # 廊下を塗りつぶし
                cv2.rectangle(out, (rx1, ry1), (rx2, ry2), color, -1)
                
                # 廊下の枠線を描画
                cv2.rectangle(out, (rx1, ry1), (rx2, ry2), (150, 150, 150), 1)
    
    # 全体の枠線を描画
    contours, _ = cv2.findContours((grid_data > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(out, contours, -1, (0, 0, 0), 3, offset=(x, y), lineType=cv2.LINE_AA)
    
    # 寸法線を追加
    # 横方向の寸法線
    max_x = 0
    max_y = 0
    for name, pos in positions.items():
        room_x, room_y = pos
        m = madori_info.get(name)
        if m is None:
            continue
        
        end_x = room_x + m.width
        end_y = room_y + m.height
        
        if end_x > max_x:
            max_x = end_x
        if end_y > max_y:
            max_y = end_y
    
    # 横方向の寸法線
    dim_y = y + (max_y + 1) * cell_px + 30
    cv2.line(out, (x, dim_y), (x + max_x * cell_px, dim_y), (0, 0, 0), 1, cv2.LINE_AA)
    
    # 縦方向の寸法線
    dim_x = x + (max_x + 1) * cell_px + 30
    cv2.line(out, (dim_x, y), (dim_x, y + max_y * cell_px), (0, 0, 0), 1, cv2.LINE_AA)
    
    # 各部屋の寸法を追加
    for name, pos in positions.items():
        if name == 'C':  # 廊下はスキップ
            continue
            
        room_x, room_y = pos
        m = madori_info.get(name)
        if m is None:
            continue
        
        # 横方向の寸法
        width_mm = m.width * 910  # 1マス = 910mm (91.0cm)
        width_text = f"{width_mm}mm"
        text_size = cv2.getTextSize(width_text, font, 0.5, 1)[0]
        text_x = x + room_x * cell_px + (m.width * cell_px - text_size[0]) // 2
        cv2.putText(out, width_text, (text_x, dim_y - 10), font, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        
        # 縦方向の寸法
        height_mm = m.height * 910  # 1マス = 910mm (91.0cm)
        height_text = f"{height_mm}mm"
        text_size = cv2.getTextSize(height_text, font, 0.5, 1)[0]
        text_y = y + room_y * cell_px + (m.height * cell_px + text_size[0]) // 2
        # 縦書きにするため、テキストを90度回転
        for i, char in enumerate(height_text):
            cv2.putText(out, char, (dim_x - 10, text_y - i*10), font, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    
    return out
