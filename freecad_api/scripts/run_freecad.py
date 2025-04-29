import logging
import os
import sys
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FreeCAD API",
    description="""
    # FreeCAD API for House Design AI

    このAPIは、建物の3Dモデルを自動生成するためのサービスを提供します。
    YOLOv11による建物セグメンテーションの結果を基に、FreeCADを使用して3Dモデルを生成します。

    ## 主な機能
    - 建物の基本形状の3Dモデル生成
    - Cloud Storageへのモデル保存
    - カスタマイズ可能なパラメータ設定

    ## 使用方法
    1. `/generate` エンドポイントにPOSTリクエストを送信
    2. 必要なパラメータ（幅、長さ、高さ）を指定
    3. 生成されたモデルのパスを取得

    ## 注意事項
    - すべての寸法はメートル単位で指定してください
    - パラメータは適切な範囲内で指定してください
    """,
    version="1.0.0",
    contact={
        "name": "House Design AI Team",
        "url": "https://github.com/terisuke/house-design-ai",
    },
)


class ModelParameters(BaseModel):
    """
    建物モデルの詳細パラメータ
    """

    wall_thickness: float = Field(
        default=0.2, description="壁の厚さ（メートル）", ge=0.1, le=1.0
    )
    window_size: float = Field(
        default=1.5, description="窓のサイズ（メートル）", ge=0.5, le=3.0
    )


class ModelRequest(BaseModel):
    """
    3Dモデル生成リクエストのパラメータ
    """

    width: float = Field(
        default=10.0, description="建物の幅（メートル）", ge=1.0, le=100.0
    )
    length: float = Field(
        default=10.0, description="建物の長さ（メートル）", ge=1.0, le=100.0
    )
    height: float = Field(
        default=3.0, description="建物の高さ（メートル）", ge=2.0, le=50.0
    )
    parameters: ModelParameters = Field(
        default_factory=ModelParameters, description="詳細なモデルパラメータ"
    )


class ModelResponse(BaseModel):
    """
    3Dモデル生成レスポンス
    """

    status: str = Field(description="処理の状態（success/error）")
    message: str = Field(description="処理結果の説明メッセージ")
    file: str = Field(description="生成されたモデルファイルのパス")
    storage_url: Optional[str] = Field(
        None, description="Cloud Storageに保存された場合のURL"
    )


@app.post(
    "/generate",
    response_model=ModelResponse,
    summary="3Dモデルの生成",
    description="""
    指定されたパラメータに基づいて建物の3Dモデルを生成します。

    生成されたモデルは一時ディレクトリに保存され、
    BUCKET_NAME環境変数が設定されている場合はCloud Storageにもアップロードされます。

    ## パラメータの制約
    - width: 1.0m ～ 100.0m
    - length: 1.0m ～ 100.0m
    - height: 2.0m ～ 50.0m
    - wall_thickness: 0.1m ～ 1.0m
    - window_size: 0.5m ～ 3.0m
    """,
    response_description="生成されたモデルの情報",
)
async def generate_model(request: ModelRequest) -> ModelResponse:
    try:
        logger.info("FreeCAD CLIスクリプトを開始します")
        logger.info(f"リクエストパラメータ: {request.dict()}")

        import FreeCAD
        import Part

        doc = FreeCAD.newDocument("Example")

        box = Part.makeBox(request.width, request.length, request.height)

        obj = doc.addObject("Part::Feature", "Box")
        obj.Shape = box

        doc.recompute()

        output_dir = os.environ.get("OUTPUT_DIR", "/tmp")
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(output_dir, "model.FCStd")
        doc.saveAs(output_file)

        logger.info(f"モデルを保存しました: {output_file}")

        storage_url = None
        bucket_name = os.environ.get("BUCKET_NAME")
        if bucket_name:
            try:
                from google.cloud import storage

                logger.info(
                    f"Cloud Storageクライアントを初期化します。バケット名: {bucket_name}"
                )

                client = storage.Client()
                bucket = client.bucket(bucket_name)
                logger.info(f"バケットを取得しました: {bucket.name}")

                blob = bucket.blob("models/model.FCStd")
                logger.info(
                    f"アップロードを開始します: {output_file} → gs://{bucket_name}/models/model.FCStd"
                )

                blob.upload_from_filename(output_file)
                storage_url = f"gs://{bucket_name}/models/model.FCStd"
                logger.info(
                    f"モデルをCloud Storageにアップロードしました: {storage_url}"
                )
            except Exception as e:
                logger.error(
                    f"Cloud Storageへのアップロードに失敗しました: {str(e)}",
                    exc_info=True,
                )
                logger.error(f"エラーの詳細: {type(e).__name__}: {str(e)}")

        return ModelResponse(
            status="success",
            message="モデルを生成しました",
            file=output_file,
            storage_url=storage_url,
        )

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/health",
    summary="ヘルスチェック",
    description="APIサービスの稼働状態を確認します",
    response_description="ヘルスチェックの結果",
)
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
