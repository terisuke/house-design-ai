# House Design AI: GoogleCloud構築計画

## 概要

このドキュメントは、House Design AIプロジェクトのGoogleCloud環境への構築計画を詳細に説明します。FreeCADとの統合を目的とし、将来的なTerraform管理も考慮した設計となっています。

## 目次

1. [全体アーキテクチャ](#1-全体アーキテクチャ)
2. [主要コンポーネント](#2-主要コンポーネント)
3. [実装計画](#3-実装計画)
4. [CI/CDパイプライン](#4-cicd-パイプライン)
5. [Terraform対応計画](#5-terraform-対応計画)
6. [実装ロードマップ](#6-実装ロードマップ)
7. [予算と運用コスト見積もり](#7-予算と運用コスト見積もり)
8. [結論と次のステップ](#8-結論と次のステップ)

## 1. 全体アーキテクチャ

```
[ユーザー] → [Cloud Run: Streamlit WebUI]
                      ↑↓
         ┌───────────┴┬───────────┐
         ↓            ↓           ↓
[Cloud Run: FreeCAD API] ← [Vertex AI モデル] → [Cloud Storage]
         ↑                      ↑
         └─────────────┬────────┘
                       ↓
               [Artifact Registry]
```

### 1.1 システムコンポーネント間の通信フロー

1. ユーザーはStreamlit WebUIを通じて画像をアップロード
2. Streamlitアプリは画像をVertex AIモデルに送信
3. モデルは建物セグメンテーションとグリッド生成を実行
4. 結果はFreeCAD APIに送信され、3Dモデルを生成
5. 生成されたモデルはCloud Storageに保存
6. ユーザーは生成されたモデルをダウンロード可能

## 2. 主要コンポーネント

### 2.1 アプリケーションサービス

| サービス                    | 目的         | 技術スタック                               |
|-------------------------|--------------|----------------------------------------|
| **Streamlit WebUI**     | ユーザーインターフェース | Cloud Run, Streamlit, Python           |
| **FreeCAD API Service** | CAD処理機能  | Cloud Run, FreeCAD Python API, FastAPI |
| **ML Model Service**    | YOLO推論処理 | Vertex AI, YOLOv8                      |

### 2.2 データストレージ

| サービス                   | 目的         | データタイプ             |
|------------------------|--------------|--------------------|
| **Cloud Storage**      | 永続データ保存  | 画像、CADモデル、ML結果 |
| **Firebase/Firestore** | ユーザーデータ、設定 | JSON, メタデータ        |
| **Artifact Registry**  | コンテナイメージ     | Docker images      |

## 3. 実装計画

### 3.1 Dockerイメージ構築

#### 3.1.1 Streamlit WebUI

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 依存関係をインストール
COPY requirements-streamlit.txt .
RUN pip install --no-cache-dir -r requirements-streamlit.txt

# アプリケーションコードをコピー
COPY streamlit/ /app/streamlit/
COPY src/ /app/src/

# Cloud SDKの認証設定
ENV PORT=8080

# Streamlitアプリ起動
CMD ["streamlit", "run", "streamlit/app.py", "--server.port", "$PORT", "--server.address", "0.0.0.0"]
```

#### 3.1.2 FreeCAD API Service

```dockerfile
FROM ubuntu:20.04

WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    software-properties-common \
    python3-pip \
    python3-dev \
    freecad \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
COPY requirements-freecad-api.txt .
RUN pip3 install --no-cache-dir -r requirements-freecad-api.txt

# FreeCADのPythonパスを環境変数に設定
ENV PYTHONPATH="${PYTHONPATH}:/usr/lib/freecad/lib"
ENV PORT=8000

# APIコードをコピー
COPY freecad_api/ /app/freecad_api/

# FastAPIサーバー起動
CMD ["uvicorn", "freecad_api.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
```

### 3.2 Google Cloud 初期セットアップ

```bash
# プロジェクト作成
gcloud projects create house-design-ai --name="House Design AI"

# APIの有効化
gcloud services enable run.googleapis.com \
                       artifactregistry.googleapis.com \
                       cloudbuild.googleapis.com \
                       aiplatform.googleapis.com \
                       storage.googleapis.com \
                       firestore.googleapis.com

# Artifact Registryリポジトリ作成
gcloud artifacts repositories create house-design-ai \
    --repository-format=docker \
    --location=asia-northeast1 \
    --description="House Design AI Docker images"

# Cloud Storageバケット作成
gcloud storage buckets create gs://house-design-ai-data \
    --location=asia-northeast1
```

### 3.3 FreeCAD API Service 実装計画

`freecad_api/main.py`の概要:

```python
import os
import tempfile
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
import FreeCAD
import Part
import Draft
import ImportGui
import Mesh
from google.cloud import storage

app = FastAPI()
storage_client = storage.Client()

@app.post("/process/grid")
async def process_grid(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    グリッドデータからFreeCADモデルを生成するエンドポイント
    """
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, "input.json")
    
    # 入力ファイルを保存
    with open(temp_file, "wb") as f:
        f.write(await file.read())
    
    # FreeCADドキュメント作成
    doc = FreeCAD.newDocument("HouseDesign")
    
    # JSONからグリッドデータを読み込む
    # ...
    
    # 3Dモデル生成
    # ...
    
    # ファイル保存
    output_file = os.path.join(temp_dir, "output.fcstd")
    doc.saveAs(output_file)
    
    # Cloud Storageにアップロード
    bucket = storage_client.bucket("house-design-ai-data")
    blob = bucket.blob(f"cad_models/{os.path.basename(output_file)}")
    blob.upload_from_filename(output_file)
    
    return {"status": "success", "file_url": blob.public_url}

@app.post("/convert/2d")
async def convert_to_2d(file: UploadFile = File(...)):
    """
    3Dモデルから2D図面を生成するエンドポイント
    """
    # ... 実装省略 ...
    pass
```

### 3.4 Streamlit アプリ更新計画

`streamlit/app.py`の主な更新点:

1. FreeCAD APIと連携
2. Cloud Storage連携機能の強化
3. 認証機能の追加
4. UI/UXの改善

例:
```python
# FreeCAD APIとの連携
def send_to_freecad_api(processed_image_data, grid_data):
    api_url = os.environ.get("FREECAD_API_URL", "http://freecad-api:8000")
    
    try:
        # グリッドデータをJSON形式に変換
        grid_json = json.dumps(grid_data)
        
        # FreeCAD APIにリクエスト送信
        response = requests.post(
            f"{api_url}/process/grid",
            files={"file": ("grid_data.json", grid_json)},
        )
        
        if response.status_code == 200:
            result = response.json()
            st.success("CADモデルの生成に成功しました")
            return result["file_url"]
        else:
            st.error(f"CADモデル生成エラー: {response.text}")
            return None
    except Exception as e:
        st.error(f"APIリクエストエラー: {str(e)}")
        return None
```

## 4. CI/CD パイプライン

### 4.1 Cloud Build 設定

`cloudbuild.yaml`:

```yaml
steps:
  # Streamlit イメージのビルド
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'asia-northeast1-docker.pkg.dev/$PROJECT_ID/house-design-ai/streamlit:$COMMIT_SHA', '-f', 'Dockerfile.streamlit', '.']

  # FreeCAD API イメージのビルド
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'asia-northeast1-docker.pkg.dev/$PROJECT_ID/house-design-ai/freecad-api:$COMMIT_SHA', '-f', 'Dockerfile.freecad', '.']

  # イメージのプッシュ
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'asia-northeast1-docker.pkg.dev/$PROJECT_ID/house-design-ai/streamlit:$COMMIT_SHA']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'asia-northeast1-docker.pkg.dev/$PROJECT_ID/house-design-ai/freecad-api:$COMMIT_SHA']

  # Cloud Run へのデプロイ
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
    - 'run'
    - 'deploy'
    - 'streamlit-web'
    - '--image=asia-northeast1-docker.pkg.dev/$PROJECT_ID/house-design-ai/streamlit:$COMMIT_SHA'
    - '--region=asia-northeast1'
    - '--platform=managed'
    - '--allow-unauthenticated'

  - name: 'gcr.io/cloud-builders/gcloud'
    args:
    - 'run'
    - 'deploy'
    - 'freecad-api'
    - '--image=asia-northeast1-docker.pkg.dev/$PROJECT_ID/house-design-ai/freecad-api:$COMMIT_SHA'
    - '--region=asia-northeast1'
    - '--platform=managed'
    - '--memory=2Gi'

images:
  - 'asia-northeast1-docker.pkg.dev/$PROJECT_ID/house-design-ai/streamlit:$COMMIT_SHA'
  - 'asia-northeast1-docker.pkg.dev/$PROJECT_ID/house-design-ai/freecad-api:$COMMIT_SHA'
```

## 5. Terraform 対応計画

将来的なTerraform管理のためのディレクトリ構造と主要モジュール:

```
terraform/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── prod/
│       ├── main.tf
│       ├── variables.tf
│       └── terraform.tfvars
├── modules/
│   ├── cloud-run/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── cloud-storage/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── vertex-ai/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── artifact-registry/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── README.md
```

### 5.1 Terraform Cloud Run モジュール例

`modules/cloud-run/main.tf`:

```hcl
variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
  default     = "asia-northeast1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
}

variable "image" {
  description = "Container image to deploy"
  type        = string
}

variable "memory" {
  description = "Memory allocation"
  type        = string
  default     = "512Mi"
}

variable "cpu" {
  description = "CPU allocation"
  type        = string
  default     = "1"
}

variable "environment_variables" {
  description = "Environment variables"
  type        = map(string)
  default     = {}
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access"
  type        = bool
  default     = false
}

resource "google_cloud_run_service" "default" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      containers {
        image = var.image
        
        resources {
          limits = {
            memory = var.memory
            cpu    = var.cpu
          }
        }
        
        dynamic "env" {
          for_each = var.environment_variables
          content {
            name  = env.key
            value = env.value
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

data "google_iam_policy" "noauth" {
  count = var.allow_unauthenticated ? 1 : 0
  
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  count = var.allow_unauthenticated ? 1 : 0
  
  location = google_cloud_run_service.default.location
  project  = google_cloud_run_service.default.project
  service  = google_cloud_run_service.default.name

  policy_data = data.google_iam_policy.noauth[0].policy_data
}

output "url" {
  value = google_cloud_run_service.default.status[0].url
}
```

## 6. 実装ロードマップ

### フェーズ1: 基本インフラストラクチャのセットアップ（2週間）

1. Google Cloud プロジェクト作成
2. 必要なAPIの有効化
3. ストレージバケットと権限の設定
4. Artifactリポジトリの設定

### フェーズ2: FreeCAD APIサービスの開発（3週間）

1. FreeCAD Python APIを使用した処理モジュール開発
2. FastAPIベースのRESTfulエンドポイント実装
3. Dockerイメージのビルドとテスト
4. Cloud Runへのデプロイ

### フェーズ3: Streamlitアプリの拡張とクラウド対応（2週間）

1. Cloud Runに対応するStreamlitアプリの修正
2. FreeCAD APIとの連携実装
3. Cloud Storage連携の強化
4. UIの改良とユーザーフローの最適化

### フェーズ4: Vertex AIモデルの最適化と統合（2週間）

1. Vertex AIエンドポイントのセットアップ
2. 推論結果をFreeCAD形式に変換する機能
3. エンドツーエンドのパイプラインテスト

### フェーズ5: Terraform対応（2週間）

1. 現状環境のTerraform IaCへの移行
2. モジュール化とベストプラクティスの適用
3. CI/CDパイプラインの整備

## 7. 予算と運用コスト見積もり

| コンポーネント                 | 想定使用量                        | 月額概算 (USD) |
|-------------------------|-----------------------------------|----------------|
| Cloud Run (Streamlit)   | 1インスタンス、1 CPU、1GB RAM、月間150時間 | $15-25         |
| Cloud Run (FreeCAD API) | オンデマンド、2 CPU、2GB RAM              | $20-40         |
| Cloud Storage           | 10GB データ + 1000操作/月            | $1-3           |
| Vertex AI               | 推論エンドポイント、小規模モデル             | $40-80         |
| Artifact Registry       | 5GB ストレージ                         | $1-2           |
| Cloud Build             | 120ビルド分/月                       | $0-5           |
| **合計**                |                                   | **$77-155**    |

## 8. 結論と次のステップ

このGoogleCloud構築計画は、既存のHouse Design AIプロジェクトをクラウドネイティブな環境に移行し、FreeCAD統合を実現するための包括的なロードマップです。Terraformによるインフラストラクチャのコード化も計画に含まれており、将来的な拡張性と保守性を確保しています。

### 次のステップ

1. **基本インフラのセットアップ（1週間）**
   - Google Cloud プロジェクトの作成
   - 必要なAPIの有効化
   - 初期設定の実施

2. **FreeCAD APIのプロトタイプ開発（2週間）**
   - 基本的なAPIエンドポイントの実装
   - Dockerイメージの作成とテスト
   - ローカル環境での動作確認

3. **Streamlitアプリの修正と最適化（1週間）**
   - クラウド環境対応の実装
   - FreeCAD APIとの連携テスト
   - UI/UXの改善

### 期待される効果

1. **アーキテクチャ依存の問題解消**
   - M1 Macなどのアーキテクチャに依存しない環境の実現
   - 一貫した開発・運用環境の提供

2. **スケーラビリティの向上**
   - オンデマンドでのリソース拡張
   - 負荷に応じた柔軟な対応

3. **保守性の向上**
   - インフラストラクチャのコード化
   - 標準化されたデプロイメントプロセス

4. **開発効率の向上**
   - CI/CDパイプラインの自動化
   - 迅速なフィードバックループ 