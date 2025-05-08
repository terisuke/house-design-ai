#!/bin/bash
set -e

# 環境変数の設定
PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
REPOSITORY="freecad-api"
STREAMLIT_IMAGE="streamlit"
FREECAD_API_IMAGE="freecad-api"

# gcloud認証（未認証なら自動で認証を要求）
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
  echo "gcloudにログインしていません。認証を開始します..."
  gcloud auth login
fi

echo "GCPに認証します..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# タグを日付＋乱数で生成（例: 20240612160000-12345）
IMAGE_TAG="$(date +%Y%m%d%H%M%S)-$RANDOM"

# Streamlitイメージのビルドとプッシュはスキップ
# echo "Streamlitイメージをビルドします..."
# docker buildx build --platform linux/amd64 -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/house-design-ai/${STREAMLIT_IMAGE}:${IMAGE_TAG} -f Dockerfile . --push

# FreeCAD APIイメージのビルドとプッシュ（buildxでamd64のみ）
REPO_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${FREECAD_API_IMAGE}:${IMAGE_TAG}"
echo "FreeCAD APIイメージをbuildxでビルド＆プッシュします..."
cd freecad_api
docker buildx build --platform linux/amd64 -t ${REPO_PATH} -f Dockerfile.freecad . --push
cd ..

echo "Dockerイメージのビルドとプッシュが完了しました。"
echo "新しいタグ: ${IMAGE_TAG}" 