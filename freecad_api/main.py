import json
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Union

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile, Body
from fastapi.responses import JSONResponse
try:
    from google.cloud import storage as gcs_storage
except ImportError:
    logging.error("google-cloud-storage package is not installed. Cloud Storage functionality will be disabled.")
    gcs_storage = None
from pydantic import BaseModel

# ロギングの設定
logging.basicConfig(level=logging.INFO)
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
    クラウドストレージの操作を行うクラス
    """

    def __init__(self):
        self.bucket_name = os.environ.get("BUCKET_NAME", "house-design-ai-data")
        if gcs_storage is not None:
            try:
                self.client = gcs_storage.Client()
                self.bucket = self.client.bucket(self.bucket_name)
                self.storage_available = True
            except Exception as e:
                logger.error(f"Cloud Storageの初期化に失敗しました: {e}")
                self.storage_available = False
        else:
            logger.warning("Cloud Storageが利用できません。ローカルファイルのみ使用します。")
            self.storage_available = False

    def upload_file(
        self, file_path: str, destination_blob_name: Optional[str] = None
    ) -> str:
        """
        ファイルをクラウドストレージにアップロードする

        Args:
            file_path: アップロードするファイルのパス
            destination_blob_name: アップロード先のBlob名（指定しない場合はファイル名を使用）

        Returns:
            アップロードされたファイルのURL
        """
        if not self.storage_available:
            logger.warning(f"Cloud Storageが利用できないため、ローカルファイルを使用します: {file_path}")
            return f"file://{file_path}"

        if destination_blob_name is None:
            destination_blob_name = os.path.basename(file_path)

        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path)

        # 署名付きURLを生成（1時間有効）
        url = blob.generate_signed_url(version="v4", expiration=3600, method="GET")

        logger.info(
            f"ファイルをアップロードしました: gs://{self.bucket_name}/{destination_blob_name}"
        )
        return url


@app.get("/")
async def root():
    """APIのルートエンドポイント"""
    return {"message": "House Design AI FreeCAD API"}


@app.post("/process/grid")
async def process_grid(grid_data: GridData):
    """
    グリッドデータを処理してFreeCADモデルを生成する

    Args:
        grid_data: グリッドデータ（部屋と壁の情報）

    Returns:
        生成されたモデルのURL
    """
    if len(grid_data.rooms) == 0:
        return JSONResponse(status_code=400, content={"error": "No rooms provided"})

    try:
        # 一時ファイルにグリッドデータを保存
        temp_json = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        with open(temp_json.name, "w") as f:
            json.dump(grid_data.dict(), f)

        # 一時ファイルにFreeCADスクリプトを保存
        temp_script = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        with open(temp_script.name, "w") as f:
            f.write(
                f"""
import json
import os
import sys
import FreeCAD
import Part

# グリッドデータを読み込む
with open("{temp_json.name}", "r") as f:
    grid_data = json.load(f)

# 新しいドキュメントを作成
doc = FreeCAD.newDocument("HouseModel")

# 部屋を作成
for room_obj in grid_data["rooms"]:
    dimensions = room_obj["dimensions"]
    position = room_obj["position"]
    
    # 部屋の形状を作成
    box = Part.makeBox(dimensions[0], dimensions[1], 2.5, 
                       FreeCAD.Vector(position[0], position[1], 0))
    
    # オブジェクトを追加
    obj = doc.addObject("Part::Feature", f"Room_{room_obj['id']}")
    obj.Shape = box

# 壁を作成
for wall in grid_data["walls"]:
    start = wall["start"]
    end = wall["end"]
    height = wall.get("height", 2.5)
    
    # 壁の形状を作成
    wall_box = Part.makeBox(end[0] - start[0], 0.2, height,
                           FreeCAD.Vector(start[0], start[1], 0))
    
    # オブジェクトを追加
    obj = doc.addObject("Part::Feature", "Wall")
    obj.Shape = wall_box

# ドキュメントを再計算
doc.recompute()

# 出力ディレクトリを設定
output_dir = os.environ.get("OUTPUT_DIR", "/tmp")
os.makedirs(output_dir, exist_ok=True)

# ファイルを保存
output_file = os.path.join(output_dir, "model.FCStd")
doc.saveAs(output_file)

print(f"モデルを保存しました: {{output_file}}")
"""
            )

        # FreeCADスクリプトを実行
        output_file = tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False).name
        os.environ["OUTPUT_DIR"] = os.path.dirname(output_file)

        result = subprocess.run(
            ["FreeCADCmd", temp_script.name], capture_output=True, text=True
        )

        if result.returncode != 0:
            logger.error(f"FreeCADスクリプトの実行に失敗しました: {result.stderr}")
            return JSONResponse(
                status_code=500, content={"error": "Failed to process grid data"}
            )

        # 一時ファイルを削除
        os.unlink(temp_json.name)
        os.unlink(temp_script.name)

        # 生成されたモデルをCloud Storageにアップロード
        storage_client = CloudStorage()
        url = storage_client.upload_file(output_file, f"models/{uuid.uuid4()}.fcstd")

        # 一時ファイルを削除
        os.unlink(output_file)

        return {"url": url}
    except Exception as e:
        logger.error(f"グリッドデータの処理中にエラーが発生しました: {e}")
        return JSONResponse(
            status_code=500, content={"error": f"Error processing grid: {str(e)}"}
        )


@app.post("/convert/2d")
async def convert_to_2d(file: Optional[UploadFile] = File(None), grid_data: Optional[Dict] = Body(None)):
    """
    3DモデルをPDF図面に変換する

    Args:
        file: アップロードされたFreeCADファイル（ファイルアップロード方式）
        grid_data: グリッドデータ（JSON方式）

    Returns:
        生成されたPDF図面のURL
    """
    is_file_upload = file is not None
    is_json_data = grid_data is not None

    if not is_file_upload and not is_json_data:
        return JSONResponse(
            status_code=400,
            content={"error": "Either file upload or grid data must be provided."},
        )

    try:
        temp_file = None
        
        if is_file_upload:
            if not file.filename.endswith(".fcstd"):
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid file format. Only .fcstd files are supported."},
                )
                
            # 一時ファイルにアップロードされたファイルを保存
            temp_file = tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False)
            content = await file.read()
            temp_file.write(content)
            temp_file.close()
            
        elif is_json_data:
            temp_json = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
            with open(temp_json.name, "w") as f:
                json.dump(grid_data, f)
                
            # 一時ファイルにFreeCADスクリプトを保存（モデル生成用）
            temp_model_script = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
            with open(temp_model_script.name, "w") as f:
                f.write(
                    f"""
import json
import os
import sys
import FreeCAD
import Part

# グリッドデータを読み込む
with open("{temp_json.name}", "r") as f:
    grid_data = json.load(f)

# 新しいドキュメントを作成
doc = FreeCAD.newDocument("HouseModel")

wall_thickness = 0.12  # 120mm
first_floor_height = 2.9  # 2900mm
second_floor_height = 2.8  # 2800mm

if "rooms" in grid_data:
    for room_obj in grid_data["rooms"]:
        dimensions = room_obj["dimensions"]
        position = room_obj["position"]
        
        # 部屋の形状を作成
        box = Part.makeBox(dimensions[0], dimensions[1], first_floor_height, 
                           FreeCAD.Vector(position[0], position[1], 0))
        
        # オブジェクトを追加
        obj = doc.addObject("Part::Feature", f"Room_{{room_obj['id']}}")
        obj.Shape = box

if "walls" in grid_data:
    for i, wall in enumerate(grid_data["walls"]):
        start = wall["start"]
        end = wall["end"]
        height = wall.get("height", first_floor_height)
        
        import math
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx) * 180 / math.pi
        
        # 壁の形状を作成
        wall_box = Part.makeBox(length, wall_thickness, height,
                               FreeCAD.Vector(start[0], start[1], 0))
        
        if angle != 0:
            wall_box.rotate(FreeCAD.Vector(start[0], start[1], 0), FreeCAD.Vector(0, 0, 1), angle)
        
        # オブジェクトを追加
        obj = doc.addObject("Part::Feature", f"Wall_{{i}}")
        obj.Shape = wall_box

# ドキュメントを再計算
doc.recompute()

# 出力ディレクトリを設定
output_dir = os.environ.get("OUTPUT_DIR", "/tmp")
os.makedirs(output_dir, exist_ok=True)

# ファイルを保存
output_file = os.path.join(output_dir, "model.FCStd")
doc.saveAs(output_file)

print(f"モデルを保存しました: {{output_file}}")
"""
                )
                
            # FreeCADスクリプトを実行してモデルを生成
            temp_file = tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False).name
            os.environ["OUTPUT_DIR"] = os.path.dirname(temp_file)
            
            model_result = subprocess.run(
                ["FreeCADCmd", temp_model_script.name], capture_output=True, text=True
            )
            
            if model_result.returncode != 0:
                logger.error(f"FreeCADモデル生成に失敗しました: {model_result.stderr}")
                return JSONResponse(
                    status_code=500, content={"error": "Failed to generate 3D model from grid data"}
                )
                
            # 一時ファイルを削除
            os.unlink(temp_json.name)
            os.unlink(temp_model_script.name)

        # 一時ファイルにFreeCADスクリプトを保存（2D変換用）
        temp_script = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        with open(temp_script.name, "w") as f:
            f.write(
                f"""
import os
import sys
import FreeCAD
import TechDraw

# モデルを開く
doc = FreeCAD.open("{temp_file}")

# 新しいTechDrawドキュメントを作成
tdoc = FreeCAD.newDocument("TechDraw")

# ページを作成
page = tdoc.addObject('TechDraw::DrawPage', 'Page')
template = FreeCAD.getResourceDir() + '/Mod/TechDraw/Templates/A3_Landscape.svg'
page.Template = template

# ビューを作成
view = tdoc.addObject('TechDraw::DrawViewPart', 'View')
view.Source = doc.Objects[0]
page.addView(view)

# ドキュメントを再計算
tdoc.recompute()

# 出力ディレクトリを設定
output_dir = os.environ.get("OUTPUT_DIR", "/tmp")
os.makedirs(output_dir, exist_ok=True)

# PDFをエクスポート
output_file = os.path.join(output_dir, "drawing.pdf")
page.exportPDF(output_file)

print(f"図面を保存しました: {{output_file}}")
"""
            )

        # FreeCADスクリプトを実行
        output_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name
        os.environ["OUTPUT_DIR"] = os.path.dirname(output_file)

        result = subprocess.run(
            ["FreeCADCmd", temp_script.name], capture_output=True, text=True
        )

        if result.returncode != 0:
            logger.error(f"FreeCADスクリプトの実行に失敗しました: {result.stderr}")
            return JSONResponse(
                status_code=500, content={"error": "Failed to convert to 2D"}
            )

        # 一時ファイルを削除
        if is_file_upload and isinstance(temp_file, tempfile._TemporaryFileWrapper):
            os.unlink(temp_file.name)
        os.unlink(temp_script.name)

        # 生成されたPDFをCloud Storageにアップロード
        storage_client = CloudStorage()
        url = storage_client.upload_file(output_file, f"drawings/{uuid.uuid4()}.pdf")

        # 一時ファイルを削除
        os.unlink(output_file)

        return {"url": url}
    except Exception as e:
        logger.error(f"2D変換中にエラーが発生しました: {e}")
        return JSONResponse(
            status_code=500, content={"error": f"Error converting to 2D: {str(e)}"}
        )


@app.post("/convert/3d")
async def convert_to_3d(file: UploadFile = File(...)):
    """
    FCStdファイルをglTFに変換し、Cloud StorageにアップロードしてURLを返す
    """
    if not file.filename.endswith(".fcstd"):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid file format. Only .fcstd files are supported."},
        )
    try:
        # 一時ファイル保存
        temp_file = tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False)
        content = await file.read()
        temp_file.write(content)
        temp_file.close()

        # FreeCADスクリプトでglTF変換
        temp_script = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        with open(temp_script.name, "w") as f:
            f.write(f"""
import os
import FreeCAD
import Import
import Mesh
import ImportGui
import Part
import MeshPart
import ImportExport
import ImportGLTF

doc = FreeCAD.open(\"{temp_file.name}\")
obj = doc.Objects[0]
output_file = \"{temp_file.name}.gltf\"
ImportGLTF.export([obj], output_file)
print(f\"Exported: {{output_file}}\")
""")
        output_file = f"{temp_file.name}.gltf"
        os.environ["OUTPUT_DIR"] = os.path.dirname(output_file)
        result = subprocess.run(
            ["FreeCADCmd", temp_script.name], capture_output=True, text=True
        )
        if result.returncode != 0:
            return JSONResponse(status_code=500, content={"error": "Failed to convert to glTF", "stderr": result.stderr})
        # Cloud Storageアップロード
        storage_client = CloudStorage()
        url = storage_client.upload_file(output_file, f"models/{uuid.uuid4()}.gltf")
        os.unlink(temp_file.name)
        os.unlink(temp_script.name)
        os.unlink(output_file)
        return {"url": url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
