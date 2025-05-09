# Cloud Run メモリ最適化ガイド

このドキュメントでは、House Design AIアプリケーションをGoogle Cloud Runにデプロイする際のメモリ最適化について説明します。

## 問題: メモリ制限超過

Cloud Runのデフォルトメモリ制限（512 MiB）を超えると、以下のようなエラーが発生します:

```
Memory limit of 512 MiB exceeded with 562 MiB used. Consider increasing the memory limit, see https://cloud.google.com/run/docs/configuring/memory-limits
```

このエラーが発生すると、アプリケーションは強制終了され、ブラウザでは「The page that you have requested does not seem to exist」というエラーや、「Running...」と「Connecting...」が繰り返し表示されるだけになります。

### FreeCAD API特有の問題

FreeCAD APIでは、3Dモデル生成時に500エラー（Internal Server Error）が発生する場合があります。これは多くの場合、メモリ不足が原因です。FreeCADは3Dモデル処理に多くのメモリを必要とするため、デフォルトの512MiBでは不十分です。

## 解決策

### 1. Cloud Runのメモリ割り当てを増やす

デプロイコマンドに`--memory`パラメータを追加して、メモリ割り当てを増やします:

```bash
gcloud run deploy house-design-ai-streamlit \
  --image gcr.io/yolov8environment/house-design-ai-streamlit \
  --platform managed \
  --region asia-northeast1 \
  --memory 1Gi \
  --allow-unauthenticated
```

### 2. アプリケーションの最適化

以下の最適化を実装しました:

1. **遅延モデルロード**: YOLOモデルは、ユーザーが画像をアップロードしたときにのみロードされるようになりました。これにより、初期起動時のメモリ使用量が削減されます。

2. **軽量Dockerイメージ**: CUDAを含む重いNVIDIAイメージから、より軽量なPythonイメージに変更しました。Cloud RunはGPUをサポートしていないため、CUDAは不要です。

## デプロイ手順

1. コードの変更をビルドしてイメージを作成:

```bash
gcloud builds submit --tag gcr.io/yolov8environment/house-design-ai-streamlit
```

2. 十分なメモリを割り当ててデプロイ:

```bash
gcloud run deploy house-design-ai-streamlit \
  --image gcr.io/yolov8environment/house-design-ai-streamlit \
  --platform managed \
  --region asia-northeast1 \
  --memory 1Gi \
  --allow-unauthenticated
```

3. デプロイ後、以下のURLにアクセスしてアプリケーションが正常に動作することを確認:
   https://streamlit-web-513507930971.asia-northeast1.run.app/

## 追加の最適化オプション

さらにメモリ使用量を削減したい場合は、以下の方法も検討できます:

1. YOLOモデルの軽量版を使用する
2. 画像処理のバッチサイズを小さくする
3. 不要なライブラリを削除する

## 参考リンク

- [Cloud Run メモリ制限の設定](https://cloud.google.com/run/docs/configuring/memory-limits)
- [Cloud Run リソース割り当ての最適化](https://cloud.google.com/run/docs/configuring/services/memory)
