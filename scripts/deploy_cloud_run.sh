set -e

PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
SERVICE_NAME="house-design-ai-streamlit"
MEMORY="1Gi"

IMAGE_PATH="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "必須ファイルの存在を確認しています..."
./scripts/check_required_files.sh

echo "StreamlitアプリのDockerイメージをビルドしています..."
gcloud builds submit --config=cloudbuild.yaml --substitutions=_IMAGE_NAME=${IMAGE_PATH} .

echo "Cloud Runにデプロイしています..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_PATH} \
  --platform managed \
  --region ${REGION} \
  --memory ${MEMORY} \
  --allow-unauthenticated \
  --set-env-vars="USE_GCP_DEFAULT_CREDENTIALS=true"

echo "デプロイが完了しました。"
echo "サービスURL: https://streamlit-web-513507930971.${REGION}.run.app"
