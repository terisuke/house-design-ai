# Google Cloud Platform デプロイメントガイド

このガイドでは、House Design AIをGoogle Cloud Platform (GCP)にデプロイする手順を説明します。

## 前提条件

- Google Cloud Platformアカウント
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)がインストールされていること
- Dockerがインストールされていること
- プロジェクトのソースコードがローカルにクローンされていること

## 1. GCPプロジェクトの設定

### プロジェクトの作成

```bash
# プロジェクトの作成
gcloud projects create [PROJECT_ID] --name="House Design AI"

# プロジェクトの設定
gcloud config set project [PROJECT_ID]

# リージョンの設定
gcloud config set compute/region asia-northeast1
```

### 必要なAPIの有効化

```bash
# 必要なAPIの有効化
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

## 2. サービスアカウントの設定

### サービスアカウントの作成と権限設定

```bash
# サービスアカウントの作成
gcloud iam service-accounts create house-design-ai-sa

# 必要な権限の付与
gcloud projects add-iam-policy-binding [PROJECT_ID] \
    --member="serviceAccount:house-design-ai-sa@[PROJECT_ID].iam.gserviceaccount.com" \
    --role="roles/run.admin"
gcloud projects add-iam-policy-binding [PROJECT_ID] \
    --member="serviceAccount:house-design-ai-sa@[PROJECT_ID].iam.gserviceaccount.com" \
    --role="roles/storage.admin"
gcloud projects add-iam-policy-binding [PROJECT_ID] \
    --member="serviceAccount:house-design-ai-sa@[PROJECT_ID].iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# キーファイルの生成
gcloud iam service-accounts keys create config/service_account.json \
    --iam-account=house-design-ai-sa@[PROJECT_ID].iam.gserviceaccount.com
```

## 3. Artifact Registryの設定

### Dockerリポジトリの作成

```bash
# Dockerリポジトリの作成
gcloud artifacts repositories create house-design-ai \
    --repository-format=docker \
    --location=asia-northeast1 \
    --description="Docker repository for House Design AI"
```

### 認証の設定

```bash
# Artifact Registryの認証設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

## 4. Dockerイメージのビルドとプッシュ

### イメージのビルド

```bash
# FreeCAD APIのイメージをビルド
docker build -t asia-northeast1-docker.pkg.dev/[PROJECT_ID]/house-design-ai/freecad:v1.0.0 -f freecad_api/Dockerfile.freecad freecad_api/
```

### イメージのプッシュ

```bash
# イメージをArtifact Registryにプッシュ
docker push asia-northeast1-docker.pkg.dev/[PROJECT_ID]/house-design-ai/freecad:v1.0.0
```

## 5. Cloud Runへのデプロイ

### サービスの作成

```bash
# FreeCAD APIサービスのデプロイ
gcloud run deploy house-design-ai-freecad \
    --image asia-northeast1-docker.pkg.dev/[PROJECT_ID]/house-design-ai/freecad:v1.0.0 \
    --platform managed \
    --region asia-northeast1 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/workspace/service_account.json" \
    --service-account=house-design-ai-sa@[PROJECT_ID].iam.gserviceaccount.com
```

### 環境変数の設定

```bash
# 環境変数の設定
gcloud run services update house-design-ai-freecad \
    --set-env-vars="MODEL_PATH=/workspace/models/yolov8l-seg.pt,DATA_PATH=/workspace/data"
```

## 6. メンテナンス

### バージョン管理

- イメージのタグ付けは `v1.0.0` のような形式で行う
- メジャーバージョン（1.0.0）: 大きな変更がある場合
- マイナーバージョン（1.1.0）: 機能追加がある場合
- パッチバージョン（1.0.1）: バグ修正がある場合

### モニタリング

```bash
# ログの確認
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=house-design-ai-freecad" --limit 50

# メトリクスの確認
gcloud run services describe house-design-ai-freecad --region asia-northeast1
```

### バックアップ

- 定期的にモデルとデータのバックアップを取る
- Cloud Storageを使用してバックアップを保存

```bash
# バックアップの作成
gsutil cp -r /path/to/backup gs://[PROJECT_ID]-backup/
```

## トラブルシューティング

### 一般的な問題

1. **認証エラー**
   - サービスアカウントのキーが正しく設定されているか確認
   - 必要な権限が付与されているか確認

2. **メモリ不足**
   - Cloud Runのメモリ設定を増やす
   - バッチサイズを調整する

3. **タイムアウト**
   - Cloud Runのタイムアウト設定を調整
   - 処理を最適化する

### ログの確認

```bash
# リアルタイムログの確認
gcloud beta run services logs tail house-design-ai-freecad --region asia-northeast1
```

## セキュリティ考慮事項

1. **認証情報の管理**
   - サービスアカウントキーを安全に管理
   - 環境変数を使用して機密情報を管理

2. **ネットワークセキュリティ**
   - VPCコネクタの使用を検討
   - 適切なファイアウォールルールを設定

3. **アクセス制御**
   - 最小権限の原則に従う
   - IAMポリシーを定期的にレビュー

## コスト最適化

1. **リソース設定**
   - 適切なインスタンスサイズを選択
   - オートスケーリングの設定を最適化

2. **使用量の監視**
   - 定期的にコストを確認
   - 未使用のリソースを削除

3. **予算の設定**
   - 予算アラートを設定
   - コスト超過を防止

## 次のステップ

1. [FreeCAD.md](FreeCAD.md)を参照してFreeCADの統合を設定
2. [ROADMAP.md](ROADMAP.md)を確認して今後の開発計画を確認
3. モニタリングとログ分析の設定を行う
4. バックアップ戦略を実装する 