#!/bin/bash
set -e

# 環境変数の設定
PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
REPOSITORY="house-design-ai"
IMAGE_NAME="streamlit"
TAG="latest"

# リポジトリのフルパス
REPOSITORY_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}"

# Dockerイメージのビルド
echo "StreamlitアプリのDockerイメージをビルドしています..."
docker build -t ${REPOSITORY_PATH}/${IMAGE_NAME}:${TAG} -f house_design_app/Dockerfile house_design_app/

# Artifact Registryへのプッシュ
echo "DockerイメージをArtifact Registryにプッシュしています..."
docker push ${REPOSITORY_PATH}/${IMAGE_NAME}:${TAG}

echo "Streamlitアプリのデプロイが完了しました。"
echo "イメージ: ${REPOSITORY_PATH}/${IMAGE_NAME}:${TAG}" 