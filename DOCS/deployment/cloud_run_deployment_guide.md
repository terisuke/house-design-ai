# Cloud Run デプロイガイド

このガイドでは、House Design AIアプリケーションをGoogle Cloud Runに正しくデプロイする方法を説明します。

## 前提条件

- Google Cloud SDKがインストールされていること
- プロジェクト `yolov8environment` へのアクセス権があること
- Dockerがインストールされていること（ローカルビルドの場合）

## デプロイ方法

### 1. デプロイスクリプトを使用する方法（推奨）

提供されているデプロイスクリプトを使用すると、ビルドからデプロイまでの全プロセスを自動化できます。

```bash
# スクリプトに実行権限を付与
chmod +x scripts/deploy_cloud_run.sh

# スクリプトを実行
./scripts/deploy_cloud_run.sh
```

このスクリプトは以下の処理を行います：
- Cloud Buildsを使用してDockerイメージをビルド
- 適切なメモリ設定（1Gi）でCloud Runにデプロイ

### 2. 手動でデプロイする方法

手動でデプロイする場合は、以下のコマンドを実行します：

```bash
# イメージをビルド
gcloud builds submit --tag gcr.io/yolov8environment/house-design-ai-streamlit .

# Cloud Runにデプロイ（重要: --memory 1Giパラメータを必ず指定）
gcloud run deploy house-design-ai-streamlit \
  --image gcr.io/yolov8environment/house-design-ai-streamlit \
  --platform managed \
  --region asia-northeast1 \
  --memory 1Gi \
  --allow-unauthenticated
```

## 重要な設定

### メモリ割り当て

YOLOモデルを使用するため、デフォルトの512MiBでは不十分です。必ず `--memory 1Gi` パラメータを指定してください。

```bash
gcloud run deploy house-design-ai-streamlit --memory 1Gi ...
```

### 認証設定

アプリケーションはGoogle Cloud Storageにアクセスするために認証が必要です。認証方法は以下の優先順位で試行されます：

1. Streamlit secrets（ローカル環境）
2. サービスアカウントファイル（`config/service_account.json`）
3. Cloud Runのデフォルト認証（`USE_GCP_DEFAULT_CREDENTIALS=true`）
4. 環境変数 `GOOGLE_APPLICATION_CREDENTIALS`
5. デフォルト認証

Cloud Run環境では、サービスアカウントに適切なIAMロールが付与されていることを確認してください：

- `roles/storage.objectViewer` - GCSバケットからのモデルダウンロード用

## トラブルシューティング

### メモリ制限エラー

```
Memory limit of 512 MiB exceeded with XXX MiB used.
```

このエラーが表示される場合は、デプロイコマンドに `--memory 1Gi` パラメータを追加してください。

### 認証エラー

```
ERROR:src.cloud.storage:モデルダウンロードエラー: Access denied: bucket yolo-v11-training: ...
```

このエラーが表示される場合は、以下を確認してください：

1. Cloud Runサービスに適切なIAMロールが付与されているか
2. サービスアカウントがGCSバケットにアクセスできるか

## デプロイ後の確認

デプロイ後、以下のURLにアクセスしてアプリケーションが正常に動作することを確認してください：

https://streamlit-web-513507930971.asia-northeast1.run.app/

正常に動作している場合：
- ロゴが表示される
- 画像をアップロードするとYOLOモデルが正常にロードされる
- 処理結果が表示される
