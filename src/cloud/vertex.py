"""
Google Cloud Vertex AI との連携モジュール。
カスタムトレーニングジョブの設定と実行を担当します。
"""
from typing import List, Dict, Any, Optional
import datetime
import logging
import argparse
from google.cloud import aiplatform
from pathlib import Path

# ロギング設定
logger = logging.getLogger(__name__)


def init_vertex_ai(
    project_id: str,
    region: str,
    staging_bucket: str
) -> None:
    """
    Vertex AI クライアントを初期化します。

    Args:
        project_id: GCP プロジェクト ID
        region: GCP リージョン（例: asia-northeast1）
        staging_bucket: ステージングバケット URI（例: gs://bucket-name）
    """
    aiplatform.init(
        project=project_id,
        location=region,
        staging_bucket=staging_bucket
    )
    logger.info(f"Vertex AI initialized with project: {project_id}, region: {region}")


def create_custom_training_job(
    display_name: str,
    container_image_uri: str,
    args: List[str],
    machine_type: str = "n1-highmem-8",
    accelerator_type: Optional[str] = "NVIDIA_TESLA_T4",
    accelerator_count: int = 1,
    replica_count: int = 1
) -> aiplatform.CustomJob:
    """
    Vertex AI カスタムトレーニングジョブを作成します。

    Args:
        display_name: ジョブの表示名
        container_image_uri: コンテナイメージURI
        args: コンテナに渡す引数リスト
        machine_type: マシンタイプ（デフォルト: n1-highmem-8）
        accelerator_type: アクセラレータタイプ（デフォルト: NVIDIA_TESLA_T4、Noneの場合はGPUなし）
        accelerator_count: アクセラレータ数（デフォルト: 1）
        replica_count: レプリカ数（デフォルト: 1）

    Returns:
        作成されたCustomJobオブジェクト
    """
    machine_spec = {
        "machine_type": machine_type,
    }
    
    if accelerator_type:
        machine_spec["accelerator_type"] = accelerator_type
        machine_spec["accelerator_count"] = accelerator_count

    job = aiplatform.CustomJob(
        display_name=display_name,
        worker_pool_specs=[
            {
                "machine_spec": machine_spec,
                "replica_count": replica_count,
                "container_spec": {
                    "image_uri": container_image_uri,
                    "command": [],
                    "args": ["train"] + args,
                    "env": [{"name": "AIP_DISABLE_HEALTH_CHECK", "value": "true"}],
                },
            }
        ],
    )
    
    logger.info(f"Created custom training job: {display_name}")
    logger.info(f"Container image: {container_image_uri}")
    logger.info(f"Container command: python3 -m src.cli")
    logger.info(f"Container args: {args}")
    logger.info(f"Machine type: {machine_type}, Accelerator: {accelerator_type} x {accelerator_count if accelerator_type else 0}")
    return job


def run_vertex_job(
    project_id: str,
    region: str,
    job_name: str,
    container_image_uri: str,
    service_account: str,
    staging_bucket: str,
    args: List[str],
    machine_type: str = "n1-highmem-8",
    accelerator_type: str = "NVIDIA_TESLA_T4",
    accelerator_count: int = 1
) -> aiplatform.CustomJob:
    """
    Vertex AI上でカスタムトレーニングジョブを実行します。

    Args:
        project_id: GCPプロジェクトID
        region: GCPリージョン
        job_name: ジョブ名
        container_image_uri: コンテナイメージURI
        service_account: サービスアカウントメールアドレス
        staging_bucket: ステージングバケットURI
        args: コンテナに渡す引数リスト
        machine_type: マシンタイプ
        accelerator_type: アクセラレータタイプ（Noneを指定するとGPUなし）
        accelerator_count: アクセラレータ数

    Returns:
        実行されたCustomJobオブジェクト
    """
    # Vertex AI の初期化
    init_vertex_ai(project_id, region, staging_bucket)
    
    # 実行コマンドのデバッグログ出力
    command_str = "python3 -m src.cli " + " ".join(args)
    logger.info(f"実行されるコマンド: {command_str}")
    
    # カスタムジョブの作成
    job = create_custom_training_job(
        display_name=job_name,
        container_image_uri=container_image_uri,
        args=args,
        machine_type=machine_type,
        accelerator_type=accelerator_type,
        accelerator_count=accelerator_count
    )
    
    # ジョブの実行
    job.run(service_account=service_account)
    logger.info(f"CustomJob '{job_name}' started successfully.")
    return job


# スクリプトとして実行された場合の処理
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vertex AI Custom Job Launcher")
    parser.add_argument("--project_id", required=True, help="GCP Project ID")
    parser.add_argument("--region", default="asia-northeast1", help="GCP Region")
    parser.add_argument("--job_name", required=True, help="Display name of the CustomJob")
    parser.add_argument("--container_image_uri", required=True, help="Training container image URI")
    parser.add_argument("--service_account", required=True, help="Service account email for the job")
    parser.add_argument("--staging_bucket", required=True, help="GCS staging bucket (gs://bucket)")
    # 以降のパラメータはトレーニング用としてそのまま Docker に渡す
    known_args, remaining_args = parser.parse_known_args()

    # ジョブ実行
    job = run_vertex_job(
        project_id=known_args.project_id,
        region=known_args.region,
        job_name=known_args.job_name,
        container_image_uri=known_args.container_image_uri,
        service_account=known_args.service_account,
        staging_bucket=known_args.staging_bucket,
        args=remaining_args
    )

    print(f"CustomJob '{known_args.job_name}' started successfully. Check the Vertex AI Console for progress.")