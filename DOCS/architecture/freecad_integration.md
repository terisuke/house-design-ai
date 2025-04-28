# FreeCAD統合ガイド

## 概要

このドキュメントでは、House Design AIプロジェクトにおけるFreeCADの統合方法について説明します。FreeCADはオープンソースの3DパラメトリックCADモデラーであり、本プロジェクトでは建物の3Dモデルや2D図面の生成に使用しています。

## 目次

1. [前提条件](#前提条件)
2. [FreeCADのDockerコンテナ化](#FreeCADのDockerコンテナ化)
3. [Cloud Runへのデプロイ](#Cloud-Runへのデプロイ)
4. [GKEへのデプロイ](#GKEへのデプロイ)
5. [トラブルシューティング](#トラブルシューティング)
6. [ベストプラクティス](#ベストプラクティス)
7. [制限事項と今後の改善点](#制限事項と今後の改善点)
8. [実装状況](#実装状況)

## 前提条件

- Docker
- Google Cloud Platform アカウント
- Google Cloud SDK
- Terraform（オプション）

## FreeCADのDockerコンテナ化

FreeCADをDockerコンテナ化することで、環境依存性を排除し、クラウド環境での一貫した実行を可能にします。

### Dockerfileの作成

以下は、FreeCADをインストールし、Pythonスクリプトを実行するためのDockerfileの例です。

```dockerfile
FROM ubuntu:22.04

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    freecad \
    python3-pip \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# 作業ディレクトリの設定
WORKDIR /app

# スクリプトのコピー
COPY script.py /app/

# 環境変数の設定
ENV PYTHONPATH=/usr/lib/freecad/lib
ENV QT_QPA_PLATFORM=offscreen

# エントリーポイントの設定
ENTRYPOINT ["python3", "script.py"]
```

### Dockerイメージのビルドとテスト

```bash
# イメージのビルド
docker build -t freecad-api:latest -f Dockerfile.freecad .

# ローカルでのテスト実行
docker run --rm -v $(pwd)/output:/app/output freecad-api:latest
```

## Cloud Runへのデプロイ

FreeCAD APIをCloud Runにデプロイすることで、サーバーレスでスケーラブルな環境を構築できます。

### イメージのプッシュ

```bash
# Artifact Registryの認証設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# イメージのタグ付け
docker tag freecad-api:latest asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:latest

# イメージのプッシュ
docker push asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:latest
```

### Cloud Runサービスのデプロイ

```bash
# サービスのデプロイ
gcloud run deploy freecad-api \
    --image asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:latest \
    --platform managed \
    --region asia-northeast1 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300s \
    --allow-unauthenticated
```

## GKEへのデプロイ

より複雑な処理や長時間実行が必要な場合は、Google Kubernetes Engine (GKE)にデプロイすることも可能です。

### クラスタの作成

```bash
# クラスタの作成
gcloud container clusters create freecad-cluster \
    --zone asia-northeast1-a \
    --num-nodes 1 \
    --machine-type e2-standard-4
```

### Jobの定義と実行

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: freecad-job
spec:
  template:
    spec:
      containers:
      - name: freecad
        image: asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:latest
      restartPolicy: Never
```

```bash
# Jobの適用
kubectl apply -f freecad-job.yaml
```

## トラブルシューティング

### 一般的な問題と解決策

1. **QTエラー**
   - 症状: `QXcbConnection: Could not connect to display`
   - 解決策: 環境変数`QT_QPA_PLATFORM=offscreen`を設定

2. **メモリ不足**
   - 症状: `Killed`または`OOMKilled`
   - 解決策: Cloud RunまたはGKEのメモリ割り当てを増やす

3. **タイムアウト**
   - 症状: `DEADLINE_EXCEEDED`
   - 解決策: Cloud Runのタイムアウト設定を延長（最大60分）

### ログの確認

```bash
# Cloud Runのログを確認
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=freecad-api" --limit 50

# GKEのログを確認
kubectl logs job/freecad-job
```

## ベストプラクティス

### パフォーマンス最適化

1. **リソース割り当ての最適化**
   - 必要に応じてメモリとCPUを調整
   - 大規模モデルの場合は4GB以上のメモリを割り当て

2. **処理の分割**
   - 複雑な処理は小さなタスクに分割
   - 非同期処理の活用

### セキュリティ

1. **最小権限の原則**
   - サービスアカウントに必要最小限の権限を付与
   - 機密情報はSecret Managerで管理

2. **コンテナのセキュリティ**
   - ベースイメージを定期的に更新
   - 不要なパッケージをインストールしない

## 制限事項と今後の改善点

1. **処理時間の制約**
   - Cloud Runのタイムアウト制限（最大60分）
   - 複雑なモデルの場合はGKEの使用を検討

2. **リソースの制約**
   - Cloud Runの最大メモリ（8GB）とCPU（8vCPU）
   - 大規模モデルの場合はGKEの使用を検討

3. **今後の改善点**
   - キャッシュ機構の実装
   - 並列処理の最適化
   - エラーハンドリングの強化

## 実装状況 (2025-04-28更新)

FreeCAD APIのCloud Run実装は成功しています。以下のテスト結果が確認されています：

```
PYTHONPATH=. streamlit run house_design_app/main.py
```
でstreamlitの実行成功を確認しました。また、

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

### FreeCAD API仕様

APIエンドポイント: https://freecad-api-513507930971.asia-northeast1.run.app

リクエスト形式:
```json
{
  "width": 10.0,
  "length": 15.0,
  "height": 3.0,
  "parameters": {"wall_thickness": 0.2, "window_size": 1.5}
}
```

レスポンス形式:
```json
{
  "status": "success",
  "message": "モデルを生成しました",
  "file": "/tmp/model.FCStd",
  "storage_url": "<gs://house-design-ai-data/models/model.FCStd>"
}
```
