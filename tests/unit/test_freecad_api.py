import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from freecad_api.main import app

client = TestClient(app)

# テストデータ
SAMPLE_GRID_DATA = {
    "rooms": [{"id": 1, "dimensions": [10, 10], "position": [0, 0], "label": "Room 1"}],
    "walls": [{"start": [0, 0], "end": [10, 0], "height": 2.5}],
}


@pytest.fixture
def mock_storage():
    with patch("freecad_api.main.CloudStorage") as mock:
        mock_instance = MagicMock()
        mock_instance.upload_file.return_value = "https://example.com/model.fcstd"
        mock.return_value = mock_instance
        yield mock_instance


def test_root_endpoint():
    """ルートエンドポイントが正常に応答することをテスト"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_process_grid_success(mock_storage):
    """グリッドデータの処理が成功することをテスト"""
    response = client.post("/process/grid", json=SAMPLE_GRID_DATA)
    assert response.status_code == 200
    assert "url" in response.json()
    assert response.json()["url"] == "https://example.com/model.fcstd"
    mock_storage.upload_file.assert_called_once()


def test_process_grid_invalid_data():
    """無効なグリッドデータの処理をテスト"""
    invalid_data = {"rooms": [], "walls": []}  # 部屋データが空  # 壁データが空
    response = client.post("/process/grid", json=invalid_data)
    assert response.status_code == 400
    assert "error" in response.json()


def test_convert_to_2d_success(mock_storage):
    """3DモデルからPDF図面への変換が成功することをテスト"""
    # テスト用のFreeCADファイルを作成
    test_file = "test.fcstd"
    with open(test_file, "wb") as f:
        f.write(b"dummy fcstd content")

    with open(test_file, "rb") as f:
        response = client.post(
            "/convert/2d", files={"file": ("test.fcstd", f, "application/octet-stream")}
        )

    os.remove(test_file)  # テストファイルを削除

    assert response.status_code == 200
    assert "url" in response.json()
    assert response.json()["url"] == "https://example.com/model.fcstd"
    mock_storage.upload_file.assert_called_once()


def test_convert_to_2d_invalid_file():
    """無効なファイルでの2D変換をテスト"""
    response = client.post(
        "/convert/2d", files={"file": ("test.txt", b"invalid content", "text/plain")}
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_process_grid_freecad_error(mock_storage):
    """FreeCADでエラーが発生した場合の処理をテスト"""
    mock_storage.upload_file.side_effect = Exception("FreeCAD error")

    response = client.post("/process/grid", json=SAMPLE_GRID_DATA)
    assert response.status_code == 500
    assert "error" in response.json()
