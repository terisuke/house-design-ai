set -e

PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
REPOSITORY="house-design-ai"
STREAMLIT_IMAGE="streamlit"
SERVICE_NAME="house-design-ai-streamlit"
MEMORY="1Gi"

handle_error() {
    echo "エラーが発生しました: $1"
    exit 1
}

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

echo "必須ファイルの存在を確認しています..."
./scripts/check_required_files.sh || handle_error "必須ファイルの確認に失敗しました"

IMAGE_TAG="$(date +%Y%m%d%H%M%S)-$RANDOM"

REPO_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${STREAMLIT_IMAGE}:${IMAGE_TAG}"

echo "Streamlitアプリのイメージをビルドします..."
cd house_design_app || handle_error "house_design_appディレクトリに移動できませんでした"

if [ -f "../config/service_account.json" ]; then
    echo "サービスアカウントキーをhouse_design_appディレクトリにコピーしています..."
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
docker buildx build --platform linux/amd64 -t ${REPO_PATH} -f Dockerfile . --push || handle_error "Dockerイメージのビルドに失敗しました"

cd .. || handle_error "親ディレクトリに戻れませんでした"

echo "Cloud Runにデプロイします..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${REPO_PATH} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory ${MEMORY} \
    --timeout 3600 \
    --set-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/app/config/service_account.json,USE_GCP_DEFAULT_CREDENTIALS=true,FREECAD_API_URL=https://freecad-api-513507930971.asia-northeast1.run.app,LOGO_GCS_PATH=gs://house-design-ai-dev-bucket/assets/logo.png" || handle_error "Cloud Runへのデプロイに失敗しました"

SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)') || handle_error "サービスURLの取得に失敗しました"

echo "================================================"
echo "デプロイが正常に完了しました！"
echo "新しいタグ: ${IMAGE_TAG}"
echo "デプロイされたサービスURL: ${SERVICE_URL}"
echo "================================================"
