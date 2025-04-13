# GCP環境へのデプロイ手順書

このドキュメントでは、House Design AIプロジェクトをGCP環境にデプロイする手順を説明します。

## 前提条件

- Google Cloud SDKがインストールされていること
- Dockerがインストールされていること
- Terraformがインストールされていること
- GCPプロジェクト（`yolov8environment`）にアクセス権限があること
- サービスアカウントの認証情報（`config/service_account.json`）が用意されていること

## デプロイ手順

### 1. GCP認証の設定

```bash
# サービスアカウントの認証情報を設定
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/config/service_account.json"

# GCPプロジェクトを設定
gcloud config set project yolov8environment
```

### 2. Dockerイメージのビルドとプッシュ

```bash
# DockerイメージをビルドしてArtifact Registryにプッシュ
./scripts/build_and_push_docker.sh
```

### 3. Terraformの適用

```bash
# Terraformを適用してGCP環境を構築
./scripts/apply_terraform.sh
```

### 4. FreeCAD APIのテスト

```bash
# FreeCAD APIをテスト
./scripts/test_freecad_api.sh
```

## トラブルシューティング

### Dockerイメージのビルドに失敗する場合

- Dockerが正しくインストールされているか確認してください
- GCP認証が正しく設定されているか確認してください
- 必要なパッケージがインストールされているか確認してください

### Terraformの適用に失敗する場合

- Terraformが正しくインストールされているか確認してください
- GCP認証が正しく設定されているか確認してください
- 必要なAPIが有効化されているか確認してください

### FreeCAD APIのテストに失敗する場合

- Cloud Runサービスが正しくデプロイされているか確認してください
- サービスアカウントに必要な権限が付与されているか確認してください
- FreeCADの処理が正しく実装されているか確認してください

## 参考リンク

- [Google Cloud SDK ドキュメント](https://cloud.google.com/sdk/docs)
- [Terraform ドキュメント](https://www.terraform.io/docs)
- [Cloud Run ドキュメント](https://cloud.google.com/run/docs)
- [Artifact Registry ドキュメント](https://cloud.google.com/artifact-registry/docs)
- [Cloud Storage ドキュメント](https://cloud.google.com/storage/docs) 