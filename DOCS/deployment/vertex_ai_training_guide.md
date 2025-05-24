# Vertex AI YOLO学習デプロイメントガイド

このドキュメントでは、House Design AIプロジェクトにおけるVertex AI統合YOLO学習の設定、実行、トラブルシューティングについて詳しく説明します。

## 概要

Vertex AI統合により、以下の機能が利用可能になりました：

- **統合ワークフロー**: ビルド・プッシュ・学習を一つのスクリプトで実行
- **クロスプラットフォーム対応**: ARM64 Mac からAMD64 Linux向けビルド
- **セキュリティ強化**: Docker secret mountによる安全な認証情報処理
- **柔軟な設定**: コマンドライン引数による学習パラメータのカスタマイズ

## 前提条件

### 必要なツール

- **Google Cloud CLI**: `gcloud` コマンドが利用可能であること
- **Docker**: Docker Engine（ARM64 Macの場合はDocker Desktop推奨）
- **Docker buildx**: クロスプラットフォームビルド用（通常Docker Desktopに含まれる）
- **Python 3.9+**: 仮想環境 `venv_base` をセットアップ済み

### GCP設定

- プロジェクトID: `yolov8environment`
- リージョン: `asia-northeast1`
- サービスアカウント: `yolo-v8-enviroment@yolov8environment.iam.gserviceaccount.com`
- データセットバケット: `yolo-v11-training`

### 必要なサービス

以下のGoogle Cloud APIが有効化されている必要があります：

```bash
gcloud services enable aiplatform.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

## セットアップ手順

### 1. 仮想環境の準備

```bash
# プロジェクトディレクトリに移動
cd house-design-ai

# 仮想環境の有効化
source venv_base/bin/activate

# 環境変数の設定
export PYTHONPATH=.
```

### 2. GCP認証

```bash
# GCPにログイン
gcloud auth login

# アプリケーションデフォルト認証の設定
gcloud auth application-default login

# プロジェクトの設定
gcloud config set project yolov8environment

# Docker認証の設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

### 3. サービスアカウント認証情報

**重要**: サービスアカウント認証情報（`config/service_account.json`）がローカルに存在することを確認してください。このファイルはGitリポジトリには含まれません。

```bash
# ファイルの存在確認
ls -la config/service_account.json

# ファイルサイズの確認（空でないことを確認）
wc -c config/service_account.json
```

## 基本的な使用方法

### デフォルト設定での実行

```bash
./scripts/build_and_run_vertex_training.sh
```

デフォルト設定：
- エポック数: 600
- バッチサイズ: 2
- 画像サイズ: 416x416
- モデル: yolo11m-seg.pt
- 学習率: 0.001
- オプティマイザ: AdamW

### カスタム設定での実行

```bash
# より高性能な設定例
./scripts/build_and_run_vertex_training.sh \
  --epochs 100 \
  --batch-size 4 \
  --image-size 640 \
  --model yolo11l-seg.pt \
  --lr0 0.01 \
  --optimizer AdamW

# 軽量設定例（テスト用）
./scripts/build_and_run_vertex_training.sh \
  --epochs 10 \
  --batch-size 1 \
  --image-size 320 \
  --model yolo11n-seg.pt
```

### ビルドをスキップしての実行

既存のDockerイメージを使用して学習のみを実行：

```bash
./scripts/build_and_run_vertex_training.sh \
  --skip-build \
  --epochs 200 \
  --batch-size 2
```

## 利用可能なオプション

| オプション             | データ型      | デフォルト値        | 説明                 |
|-------------------|------------|----------------|----------------------|
| `--epochs`        | 整数       | 50             | 学習エポック数           |
| `--batch-size`    | 整数       | 2              | バッチサイズ               |
| `--image-size`    | 整数       | 416            | 入力画像サイズ (正方形) |
| `--model`         | 文字列     | yolo11m-seg.pt | YOLOモデル名            |
| `--lr0`           | 浮動小数点 | 0.001          | 初期学習率           |
| `--optimizer`     | 文字列     | AdamW          | オプティマイザ              |
| `--iou-threshold` | 浮動小数点 | 0.5            | IoU閾値              |
| `--data-yaml`     | 文字列     | data.yaml      | データセット設定ファイル       |
| `--skip-build`    | フラグ        | false          | ビルドをスキップ             |
| `--help`          | フラグ        | -              | ヘルプ表示              |

## アーキテクチャとセキュリティ

### クロスプラットフォームビルド

ARM64 Mac（M1/M2/M3/M4）からAMD64 Linux用Dockerイメージをビルド：

```bash
# buildxビルダーの確認
docker buildx ls

# マルチアーキテクチャビルド
docker buildx build \
  --platform linux/amd64 \
  --secret id=gcp_credentials,src=config/service_account.json \
  -t <image-tag> \
  --push \
  .
```

### セキュリティ強化

**Docker Secret Mount:**
- サービスアカウント認証情報はビルド時のみアクセス
- 最終Dockerイメージには認証情報を含まない
- Git履歴に認証情報が残らない

**実装詳細:**
```dockerfile
# Dockerfile内でのsecret mount使用例
RUN --mount=type=secret,id=gcp_credentials,target=/run/secrets/gcp_credentials \
  if [ -f /run/secrets/gcp_credentials ]; then \
    cp /run/secrets/gcp_credentials /app/config/service_account.json && \
    chmod 600 /app/config/service_account.json; \
  fi
```

## モニタリングとログ

### Vertex AIジョブの監視

実行されたジョブは以下のURLから監視できます：

```
https://console.cloud.google.com/vertex-ai/training/custom-jobs?project=yolov8environment
```

### ログの確認

```bash
# 最新のジョブログを確認
gcloud ai custom-jobs stream-logs <JOB_ID> --region=asia-northeast1

# Cloud Loggingでの確認
gcloud logging read "resource.type=ml_job AND resource.labels.job_id=<JOB_ID>" --limit=50
```

## トラブルシューティング

### 一般的な問題と解決方法

#### 1. サービスアカウント認証エラー

**症状**: `Expecting value: line 1 column 1 (char 0)`

**解決方法**:
```bash
# ファイルの存在と内容を確認
ls -la config/service_account.json
cat config/service_account.json | jq .

# ファイルが空または破損している場合は再ダウンロード
gcloud iam service-accounts keys create config/service_account.json \
  --iam-account=yolo-v8-enviroment@yolov8environment.iam.gserviceaccount.com
```

#### 2. Docker buildx エラー

**症状**: `buildx: failed to create builder`

**解決方法**:
```bash
# buildxビルダーを再作成
docker buildx rm multiarch || true
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap
```

#### 3. CUDA out of memory エラー

**症状**: Vertex AI学習中にGPUメモリ不足

**解決方法**:
```bash
# バッチサイズと画像サイズを削減
./scripts/build_and_run_vertex_training.sh \
  --batch-size 1 \
  --image-size 320 \
  --model yolo11n-seg.pt
```

#### 4. タグ不変エラー

**症状**: `cannot update tag v3. The repository has enabled tag immutability`

**解決方法**: スクリプトは自動的にタイムスタンプベースのユニークなタグを生成するため、この問題は発生しません。

### パフォーマンス最適化

#### GPU使用率の最適化

```bash
# より大きなバッチサイズでの実行（V100/T4 GPU用）
./scripts/build_and_run_vertex_training.sh \
  --batch-size 8 \
  --image-size 640 \
  --model yolo11m-seg.pt
```

#### 学習時間の短縮

```bash
# 軽量モデルでの高速学習
./scripts/build_and_run_vertex_training.sh \
  --model yolo11n-seg.pt \
  --epochs 50 \
  --batch-size 4
```

## ベストプラクティス

### 1. 段階的な学習アプローチ

```bash
# 1. 小規模テスト
./scripts/build_and_run_vertex_training.sh \
  --epochs 5 \
  --batch-size 1 \
  --image-size 320

# 2. 中規模検証
./scripts/build_and_run_vertex_training.sh \
  --epochs 25 \
  --batch-size 2 \
  --image-size 416

# 3. 本格学習
./scripts/build_and_run_vertex_training.sh \
  --epochs 100 \
  --batch-size 4 \
  --image-size 640
```

### 2. モデルサイズの選択指針

- **yolo11n-seg.pt**: テスト・プロトタイプ用（最速）
- **yolo11s-seg.pt**: 軽量本番用
- **yolo11m-seg.pt**: バランス型（推奨）
- **yolo11l-seg.pt**: 高精度用（推奨、GPUメモリに注意）
- **yolo11x-seg.pt**: 最高精度用（大容量GPU必須）

### 3. バッチサイズの指針

- **GPU T4**: batch-size 1-2
- **GPU V100**: batch-size 2-4
- **GPU A100**: batch-size 4-8

## サポートとコミュニティ

問題が発生した場合は、以下のリソースを活用してください：

1. **プロジェクトIssues**: GitHub Issues
2. **GCP Vertex AI ドキュメント**: [公式ドキュメント](https://cloud.google.com/vertex-ai/docs)
3. **YOLO公式ドキュメント**: [Ultralytics Documentation](https://docs.ultralytics.com/)

## 更新履歴

- **2025年5月25日**: 初版作成
  - Vertex AI統合機能の追加
  - セキュリティ強化実装
  - クロスプラットフォーム対応
  - 統合デプロイメントスクリプト実装 