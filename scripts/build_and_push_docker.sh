#!/bin/bash
set -e

# 環境変数の設定
PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
REPOSITORY="house-design-ai"
STREAMLIT_IMAGE="streamlit"
FREECAD_API_IMAGE="freecad-api"

# gcloud認証（未認証なら自動で認証を要求）
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
  echo "gcloudにログインしていません。認証を開始します..."
  gcloud auth login
fi

echo "GCPに認証します..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# 一意なタグ（コミットハッシュ or 日付）を使う
GIT_TAG=$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)
IMAGE_TAG=${GIT_TAG}

# Streamlitイメージのビルドとプッシュはスキップ
# echo "Streamlitイメージをビルドします..."
# docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${STREAMLIT_IMAGE}:${IMAGE_TAG} -f Dockerfile .
# docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${STREAMLIT_IMAGE}:${IMAGE_TAG}

# FreeCAD APIイメージのビルドとプッシュ
echo "FreeCAD APIイメージをビルドします..."
cd freecad_api
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${FREECAD_API_IMAGE}:${IMAGE_TAG} -f Dockerfile.freecad .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${FREECAD_API_IMAGE}:${IMAGE_TAG}
cd ..

echo "Dockerイメージのビルドとプッシュが完了しました。"
echo "新しいタグ: ${IMAGE_TAG}" 