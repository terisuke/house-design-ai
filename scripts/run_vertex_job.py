import sys
import os
from pathlib import Path
import datetime
import argparse

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent  # scripts ディレクトリの2つ上
sys.path.insert(0, str(project_root))

# 既存のモジュールを使用
from src.cloud.vertex import run_vertex_job

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submit Vertex AI Custom Job")
    parser.add_argument("--container_image_uri", type=str, required=True,
                        help="Full URI of the Docker image in Artifact Registry for the Vertex AI job.")
    parser.add_argument("--project_id", type=str, default=os.environ.get("PROJECT_ID", "yolov8environment"))
    parser.add_argument("--region", type=str, default=os.environ.get("REGION", "asia-northeast1"))
    parser.add_argument("--job_name_prefix", type=str, default="yolo-custom-training",
                        help="Prefix for the Vertex AI job name. A timestamp will be appended.")
    parser.add_argument("--service_account", type=str,
                        default=os.environ.get("SERVICE_ACCOUNT", "yolo-v8-enviroment@yolov8environment.iam.gserviceaccount.com"))
    parser.add_argument("--staging_bucket", type=str,
                        default=os.environ.get("STAGING_BUCKET", "gs://yolo-v11-training-staging"))
    parser.add_argument("--bucket_name", type=str, required=True,
                        help="GCS bucket name for training data (without gs:// prefix)")
    parser.add_argument("--upload_bucket", type=str, required=True,
                        help="GCS bucket name for uploading trained models (without gs:// prefix)")
    # YOLO training parameters
    parser.add_argument("--epochs", type=int, default=600)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--model", type=str, default="yolo11m-seg.pt")
    parser.add_argument("--lr0", type=float, default=0.005)
    parser.add_argument("--optimizer", type=str, default="SGD")
    parser.add_argument("--iou_threshold", type=float, default=0.65)
    parser.add_argument("--conf_threshold", type=float, default=0.2)
    parser.add_argument("--data_yaml", type=str, default="/app/config/data.yaml")
    parser.add_argument("--job_name", type=str, help="Override the auto-generated job name")

    script_args = parser.parse_args()

    # Generate a unique job name with a timestamp if not provided
    if script_args.job_name:
        unique_job_name = script_args.job_name
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        unique_job_name = f"{script_args.job_name_prefix}-{timestamp}"

    # Define arguments for the training container (src.cli train)
    now_for_savedir = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    save_dir = f"runs/segment/train_{now_for_savedir}"
    training_args_for_container = [
        "train",
        "--bucket_name", script_args.bucket_name,
        "--model", script_args.model,
        "--epochs", str(script_args.epochs),
        "--batch_size", str(script_args.batch_size),
        "--imgsz", str(script_args.imgsz),
        "--optimizer", script_args.optimizer,
        "--lr0", str(script_args.lr0),
        "--upload_bucket", script_args.upload_bucket,
        "--upload_dir", "trained_models",
        "--iou_threshold", str(script_args.iou_threshold),
        "--conf_threshold", str(script_args.conf_threshold),
        "--rect",
        "--cos_lr",
        "--mosaic", "1.0",
        "--degrees", "10.0",
        "--scale", "0.6",
        "--data_yaml", script_args.data_yaml,
        "--save_dir", save_dir
    ]

    # Call the function that submits the Vertex AI Job
    job = run_vertex_job(
        project_id=script_args.project_id,
        region=script_args.region,
        job_name=unique_job_name,
        container_image_uri=script_args.container_image_uri,  # Use the parsed argument
        service_account=script_args.service_account,
        staging_bucket=script_args.staging_bucket,
        args=training_args_for_container,
        machine_type="n1-highmem-8",
        accelerator_type="NVIDIA_TESLA_T4",
        accelerator_count=1
    )
    print(f"CustomJob '{unique_job_name}' submitted successfully with image '{script_args.container_image_uri}'.")