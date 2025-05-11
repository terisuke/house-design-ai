# Google Cloud Deployment Guide

このドキュメントでは、House Design AIアプリケーションとFreeCAD APIをGoogle Cloudにデプロイする方法について説明します。

## 前提条件

- Google Cloudアカウントとプロジェクト
- Google Cloud CLIのインストールと設定
- Terraformのインストール
- Dockerのインストール
- サービスアカウント認証情報（`service_account.json`）

## デプロイの概要

House Design AIのデプロイは以下のコンポーネントで構成されています：

1. **FreeCAD API**: Cloud Runサービスとして実行
2. **Streamlitアプリケーション**: Cloud Runサービスとして実行
3. **Cloud Storage**: 3Dモデルと図面の保存
4. **Artifact Registry**: Dockerイメージの保存

## デプロイ手順

### 1. サービスアカウントの設定

1. Google Cloud Consoleで適切な権限を持つサービスアカウントを作成します
2. サービスアカウントのJSONキーをダウンロードし、`config/service_account.json`として保存します

```bash
# サービスアカウント認証の設定
mkdir -p config
cp /path/to/your/service_account.json config/service_account.json
```

### 2. Terraformを使用したインフラストラクチャのデプロイ

Terraformを使用して、必要なGoogle Cloudリソースをプロビジョニングします。

```bash
# Terraformディレクトリに移動
cd terraform/environments/dev

# Terraformの初期化
terraform init

# デプロイ計画の確認
terraform plan

# インフラストラクチャのデプロイ
terraform apply
```

または、提供されているスクリプトを使用することもできます：

```bash
# スクリプトを使用したTerraformの適用
./scripts/apply_terraform.sh
```

### 3. Dockerイメージのビルドとプッシュ

FreeCAD APIとStreamlitアプリケーションのDockerイメージをビルドし、Artifact Registryにプッシュします。

```bash
# FreeCAD APIのDockerイメージをビルドしてプッシュ
./scripts/build_and_push_docker.sh freecad-api

# Streamlitアプリケーションのイメージをビルドしてプッシュ
./scripts/build_and_push_docker.sh streamlit-app
```

### 4. Cloud Runへのデプロイ

ビルドしたDockerイメージをCloud Runにデプロイします。

```bash
# FreeCAD APIをデプロイ
./scripts/deploy_cloud_run.sh freecad-api

# Streamlitアプリケーションをデプロイ
./scripts/deploy_streamlit.sh
```

## 主要なTerraformモジュール

### Cloud Run

`terraform/modules/cloud-run`モジュールは、Cloud Runサービスをデプロイするために使用されます。

主な設定パラメータ：

- `name`: サービス名
- `image`: デプロイするDockerイメージ
- `region`: デプロイするリージョン
- `memory`: メモリ割り当て（デフォルト: 1Gi）
- `cpu`: CPU割り当て
- `max_instances`: 最大インスタンス数
- `min_instances`: 最小インスタンス数
- `timeout`: リクエストタイムアウト

### Artifact Registry

`terraform/modules/artifact-registry`モジュールは、Dockerイメージを保存するためのArtifact Registryリポジトリを作成します。

主な設定パラメータ：

- `project_id`: Google Cloudプロジェクトのプロジェクトid
- `location`: リポジトリのロケーション
- `repository_id`: リポジトリのID

### Cloud Storage

`terraform/modules/cloud-storage`モジュールは、3Dモデルと図面を保存するためのCloud Storageバケットを作成します。

主な設定パラメータ：

- `name`: バケット名
- `location`: バケットのロケーション
- `storage_class`: ストレージクラス

## 環境変数

FreeCAD APIとStreamlitアプリケーションは、以下の環境変数を使用します：

### FreeCAD API

- `PORT`: APIサーバーのポート（デフォルト: 8080）
- `BUCKET_NAME`: Cloud Storageバケット名（デフォルト: house-design-ai-data）
- `OUTPUT_DIR`: 一時ファイルの出力ディレクトリ（デフォルト: /tmp）

### Streamlitアプリケーション

- `FREECAD_API_URL`: FreeCAD APIのURL
- `GOOGLE_APPLICATION_CREDENTIALS`: サービスアカウント認証情報のパス（デフォルト: /app/config/service_account.json）

## メモリ割り当ての最適化

FreeCAD APIとStreamlitアプリケーションは、メモリを多く使用するため、適切なメモリ割り当てが重要です。

```bash
# メモリ割り当てを指定してCloud Runにデプロイ
gcloud run deploy freecad-api \
  --image asia-northeast1-docker.pkg.dev/your-project-id/house-design-ai/freecad-api:latest \
  --platform managed \
  --region asia-northeast1 \
  --memory 1Gi \
  --allow-unauthenticated
```

## トラブルシューティング

### Cloud Storageの接続問題

FreeCAD APIがCloud Storageに接続できない場合は、以下を確認してください：

1. サービスアカウントに適切な権限があることを確認
2. 環境変数`GOOGLE_APPLICATION_CREDENTIALS`が正しく設定されていることを確認
3. Cloud Storageバケットが存在し、アクセス可能であることを確認

### メモリ不足エラー

メモリ不足エラーが発生した場合は、Cloud Runサービスのメモリ割り当てを増やしてください：

```bash
gcloud run services update freecad-api \
  --memory 2Gi \
  --region asia-northeast1
```

### デプロイスクリプトのカスタマイズ

デプロイスクリプトは、プロジェクトのルートディレクトリにある`scripts`フォルダにあります。必要に応じてこれらのスクリプトをカスタマイズして、デプロイプロセスを調整できます。

## 定期的なメンテナンス

- 定期的にDockerイメージを更新して、セキュリティパッチを適用
- Cloud Runサービスのログを監視して、エラーや問題を特定
- 使用状況に基づいてリソース割り当てを調整
