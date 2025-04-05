import os
import sys
from unittest.mock import MagicMock, patch

import pytest

import streamlit as st

# プロジェクトルートディレクトリをPythonパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

# streamlitディレクトリをPythonパスに追加
streamlit_dir = os.path.join(project_root, "streamlit")
sys.path.append(streamlit_dir)

from app import (
    convert_to_2d_drawing,
    generate_grid,
    load_yolo_model,
    process_image,
    send_to_freecad_api,
)


@pytest.fixture
def mock_yolo_model():
    with patch("ultralytics.YOLO") as mock:
        yield mock


@pytest.fixture
def mock_storage():
    with patch("src.cloud.storage.CloudStorage") as mock:
        yield mock


@pytest.fixture
def mock_freecad_api():
    with patch("requests.post") as mock:
        yield mock


def test_load_yolo_model_success(mock_yolo_model):
    """YOLOモデルの読み込みが成功することをテスト"""
    model_path = "path/to/model.pt"
    mock_model = MagicMock()
    mock_yolo_model.return_value = mock_model

    result = load_yolo_model(model_path)

    mock_yolo_model.assert_called_once_with(model_path)
    assert result == mock_model


def test_load_yolo_model_download(mock_yolo_model, mock_storage):
    """モデルパスが指定されていない場合、Cloud Storageからダウンロードされることをテスト"""
    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance
    mock_storage_instance.download_model.return_value = "downloaded_model.pt"

    mock_model = MagicMock()
    mock_yolo_model.return_value = mock_model

    result = load_yolo_model()

    mock_storage_instance.download_model.assert_called_once()
    mock_yolo_model.assert_called_once_with("downloaded_model.pt")
    assert result == mock_model


def test_process_image_success(mock_yolo_model):
    """画像処理が成功し、建物が検出されることをテスト"""
    image_path = "path/to/image.jpg"
    mock_model = MagicMock()
    mock_results = MagicMock()
    mock_results.boxes.data = [[0, 0, 100, 100, 0.9, 1]]  # x1, y1, x2, y2, conf, class
    mock_model.predict.return_value = [mock_results]

    buildings = process_image(mock_model, image_path)

    mock_model.predict.assert_called_once_with(image_path, conf=0.25)
    assert len(buildings) == 1
    assert buildings[0]["confidence"] == 0.9
    assert buildings[0]["bbox"] == [0, 0, 100, 100]


def test_generate_grid_success():
    """建物データからグリッドが正しく生成されることをテスト"""
    building_data = {"bbox": [0, 0, 100, 100], "confidence": 0.9}

    grid = generate_grid([building_data])

    assert isinstance(grid, dict)
    assert "rooms" in grid
    assert "walls" in grid
    assert len(grid["rooms"]) > 0


def test_send_to_freecad_api_success(mock_freecad_api):
    """FreeCAD APIへのデータ送信が成功することをテスト"""
    grid_data = {
        "rooms": [{"id": 1, "dimensions": [10, 10]}],
        "walls": [{"start": [0, 0], "end": [10, 0]}],
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"url": "https://example.com/model.fcstd"}
    mock_freecad_api.return_value = mock_response

    result = send_to_freecad_api(grid_data)

    mock_freecad_api.assert_called_once()
    assert result == "https://example.com/model.fcstd"


def test_convert_to_2d_drawing_success(mock_freecad_api):
    """2D図面の生成が成功することをテスト"""
    fcstd_file_path = "path/to/model.fcstd"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"url": "https://example.com/drawing.pdf"}
    mock_freecad_api.return_value = mock_response

    result = convert_to_2d_drawing(fcstd_file_path)

    mock_freecad_api.assert_called_once()
    assert result == "https://example.com/drawing.pdf"


def test_error_handling():
    """無効な画像パスが指定された場合のエラー処理をテスト"""
    with pytest.raises(FileNotFoundError):
        process_image(MagicMock(), "invalid/path/to/image.jpg")
