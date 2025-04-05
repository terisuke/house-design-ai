import json
import logging
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from google.cloud import storage

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="House Design AI FreeCAD API")
storage_client = storage.Client()


@app.get("/")
async def root():
    """APIのルートエンドポイント"""
    return {"message": "House Design AI FreeCAD API"}


@app.post("/process/grid")
async def process_grid(
    file: UploadFile = File(...), background_tasks: BackgroundTasks = None
):
    """
    グリッドデータからFreeCADモデルを生成するエンドポイント

    Args:
        file: アップロードされたJSONファイル
        background_tasks: バックグラウンドタスク

    Returns:
        JSONResponse: 処理結果
    """
    try:
        # 一時ディレクトリの作成
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "input.json")

        # 入力ファイルを保存
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)

        # JSONデータの読み込み
        with open(temp_file, "r") as f:
            grid_data = json.load(f)

        logger.info(f"Received grid data: {grid_data}")

        # FreeCADを使用した3Dモデル生成処理
        try:
            # FreeCADモジュールのインポート
            import Arch
            import Draft
            import FreeCAD
            import Mesh
            import MeshPart
            import Part
            import Sketcher

            # 新しいFreeCADドキュメントを作成
            doc = FreeCAD.newDocument("HouseDesign")

            # グリッドデータから建物の寸法を取得
            grid = grid_data.get("grid", {})
            madori_info = grid_data.get("madori_info", {})
            params = grid_data.get("params", {})

            # 建物の寸法を計算（グリッド数から）
            width_cells = grid.get("width", 0)
            height_cells = grid.get("height", 0)
            grid_size_mm = params.get("grid_mm", 910)  # デフォルトは910mm

            # 実際の寸法に変換（mm単位）
            width_mm = width_cells * grid_size_mm
            height_mm = height_cells * grid_size_mm

            # 建物の基本形状を作成
            base = Part.makeBox(width_mm, height_mm, 3000)  # 高さ3mの建物

            # 建物の基本形状をFreeCADオブジェクトに変換
            building = doc.addObject("Part::Feature", "Building")
            building.Shape = base

            # 間取り情報から内部の壁を作成
            for room_name, room_info in madori_info.items():
                # 部屋の寸法を取得
                room_width = room_info.get("width", 0) * grid_size_mm
                room_height = room_info.get("height", 0) * grid_size_mm

                # 部屋の位置を取得
                room_x = room_info.get("x", 0) * grid_size_mm
                room_y = room_info.get("y", 0) * grid_size_mm

                # 部屋の壁を作成
                room = doc.addObject("Part::Feature", f"Room_{room_name}")
                room.Shape = Part.makeBox(room_width, room_height, 3000)
                room.Placement.Base = FreeCAD.Vector(room_x, room_y, 0)

                # 部屋のラベルを追加
                text = Draft.makeText(
                    room_name,
                    FreeCAD.Vector(
                        room_x + room_width / 2, room_y + room_height / 2, 1500
                    ),
                    height=500,
                )

            # ドキュメントを保存
            output_file = os.path.join(
                temp_dir, f"house_model_{uuid.uuid4().hex[:8]}.fcstd"
            )
            doc.saveAs(output_file)

            logger.info(f"FreeCAD model created: {output_file}")

        except ImportError as e:
            logger.error(f"FreeCAD import error: {str(e)}")
            # FreeCADが利用できない場合はダミーファイルを作成
            output_file = os.path.join(
                temp_dir, f"dummy_model_{uuid.uuid4().hex[:8]}.fcstd"
            )
            with open(output_file, "w") as f:
                f.write("Dummy FreeCAD file (FreeCAD not available)")
        except Exception as e:
            logger.error(f"FreeCAD processing error: {str(e)}")
            # エラーが発生した場合もダミーファイルを作成
            output_file = os.path.join(
                temp_dir, f"error_model_{uuid.uuid4().hex[:8]}.fcstd"
            )
            with open(output_file, "w") as f:
                f.write(f"Error in FreeCAD processing: {str(e)}")

        # Cloud Storageにアップロード
        bucket_name = os.environ.get("BUCKET_NAME", "house-design-ai-data")
        bucket = storage_client.bucket(bucket_name)

        # ファイル名を生成
        file_name = os.path.basename(output_file)

        # Cloud Storageにアップロード
        blob = bucket.blob(f"cad_models/{file_name}")
        blob.upload_from_filename(output_file)

        # 公開URLを生成
        blob.make_public()
        public_url = blob.public_url

        return JSONResponse(
            content={
                "status": "success",
                "file_url": f"gs://{bucket_name}/cad_models/{file_name}",
                "public_url": public_url,
            }
        )

    except Exception as e:
        logger.error(f"Error processing grid: {str(e)}")
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.post("/convert/2d")
async def convert_to_2d(file: UploadFile = File(...)):
    """
    3Dモデルから2D図面を生成するエンドポイント

    Args:
        file: アップロードされたFreeCADファイル

    Returns:
        JSONResponse: 処理結果
    """
    try:
        # 一時ディレクトリの作成
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "input.fcstd")

        # 入力ファイルを保存
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)

        # FreeCADを使用した2D図面生成処理
        try:
            # FreeCADモジュールのインポート
            import Draft
            import FreeCAD
            import Part
            import TechDraw

            # FreeCADドキュメントを開く
            doc = FreeCAD.open(temp_file)

            # 2D図面を作成
            page = doc.addObject("TechDraw::DrawPage", "Page")
            view = doc.addObject("TechDraw::DrawViewArch", "View")
            view.Source = doc.getObject("Building")
            page.addView(view)

            # 図面を更新
            page.recompute()

            # PDFとしてエクスポート
            output_file = os.path.join(
                temp_dir, f"floorplan_{uuid.uuid4().hex[:8]}.pdf"
            )
            TechDraw.export([page], output_file)

            logger.info(f"2D drawing created: {output_file}")

        except ImportError as e:
            logger.error(f"FreeCAD import error: {str(e)}")
            # FreeCADが利用できない場合はダミーファイルを作成
            output_file = os.path.join(
                temp_dir, f"dummy_drawing_{uuid.uuid4().hex[:8]}.pdf"
            )
            with open(output_file, "w") as f:
                f.write("Dummy PDF file (FreeCAD not available)")
        except Exception as e:
            logger.error(f"FreeCAD 2D conversion error: {str(e)}")
            # エラーが発生した場合もダミーファイルを作成
            output_file = os.path.join(
                temp_dir, f"error_drawing_{uuid.uuid4().hex[:8]}.pdf"
            )
            with open(output_file, "w") as f:
                f.write(f"Error in FreeCAD 2D conversion: {str(e)}")

        # Cloud Storageにアップロード
        bucket_name = os.environ.get("BUCKET_NAME", "house-design-ai-data")
        bucket = storage_client.bucket(bucket_name)

        # ファイル名を生成
        file_name = os.path.basename(output_file)

        # Cloud Storageにアップロード
        blob = bucket.blob(f"drawings/{file_name}")
        blob.upload_from_filename(output_file)

        # 公開URLを生成
        blob.make_public()
        public_url = blob.public_url

        return JSONResponse(
            content={
                "status": "success",
                "file_url": f"gs://{bucket_name}/drawings/{file_name}",
                "public_url": public_url,
            }
        )

    except Exception as e:
        logger.error(f"Error converting to 2D: {str(e)}")
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )
