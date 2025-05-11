#!/bin/bash
set -e

# 環境変数の設定
PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
REPOSITORY="freecad-api"
STREAMLIT_IMAGE="streamlit"
FREECAD_API_IMAGE="freecad-api"
SERVICE_NAME="freecad-api"

# エラーハンドリング関数
handle_error() {
    echo "エラーが発生しました: $1"
    exit 1
}

# gcloud認証（未認証なら自動で認証を要求）
echo "GCP認証を確認しています..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "gcloudにログインしていません。認証を開始します..."
    gcloud auth login || handle_error "GCP認証に失敗しました"
fi

echo "Docker認証を設定します..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev || handle_error "Docker認証の設定に失敗しました"

echo "サービスアカウントキーの存在を確認しています..."
if [ -f "config/service_account.json" ]; then
    echo "サービスアカウントキーが見つかりました: config/service_account.json"
else
    echo "警告: サービスアカウントキーが見つかりません。署名付きURLの生成に失敗する可能性があります。"
fi

# タグを日付＋乱数で生成（例: 20240612160000-12345）
IMAGE_TAG="$(date +%Y%m%d%H%M%S)-$RANDOM"

# Streamlitイメージのビルドとプッシュはスキップ
# echo "Streamlitイメージをビルドします..."
# docker buildx build --platform linux/amd64 -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/house-design-ai/${STREAMLIT_IMAGE}:${IMAGE_TAG} -f Dockerfile . --push

# FreeCAD APIイメージのビルドとプッシュ
REPO_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${FREECAD_API_IMAGE}:${IMAGE_TAG}"
echo "FreeCAD APIイメージをbuildxでビルド＆プッシュします..."
cd freecad_api || handle_error "freecad_apiディレクトリに移動できませんでした"

if [ -f "../config/service_account.json" ]; then
    echo "サービスアカウントキーをfreecad_apiディレクトリにコピーしています..."
    mkdir -p config
    cp ../config/service_account.json config/ || echo "警告: サービスアカウントキーのコピーに失敗しました"
    
    if [ -f "config/service_account.json" ]; then
        echo "サービスアカウントキーのコピーに成功しました"
    else
        echo "警告: サービスアカウントキーのコピー後の確認に失敗しました"
    fi
else
    echo "警告: サービスアカウントキーが見つからないため、コピーをスキップします"
fi

echo "Dockerイメージをビルドしています..."
docker buildx build --platform linux/amd64 -t ${REPO_PATH} -f Dockerfile.freecad . --push || handle_error "Dockerイメージのビルドに失敗しました"

cd .. || handle_error "親ディレクトリに戻れませんでした"

# Cloud Runへのデプロイ
echo "Cloud Runにデプロイします..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${REPO_PATH} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --set-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/app/config/service_account.json,BUCKET_NAME=house-design-ai-data" || handle_error "Cloud Runへのデプロイに失敗しました"

# デプロイ完了後の情報表示
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)') || handle_error "サービスURLの取得に失敗しました"

echo "================================================"
echo "デプロイが正常に完了しました！"
echo "新しいタグ: ${IMAGE_TAG}"
echo "デプロイされたサービスURL: ${SERVICE_URL}"
echo "================================================"  