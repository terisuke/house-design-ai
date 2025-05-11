"""
YOLOアノテーションをベクターデータおよびグラフ構造のJSONに変換するモジュール
"""
from typing import List, Dict, Tuple, Optional, Union, Any
import numpy as np
import json
import cv2
import logging
import networkx as nx
from shapely.geometry import Polygon, LineString, Point as ShapelyPoint
from shapely.ops import unary_union, polygonize
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

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
    module_size: float = 910.0  # 910mmモジュール

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

def load_yolo_annotations(annotations_path: str) -> Dict[str, Any]:
    """
    YOLOアノテーションファイルを読み込む
    
    Args:
        annotations_path: YOLOアノテーションファイルのパス
        
    Returns:
        Dict: YOLOアノテーションデータ
    """
    try:
        with open(annotations_path, 'r') as f:
            lines = f.readlines()
        
        annotations = {}
        for line in lines:
            parts = line.strip().split()
            if len(parts) < 5:  # クラスIDと少なくとも1つの座標ペアが必要
                continue
                
            class_id = int(parts[0])
            coords = [float(p) for p in parts[1:]]
            
            if len(coords) > 4:
                points = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
                if class_id not in annotations:
                    annotations[class_id] = []
                annotations[class_id].append(points)
            else:
                x_center, y_center, width, height = coords
                if class_id not in annotations:
                    annotations[class_id] = []
                annotations[class_id].append({
                    'x_center': x_center,
                    'y_center': y_center,
                    'width': width,
                    'height': height
                })
                
        return annotations
    except Exception as e:
        logger.error(f"YOLOアノテーションの読み込みに失敗しました: {e}")
        return {}

def convert_yolo_to_mask(annotations: Dict[str, Any], image_width: int, image_height: int, class_ids: List[int]) -> Dict[int, np.ndarray]:
    """
    YOLOアノテーションをマスク画像に変換
    
    Args:
        annotations: YOLOアノテーションデータ
        image_width: 元画像の幅
        image_height: 元画像の高さ
        class_ids: 変換対象のクラスID
        
    Returns:
        Dict[int, np.ndarray]: クラスIDをキーとするマスク画像の辞書
    """
    masks = {}
    
    for class_id in class_ids:
        if class_id not in annotations:
            continue
            
        mask = np.zeros((image_height, image_width), dtype=np.uint8)
        
        for annotation in annotations[class_id]:
            if isinstance(annotation, list):  # ポリゴンの場合
                points = [(int(x * image_width), int(y * image_height)) for x, y in annotation]
                points = np.array(points, dtype=np.int32)
                cv2.fillPoly(mask, [points], 1)
            else:  # バウンディングボックスの場合
                x_center = int(annotation['x_center'] * image_width)
                y_center = int(annotation['y_center'] * image_height)
                width = int(annotation['width'] * image_width)
                height = int(annotation['height'] * image_height)
                
                x1 = max(0, int(x_center - width / 2))
                y1 = max(0, int(y_center - height / 2))
                x2 = min(image_width, int(x_center + width / 2))
                y2 = min(image_height, int(y_center + height / 2))
                
                cv2.rectangle(mask, (x1, y1), (x2, y2), 1, -1)
                
        masks[class_id] = mask
        
    return masks

def extract_contours_from_mask(mask: np.ndarray, epsilon_factor: float = 0.005) -> List[np.ndarray]:
    """
    マスク画像から輪郭を抽出し、ポリゴンを単純化
    
    Args:
        mask: マスク画像
        epsilon_factor: Douglas-Peuckerアルゴリズムの単純化パラメータ
        
    Returns:
        List[np.ndarray]: 単純化された輪郭のリスト
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    simplified_contours = []
    
    for contour in contours:
        if cv2.contourArea(contour) < 100:
            continue
            
        epsilon = epsilon_factor * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        simplified_contours.append(approx)
        
    return simplified_contours

def contours_to_shapely_polygons(contours: List[np.ndarray]) -> List[Polygon]:
    """
    OpenCV輪郭をShapelyポリゴンに変換
    
    Args:
        contours: OpenCV輪郭のリスト
        
    Returns:
        List[Polygon]: Shapelyポリゴンのリスト
    """
    polygons = []
    
    for contour in contours:
        coords = [(point[0][0], point[0][1]) for point in contour]
        if coords[0] != coords[-1]:
            coords.append(coords[0])
            
        if len(coords) >= 4:  # 少なくとも3点+閉じるための点が必要
            poly = Polygon(coords)
            if poly.is_valid:
                polygons.append(poly)
                
    return polygons

def extract_room_adjacency(polygons: List[Polygon], buffer_distance: float = 5.0) -> nx.Graph:
    """
    部屋ポリゴン間の隣接関係を抽出してグラフ構造を作成
    
    Args:
        polygons: 部屋ポリゴンのリスト
        buffer_distance: 隣接判定の距離閾値
        
    Returns:
        nx.Graph: 部屋の隣接関係を表すグラフ
    """
    graph = nx.Graph()
    
    for i, poly in enumerate(polygons):
        room_id = f"room_{i}"
        graph.add_node(room_id, polygon=poly, area=poly.area)
        
    for i, poly1 in enumerate(polygons):
        room_id1 = f"room_{i}"
        buffered = poly1.buffer(buffer_distance)
        
        for j, poly2 in enumerate(polygons):
            if i == j:
                continue
                
            room_id2 = f"room_{j}"
            if buffered.intersects(poly2):
                intersection = buffered.intersection(poly2)
                weight = 1.0
                if isinstance(intersection, LineString):
                    weight = intersection.length
                elif isinstance(intersection, Polygon):
                    weight = intersection.area
                    
                graph.add_edge(room_id1, room_id2, weight=weight)
                
    return graph

def convert_to_pydantic_models(polygons: List[Polygon], graph: nx.Graph, 
                              road_polygons: Optional[List[Polygon]] = None,
                              north_direction: float = 0.0) -> Site:
    """
    ShapelyポリゴンとNetworkXグラフからPydanticモデルに変換
    
    Args:
        polygons: 部屋ポリゴンのリスト
        graph: 部屋の隣接関係を表すグラフ
        road_polygons: 道路ポリゴンのリスト
        north_direction: 北方向（ラジアン）
        
    Returns:
        Site: サイトデータを表すPydanticモデル
    """
    rooms = []
    for i, poly in enumerate(polygons):
        room_id = f"room_{i}"
        
        points = []
        for x, y in poly.exterior.coords[:-1]:  # 最後の点は最初と同じなので除外
            points.append(Point(x=float(x), y=float(y)))
            
        neighbors = [neighbor for neighbor in graph.neighbors(room_id)]
        
        room_type = "other"
        area = poly.area
        if area > 20000:  # 20平方メートル以上
            room_type = "living"
        elif 10000 <= area <= 20000:
            room_type = "bedroom"
        elif 5000 <= area <= 10000:
            if i == 0:  # 最初の小さい部屋は玄関と仮定
                room_type = "entrance"
            else:
                room_type = "kitchen"
        elif area < 5000:
            room_type = "bathroom"
            
        room = Room(
            id=room_id,
            name=f"Room {i+1}",
            points=points,
            area=float(area),
            neighbors=neighbors,
            room_type=room_type
        )
        rooms.append(room)
        
    walls = []
    for room in rooms:
        points = room.points
        for i in range(len(points)):
            start = points[i]
            end = points[(i + 1) % len(points)]
            wall = Line(start=start, end=end)
            walls.append(wall)
            
    building = Building(rooms=rooms, walls=walls)
    
    all_polygons = unary_union([Polygon([(p.x, p.y) for p in room.points]) for room in rooms])
    boundary_points = []
    for x, y in all_polygons.exterior.coords[:-1]:
        boundary_points.append(Point(x=float(x), y=float(y)))
        
    road_access = []
    if road_polygons:
        for road_poly in road_polygons:
            if all_polygons.intersects(road_poly):
                intersection = all_polygons.intersection(road_poly)
                if isinstance(intersection, LineString):
                    coords = list(intersection.coords)
                    if len(coords) >= 2:
                        start = Point(x=float(coords[0][0]), y=float(coords[0][1]))
                        end = Point(x=float(coords[-1][0]), y=float(coords[-1][1]))
                        road_access.append(Line(start=start, end=end, type="road_access"))
                        
    site = Site(
        building=building,
        boundary=boundary_points,
        road_access=road_access,
        north_direction=north_direction
    )
    
    return site

def convert_yolo_to_vector(annotations_path: str, image_width: int, image_height: int, 
                          house_class_id: int = 0, road_class_id: int = 1,
                          north_direction: float = 0.0) -> Site:
    """
    YOLOアノテーションをベクターデータに変換
    
    Args:
        annotations_path: YOLOアノテーションファイルのパス
        image_width: 元画像の幅
        image_height: 元画像の高さ
        house_class_id: 家のクラスID
        road_class_id: 道路のクラスID
        north_direction: 北方向（ラジアン）
        
    Returns:
        Site: サイトデータを表すPydanticモデル
    """
    annotations = load_yolo_annotations(annotations_path)
    
    masks = convert_yolo_to_mask(annotations, image_width, image_height, [house_class_id, road_class_id])
    
    house_contours = []
    if house_class_id in masks:
        house_contours = extract_contours_from_mask(masks[house_class_id])
        
    road_contours = []
    if road_class_id in masks:
        road_contours = extract_contours_from_mask(masks[road_class_id])
        
    house_polygons = contours_to_shapely_polygons(house_contours)
    road_polygons = contours_to_shapely_polygons(road_contours)
    
    if len(house_polygons) == 1:
        house_polygons = divide_house_into_rooms(house_polygons[0])
        
    graph = extract_room_adjacency(house_polygons)
    
    site = convert_to_pydantic_models(house_polygons, graph, road_polygons, north_direction)
    
    return site

def divide_house_into_rooms(house_polygon: Polygon, num_rooms: int = 4) -> List[Polygon]:
    """
    家ポリゴンを複数の部屋に分割
    
    Args:
        house_polygon: 家全体のポリゴン
        num_rooms: 分割する部屋の数
        
    Returns:
        List[Polygon]: 部屋ポリゴンのリスト
    """
    minx, miny, maxx, maxy = house_polygon.bounds
    width = maxx - minx
    height = maxy - miny
    
    rooms = []
    
    if num_rooms == 4:
        for i in range(2):
            for j in range(2):
                x1 = minx + j * (width / 2)
                y1 = miny + i * (height / 2)
                x2 = minx + (j + 1) * (width / 2)
                y2 = miny + (i + 1) * (height / 2)
                
                room = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
                intersection = house_polygon.intersection(room)
                if isinstance(intersection, Polygon) and intersection.area > 0:
                    rooms.append(intersection)
    else:
        for i in range(num_rooms):
            x1 = minx + i * (width / num_rooms)
            y1 = miny
            x2 = minx + (i + 1) * (width / num_rooms)
            y2 = maxy
            
            room = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
            intersection = house_polygon.intersection(room)
            if isinstance(intersection, Polygon) and intersection.area > 0:
                rooms.append(intersection)
                
    return rooms

def serialize_to_json(site: Site, output_path: str) -> bool:
    """
    サイトデータをJSON形式でシリアライズして保存
    
    Args:
        site: サイトデータを表すPydanticモデル
        output_path: 出力JSONファイルのパス
        
    Returns:
        bool: 保存に成功したかどうか
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(site.json(indent=2))
        return True
    except Exception as e:
        logger.error(f"JSONの保存に失敗しました: {e}")
        return False

def visualize_vector_data(site: Site, output_path: str, image_width: int = 800, image_height: int = 600) -> bool:
    """
    ベクターデータを視覚化して画像として保存
    
    Args:
        site: サイトデータを表すPydanticモデル
        output_path: 出力画像ファイルのパス
        image_width: 出力画像の幅
        image_height: 出力画像の高さ
        
    Returns:
        bool: 保存に成功したかどうか
    """
    try:
        image = np.ones((image_height, image_width, 3), dtype=np.uint8) * 255
        
        all_x = []
        all_y = []
        for room in site.building.rooms:
            for point in room.points:
                all_x.append(point.x)
                all_y.append(point.y)
                
        min_x = min(all_x) if all_x else 0
        max_x = max(all_x) if all_x else image_width
        min_y = min(all_y) if all_y else 0
        max_y = max(all_y) if all_y else image_height
        
        scale_x = (image_width - 40) / (max_x - min_x) if max_x > min_x else 1
        scale_y = (image_height - 40) / (max_y - min_y) if max_y > min_y else 1
        scale = min(scale_x, scale_y)
        
        for room in site.building.rooms:
            color = (200, 200, 200)  # デフォルトはグレー
            if room.room_type == "living":
                color = (144, 238, 144)  # ライトグリーン
            elif room.room_type == "bedroom":
                color = (255, 191, 0)  # ライトブルー
            elif room.room_type == "kitchen":
                color = (147, 20, 255)  # パープル
            elif room.room_type == "bathroom":
                color = (95, 158, 160)  # カデットブルー
            elif room.room_type == "entrance":
                color = (102, 178, 255)  # ライトブルー
                
            points = []
            for point in room.points:
                x = int(20 + (point.x - min_x) * scale)
                y = int(20 + (point.y - min_y) * scale)
                points.append((x, y))
                
            points = np.array(points, dtype=np.int32)
            cv2.fillPoly(image, [points], color)
            cv2.polylines(image, [points], True, (0, 0, 0), 2)
            
            center_x = int(np.mean([p[0] for p in points]))
            center_y = int(np.mean([p[1] for p in points]))
            cv2.putText(image, room.name, (center_x, center_y), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.5, (0, 0, 0), 1, cv2.LINE_AA)
                       
        for access in site.road_access:
            start_x = int(20 + (access.start.x - min_x) * scale)
            start_y = int(20 + (access.start.y - min_y) * scale)
            end_x = int(20 + (access.end.x - min_x) * scale)
            end_y = int(20 + (access.end.y - min_y) * scale)
            cv2.line(image, (start_x, start_y), (end_x, end_y), (255, 0, 0), 3)
            
        boundary_points = []
        for point in site.boundary:
            x = int(20 + (point.x - min_x) * scale)
            y = int(20 + (point.y - min_y) * scale)
            boundary_points.append((x, y))
            
        boundary_points = np.array(boundary_points, dtype=np.int32)
        cv2.polylines(image, [boundary_points], True, (0, 0, 255), 2)
        
        arrow_length = 50
        arrow_x = image_width - 70
        arrow_y = 70
        end_x = int(arrow_x + arrow_length * np.sin(site.north_direction))
        end_y = int(arrow_y - arrow_length * np.cos(site.north_direction))
        cv2.arrowedLine(image, (arrow_x, arrow_y), (end_x, end_y), (0, 0, 255), 2)
        cv2.putText(image, "N", (end_x + 5, end_y), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.7, (0, 0, 255), 2, cv2.LINE_AA)
                   
        cv2.imwrite(output_path, image)
        return True
    except Exception as e:
        logger.error(f"ベクターデータの視覚化に失敗しました: {e}")
        return False

def convert_vector_to_graph(site: Site) -> nx.Graph:
    """
    ベクターデータをNetworkXグラフに変換
    
    Args:
        site: サイトデータを表すPydanticモデル
        
    Returns:
        nx.Graph: 部屋の隣接関係を表すグラフ
    """
    graph = nx.Graph()
    
    for room in site.building.rooms:
        graph.add_node(room.id, 
                      name=room.name, 
                      area=room.area, 
                      room_type=room.room_type,
                      module_size=room.module_size)
        
    for room in site.building.rooms:
        for neighbor_id in room.neighbors:
            graph.add_edge(room.id, neighbor_id)
            
    return graph
