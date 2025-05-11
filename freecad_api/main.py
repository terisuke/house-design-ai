import json
import logging
import os
import tempfile
import uuid
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile, Body, Form, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
try:
    from google.cloud import storage as gcs_storage
except ImportError:
    logging.error("google-cloud-storage package is not installed. Cloud Storage functionality will be disabled.")
    gcs_storage = None
from pydantic import BaseModel

try:
    import trimesh
except ImportError:
    logging.error("Failed to import trimesh module")
    trimesh = None

# FreeCADのPython APIをインポート
try:
    import FreeCAD
    import Part
    import Mesh
    import MeshPart
    import TechDraw
except ImportError as e:
    logging.error(f"FreeCADのインポートに失敗しました: {e}")
    raise

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="House Design AI FreeCAD API")

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Room(BaseModel):
    id: int
    dimensions: List[float]
    position: List[float]
    label: str


class Wall(BaseModel):
    start: List[float]
    end: List[float]
    height: float = 2.9  # Default for 1st floor (2900mm)
    floor: int = 1  # 1 for first floor, 2 for second floor


class GridData(BaseModel):
    rooms: List[Room]
    walls: List[Wall]
    wall_thickness: float = 0.12  # デフォルト値0.12m（120mm）
    include_furniture: bool = True


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
                self.client = None
                self.bucket = None
        else:
            logger.warning("Cloud Storageが利用できません。ローカルファイルのみ使用します。")
            self.storage_available = False
            self.client = None
            self.bucket = None

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
        if not self.storage_available or self.client is None or self.bucket is None:
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


class ModelParameters(BaseModel):
    wall_thickness: float = 0.2
    window_size: float = 1.5
    include_furniture: bool = True


class ModelRequest(BaseModel):
    width: float = 10.0
    length: float = 10.0
    height: float = 3.0
    parameters: ModelParameters = ModelParameters()


class ModelResponse(BaseModel):
    status: str
    message: str
    file: str
    storage_url: Optional[str] = None


@app.get("/")
async def root():
    """APIのルートエンドポイント"""
    return {"message": "House Design AI FreeCAD API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/process/grid")
async def process_grid(grid_data: GridData):
    """
    グリッドデータを処理してFreeCADモデルを生成する

    Args:
        grid_data: グリッドデータ（部屋と壁の情報）

    Returns:
        生成されたモデルのURL
    """
    logger.info(f"Input grid_data: {grid_data.dict()}")
    
    if len(grid_data.rooms) == 0:
        return JSONResponse(status_code=400, content={"error": "No rooms provided"})
    
    if len(grid_data.walls) == 0:
        logger.warning("No walls provided in grid data")

    try:
        # 新しいドキュメントを作成
        doc = FreeCAD.newDocument("HouseModel")
        
        # パラメータを取得
        wall_thickness = grid_data.wall_thickness
        include_furniture = grid_data.include_furniture
        
        # 部屋を作成
        for room in grid_data.rooms:
            dimensions = room.dimensions
            position = room.position
            
            # 部屋の形状を作成
            box = Part.makeBox(dimensions[0], dimensions[1], 2.5, 
                            FreeCAD.Vector(position[0], position[1], 0))
            
            # オブジェクトを追加
            obj = doc.addObject("Part::Feature", f"Room_{room.id}")
            obj.Shape = box
        
        # 壁を作成
        for wall in grid_data.walls:
            start = wall.start
            end = wall.end
            
            if hasattr(wall, 'floor') and wall.floor == 2:
                height = 2.8  # 2nd floor height (2800mm)
            else:
                height = 2.9  # 1st floor height (2900mm)
            
            # 壁の長さを計算
            wall_length = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
            
            is_x_direction = abs(end[0] - start[0]) > abs(end[1] - start[1])
            
            if is_x_direction:
                # X方向の壁
                wall_box = Part.makeBox(
                    wall_length, wall_thickness, height,
                    FreeCAD.Vector(start[0], start[1] - wall_thickness/2, 0)
                )
            else:
                # Y方向の壁
                wall_box = Part.makeBox(
                    wall_thickness, wall_length, height,
                    FreeCAD.Vector(start[0] - wall_thickness/2, start[1], 0)
                )
            
            # オブジェクトを追加
            obj = doc.addObject("Part::Feature", f"Wall_{start[0]}_{start[1]}")
            obj.Shape = wall_box
        
        # ドキュメントを再計算
        doc.recompute()
        output_file = tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False).name
        doc.saveAs(output_file)
        
        # Cloud Storageにアップロード
        storage_client = CloudStorage()
        url = storage_client.upload_file(output_file, f"models/{uuid.uuid4()}.fcstd")
        # 一時ファイルを削除
        os.unlink(output_file)
        
        return {"url": url}
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"グリッドデータの処理中にエラーが発生しました: {e}")
        logger.error(f"エラートレース: {error_trace}")
        return JSONResponse(
            status_code=500, 
            content={
                "error": f"Error processing grid: {str(e)}", 
                "trace": error_trace if os.environ.get("DEBUG", "false").lower() == "true" else None
            }
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

# ページを作成 - A3サイズを使用
page = tdoc.addObject('TechDraw::DrawPage', 'Page')
template = FreeCAD.getResourceDir() + '/Mod/TechDraw/Templates/A3_Landscape_ISO.svg'
page.Template = template

# モデル内のすべてのオブジェクトを取得
objects = []
for obj in doc.Objects:
    if hasattr(obj, "Shape"):
        objects.append(obj)

# ビューを作成（すべてのオブジェクトを対象に）
if objects:
    top_view = tdoc.addObject('TechDraw::DrawViewPart', 'TopView')
    top_view.Source = objects
    top_view.Direction = FreeCAD.Vector(0, 0, 1)
    top_view.Scale = 0.1  # 1:10スケール
    top_view.X = 100
    top_view.Y = 100
    page.addView(top_view)
    
    front_view = tdoc.addObject('TechDraw::DrawViewPart', 'FrontView')
    front_view.Source = objects
    front_view.Direction = FreeCAD.Vector(0, -1, 0)
    front_view.Scale = 0.1
    front_view.X = 100
    front_view.Y = 250
    page.addView(front_view)
    
    side_view = tdoc.addObject('TechDraw::DrawViewPart', 'SideView')
    side_view.Source = objects
    side_view.Direction = FreeCAD.Vector(1, 0, 0)
    side_view.Scale = 0.1
    side_view.X = 250
    side_view.Y = 250
    page.addView(side_view)
    
    iso_view = tdoc.addObject('TechDraw::DrawViewPart', 'IsoView')
    iso_view.Source = objects
    iso_view.Direction = FreeCAD.Vector(1, 1, 1)
    iso_view.Scale = 0.1
    iso_view.X = 250
    iso_view.Y = 100
    page.addView(iso_view)
else:
    print("モデル内に表示可能なオブジェクトが見つかりません")
    sys.exit(1)

# ドキュメントを再計算
tdoc.recompute()

# 出力ディレクトリを設定
output_dir = os.environ.get("OUTPUT_DIR", "/tmp")
os.makedirs(output_dir, exist_ok=True)

# PDFをエクスポート
output_file = os.path.join(output_dir, "drawing.pdf")
page.exportPDF(output_file)

print(f"PDFを保存しました: {{output_file}}")
"""
            )

        output_file = os.path.join(os.path.dirname(temp_script.name), "drawing.pdf")
        os.environ["OUTPUT_DIR"] = os.path.dirname(output_file)
        
        # FreeCADスクリプトを実行
        result = subprocess.run(
            ["FreeCADCmd", temp_script.name], capture_output=True, text=True
        )
        
        if result.returncode != 0:
            logger.error(f"FreeCADスクリプトの実行に失敗しました: {result.stderr}")
            return JSONResponse(
                status_code=500, content={"error": "Failed to convert to 2D drawing"}
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
async def convert_to_3d(
    file: Optional[UploadFile] = File(None),
    grid_data: Optional[GridData] = None
):
    """
    FCStdファイルをSTL形式に変換する

    Args:
        file: アップロードされたFreeCADファイル（ファイルアップロード方式）
        grid_data: グリッドデータ（JSON方式）

    Returns:
        変換されたSTLモデルのURL
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

        # モデルを開く
        if temp_file is None:
            return JSONResponse(
                status_code=500, content={"error": "Failed to create temporary file"}
            )
        doc = FreeCAD.open(temp_file if isinstance(temp_file, str) else temp_file.name)
        
        # すべてのオブジェクトを取得
        objects = doc.Objects

        # メッシュ変換
        meshes = []
        for obj in objects:
            if hasattr(obj, "Shape"):
                mesh = MeshPart.meshFromShape(
                    Shape=obj.Shape,
                    LinearDeflection=0.1,
                    AngularDeflection=0.1,
                    Relative=False
                )
                meshes.append(mesh)

        # 出力ディレクトリとファイル名を設定
        output_dir = tempfile.mkdtemp()
        output_stl = os.path.join(output_dir, "model.stl")

        # STLファイルとして保存
        if meshes:
            Mesh.Mesh(meshes).write(output_stl)
            logger.info(f"STLモデルを保存しました: {output_stl}")
        else:
            logger.error("No meshes were created")
            return JSONResponse(
                status_code=500, content={"error": "No meshes were created"}
            )

        # Cloud Storageにアップロード
        storage = CloudStorage()
        url = storage.upload_file(output_stl, f"models/{uuid.uuid4()}.stl")

        # 一時ファイルを削除
        if is_file_upload and isinstance(temp_file, tempfile._TemporaryFileWrapper):
            os.unlink(temp_file.name)
        elif isinstance(temp_file, str):
            os.unlink(temp_file)
        os.unlink(output_stl)
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)

        return {"url": url, "format": "stl"}
    except Exception as e:
        logger.error(f"3D変換中にエラーが発生しました: {e}")
        return JSONResponse(
            status_code=500, content={"error": f"Error converting to 3D: {str(e)}"}
        )


@app.post("/convert/stl-to-gltf")
async def convert_stl_to_gltf(file: UploadFile = File(...)):
    """
    STLファイルをglTF形式に変換する
    """
    if not file.filename.endswith(".stl"):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid file format. Only .stl files are supported."},
        )

    try:
        if trimesh is None:
            return JSONResponse(
                status_code=500, 
                content={"error": "trimesh module not available for STL to glTF conversion"}
            )
            
        # 一時ファイルにアップロードされたファイルを保存
        temp_stl = tempfile.NamedTemporaryFile(suffix=".stl", delete=False)
        content = await file.read()
        temp_stl.write(content)
        temp_stl.close()

        if trimesh is not None:
            mesh = trimesh.load(temp_stl.name)
            
            output_gltf = temp_stl.name.replace(".stl", ".gltf")
            mesh.export(output_gltf, file_type="gltf")
            
            # Cloud Storageにアップロード
            storage = CloudStorage()
            url = storage.upload_file(output_gltf, f"models/{uuid.uuid4()}.gltf")
            
            # 一時ファイルを削除
            os.unlink(temp_stl.name)
            os.unlink(output_gltf)
            
            return {"url": url, "format": "gltf"}
        else:
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

doc = FreeCAD.open(\"{temp_stl.name}\")
obj = doc.Objects[0]
output_file = \"{temp_stl.name}.gltf\"
ImportGLTF.export([obj], output_file)
print(f\"Exported: {{output_file}}\")
""")
            output_file = f"{temp_stl.name}.gltf"
            os.environ["OUTPUT_DIR"] = os.path.dirname(output_file)
            result = subprocess.run(
                ["FreeCADCmd", temp_script.name], capture_output=True, text=True
            )
            if result.returncode != 0:
                return JSONResponse(status_code=500, content={"error": "Failed to convert to glTF", "stderr": result.stderr})
            # Cloud Storageアップロード
            storage = CloudStorage()
            url = storage.upload_file(output_file, f"models/{uuid.uuid4()}.gltf")
            os.unlink(temp_stl.name)
            os.unlink(temp_script.name)
            os.unlink(output_file)
            return {"url": url, "format": "gltf"}
    except Exception as e:
        logger.error(f"STL→glTF変換中にエラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500, content={"error": f"Error converting STL to glTF: {str(e)}"}
        )


@app.post("/process/drawing")
async def process_drawing(
    model_url: str = Form(...),
    drawing_type: str = Form(..., description="平面図、立面図、断面図、アイソメトリック"),
    scale: str = Form(..., description="1:50, 1:100, 1:200"),
):
    """
    3DモデルからCAD図面を生成する
    """
    try:
        # モデルURLからFCStdファイルをダウンロード
        temp_fcstd = tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False)
        temp_fcstd.close()
        
        # URLがgcs://から始まる場合はCloud Storageから取得
        if model_url.startswith("gs://"):
            import re
            match = re.match(r'gs://([^/]+)/(.+)', model_url)
            if match:
                bucket_name = match.group(1)
                object_name = match.group(2)
                
                try:
                    from google.cloud import storage as gcs
                    storage_client = gcs.Client()
                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(object_name)
                except ImportError:
                    logger.error("Google Cloud Storage module not available")
                    return JSONResponse(
                        status_code=500, content={"error": "Cloud Storage module not available"}
                    )
                blob.download_to_filename(temp_fcstd.name)
            else:
                return JSONResponse(
                    status_code=400, content={"error": "Invalid GCS URL format"}
                )
        else:
            # 通常のHTTP URLからダウンロード
            response = requests.get(model_url)
            if response.status_code != 200:
                return JSONResponse(
                    status_code=400, 
                    content={"error": f"Failed to download model from URL: {response.status_code}"}
                )
            with open(temp_fcstd.name, "wb") as f:
                f.write(response.content)

        # 図面タイプに基づいてビュー方向を設定
        view_dir = {"X": 0, "Y": 0, "Z": 1}  # デフォルトは平面図（上から）
        if drawing_type == "立面図":
            view_dir = {"X": 0, "Y": 1, "Z": 0}  # Y軸方向から
        elif drawing_type == "側面図":
            view_dir = {"X": 1, "Y": 0, "Z": 0}  # X軸方向から
        elif drawing_type == "アイソメトリック":
            view_dir = {"X": 1, "Y": 1, "Z": 1}  # 等角投影

        # 縮尺を抽出
        scale_value = float(scale.split(":")[1])
        scale_factor = 1.0 / scale_value

        # モデルを開く
        doc = FreeCAD.open(temp_fcstd.name)

        # 新しいTechDrawドキュメントを作成
        tdoc = FreeCAD.newDocument("TechDraw")

        # ページを作成 - A3サイズを使用
        page = tdoc.addObject('TechDraw::DrawPage', 'Page')
        template = FreeCAD.getResourceDir() + '/Mod/TechDraw/Templates/A3_Landscape_ISO.svg'
        page.Template = template

        # ビュー方向の設定
        direction = FreeCAD.Vector(view_dir["X"], view_dir["Y"], view_dir["Z"])

        # モデル内のすべてのオブジェクトを取得
        objects = []
        for obj in doc.Objects:
            if hasattr(obj, "Shape"):
                objects.append(obj)

        # ビューを作成（すべてのオブジェクトを対象に）
        if objects:
            view = tdoc.addObject('TechDraw::DrawViewPart', 'View')
            view.Source = objects
            view.Direction = direction
            view.Scale = scale_factor
            page.addView(view)
            
            # 寸法線の追加（すべてのエッジに対して自動的に追加）
            if drawing_type != 'アイソメトリック':  # 等角投影では寸法線は追加しない
                edges = view.getEdgesForVertex(0)  # すべてのエッジを取得
                for i, edge in enumerate(edges[:5]):  # 最初の5つのエッジにのみ寸法線を追加
                    dim = tdoc.addObject('TechDraw::DrawViewDimension', f'Dimension{i}')
                    dim.Type = 'Distance'
                    dim.References2D = [(view, edge)]
                    page.addView(dim)
            
            # アイソメトリック表示の場合は追加設定
            if drawing_type == 'アイソメトリック':
                view.XSource = FreeCAD.Vector(1, 0, 0)
                view.YSource = FreeCAD.Vector(0, 1, 0)
                view.CoarseView = False
                view.ShowHiddenLines = True
                view.ShowSmoothLines = True
        else:
            logger.error("モデル内に表示可能なオブジェクトが見つかりません")
            return JSONResponse(
                status_code=500, content={"error": "No visible objects found in model"}
            )

        # ドキュメントを再計算
        tdoc.recompute()

        # 出力ディレクトリを設定
        output_dir = tempfile.mkdtemp()
        output_pdf = os.path.join(output_dir, "drawing.pdf")

        # PDFをエクスポート
        page.exportPDF(output_pdf)
        logger.info(f"PDFを保存しました: {output_pdf}")

        # Cloud Storageにアップロード
        storage = CloudStorage()
        url = storage.upload_file(output_pdf, f"drawings/{uuid.uuid4()}.pdf")

        # 一時ファイルを削除
        os.unlink(temp_fcstd.name)
        os.unlink(output_pdf)
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)

        return {"url": url, "format": "pdf"}
    except Exception as e:
        logger.error(f"図面生成中にエラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500, content={"error": f"Error generating drawing: {str(e)}"}
        )


@app.post("/generate")
async def generate_model(request: ModelRequest):
    """
    指定されたパラメータに基づいて建物の3Dモデルを生成します。
    """
    try:
        # 新しいドキュメントを作成
        doc = FreeCAD.newDocument("HouseModel")

        # 基本形状を作成
        box = Part.makeBox(request.width, request.length, request.height, 
                       FreeCAD.Vector(0, 0, 0))

        # オブジェクトを追加
        obj = doc.addObject("Part::Feature", "House")
        obj.Shape = box

        # ドキュメントを再計算
        doc.recompute()

        # 出力ディレクトリを設定
        output_file = tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False).name

        # ファイルを保存
        doc.saveAs(output_file)
        logger.info(f"モデルを保存しました: {output_file}")

        # 生成されたモデルをCloud Storageにアップロード
        storage = CloudStorage()
        storage_url = storage.upload_file(output_file, f"models/{uuid.uuid4()}.fcstd")

        # 一時ファイルを削除
        os.unlink(output_file)

        return ModelResponse(
            status="success",
            message="3Dモデルの生成に成功しました",
            file=output_file,
            storage_url=storage_url
        )
    except Exception as e:
        logger.error(f"モデル生成中にエラーが発生しました: {e}")
        return JSONResponse(
            status_code=500, content={"error": f"Error generating model: {str(e)}"}
        )
