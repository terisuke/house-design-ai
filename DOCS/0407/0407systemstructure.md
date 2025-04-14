# 土地図から一軒家CAD図自動生成システム - プロジェクト構成

## システム概要

土地図をアップロードするだけで一軒家のCAD図を自動的に生成するシステム。YOLOv8ベースの土地・道路分析からFreeCADを活用したCAD図面生成までを一貫して行う。

## システムアーキテクチャ

```mermaid
graph TB
    subgraph "ユーザーインターフェース"
        A[Streamlit Web UI] --> B[画像アップロード]
        B --> C[設計パラメータ設定]
        C --> D[結果表示・ダウンロード]
    end

    subgraph "分析処理層"
        E[YOLOv8 推論エンジン] --> F[土地・道路セグメンテーション]
        F --> G[建築可能領域計算]
        G --> H[建物配置最適化]
        H --> I[間取り自動生成]
    end

    subgraph "CAD生成層"
        I --> J[FreeCAD スクリプト生成]
        J --> K[FreeCAD エンジン]
        K --> L[CAD図面出力]
        L --> M[DXF/DWG変換]
    end

    subgraph "データストレージ"
        N[Cloud Storage] --> O[入力画像]
        N --> P[生成CAD図面]
        N --> Q[トレーニングデータ]
        N --> R[モデル重み]
    end

    subgraph "管理・監視"
        S[Google IAM] --> T[認証・権限]
        U[Cloud Monitoring] --> V[システム監視]
        W[Cloud Logging] --> X[ログ管理]
    end

    B --> E
    D --> P
    E --> N
    K --> N
    S --> A
    S --> E
    S --> K
    U --> A
    U --> E
    U --> K
    W --> A
    W --> E
    W --> K
```

## Google Cloudリソース構成

| リソース                  | 用途                  | 詳細設定                    |
|-----------------------|-----------------------|-----------------------------|
| **Vertex AI**         | YOLOv8モデルのトレーニングと推論 | カスタムコンテナ、GPUインスタンス          |
| **Cloud Storage**     | データ・モデル・CAD図の保存    | 階層化ストレージ、適切なアクセス制御   |
| **Cloud Run**         | FreeCAD APIのホスティング    | メモリ2GB、CPU 2コア、タイムアウト300秒  |
| **Artifact Registry** | コンテナイメージの保存         | FreeCAD APIイメージの管理        |
| **Cloud Build**       | CI/CDパイプライン           | ソースコード変更時の自動ビルド・デプロイ   |
| **Cloud Monitoring**  | システム監視              | エラー率、レイテンシー、メモリ使用量の監視 |
| **Cloud Logging**     | ログ収集・分析           | 集中管理、フィルタリング            |

## コンテナ構成

### 1. YOLOv8 トレーニングコンテナ
- **ベースイメージ**: NVIDIA CUDA + Python
- **主要コンポーネント**: ultralytics, OpenCV, Google Cloud SDK
- **機能**: セグメンテーションモデルのトレーニング

### 2. YOLOv8 推論コンテナ
- **ベースイメージ**: Python Slim
- **主要コンポーネント**: ultralytics, OpenCV, NumPy
- **機能**: 土地・道路のセグメンテーション、建築可能領域計算

### 3. Streamlit アプリコンテナ
- **ベースイメージ**: Python
- **主要コンポーネント**: Streamlit, Google Cloud クライアントライブラリ
- **機能**: WebUI提供、ユーザー入力処理、結果表示

### 4. FreeCAD サーバーコンテナ
- **ベースイメージ**: Ubuntu 22.04
- **主要コンポーネント**: 
  - FreeCAD
  - Python API
  - libgl1-mesa-glx
- **機能**: CAD図面生成
- **デプロイメント**:
  - Google Cloud Artifact Registryに保存
  - イメージ名: `asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api`
  - タグ: `latest`
- **ビルド手順**:
  ```bash
  cd freecad_api
  docker build --platform linux/amd64 \
      -t asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:latest \
      -f Dockerfile.freecad .
  docker push asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:latest
  ```
- **環境変数**:
  - `PYTHONPATH`: `/usr/lib/freecad/lib`
  - `QT_QPA_PLATFORM`: `offscreen`
- **エントリーポイント**: `FreeCADCmd /app/run_freecad.py`

## データフロー

1. **入力処理**:
   - ユーザーがStreamlit UIから土地図をアップロード
   - 画像はCloud Storageに保存
   - 処理パラメータ設定

2. **分析処理**:
   - YOLOv8推論エンジンが土地・道路をセグメンテーション
   - 建築可能領域を計算（法規制も考慮）
   - 最適な建物配置と間取りを自動生成

3. **CAD生成**:
   - 最適化された建物データからFreeCADスクリプトを生成
   - FreeCADエンジンでスクリプトを実行
   - CAD図面を生成しCloud Storageに保存

4. **出力処理**:
   - 生成されたCAD図面をStreamlit UIに表示
   - ユーザーがDXF/DWG形式でダウンロード

## ディレクトリ構造

```
house-design-ai/
├── terraform/               # インフラストラクチャコード
│   ├── environments/        # 環境別の設定
│   │   ├── dev/            # 開発環境
│   │   └── prod/           # 本番環境
│   └── modules/            # 再利用可能なモジュール
│       ├── monitoring/     # モニタリング設定
│       └── storage/        # ストレージ設定
│
├── deploy/                 # デプロイメント関連
│   ├── dockerfiles/        # コンテナ定義
│   └── cloud-build/        # CI/CD設定
│
├── src/                    # ソースコード
│   ├── cloud/              # クラウド連携 (Vertex AI)
│   ├── processing/         # 画像処理ロジック
│   ├── utils/              # ユーティリティ関数
│   ├── visualization/      # 可視化ツール
│   ├── cli.py              # コマンドラインインターフェース
│   ├── train.py            # モデルトレーニングロジック
│   └── inference.py        # 推論ロジック
│
├── streamlit/             # Streamlitアプリケーション
│   ├── app.py             # メインアプリケーション
│   └── pages/             # 追加ページ
│
├── freecad_api/           # FreeCAD連携API
│   ├── server.py          # FreeCADサーバー
│   ├── client.py          # FreeCADクライアント
│   └── templates/         # FreeCADスクリプトテンプレート
│
├── config/                # 設定ファイル
│   ├── data.yaml          # データ設定
│   └── service_account.json # サービスアカウント認証情報
│
├── tests/                 # テストコード
│   ├── unit/              # ユニットテスト
│   └── integration/       # 統合テスト
│
├── notebooks/             # Jupyter notebooks
├── datasets/              # データセットディレクトリ
├── scripts/               # ユーティリティスクリプト
├── DOCS/                  # ドキュメント
├── requirements.txt       # 依存関係
├── requirements-dev.txt   # 開発用依存関係
└── README.md             # プロジェクト説明
```

## デプロイメントフロー

1. **インフラストラクチャプロビジョニング**:
   - Terraformによる基盤リソースの作成
   - ネットワーク・IAM・ストレージの設定
   - モニタリング・アラートの設定

2. **コンテナイメージのビルドとプッシュ**:
   - Cloud Buildによる自動ビルド
   - Artifact Registryへのプッシュ
   - イメージのタグ付けと管理

3. **アプリケーションのデプロイ**:
   - Cloud Runへのデプロイ
   - 環境変数の設定
   - スケーリング設定

4. **モニタリングの設定**:
   - アラートポリシーの設定
   - ダッシュボードの作成
   - ログの収集と分析