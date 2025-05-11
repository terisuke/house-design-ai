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

### 3. FreeCAD APIのビルドとデプロイ

FreeCAD APIのDockerイメージをビルドし、Artifact Registryにプッシュして、Cloud Runにデプロイします。

```bash
# FreeCAD APIのDockerイメージをビルド、プッシュ、デプロイ
./scripts/build_and_push_docker.sh
```

このスクリプトは以下の処理を行います：
- FreeCAD APIのDockerイメージをビルド
- Artifact Registryにイメージをプッシュ
- Cloud Runにサービスをデプロイ（メモリ2Gi、CPU 2、タイムアウト3600秒）
- デプロイ完了後にサービスURLを表示

### 4. Streamlitアプリケーションのビルドとデプロイ

Streamlitアプリケーションのビルドとデプロイには、新しく統合されたスクリプトを使用します。

```bash
# Streamlitアプリケーションのビルド、プッシュ、デプロイ
./scripts/build_and_push_streamlit.sh
```

このスクリプトは以下の処理を行います：
- Streamlitアプリケーションのイメージをビルド
- Artifact Registryにイメージをプッシュ
- Cloud Runにサービスをデプロイ（メモリ1Gi、タイムアウト3600秒）
- デプロイ完了後にサービスURLを表示

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
- `GOOGLE_APPLICATION_CREDENTIALS`: サービスアカウント認証情報のパス（デフォルト: /app/config/service_account.json）

### Streamlitアプリケーション

- `FREECAD_API_URL`: FreeCAD APIのURL（デフォルト: https://freecad-api-513507930971.asia-northeast1.run.app）
- `GOOGLE_APPLICATION_CREDENTIALS`: サービスアカウント認証情報のパス（デフォルト: /app/config/service_account.json）
- `USE_GCP_DEFAULT_CREDENTIALS`: GCPのデフォルト認証情報を使用するかどうか（デフォルト: true）

## デプロイスクリプトの詳細

### build_and_push_docker.sh（FreeCAD API用）

このスクリプトはFreeCAD APIのビルド、プッシュ、デプロイを行います：

- **ビルド**: Dockerfileを使用してFreeCAD APIのイメージをビルド
- **プッシュ**: ビルドしたイメージをArtifact Registryにプッシュ
- **デプロイ**: Cloud Runにサービスをデプロイ（メモリ2Gi、CPU 2）

```bash
# FreeCAD APIのデプロイ
./scripts/build_and_push_docker.sh
```

### build_and_push_streamlit.sh（Streamlitアプリケーション用）

このスクリプトはStreamlitアプリケーションのビルド、プッシュ、デプロイを行います：

- **ビルド**: Dockerfileを使用してStreamlitアプリケーションのイメージをビルド
- **プッシュ**: ビルドしたイメージをArtifact Registryにプッシュ
- **デプロイ**: Cloud Runにサービスをデプロイ（メモリ1Gi）

```bash
# Streamlitアプリケーションのデプロイ
./scripts/build_and_push_streamlit.sh
```

## メモリ割り当ての最適化

FreeCAD APIとStreamlitアプリケーションは、メモリを多く使用するため、適切なメモリ割り当てが重要です。デプロイスクリプトでは以下のメモリ設定を使用しています：

- **FreeCAD API**: 2Gi（CPU: 2）
- **Streamlitアプリケーション**: 1Gi

メモリ不足エラーが発生した場合は、以下のコマンドでメモリ割り当てを増やすことができます：

```bash
# FreeCAD APIのメモリ割り当てを増やす
gcloud run services update freecad-api \
  --memory 4Gi \
  --region asia-northeast1

# Streamlitアプリケーションのメモリ割り当てを増やす
gcloud run services update house-design-ai-streamlit \
  --memory 2Gi \
  --region asia-northeast1
```

## トラブルシューティング

### Cloud Storageの接続問題

FreeCAD APIがCloud Storageに接続できない場合は、以下を確認してください：

1. サービスアカウントに適切な権限があることを確認
2. 環境変数`GOOGLE_APPLICATION_CREDENTIALS`が正しく設定されていることを確認
3. Cloud Storageバケットが存在し、アクセス可能であることを確認

### サービスアカウントキーの問題

サービスアカウントキーに関する問題が発生した場合は、以下を確認してください：

1. `config/service_account.json`ファイルが存在することを確認
2. サービスアカウントに必要な権限（Storage Admin、Cloud Run Admin）があることを確認
3. Dockerイメージ内の正しい場所（`/app/config/service_account.json`）にファイルがコピーされていることを確認

### デプロイスクリプトのカスタマイズ

デプロイスクリプトは、プロジェクトのルートディレクトリにある`scripts`フォルダにあります。必要に応じてこれらのスクリプトをカスタマイズして、デプロイプロセスを調整できます。

## 定期的なメンテナンス

- 定期的にDockerイメージを更新して、セキュリティパッチを適用
- Cloud Runサービスのログを監視して、エラーや問題を特定
- 使用状況に基づいてリソース割り当てを調整
- サービスアカウントの権限を定期的に確認し、必要に応じて更新
