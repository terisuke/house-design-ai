"""
YOLOアノテーション → ベクター/グラフJSON変換システムのテスト
"""
import os
import sys
import unittest
import tempfile
import json
import numpy as np
import cv2
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.processing.yolo_to_vector import (
    Point, Line, Room, Building, Site,
    load_yolo_annotations, convert_yolo_to_mask,
    extract_contours_from_mask, contours_to_shapely_polygons,
    extract_room_adjacency, convert_to_pydantic_models,
    convert_yolo_to_vector, divide_house_into_rooms,
    serialize_to_json, visualize_vector_data,
    convert_vector_to_graph
)

class TestYoloToVector(unittest.TestCase):
    """YOLOアノテーション → ベクター/グラフJSON変換システムのテスト"""
    
    def setUp(self):
        """テスト用のデータを準備"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.annotations_path = os.path.join(self.temp_dir.name, "test_annotations.txt")
        
        with open(self.annotations_path, "w") as f:
            f.write("0 0.5 0.5 0.6 0.6\n")
            f.write("1 0.2 0.8 0.4 0.2\n")
        
        self.image_width = 640
        self.image_height = 480
        
    def tearDown(self):
        """テスト用のデータを削除"""
        self.temp_dir.cleanup()
        
    def test_load_yolo_annotations(self):
        """YOLOアノテーションの読み込みテスト"""
        annotations = load_yolo_annotations(self.annotations_path)
        
        self.assertIn(0, annotations)
        self.assertIn(1, annotations)
        self.assertEqual(len(annotations[0]), 1)
        self.assertEqual(len(annotations[1]), 1)
        
        self.assertAlmostEqual(annotations[0][0]['x_center'], 0.5)
        self.assertAlmostEqual(annotations[0][0]['y_center'], 0.5)
        self.assertAlmostEqual(annotations[0][0]['width'], 0.6)
        self.assertAlmostEqual(annotations[0][0]['height'], 0.6)
        
    def test_convert_yolo_to_mask(self):
        """YOLOアノテーションからマスク画像への変換テスト"""
        annotations = load_yolo_annotations(self.annotations_path)
        masks = convert_yolo_to_mask(annotations, self.image_width, self.image_height, [0, 1])
        
        self.assertIn(0, masks)
        self.assertIn(1, masks)
        self.assertEqual(masks[0].shape, (self.image_height, self.image_width))
        self.assertEqual(masks[1].shape, (self.image_height, self.image_width))
        
        self.assertTrue(np.any(masks[0] > 0))
        self.assertTrue(np.any(masks[1] > 0))
        
    def test_extract_contours_from_mask(self):
        """マスク画像からの輪郭抽出テスト"""
        mask = np.zeros((100, 100), dtype=np.uint8)
        cv2.rectangle(mask, (20, 20), (80, 80), 1, -1)
        
        contours = extract_contours_from_mask(mask)
        
        self.assertEqual(len(contours), 1)
        self.assertTrue(len(contours[0]) >= 4)  # 少なくとも矩形の4点があるはず
        
    def test_contours_to_shapely_polygons(self):
        """OpenCV輪郭からShapelyポリゴンへの変換テスト"""
        contour = np.array([[[20, 20]], [[80, 20]], [[80, 80]], [[20, 80]]])
        
        polygons = contours_to_shapely_polygons([contour])
        
        self.assertEqual(len(polygons), 1)
        self.assertTrue(polygons[0].is_valid)
        self.assertAlmostEqual(polygons[0].area, 3600)  # 60x60の矩形
        
    def test_extract_room_adjacency(self):
        """部屋ポリゴン間の隣接関係抽出テスト"""
        from shapely.geometry import Polygon
        
        poly1 = Polygon([(0, 0), (50, 0), (50, 50), (0, 50)])
        poly2 = Polygon([(50, 0), (100, 0), (100, 50), (50, 50)])
        
        graph = extract_room_adjacency([poly1, poly2])
        
        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(len(graph.edges), 1)
        self.assertTrue(graph.has_edge("room_0", "room_1"))
        
    def test_convert_to_pydantic_models(self):
        """ShapelyポリゴンとNetworkXグラフからPydanticモデルへの変換テスト"""
        from shapely.geometry import Polygon
        import networkx as nx
        
        poly1 = Polygon([(0, 0), (50, 0), (50, 50), (0, 50)])
        poly2 = Polygon([(50, 0), (100, 0), (100, 50), (50, 50)])
        
        graph = nx.Graph()
        graph.add_node("room_0", polygon=poly1, area=poly1.area)
        graph.add_node("room_1", polygon=poly2, area=poly2.area)
        graph.add_edge("room_0", "room_1", weight=1.0)
        
        site = convert_to_pydantic_models([poly1, poly2], graph)
        
        self.assertEqual(len(site.building.rooms), 2)
        self.assertEqual(len(site.building.walls), 8)  # 2つの矩形で8つの壁
        self.assertEqual(len(site.boundary), 4)  # 外側の境界は矩形
        
    def test_divide_house_into_rooms(self):
        """家ポリゴンを部屋に分割するテスト"""
        from shapely.geometry import Polygon
        
        house = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        
        rooms = divide_house_into_rooms(house, num_rooms=4)
        
        self.assertEqual(len(rooms), 4)
        for room in rooms:
            self.assertTrue(room.is_valid)
            self.assertAlmostEqual(room.area, 2500)  # 50x50の部屋
            
    def test_serialize_to_json(self):
        """サイトデータのJSON形式でのシリアライズテスト"""
        room = Room(
            id="room_0",
            name="Room 1",
            points=[Point(x=0, y=0), Point(x=10, y=0), Point(x=10, y=10), Point(x=0, y=10)],
            area=100.0,
            room_type="living"
        )
        
        wall = Line(
            start=Point(x=0, y=0),
            end=Point(x=10, y=0),
            type="wall"
        )
        
        building = Building(
            rooms=[room],
            walls=[wall]
        )
        
        site = Site(
            building=building,
            boundary=[Point(x=0, y=0), Point(x=10, y=0), Point(x=10, y=10), Point(x=0, y=10)]
        )
        
        output_path = os.path.join(self.temp_dir.name, "test_output.json")
        result = serialize_to_json(site, output_path)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
        
        with open(output_path, 'r') as f:
            data = json.load(f)
            
        self.assertEqual(len(data["building"]["rooms"]), 1)
        self.assertEqual(data["building"]["rooms"][0]["id"], "room_0")
        self.assertEqual(data["building"]["rooms"][0]["room_type"], "living")
        
    def test_convert_vector_to_graph(self):
        """ベクターデータからNetworkXグラフへの変換テスト"""
        room1 = Room(
            id="room_0",
            name="Room 1",
            points=[Point(x=0, y=0), Point(x=10, y=0), Point(x=10, y=10), Point(x=0, y=10)],
            area=100.0,
            room_type="living",
            neighbors=["room_1"]
        )
        
        room2 = Room(
            id="room_1",
            name="Room 2",
            points=[Point(x=10, y=0), Point(x=20, y=0), Point(x=20, y=10), Point(x=10, y=10)],
            area=100.0,
            room_type="bedroom",
            neighbors=["room_0"]
        )
        
        building = Building(
            rooms=[room1, room2],
            walls=[]
        )
        
        site = Site(
            building=building,
            boundary=[]
        )
        
        graph = convert_vector_to_graph(site)
        
        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(len(graph.edges), 1)
        self.assertTrue(graph.has_edge("room_0", "room_1"))
        self.assertEqual(graph.nodes["room_0"]["room_type"], "living")
        self.assertEqual(graph.nodes["room_1"]["room_type"], "bedroom")
        
    def test_end_to_end(self):
        """エンドツーエンドのテスト"""
        site = convert_yolo_to_vector(
            self.annotations_path,
            self.image_width,
            self.image_height
        )
        
        self.assertIsInstance(site, Site)
        self.assertTrue(len(site.building.rooms) > 0)
        
        output_path = os.path.join(self.temp_dir.name, "output.json")
        result = serialize_to_json(site, output_path)
        self.assertTrue(result)
        
        vis_path = os.path.join(self.temp_dir.name, "visualization.png")
        result = visualize_vector_data(site, vis_path)
        self.assertTrue(result)
        
if __name__ == "__main__":
    unittest.main()
