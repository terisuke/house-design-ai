#!/bin/bash
set -e

# 環境変数の設定
PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
REPOSITORY="house-design-ai"
STREAMLIT_IMAGE="streamlit"
FREECAD_API_IMAGE="freecad-api"

# 認証
echo "GCPに認証します..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Streamlitイメージのビルドとプッシュはスキップ
# echo "Streamlitイメージをビルドします..."
# docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${STREAMLIT_IMAGE}:latest -f Dockerfile .
# docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${STREAMLIT_IMAGE}:latest

# FreeCAD APIイメージのビルドとプッシュ
echo "FreeCAD APIイメージをビルドします..."
cd freecad_api
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${FREECAD_API_IMAGE}:latest -f Dockerfile.freecad .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${FREECAD_API_IMAGE}:latest
cd ..

echo "Dockerイメージのビルドとプッシュが完了しました。" 