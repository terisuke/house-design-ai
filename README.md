# House Design AI

建物のセグメンテーションとグリッド生成のためのYOLOシリーズベースのAIソリューション

## 概要

House Design AIは、建物のセグメンテーションとグリッド生成を自動化するAIソリューションです。YOLOシリーズを使用した物体検出とセグメンテーション、Google Cloud Platform (Vertex AI)を活用したトレーニング、Streamlitを使用した使いやすいインターフェースを提供します。

## 主な機能

- 建物と道路の検出・セグメンテーション
- 住居と道路の関係性を考慮した建物解析
- 建物領域への規則的なグリッド適用
- YOLOアノテーションからベクター/グラフJSONへの変換
- Vertex AIでのモデルトレーニング
- Streamlitベースの直感的なUIの提供
- FreeCAD APIによる3Dモデル生成
- STLからglTFへの変換によるウェブブラウザでの3D表示

## 技術スタック

- **Python バージョン:** Python 3.9+
- **依存関係管理:** pip (requirements.txt)
- **コード整形:** Ruff (black併用)
- **型ヒント:** typingモジュールを厳格に使用
- **テストフレームワーク:** pytest
- **ドキュメント:** Googleスタイルのdocstring
- **環境管理:** venv
- **コンテナ化:** docker
- **デモフレームワーク:** streamlit
- **コンピュータビジョン:** ultralytics (YOLO v11)
- **画像処理:** OpenCV, PIL, numpy, matplotlib
- **クラウドインフラ:** Google Cloud Platform (Vertex AI, Cloud Storage)
- **データ処理:** PyYAML, numpy
- **データ検証:** pydantic
- **バージョン管理:** git
- **3Dモデリング:** FreeCAD API

## プロジェクト構造

```
house-design-ai/
├── config/                   # 設定ファイル (data.yaml, service_account.json)
├── datasets/                 # データセットディレクトリ
├── deploy/                   # デプロイ関連ファイル
├── DOCS/                     # ドキュメント
│   ├── architecture/         # アーキテクチャ関連ドキュメント
│   ├── deployment/           # デプロイメント関連ドキュメント
│   ├── development/          # 開発関連ドキュメント
│   └── roadmap/              # ロードマップ関連ドキュメント
├── freecad_api/              # FreeCAD API関連
│   ├── Dockerfile            # FreeCAD API用Dockerfile
│   ├── Dockerfile.freecad    # FreeCAD用Dockerfile
│   ├── examples/             # サンプルコード
│   ├── main.py               # FreeCAD APIのメインコード
│   ├── requirements-freecad-api.txt # FreeCAD API用依存関係
│   ├── scripts/              # FreeCAD用スクリプト
│   └── test_data.json        # テストデータ
├── house_design_app/         # Streamlitアプリケーション
│   ├── main.py               # メインアプリケーション
│   ├── pages/                # マルチページアプリのサブページ
│   ├── requirements-streamlit.txt # Streamlit用依存関係
│   └── logo.png              # アプリロゴ
├── notebooks/                # Jupyter notebooks
├── scripts/                  # ユーティリティスクリプト
├── src/                      # ソースコード
│   ├── cloud/                # クラウド連携 (Vertex AI)
│   ├── processing/           # 画像処理ロジック、YOLOアノテーション変換
│   ├── utils/                # ユーティリティ関数
│   ├── visualization/        # 可視化ツール
│   ├── cli.py                # コマンドラインインターフェース
│   ├── train.py              # モデルトレーニングロジック
│   └── inference.py          # 推論ロジック
├── terraform/                # Terraformインフラストラクチャコード
├── tests/                    # テストコード
├── Dockerfile                # メインDockerfile
├── requirements.txt          # 依存関係
├── requirements-dev.txt      # 開発用依存関係
├── README.md                 # プロジェクト説明
├── directorystructure.md     # ディレクトリ構造
└── technologystack.md        # 技術スタック
```

## セットアップ

### 前提条件

- Python 3.9以上
- pip
- git
- Docker (オプション)
- Google Cloud SDK (オプション)

### インストール

1. リポジトリのクローン:
```bash
git clone https://github.com/yourusername/house-design-ai.git
cd house-design-ai
```

2. 仮想環境の作成と有効化:
```bash
python -m venv venv
source venv/bin/activate  # Linuxの場合
# または
.\venv\Scripts\activate  # Windowsの場合
```

3. 依存関係のインストール:
```bash
pip install -r requirements.txt
```

4. 開発用依存関係のインストール（開発者の場合）:
```bash
pip install -r requirements-dev.txt
```

## 使用方法

### ローカル開発

1. Streamlitアプリの起動:
```bash
# プロジェクトのルートディレクトリで実行
PYTHONPATH=$PYTHONPATH:. streamlit run house_design_app/main.py
```

2. モデルのトレーニング:
```bash
python src/train.py --config config/train_config.yaml
```

3. 推論の実行:
```bash
python src/inference.py --image path/to/image.jpg
```

### FreeCAD APIの使用

1. FreeCAD APIの起動（ローカル開発用）:
```bash
cd freecad_api
python main.py
```

2. Dockerを使用した起動（ローカル）:
```bash
cd freecad_api
docker build -t freecad-api -f Dockerfile.freecad .
docker run -p 8000:8000 freecad-api
```

3. GCP Artifact Registryへのビルド＆プッシュ（buildx推奨）:
```bash
bash scripts/build_and_push_docker.sh
```

4. Cloud Runへのデプロイ:
```bash
gcloud run deploy freecad-api \
  --image asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:<TAG> \
  --region asia-northeast1 \
  --platform=managed \
  --allow-unauthenticated
```

5. 動作テスト:
```bash
python3 scripts/test_freecad_api.py
```

- テスト成功例:
```
✅ FreeCAD APIテスト成功
レスポンス: {
  "status": "success",
  "message": "モデルを生成しました",
  "file": "/tmp/model.FCStd",
  "storage_url": "gs://house-design-ai-data/models/model.FCStd"
}
```

- Artifact Registryのリポジトリ名は `asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api` に統一されています。

### クラウドデプロイ

1. GCPプロジェクトの設定:
```bash
gcloud config set project YOUR_PROJECT_ID
```

2. 必要なAPIの有効化:
```bash
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

3. Terraformによるインフラストラクチャのデプロイ:
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## デプロイ済みサービス

### FreeCAD API
- URL: https://freecad-api-513507930971.asia-northeast1.run.app
- 設定:
  - メモリ: 2GB
  - CPU: 2
  - タイムアウト: 300秒

## 開発状況

### 完了した機能
- ✅ 環境セットアップ
- ✅ コア機能開発
- ✅ FreeCAD統合
- ✅ YOLOアノテーション→ベクター/グラフJSON変換システム
- ✅ クラウドデプロイメント

### 進行中の機能
- 🟡 運用管理強化
  - Cloud Loggingの設定
  - Cloud Monitoringのメトリクス設定
  - APIドキュメントの整備
  - エラーハンドリングの強化

### 今後の機能
- ⏳ Vertex AI統合
- ⏳ Firebase/Firestore実装
- ⏳ 高度な機能の追加

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 貢献

プロジェクトへの貢献は大歓迎です。貢献する前に、以下の手順に従ってください：

1. このリポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

詳細な貢献ガイドについては、[CONTRIBUTING.md](DOCS/development/contributing.md)を参照してください。

## 連絡先

プロジェクトに関する質問や提案がある場合は、Issueを作成してください。
