#!/bin/bash
# 新しいDockerイメージをビルドしてGoogle Container Registryにプッシュするスクリプト

set -e  # エラーが発生したら中断

# 設定
PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
REPOSITORY="yolov8-repository"
IMAGE_NAME="yolov8-training-image"
TAG="v5"  # ultralytics 8.3.81対応版

# フルイメージ名
FULL_IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"

echo "=========================================================="
echo "Dockerイメージをビルドしています: ${FULL_IMAGE_NAME}"
echo "=========================================================="

# プロジェクトルートディレクトリに移動
cd "$(dirname "$0")/.."

# Dockerイメージのビルド
docker build -t ${FULL_IMAGE_NAME} .

echo "=========================================================="
echo "ビルド完了。Google Container Registryにプッシュしています..."
echo "=========================================================="

# コンテナレジストリへのログイン (必要な場合)
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Google Container Registryにプッシュ
docker push ${FULL_IMAGE_NAME}

echo "=========================================================="
echo "プッシュ完了: ${FULL_IMAGE_NAME}"
echo "=========================================================="
echo "このイメージを使用するには以下の設定を確認してください:"
echo "- scripts/run_vertex_job.py内のCONTAINER_IMAGE_URIがこのイメージを指していること"
echo "==========================================================" 