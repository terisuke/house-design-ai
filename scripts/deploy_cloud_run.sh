set -e

PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
SERVICE_NAME="house-design-ai-streamlit"
MEMORY="1Gi"

IMAGE_PATH="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "StreamlitアプリのDockerイメージをビルドしています..."
gcloud builds submit --tag ${IMAGE_PATH} .

echo "Cloud Runにデプロイしています..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_PATH} \
  --platform managed \
  --region ${REGION} \
  --memory ${MEMORY} \
  --allow-unauthenticated

echo "デプロイが完了しました。"
echo "サービスURL: https://${SERVICE_NAME}-513507930971.${REGION}.run.app"
