#!/bin/bash
set -eo pipefail -u

# 環境変数の設定
PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
REPOSITORY="house-design-ai"
IMAGE_NAME="yolo-training"
SERVICE_ACCOUNT="yolo-v8-enviroment@yolov8environment.iam.gserviceaccount.com"
BUCKET_NAME="yolo-v11-training"
# Vertex AI のステージングバケット (存在しない場合は事前に作成しておく)
STAGING_BUCKET="gs://${BUCKET_NAME}-staging"

# エラーハンドリング関数
handle_error() {
    echo "エラーが発生しました: $1"
    exit 1
}

# 使用方法の表示
usage() {
    echo "使用方法: $0 [OPTIONS]"
    echo "オプション:"
    echo "  --epochs NUM          エポック数 (デフォルト: 600)"
    echo "  --batch-size NUM      バッチサイズ (デフォルト: 2)"
    echo "  --image-size NUM      画像サイズ (デフォルト: 416)"
    echo "  --model STRING        モデル名 (デフォルト: yolo11m-seg.pt)"
    echo "  --lr0 FLOAT          学習率 (デフォルト: 0.001)"
    echo "  --optimizer STRING    オプティマイザ (デフォルト: AdamW)"
    echo "  --iou-threshold FLOAT IoU閾値 (デフォルト: 0.5)"
    echo "  --data-yaml STRING    データセット設定ファイル (デフォルト: config/data.yaml)"
    echo "  --skip-build         ビルドをスキップしてジョブのみ実行"
    echo "  --help              このヘルプを表示"
    exit 1
}

# デフォルト値
EPOCHS=600
BATCH_SIZE=2
IMAGE_SIZE=416
MODEL="yolo11m-seg.pt"
LR0=0.001
OPTIMIZER="AdamW"
IOU_THRESHOLD=0.5
DATA_YAML="config/data.yaml"
SKIP_BUILD=false

# 引数の解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --epochs)
            EPOCHS="$2"
            shift 2
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --image-size)
            IMAGE_SIZE="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --lr0)
            LR0="$2"
            shift 2
            ;;
        --optimizer)
            OPTIMIZER="$2"
            shift 2
            ;;
        --iou-threshold)
            IOU_THRESHOLD="$2"
            shift 2
            ;;
        --data-yaml)
            DATA_YAML="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo "不明なオプション: $1"
            usage
            ;;
    esac
done

echo "================================================"
echo "Vertex AI YOLO学習ジョブ実行スクリプト"
echo "================================================"
echo "プロジェクトID: $PROJECT_ID"
echo "リージョン: $REGION"
echo "サービスアカウント: $SERVICE_ACCOUNT"
echo "エポック数: $EPOCHS"
echo "バッチサイズ: $BATCH_SIZE"
echo "画像サイズ: $IMAGE_SIZE"
echo "モデル: $MODEL"
echo "学習率: $LR0"
echo "オプティマイザ: $OPTIMIZER"
echo "IoU閾値: $IOU_THRESHOLD"
echo "データ設定: $DATA_YAML"
echo "================================================"

# 自動的にvenv_baseをアクティブ化
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [[ -d "venv_base" ]]; then
        echo "仮想環境 venv_base を自動的にアクティブ化します..."
        # shellcheck disable=SC1091
        source venv_base/bin/activate
    else
        echo "venv_base ディレクトリがありません。python -m venv venv_base && source venv_base/bin/activate で作成してください。"
        exit 1
    fi
fi

# gcloud認証チェック
echo "GCP認証を確認しています..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "gcloudにログインしていません。認証を開始します..."
    gcloud auth login || handle_error "GCP認証に失敗しました"
fi

# プロジェクト設定
echo "プロジェクトを${PROJECT_ID}に設定します..."
gcloud config set project ${PROJECT_ID} || handle_error "プロジェクトの設定に失敗しました"

# Docker認証設定
echo "Docker認証を設定します..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev || handle_error "Docker認証の設定に失敗しました"

# ──────────────────────────────────────────────
# ▼ Workload Identity を使用するため、鍵ファイルチェックは不要
# ──────────────────────────────────────────────

# タイムスタンプベースのタグ生成
IMAGE_TAG="v$(date +%Y%m%d-%H%M%S)"
REPO_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"

if [ "$SKIP_BUILD" = false ]; then
    echo "================================================"
    echo "Dockerイメージのビルドを開始します..."
    echo "イメージタグ: $IMAGE_TAG"
    echo "リポジトリパス: $REPO_PATH"
    echo "================================================"

    # buildxビルダーの確認・作成
    echo "Docker buildxビルダーを確認しています..."
    if ! docker buildx inspect multiarch >/dev/null 2>&1; then
        echo "multiarchビルダーを作成します..."
        docker buildx create --name multiarch --use || handle_error "buildxビルダーの作成に失敗しました"
    else
        echo "既存のmultiarchビルダーを使用します"
        docker buildx use multiarch || handle_error "buildxビルダーの選択に失敗しました"
    fi

    # Dockerイメージのビルド＆プッシュ（--no-cache オプション付き）
    echo "ARM64 MacからAMD64向けにDockerイメージをビルド＆プッシュします..."
    docker buildx build \
        --platform linux/amd64 \
        --no-cache \
        -f Dockerfile.train \
        -t ${REPO_PATH} \
        --push \
        . || handle_error "Dockerイメージのビルドまたはプッシュに失敗しました"

    echo "Dockerイメージのビルド＆プッシュが完了しました: $REPO_PATH"
else
    echo "ビルドをスキップして既存のイメージを使用します"
    # 最新のイメージタグを取得（簡易実装）
    IMAGE_TAG="v$(date +%Y%m%d)-latest"
    REPO_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"
fi

echo "================================================"
echo "Vertex AI カスタムジョブを実行します..."
echo "================================================"

# Vertex AI ジョブの実行
JOB_NAME="yolo-training-$(date +%Y%m%d-%H%M%S)"

echo "ジョブ名: $JOB_NAME"
echo "ジョブパラメータ:"
echo "  --epochs: $EPOCHS"
echo "  --batch_size: $BATCH_SIZE"
echo "  --imgsz: $IMAGE_SIZE"
echo "  --model: $MODEL"
echo "  --lr0: $LR0"
echo "  --optimizer: $OPTIMIZER"
echo "  --iou_threshold: $IOU_THRESHOLD"
echo "  --data_yaml: $DATA_YAML"

python scripts/run_vertex_job.py \
    --project_id "$PROJECT_ID" \
    --region "$REGION" \
    --job_name "$JOB_NAME" \
    --container_image_uri "$REPO_PATH" \
    --service_account "$SERVICE_ACCOUNT" \
    --staging_bucket "$STAGING_BUCKET" \
    --epochs "$EPOCHS" \
    --batch_size "$BATCH_SIZE" \
    --imgsz "$IMAGE_SIZE" \
    --model "$MODEL" \
    --lr0 "$LR0" \
    --optimizer "$OPTIMIZER" \
    --iou_threshold "$IOU_THRESHOLD" \
    --data_yaml "$DATA_YAML" || handle_error "Vertex AIジョブの実行に失敗しました"

echo "================================================"
echo "Vertex AIジョブが正常に開始されました！"
echo "ジョブ名: $JOB_NAME"
echo "イメージ: $REPO_PATH"
echo "================================================"
echo "ジョブの状況は以下で確認できます："
echo "https://console.cloud.google.com/vertex-ai/training/custom-jobs?project=$PROJECT_ID"
echo "================================================" 