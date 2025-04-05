import json
import logging
import os
import tempfile

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

        # TODO: FreeCADを使用した3Dモデル生成処理
        # 現在はダミーの処理

        # Cloud Storageにアップロード（ダミー）
        bucket_name = os.environ.get("BUCKET_NAME", "house-design-ai-data")
        bucket = storage_client.bucket(bucket_name)
        output_file = os.path.join(temp_dir, "output.fcstd")

        # ダミーファイルの作成
        with open(output_file, "w") as f:
            f.write("Dummy FreeCAD file")

        # Cloud Storageにアップロード
        blob = bucket.blob(f"cad_models/{os.path.basename(output_file)}")
        blob.upload_from_filename(output_file)

        return JSONResponse(
            content={
                "status": "success",
                "file_url": f"gs://{bucket_name}/cad_models/{os.path.basename(output_file)}",
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

        # TODO: FreeCADを使用した2D図面生成処理
        # 現在はダミーの処理

        # Cloud Storageにアップロード（ダミー）
        bucket_name = os.environ.get("BUCKET_NAME", "house-design-ai-data")
        bucket = storage_client.bucket(bucket_name)
        output_file = os.path.join(temp_dir, "output.pdf")

        # ダミーファイルの作成
        with open(output_file, "w") as f:
            f.write("Dummy PDF file")

        # Cloud Storageにアップロード
        blob = bucket.blob(f"drawings/{os.path.basename(output_file)}")
        blob.upload_from_filename(output_file)

        return JSONResponse(
            content={
                "status": "success",
                "file_url": f"gs://{bucket_name}/drawings/{os.path.basename(output_file)}",
            }
        )

    except Exception as e:
        logger.error(f"Error converting to 2D: {str(e)}")
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )
