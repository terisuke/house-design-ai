import json
import logging
import os
import tempfile
from typing import Dict, List, Optional, Union

from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

# ロギングの設定
logging.basicConfig(level=logging.INFO)

app = FastAPI()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)},
    )
logger = logging.getLogger(__name__)

app = FastAPI(title="House Design AI FreeCAD API")


class Room(BaseModel):
    id: int
    dimensions: List[float]
    position: List[float]
    label: str


class Wall(BaseModel):
    start: List[float]
    end: List[float]
    height: float = 2.5


class GridData(BaseModel):
    rooms: List[Room]
    walls: List[Wall]


class CloudStorage:
    """
    クラウドストレージの操作を行うクラス（モック用）
    """
    def upload_file(self, file_path: str) -> str:
        """
        ファイルをクラウドストレージにアップロードする

        Args:
            file_path: アップロードするファイルのパス

        Returns:
            アップロードされたファイルのURL
        """
        return "https://example.com/model.fcstd"


@app.get("/")
async def root():
    """APIのルートエンドポイント"""
    return {"message": "House Design AI FreeCAD API"}


@app.post("/process/grid", status_code=200)
async def process_grid(grid_data: GridData):
    """
    グリッドデータを処理してFreeCADモデルを生成する

    Args:
        grid_data: グリッドデータ（部屋と壁の情報）

    Returns:
        生成されたモデルのURL
    """
    if len(grid_data.rooms) == 0:
        return JSONResponse(
            status_code=400,
            content={"error": "No rooms provided"}
        )

    try:
        storage = CloudStorage()
        
        temp_file = tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False)
        temp_file.close()
        
        url = storage.upload_file(temp_file.name)
        
        os.unlink(temp_file.name)
        
        return {"url": url}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error processing grid: {str(e)}"}
        )


@app.post("/convert/2d", status_code=200)
async def convert_to_2d(file: UploadFile = File(...)):
    """
    3DモデルをPDF図面に変換する

    Args:
        file: アップロードされたFreeCADファイル

    Returns:
        生成されたPDF図面のURL
    """
    if not file.filename.endswith(".fcstd"):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid file format. Only .fcstd files are supported."}
        )

    try:
        storage = CloudStorage()
        
        temp_file = tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False)
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        url = storage.upload_file(temp_file.name)
        
        os.unlink(temp_file.name)
        
        return {"url": url}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error converting to 2D: {str(e)}"}
        )
