#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 既存のモジュールを使用
from src.cloud.vertex import run_vertex_job
import datetime

# 各種設定
PROJECT_ID = "yolov8environment"
REGION = "asia-northeast1"
JOB_NAME = "yolov8-custom-training-job"
CONTAINER_IMAGE_URI = "asia-northeast1-docker.pkg.dev/yolov8environment/yolov8-repository/yolov8-training-image:v3"
SERVICE_ACCOUNT = "yolo-v8-enviroment@yolov8environment.iam.gserviceaccount.com"
STAGING_BUCKET = "gs://yolo-v8-training-staging"

# タイムスタンプで一意なディレクトリ名を作成
now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
save_dir = f"gs://yolo-v8-training/runs/segment/train_{now}"

# app.py に渡す引数 (リスト形式)
args = [
    "train",
    "--bucket_name", "yolo-v8-training",
    "--model", "yolo11m-seg.pt",  
    "--epochs", "600",
    "--batch_size", "16",
    "--imgsz", "640",
    "--optimizer", "SGD",
    "--lr0", "0.005",
    "--upload_bucket", "yolo-v8-training",
    "--upload_dir", "trained_models",
    "--iou_threshold", "0.65",
    "--conf_threshold", "0.2",
    "--rect",
    "--cos_lr",
    "--mosaic", "1.0",
    "--degrees", "10.0",
    "--scale", "0.6",
    "--data_yaml", "/app/config/data.yaml",
    "--train_dir", "gs://yolo-v8-training/datasets/house/train/images",
    "--val_dir", "gs://yolo-v8-training/datasets/house/val/images",
    "--save_dir", save_dir
]

# 既存の関数を使用してジョブを実行
job = run_vertex_job(
    project_id=PROJECT_ID,
    region=REGION,
    job_name=JOB_NAME,
    container_image_uri=CONTAINER_IMAGE_URI,
    service_account=SERVICE_ACCOUNT,
    staging_bucket=STAGING_BUCKET,
    args=args
)

print(f"CustomJob '{JOB_NAME}' started successfully.")