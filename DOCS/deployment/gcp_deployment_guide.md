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

### 4.2 Cloud Storage
- バケット名: house-design-ai-data
- リージョン: asia-northeast1
- アクセス制御: 細かなIAM権限設定
- 用途: 画像データ、モデルデータ、FCStdファイルの保存

## 5. モニタリングとログ

### 5.1 Cloud Runのモニタリング

```bash
# Cloud Runサービスのメトリクスを表示
gcloud monitoring metrics list --filter="metric.type=run.googleapis.com"

# Cloud Runサービスのログを表示
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=freecad-api" --limit 10
```

### 5.2 アラートの設定

```bash
# エラー率アラートの作成
gcloud alpha monitoring policies create \
    --display-name="FreeCAD API Error Rate Alert" \
    --condition-filter="metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" metric.label.\"response_code_class\"=\"4xx\" OR metric.label.\"response_code_class\"=\"5xx\"" \
    --condition-threshold-value=5 \
    --condition-threshold-duration=300s \
    --notification-channels="projects/yolov8environment/notificationChannels/123456789"
```

## 6. セキュリティ考慮事項

### 6.1 IAM権限の最小化

- サービスアカウントには必要最小限の権限のみを付与
- 定期的な権限の監査と見直し
- 不要な権限の削除

### 6.2 ネットワークセキュリティ

- VPC Service Controlsの検討
- Cloud Armorによる保護の検討
- 定期的なセキュリティスキャンの実施

## 7. コスト最適化

### 7.1 リソース使用量の最適化

- Cloud Runの自動スケーリング設定の最適化
- 不要なリソースの削除
- 定期的なコスト分析

### 7.2 予算アラートの設定

```bash
# 予算アラートの設定
gcloud billing budgets create \
    --billing-account=BILLING_ACCOUNT_ID \
    --display-name="House Design AI Budget" \
    --budget-amount=200 \
    --threshold-rule=percent=80 \
    --threshold-rule=percent=100
```

## 8. 今後の計画

### 8.1 スケーリング計画

- 負荷テストの実施
- 自動スケーリングパラメータの最適化
- リージョン間レプリケーションの検討

### 8.2 機能拡張

- Vertex AI統合の完了
- Firebase/Firestoreの統合
- CI/CDパイプラインの強化

## 9. トラブルシューティング

### 9.1 一般的な問題と解決策

1. **デプロイ失敗**
   - ログの確認
   - サービスアカウント権限の確認
   - イメージのビルド設定の確認

2. **パフォーマンス問題**
   - リソース割り当ての見直し
   - コードの最適化
   - キャッシュの活用

3. **接続問題**
   - ネットワーク設定の確認
   - IAM権限の確認
   - APIの有効化状態の確認

## 10. 実装状況 (2025-04-28更新)

FreeCAD APIのCloud Run実装は成功しています。以下のテスト結果が確認されています：

```
python scripts/test_freecad_api.py
```

のテスト結果：
```
✅ FreeCAD APIテスト成功
レスポンス: {
  "status": "success",
  "message": "モデルを生成しました",
  "file": "/tmp/model.FCStd",
  "storage_url": "<gs://house-design-ai-data/models/model.FCStd>"
}
```

FreeCADをCloud Runでデプロイし、FCStdモデルでのストレージ保存まで完了しています。
