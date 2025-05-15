#!/bin/bash
set -e

PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
REPOSITORY="house-design-ai"
STREAMLIT_IMAGE="streamlit"
SERVICE_NAME="streamlit-web"
MEMORY="8Gi"
CPU="2"

handle_error() {
    echo "エラーが発生しました: $1"
    exit 1
}

echo "GCP認証を確認しています..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "gcloudにログインしていません。認証を開始します..."
    gcloud auth login || handle_error "GCP認証に失敗しました"
fi

# 明示的にプロジェクトを設定
echo "プロジェクトを${PROJECT_ID}に設定します..."
gcloud config set project ${PROJECT_ID} || handle_error "プロジェクトの設定に失敗しました"

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

# 一時ビルドディレクトリを準備
echo "必要なファイルとディレクトリを準備しています..."
mkdir -p house_design_app/tmp_build/config
mkdir -p house_design_app/tmp_build/public/img
mkdir -p house_design_app/tmp_build/.streamlit

# 必須ファイルのコピー
echo "必須ファイルをコピーしています..."
if [ -f "config/service_account.json" ]; then
    cp config/service_account.json house_design_app/tmp_build/config/ || handle_error "サービスアカウントキーのコピーに失敗しました"
    echo "サービスアカウントキーのコピーに成功しました"
else
    handle_error "サービスアカウントキーが見つかりません"
fi

# Streamlit secretsのコピー
if [ -f ".streamlit/secrets.toml" ]; then
    cp .streamlit/secrets.toml house_design_app/tmp_build/.streamlit/ || handle_error "Streamlit secretsのコピーに失敗しました"
    echo "Streamlit secretsのコピーに成功しました"
else
    handle_error "Streamlit secretsファイルが見つかりません"
fi

# オプションのファイルのコピー
echo "オプションのファイルをコピーしています..."
[ -f "config/data.yaml" ] && cp config/data.yaml house_design_app/tmp_build/config/ && echo "data.yamlのコピーに成功しました"
[ -f "public/img/logo.png" ] && cp public/img/logo.png house_design_app/tmp_build/public/img/ && echo "ロゴのコピーに成功しました"

# utils ディレクトリが存在する場合はコピー
if [ -d "house_design_app/utils" ]; then
    mkdir -p house_design_app/tmp_build/utils
    cp -r house_design_app/utils/* house_design_app/tmp_build/utils/ || handle_error "utilsディレクトリのコピーに失敗しました"
    echo "utilsディレクトリのコピーに成功しました"
fi

# マルチステージビルドを使用した最適化されたDockerfile
cat > house_design_app/Dockerfile.temp << EOF
# ビルドステージ: 依存関係をインストール
FROM python:3.9-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y \\
  build-essential \\
  python3-dev \\
  libxml2-dev \\
  libxslt1-dev \\
  && rm -rf /var/lib/apt/lists/*

# 依存関係をコピーしてインストール
COPY house_design_app/requirements-streamlit.txt .
RUN pip wheel --wheel-dir=/wheels -r requirements-streamlit.txt

# 実行ステージ: 実際のアプリケーション
FROM python:3.9-slim

WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \\
  libgl1-mesa-glx \\
  libglib2.0-0 \\
  && rm -rf /var/lib/apt/lists/*

# ビルドステージからホイールをコピー
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# 必要なディレクトリを作成
RUN mkdir -p /app/config /app/public/img /app/.streamlit /app/src /app/utils

# アプリコードをコピー
COPY house_design_app/*.py /app/
COPY house_design_app/pages /app/pages/
COPY house_design_app/tmp_build/utils /app/utils/
COPY src /app/src/
COPY house_design_app/tmp_build/config /app/config/
COPY house_design_app/tmp_build/public/img /app/public/img/
COPY house_design_app/tmp_build/.streamlit /app/.streamlit/

# 環境変数を設定
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV TORCH_WARN_ONLY=1

# ポートを公開
EXPOSE \${PORT:-8080}

# Streamlitアプリを起動
CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0"]
EOF

echo "Dockerイメージをビルドしています..."
docker buildx build --platform linux/amd64 -t ${REPO_PATH} -f house_design_app/Dockerfile.temp . --push || handle_error "Dockerイメージのビルドに失敗しました"

rm house_design_app/Dockerfile.temp
rm -rf house_design_app/tmp_build

echo "Cloud Runにデプロイします..."
gcloud run deploy ${SERVICE_NAME} \
    --project=${PROJECT_ID} \
    --image ${REPO_PATH} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory ${MEMORY} \
    --cpu ${CPU} \
    --timeout 3600 \
    --set-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/app/config/service_account.json,USE_GCP_DEFAULT_CREDENTIALS=true,FREECAD_API_URL=https://freecad-api-513507930971.asia-northeast1.run.app,BUCKET_NAME=house-design-ai-bucket,SECRET_MANAGER_SERVICE_ACCOUNT=house-design-ai@yolov8environment.iam.gserviceaccount.com,LOGO_GCS_PATH=gs://house-design-ai-bucket/logo.png,TORCH_WARN_ONLY=1,PYTHONPATH=/app" || handle_error "Cloud Runへのデプロイに失敗しました"

SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)') || handle_error "サービスURLの取得に失敗しました"

echo "================================================"
echo "デプロイが正常に完了しました！"
echo "新しいタグ: ${IMAGE_TAG}"
echo "デプロイされたサービスURL: ${SERVICE_URL}"
echo "================================================"
