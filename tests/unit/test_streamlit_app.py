import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# プロジェクトのルートディレクトリをPYTHONPATHに追加
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

# house_design_appディレクトリをPYTHONPATHに追加
house_design_app_dir = os.path.join(project_root, "house_design_app")
if house_design_app_dir not in sys.path:
    sys.path.insert(0, house_design_app_dir)

from main import (
    convert_to_2d_drawing,
    generate_grid,
    load_yolo_model,
    process_image,
    send_to_freecad_api,
)

from src.cloud.storage import download_model_from_gcs


@pytest.fixture
def mock_yolo_model():
    with patch("ultralytics.YOLO") as mock:
        mock_result = MagicMock()
        mock_result.boxes.data = [np.array([0, 0, 100, 100, 0.9, 0])]
        mock_result.names = {0: "building"}
        mock.return_value.predict.return_value = [mock_result]
        yield mock


@pytest.fixture
def mock_path_exists():
    with patch("os.path.exists") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_storage():
    with patch("src.cloud.storage.download_model_from_gcs") as mock:
        mock.return_value = "downloaded_model.pt"
        yield mock


@pytest.fixture
def mock_freecad_api():
    with patch("requests.post") as mock:
        mock.return_value.json.return_value = {
            "success": True,
            "data": {"url": "http://example.com"},
        }
        yield mock


def test_load_yolo_model_success(mock_yolo_model, mock_path_exists):
    """YOLOモデルが正しくロードされることをテスト"""
    model = load_yolo_model("path/to/model.pt")
    assert model == mock_yolo_model.return_value


def test_load_yolo_model_download(mock_yolo_model, mock_storage):
    """GCSからのモデルダウンロードとロードをテスト"""
    model = load_yolo_model(None)
    mock_storage.assert_called_once()
    assert model == mock_yolo_model.return_value


def test_process_image_success(mock_yolo_model, mock_path_exists):
    """画像処理が正しく機能することをテスト"""
    result = process_image(mock_yolo_model.return_value, "path/to/image.jpg")
    assert isinstance(result, list)
    assert len(result) > 0
    assert "bbox" in result[0]


def test_generate_grid_success():
    """グリッド生成が正しく機能することをテスト"""
    buildings = [{"bbox": [0, 0, 100, 100]}]
    grid = generate_grid(buildings)
    assert isinstance(grid, dict)
    assert "rooms" in grid
    assert "walls" in grid


def test_send_to_freecad_api_success(mock_freecad_api):
    """FreeCAD APIへのデータ送信が正しく機能することをテスト"""
    grid_data = {
        "grid_data": {
            "rooms": [{"dimensions": [100, 100], "position": [0, 0]}],
            "walls": [{"start": [0, 0], "end": [100, 0]}],
        }
    }
    result = send_to_freecad_api(grid_data)
    assert result["success"] is True


def test_convert_to_2d_drawing_success(mock_freecad_api):
    """2D図面への変換が正しく機能することをテスト"""
    grid_data = {
        "grid_data": {
            "rooms": [{"dimensions": [100, 100], "position": [0, 0]}],
            "walls": [{"start": [0, 0], "end": [100, 0]}],
        }
    }
    result = convert_to_2d_drawing(grid_data)
    assert result["success"] is True


def test_error_handling():
    """エラーハンドリングが正しく機能することをテスト"""
    with pytest.raises(FileNotFoundError):
        process_image(MagicMock(), "nonexistent.jpg")
