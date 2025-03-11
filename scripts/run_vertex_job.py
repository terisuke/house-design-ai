import sys
import os
from pathlib import Path
import datetime

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent  # scripts ディレクトリの2つ上
sys.path.insert(0, str(project_root))

# 既存のモジュールを使用
from src.cloud.vertex import run_vertex_job

# 各種設定 (必要に応じて環境変数から取得)
PROJECT_ID = os.environ.get("PROJECT_ID", "yolov8environment")
REGION = os.environ.get("REGION", "asia-northeast1")
JOB_NAME = os.environ.get("JOB_NAME", "yolo11-custom-training-job")
# 最新のイメージタグを使用するか、環境変数で指定する
CONTAINER_IMAGE_URI = os.environ.get("CONTAINER_IMAGE_URI", "asia-northeast1-docker.pkg.dev/yolov8environment/yolov8-repository/yolov11-training-image:v1") # 例：v4部分は適宜変更
SERVICE_ACCOUNT = os.environ.get("SERVICE_ACCOUNT", "yolo-v8-enviroment@yolov8environment.iam.gserviceaccount.com")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET", "gs://yolo-v11-training-staging")

# タイムスタンプで一意なディレクトリ名を作成
now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
# save_dirを/appからの相対パスにする
save_dir = f"runs/segment/train_{now}" #  /app/ は自動的に付与される

# app.py (実際には src/train.py) に渡す引数 (リスト形式)
args = [
    "train", # trainコマンドを追加
    "--bucket_name", "yolo-v11-training",
    "--model", "yolo11l-seg.pt",
    "--epochs", "600",
    "--batch_size", "16",
    "--imgsz", "640",
    "--optimizer", "SGD",
    "--lr0", "0.005",
    "--upload_bucket", "yolo-v11-training",
    "--upload_dir", "trained_models",  # モデルをアップロードするバケット内のディレクトリ
    "--iou_threshold", "0.65",
    "--conf_threshold", "0.2",
    "--rect",
    "--cos_lr",
    "--mosaic", "1.0",
    "--degrees", "10.0",
    "--scale", "0.6",
    "--data_yaml", "/app/config/data.yaml", # data.yamlのパスを指定
    "--save_dir", save_dir # トレーニング結果の保存先
]

# 既存の関数を使用してジョブを実行
job = run_vertex_job(
    project_id=PROJECT_ID,
    region=REGION,
    job_name=JOB_NAME,
    container_image_uri=CONTAINER_IMAGE_URI,
    service_account=SERVICE_ACCOUNT,
    staging_bucket=STAGING_BUCKET,
    args=args,
    machine_type="n1-highmem-8",  # CPUマシンの例
    accelerator_type= "NVIDIA_TESLA_T4",  # GPUを使用する場合 (NoneでCPUのみ)
    accelerator_count= 1 # GPUの数
)

print(f"CustomJob '{JOB_NAME}' started successfully.")