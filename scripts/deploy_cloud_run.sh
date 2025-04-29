set -e

PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
SERVICE_NAME="house-design-ai-streamlit"
MEMORY="1Gi"

IMAGE_PATH="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "必要なディレクトリを作成しています..."
mkdir -p public/img config .streamlit

if [ ! -f "public/img/logo.png" ]; then
  echo "ロゴファイルが見つかりません。サンプルロゴを作成します..."
  echo "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAPUlEQVQokWNgGAWjgBaAiYGBgYWBgYGRkZGRkZGJiYmJiYmZmZmFhYWVlZWNjY2dnYODg5OTk4uLi5ubm4eHBwAQ+wJvyL+/ZwAAAABJRU5ErkJggg==" | base64 -d > public/img/logo.png
  echo "サンプルロゴを作成しました: public/img/logo.png"
fi

if [ ! -f "config/service_account.json" ]; then
  echo "警告: サービスアカウントファイルが見つかりません。"
  echo "GCPサービスアカウントキーを取得して config/service_account.json に配置してください。"
  echo "または、Cloud Runのサービスアカウントに適切な権限を付与してください。"
  
  read -p "サービスアカウントファイルなしで続行しますか？ (y/n): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "デプロイを中止します。"
    exit 1
  fi
  
  echo "{}" > config/service_account.json
  echo "空のサービスアカウントファイルを作成しました。Cloud Runのデフォルト認証を使用します。"
fi

if [ ! -f ".streamlit/secrets.toml" ]; then
  echo "警告: Streamlit secretsファイルが見つかりません。"
  echo "サンプルのsecrets.tomlファイルを作成します。"
  
  cat > .streamlit/secrets.toml << EOL

EOL
  echo "サンプルのsecrets.tomlファイルを作成しました: .streamlit/secrets.toml"
fi

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
