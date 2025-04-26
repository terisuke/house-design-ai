# Google Cloud Platform デプロイメントガイド

このガイドでは、House Design AIプロジェクトをGoogle Cloud Platformにデプロイする手順を説明します。

## 前提条件

- Google Cloud Platformアカウント
- Google Cloud SDKのインストール
- Dockerのインストール
- Terraformのインストール（インフラストラクチャのデプロイに使用）

## 1. プロジェクトのセットアップ

### 1.1 GCPプロジェクトの設定

```bash
# プロジェクトの設定
gcloud config set project yolov8environment
```

### 1.2 必要なAPIの有効化

```bash
# 必要なAPIの有効化
gcloud services enable run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com \
    storage.googleapis.com
```

### 1.3 サービスアカウントの設定

このプロジェクトでは、以下の既存のサービスアカウントを使用します：
```
yolo-v8-enviroment@yolov8environment.iam.gserviceaccount.com
```

このサービスアカウントには既に以下の必要な権限が付与されています：
- Artifact Registry 管理者
- Cloud Run 管理者
- Service Usage 管理者
- Storage オブジェクト関連の権限
- Vertex AI 管理者
- その他必要な権限

サービスアカウントキーが必要な場合は、以下のコマンドで取得できます：

```bash
# サービスアカウントキーのダウンロード（必要な場合のみ）
gcloud iam service-accounts keys create config/service_account.json \
    --iam-account=yolo-v8-enviroment@yolov8environment.iam.gserviceaccount.com
```

## 2. インフラストラクチャのデプロイ

### 2.1 Terraformの初期化

```bash
cd deploy/terraform
terraform init
```

### 2.2 インフラストラクチャの計画

```bash
terraform plan
```

### 2.3 インフラストラクチャのデプロイ

```bash
terraform apply
```

## 3. FreeCAD APIのデプロイ

### 3.1 イメージのビルドとプッシュ

```bash
# Artifact Registryリポジトリの作成（存在しない場合）
gcloud artifacts repositories create freecad-api \
    --repository-format=docker \
    --location=asia-northeast1 \
    --description="FreeCAD API Docker repository" \
    --project=yolov8environment

# Artifact Registryの認証設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# イメージのビルド（重要: Cloud Run用にAMD64アーキテクチャを指定）
docker build --platform linux/amd64 \
    -t asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:latest \
    -f freecad_api/Dockerfile.freecad freecad_api/

# イメージのプッシュ
docker push asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:latest
```

### 3.2 Cloud Runへのデプロイ

```bash
# サービスのデプロイ
gcloud run deploy freecad-api \
    --image asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:latest \
    --platform managed \
    --region asia-northeast1 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300s \
    --allow-unauthenticated \
    --project=yolov8environment

# 環境変数の設定
gcloud run services update freecad-api \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=yolov8environment" \
    --region asia-northeast1 \
    --project=yolov8environment
```

## 4. デプロイ済みサービス

### 4.1 FreeCAD API
- URL: https://freecad-api-513507930971.asia-northeast1.run.app
- 設定:
  - メモリ: 2GB
  - CPU: 2
  - タイムアウト: 300秒
  - プロジェクト: yolov8environment
  - リージョン: asia-northeast1
  - 認証: 不要（パブリックアクセス可能）

### 4.2 注意事項
- Cloud RunはAMD64/Linuxアーキテクチャのコンテナのみをサポートしています。
- Apple Silicon (M1/M2) Macでビルドする場合は、必ず`--platform linux/amd64`フラグを指定してください。
- デプロイ後、サービスが安定するまで数分かかる場合があります。

## 5. モニタリングとログ

### 5.1 Cloud Loggingの設定

```bash
# ログシンクの作成
gcloud logging sinks create house-design-ai-logs \
    storage.googleapis.com/yolov8environment-logs \
    --log-filter="resource.type=cloud_run_revision AND resource.labels.service_name=freecad-api" \
    --project=yolov8environment
```

### 5.2 Cloud Monitoringの設定

```bash
# アラートポリシーの作成
gcloud monitoring channels create \
    --display-name="House Design AI Alerts" \
    --type=email \
    --email-address=your-email@example.com \
    --project=yolov8environment

gcloud monitoring alert-policies create \
    --display-name="FreeCAD API Error Rate" \
    --condition-display-name="Error Rate > 5%" \
    --condition-filter="resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"freecad-api\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\"" \
    --condition-threshold-value=0.05 \
    --condition-threshold-duration=300s \
    --notification-channels=projects/yolov8environment/monitoringChannels/your-channel-id \
    --project=yolov8environment
```

### 5.3 ログの確認

```bash
# FreeCAD APIのログを確認
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=freecad-api" \
    --limit 50 \
    --project=yolov8environment
```

## 6. セキュリティ考慮事項

1. **認証情報の管理**
   - サービスアカウントキーを安全に保管
   - 環境変数での機密情報の管理
   - Secret Managerの使用を検討

2. **ネットワークセキュリティ**
   - VPCの設定
   - ファイアウォールルールの適切な設定
   - Cloud Armorの設定を検討

3. **アクセス制御**
   - IAMポリシーの適切な設定
   - 最小権限の原則に従う
   - 定期的なアクセス権限のレビュー

## 7. コスト最適化

1. **リソースの最適化**
   - 適切なインスタンスサイズの選択
   - オートスケーリングの設定
   - 未使用リソースの削除

2. **モニタリング**
   - コスト分析の設定
   - 予算アラートの設定
   - 定期的なコストレビュー

## 8. 今後の計画

1. **スケーリング**
   - マルチリージョンデプロイ
   - グローバルロードバランシング
   - CDNの統合

2. **監視の強化**
   - カスタムメトリクスの追加
   - アラートの細分化
   - ダッシュボードの作成

3. **セキュリティの強化**
   - WAFの導入
   - セキュリティスキャンの自動化
   - コンプライアンスチェックの追加              