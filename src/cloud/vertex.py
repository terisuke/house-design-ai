"""
Google Cloud Vertex AI との連携モジュール。
カスタムトレーニングジョブの設定と実行を担当します。
"""
from typing import List, Dict, Any, Optional
import datetime
import logging
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
                    "command": ["python3", "-m", "src.cli"],
                    "args": args,
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
    accelerator_count: int = 1,
    save_dir: Optional[str] = None
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
        save_dir: 結果保存ディレクトリ（指定しない場合は自動生成）

    Returns:
        実行されたCustomJobオブジェクト
    """
    # Vertex AI の初期化
    init_vertex_ai(project_id, region, staging_bucket)
    
    # 保存ディレクトリが指定されていない場合、タイムスタンプ付きディレクトリを作成
    if not save_dir:
        now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bucket_name = staging_bucket.replace("gs://", "").split("/")[0]
        save_dir = f"gs://{bucket_name}/runs/segment/train_{now}"
        
        # --save_dir 引数を追加または更新
        save_dir_index = -1
        for i, arg in enumerate(args):
            if arg == "--save_dir":
                save_dir_index = i
                break
        
        if save_dir_index >= 0 and save_dir_index + 1 < len(args):
            args[save_dir_index + 1] = save_dir
        else:
            args.extend(["--save_dir", save_dir])
    
    # trainサブコマンドが含まれていない場合のみ先頭に追加
    if len(args) == 0 or args[0] != "train":
        args = ["train"] + args
    
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
    logger.info(f"CustomJob '{job_name}' started successfully. Results will be saved to {save_dir}")
    return job


# スクリプトとして実行された場合の処理
if __name__ == "__main__":
    # デフォルト設定
    PROJECT_ID = "yolov8environment"
    REGION = "asia-northeast1"
    JOB_NAME = "yolov8-custom-training-job"
    CONTAINER_IMAGE_URI = "asia-northeast1-docker.pkg.dev/yolov8environment/yolov8-repository/yolov8-training-image:v3"
    SERVICE_ACCOUNT = "yolo-v8-enviroment@yolov8environment.iam.gserviceaccount.com"
    STAGING_BUCKET = "gs://yolo-v11-training-staging"
    
    # タイムスタンプで一意なディレクトリ名を作成
    now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    save_dir = f"gs://yolo-v11-training/runs/segment/train_{now}"
    
    # Dockerコンテナで実行されるコマンド引数リスト
    # 最初に'train'サブコマンドを追加してCLIモードを有効化
    args = [
        "--bucket_name", "yolo-v11-training",
        "--model", "yolo11m-seg.pt",
        "--epochs", "600",             # エポック数を増加
        "--batch_size", "16",
        "--imgsz", "640",
        "--optimizer", "SGD",          # AdamからSGDに変更
        "--lr0", "0.005",              # 初期学習率を調整
        "--upload_bucket", "yolo-v8-training",
        "--upload_dir", "trained_models",
        "--iou_threshold", "0.65",     # 少し緩和
        "--conf_threshold", "0.2",     # 少し緩和
        "--rect",                      # 矩形トレーニング
        "--cos_lr",                    # コサイン学習率スケジューラ
        "--mosaic", "1.0",             # モザイク拡張
        "--degrees", "10.0",           # 回転拡張を増加
        "--scale", "0.6",              # スケール拡張を少し増加
        "--save_dir", save_dir
    ]
    
    # ジョブの実行
    job = run_vertex_job(
        project_id=PROJECT_ID,
        region=REGION,
        job_name=JOB_NAME,
        container_image_uri=CONTAINER_IMAGE_URI,
        service_account=SERVICE_ACCOUNT,
        staging_bucket=STAGING_BUCKET,
        args=args
    )
    
    print(f"CustomJob '{JOB_NAME}' started successfully. Check the Vertex AI Console for progress.")