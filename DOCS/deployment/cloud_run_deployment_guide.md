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
# FreeCAD APIのビルド＆デプロイ
./scripts/build_and_push_freecad.sh

# Streamlitアプリケーションのビルド＆デプロイ
./scripts/build_and_push_streamlit.sh
```

これらのスクリプトは以下の処理を行います：
- Dockerイメージをビルド
- Artifact Registryにイメージをプッシュ
- 適切なメモリ設定（FreeCAD API: 2Gi、Streamlit: 8Gi）でCloud Runにデプロイ
- 必要な環境変数を設定

### 2. 手動でデプロイする方法

手動でデプロイする場合は、以下のコマンドを実行します：

```bash
# イメージをビルド
gcloud builds submit --tag gcr.io/yolov8environment/house-design-ai-streamlit .

# Cloud Runにデプロイ（重要: --memory 2Giパラメータを必ず指定）
gcloud run deploy house-design-ai-streamlit \
  --image gcr.io/yolov8environment/house-design-ai-streamlit \
  --platform managed \
  --region asia-northeast1 \
  --memory 8Gi \
  --allow-unauthenticated
```

## 重要な設定

### メモリ割り当て

YOLOモデルを使用するため、デフォルトの512MiBでは不十分です。Streamlitアプリケーションには `--memory 8Gi` パラメータを、FreeCAD APIには `--memory 2Gi` パラメータを指定してください。

```bash
# Streamlitアプリケーション
gcloud run deploy streamlit-web --memory 8Gi --cpu 2 ...

# FreeCAD API
gcloud run deploy freecad-api --memory 2Gi --cpu 2 ...
```

### 環境変数の設定

以下の環境変数が適切に設定されていることを確認してください：

- `GOOGLE_APPLICATION_CREDENTIALS`: サービスアカウント認証用（`/app/config/service_account.json`）
- `USE_GCP_DEFAULT_CREDENTIALS`: Cloud Run環境での認証用（`true`）
- `FREECAD_API_URL`: FreeCAD APIのURL
- `BUCKET_NAME`: Cloud Storageバケット名
- `SECRET_MANAGER_SERVICE_ACCOUNT`: Secret Managerアクセス用
- `LOGO_GCS_PATH`: ロゴファイルのGCSパス（例: `gs://house-design-ai-bucket/logo.png`）
- `TORCH_WARN_ONLY`: PyTorch警告の制御
- `PYTHONPATH`: Pythonパスの設定（`/app`）

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

このエラーが表示される場合は、デプロイコマンドに `--memory 2Gi` パラメータを追加してください。

### 認証エラー

```
ERROR:src.cloud.storage:モデルダウンロードエラー: Access denied: bucket yolo-v11-training: ...
```

このエラーが表示される場合は、以下を確認してください：

1. Cloud Runサービスに適切なIAMロールが付与されているか
2. サービスアカウントがGCSバケットにアクセスできるか

### ロゴ表示について

アプリケーションは以下の順序でロゴを表示します：
1. 環境変数 `LOGO_GCS_PATH` に指定されたGCSパスからロゴをロード
2. ローカルの `house_design_app/logo.png` ファイルをロード
3. 上記が見つからない場合はロゴなしで表示

## デプロイ後の確認

デプロイ後、以下のURLにアクセスしてアプリケーションが正常に動作することを確認してください：

https://streamlit-web-513507930971.asia-northeast1.run.app/

正常に動作している場合：
- ロゴが表示される
- 画像をアップロードするとYOLOモデルが正常にロードされる
- 処理結果が表示される
