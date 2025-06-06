# House Design AI

建物のセグメンテーションと間取り生成のためのAIソリューション

## 概要

House Design AIは、建物のセグメンテーションと間取り生成を自動化するAIソリューションです。YOLOシリーズを使用した物体検出とセグメンテーション、CP-SATを活用した間取り生成、FreeCAD APIによる3Dモデル生成、そしてStreamlitを使用した使いやすいインターフェースを提供します。

## 間取り生成システムとは？（初心者向け解説）

間取り生成システムとは、**「あなたの希望や土地の条件にピッタリ合った、夢の一軒家の間取りを、コンピューターが賢く考えて自動で提案してくれるシステム」**です。

土地の形や大きさ、「リビングは日当たり良く、広めに」「子供部屋は2つ欲しい」「家事動線が良いと嬉しいな」といった様々な希望を入力すると、建築の専門的なルールをきちんと守った上で、いくつもの素敵な間取りプランを3Dモデルや図面で見せてくれます。まるで、経験豊かな建築家がすぐそばでサポートしてくれるような、家づくりの頼もしいパートナーです。

### どのように動作するのか？

このシステムは「二層アーキテクチャ」という仕組みで動作します：

1. **アイデア出し担当（生成レイヤー）**: 「こんな間取りはどう？」「あんな配置も面白いかも！」と、創造的で多様な間取りの可能性を追求します。
2. **ルール遵守＆整理整頓担当（制約ソルバーレイヤー）**: 「この壁の位置は法律違反です」「この部屋の窓はもっと大きくないとダメ」と、建築のプロとして厳格にルールを守り、現実的で安全な計画に落とし込みます。

この二層構造により、創造性と現実性を両立した、質の高い間取り提案が可能になります。

## 主な機能

- 建物と道路の検出・セグメンテーション（YOLOv11）
- 住居と道路の関係性を考慮した建物解析
- 建物領域への規則的なグリッド適用（910mmグリッド）
- YOLOアノテーションからベクター/グラフJSONへの変換
- CP-SATによる3LDK基本レイアウト生成
- 二層アーキテクチャによる間取り生成（HouseDiffusion + CP-SAT）
- 建築基準法に準拠した間取り制約の自動適用
- 採光条件と階段寸法の基本制約実装
- Streamlitベースの直感的なUIの提供
- FreeCAD APIによる3Dモデル生成
- Cloud Storageを活用した3Dモデル保存
- STLからglTFへの変換によるウェブブラウザでの3D表示

## 技術スタック

- **Python バージョン:** Python 3.9+
- **依存関係管理:** pip (requirements-base.txt, requirements-gcp.txt, requirements-ortools.txt)
- **コード整形:** Ruff (black併用)
- **型ヒント:** typingモジュールを厳格に使用
- **テストフレームワーク:** pytest
- **ドキュメント:** Googleスタイルのdocstring
- **環境管理:** venv
- **コンテナ化:** docker
- **デモフレームワーク:** streamlit
- **コンピュータビジョン:** ultralytics (YOLO v11)
- **画像処理:** OpenCV, PIL, numpy, matplotlib
- **クラウドインフラ:** Google Cloud Platform (Cloud Run, Cloud Storage, Artifact Registry)
- **データ処理:** PyYAML, numpy
- **データ検証:** pydantic
- **バージョン管理:** git
- **3Dモデリング:** FreeCAD API
- **生成モデル:** HouseDiffusion (計画中), Graph-to-Plan
- **制約ソルバー:** Google OR-Tools CP-SAT
- **ベクトル処理:** Shapely, NetworkX
- **インフラストラクチャコード:** Terraform

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
├── requirements-base.txt     # 基本的な依存関係
├── requirements-gcp.txt      # Google Cloud関連の依存関係
├── requirements-ortools.txt  # 最適化関連の依存関係
├── requirements-dev.txt      # 開発用依存関係
├── requirements.txt          # 旧依存関係ファイル（非推奨）
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
- FreeCAD (オプション、ローカルでの3Dモデル生成に必要)

#### WSL環境での注意点

WSL (Windows Subsystem for Linux) 環境で開発する場合、以下の点に注意してください：

- パスの問題：WSLとWindowsのパス構造の違いにより、一部のファイルパスが正しく解決されない場合があります。
- 権限の問題：Windowsファイルシステム上のファイルに対する権限が正しく設定されていない場合があります。
- 環境変数：`PYTHONPATH`の設定が必要な場合があります。常に`PYTHONPATH=.`を設定してから実行してください。

### インストール

1. リポジトリのクローン:
```bash
git clone https://github.com/terisuke/house-design-ai.git
cd house-design-ai
```

2. 仮想環境の作成と有効化:
```bash
# 仮想環境の作成
python -m venv venv

# Linuxの場合
source venv/bin/activate

# macOSの場合
source venv/bin/activate

# Windowsの場合（PowerShell）
.\venv\Scripts\Activate.ps1

# Windowsの場合（コマンドプロンプト）
.\venv\Scripts\activate.bat
```

3. 依存関係のインストール:
```bash
# 基本的な依存関係のインストール
pip install --upgrade pip
pip install -r requirements-base.txt

# Google Cloud関連の依存関係のインストール（必要に応じて）
pip install -r requirements-gcp.txt

# 開発用依存関係のインストール（開発者向け）
pip install -r requirements-dev.txt
```

注意: CP-SAT最適化機能を使用する場合は、別の仮想環境を作成し、`requirements-ortools.txt`をインストールしてください。詳細は「依存関係の競合について」セクションを参照してください。

4. 環境変数の設定:
```bash
# Linuxの場合
export PYTHONPATH=.

# Windowsの場合（PowerShell）
$env:PYTHONPATH="."

# Windowsの場合（コマンドプロンプト）
set PYTHONPATH=.
```

### 依存関係の競合について

> **⚠️ 重要な警告**: 本プロジェクトでは、ortoolsとGoogle Cloud関連パッケージ間で**深刻なprotobufバージョン競合**があります。これらのパッケージを同じ環境にインストールしないでください。必ず別々の仮想環境を使用してください。

#### 競合の詳細

本プロジェクトでは、以下のようなprotobufバージョン要求の競合があります：
- **ortools**: protobuf 5.x系（>=5.26.1,<5.27）を要求
- **Google Cloud関連パッケージ**: protobuf 4.x系を要求
- **Streamlit**: protobuf <5,>=3.20 を要求

この競合により、`pip install -r requirements.txt`を実行すると「resolution-too-deep」エラーが発生します。また、Google Cloud関連パッケージとortoolsを同じ環境にインストールすると、どちらかのパッケージが正常に動作しなくなります。

#### 解決策：完全に分離された仮想環境

この問題を解決するため、requirements.txtを以下の3つのファイルに分割し、**完全に分離された仮想環境**で使用します：

- `requirements-base.txt`: 基本的なパッケージ（ultralytics, streamlit, テスト・開発ツールなど）
- `requirements-gcp.txt`: Google Cloud関連のパッケージ（google-cloud-storage, google-cloud-aiplatform等）
- `requirements-ortools.txt`: 最適化関連のパッケージ（ortools等）

#### 環境セットアップ手順

##### 1. 基本環境 + Google Cloud（Streamlit UI、クラウド連携機能用）

```bash
# 基本環境のセットアップ
python -m venv venv_base
source venv_base/bin/activate  # Linuxの場合
# または
.\venv_base\Scripts\Activate.ps1  # Windowsの場合（PowerShell）
# または
.\venv_base\Scripts\activate.bat  # Windowsの場合（コマンドプロンプト）

# 基本パッケージのインストール
pip install --upgrade pip
pip install -r requirements-base.txt

# Google Cloud関連パッケージをインストール
pip install -r requirements-gcp.txt

# 環境変数の設定
export PYTHONPATH=.  # Linuxの場合
# または
$env:PYTHONPATH="."  # Windowsの場合（PowerShell）
# または
set PYTHONPATH=.  # Windowsの場合（コマンドプロンプト）
```

##### 2. 最適化環境（CP-SAT最適化機能用）

```bash
# ortools用の完全に分離された環境
python -m venv venv_ortools
source venv_ortools/bin/activate  # Linuxの場合
# または
.\venv_ortools\Scripts\Activate.ps1  # Windowsの場合（PowerShell）
# または
.\venv_ortools\Scripts\activate.bat  # Windowsの場合（コマンドプロンプト）

# 基本パッケージとortoolsのインストール
pip install --upgrade pip
pip install -r requirements-base.txt  # 基本パッケージ（Google Cloud関連を除く）
pip install -r requirements-ortools.txt  # ortools関連パッケージ

# 環境変数の設定
export PYTHONPATH=.  # Linuxの場合
# または
$env:PYTHONPATH="."  # Windowsの場合（PowerShell）
# または
set PYTHONPATH=.  # Windowsの場合（コマンドプロンプト）
```

#### 環境の使い分け

- **Streamlit UI、クラウド連携機能**: `venv_base`環境を使用
- **CP-SAT最適化機能**: `venv_ortools`環境を使用

#### トラブルシューティング

- **「resolution-too-deep」エラー**: 依存関係の解決に失敗しています。上記の分離された環境セットアップ手順に従ってください。
- **protobufバージョン競合エラー**: Google Cloud関連パッケージとortoolsを同じ環境にインストールしないでください。
- **ImportError: cannot import name ...**: 適切な環境が有効化されているか確認してください。

## 使用方法

### ローカル開発

1. Streamlitアプリの起動:
```bash
# 仮想環境を有効化していることを確認
source venv/bin/activate  # Linuxの場合

# 環境変数の設定
export PYTHONPATH=.  # Linuxの場合

# Streamlitアプリの起動
streamlit run house_design_app/main.py
```

2. モデルのトレーニング:
```bash
# 仮想環境を有効化していることを確認
source venv/bin/activate  # Linuxの場合

# 環境変数の設定
export PYTHONPATH=.  # Linuxの場合

# トレーニングの実行
python src/train.py --data_yaml config/data.yaml
```

3. 推論の実行:
```bash
# 仮想環境を有効化していることを確認
source venv/bin/activate  # Linuxの場合

# 環境変数の設定
export PYTHONPATH=.  # Linuxの場合

# 推論の実行
python src/inference.py --image path/to/image.jpg
```

4. データセット分割・アップロード:
```bash
# 仮想環境を有効化していることを確認
source venv_base/bin/activate  # Linuxの場合

# 環境変数の設定
export PYTHONPATH=.  # Linuxの場合
export GOOGLE_APPLICATION_CREDENTIALS="config/service_account.json"  # GCP認証情報

# スクリプトの実行
bash scripts/run_split_and_upload.sh

# アップロードをスキップしてローカルでの分割のみを実行（テスト用）
bash scripts/run_split_and_upload.sh --skip-upload
```

5. テストの実行:
```bash
# 仮想環境を有効化していることを確認
source venv/bin/activate  # Linuxの場合

# 環境変数の設定
export PYTHONPATH=.  # Linuxの場合

# 全テストの実行
python -m pytest tests/ -v

# 特定のテストの実行
python -m pytest tests/test_file.py -v
```

### FreeCAD APIの使用

1. FreeCAD APIの起動（ローカル開発用）:
```bash
# 仮想環境を有効化していることを確認
source venv/bin/activate  # Linuxの場合

# 環境変数の設定
export PYTHONPATH=.  # Linuxの場合

# FreeCAD APIの起動
cd freecad_api
python main.py
```

2. Dockerを使用した起動（ローカル）:
```bash
cd freecad_api
docker build -t freecad-api -f Dockerfile.freecad .
docker run -p 8000:8000 freecad-api
```

3. GCP Artifact Registryへのビルド＆プッシュ:
```bash
# FreeCAD APIのビルド＆プッシュ
bash scripts/build_and_push_freecad.sh

# Streamlitアプリケーションのビルド＆プッシュ
bash scripts/build_and_push_streamlit.sh
```

4. Cloud Runへのデプロイ:
```bash
gcloud run deploy freecad-api \
  --image asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:<TAG> \
  --region asia-northeast1 \
  --platform=managed \
  --memory 1Gi \
  --allow-unauthenticated
```

5. 動作テスト:
```bash
# 仮想環境を有効化していることを確認
source venv/bin/activate  # Linuxの場合

# 環境変数の設定
export PYTHONPATH=.  # Linuxの場合

# テストの実行
python scripts/test_freecad_api.py
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
gcloud services enable storage.googleapis.com
```

3. Terraformによるインフラストラクチャのデプロイ:
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

4. Streamlitアプリのデプロイ:
```bash
gcloud run deploy streamlit-web \
  --image asia-northeast1-docker.pkg.dev/yolov8environment/streamlit-web/streamlit-web:<TAG> \
  --region asia-northeast1 \
  --platform=managed \
  --memory 1Gi \
  --allow-unauthenticated
```

## デプロイ済みサービス

### FreeCAD API
- URL: https://freecad-api-513507930971.asia-northeast1.run.app
- 設定:
  - メモリ: 2GB
  - CPU: 2
  - タイムアウト: 300秒

### Streamlitアプリケーション
- URL: https://streamlit-web-513507930971.asia-northeast1.run.app
- 設定:
  - メモリ: 8GB
  - CPU: 2
  - タイムアウト: 3600秒
- 環境変数:
  - GOOGLE_APPLICATION_CREDENTIALS: サービスアカウント認証用
  - USE_GCP_DEFAULT_CREDENTIALS: Cloud Run環境での認証用
  - FREECAD_API_URL: FreeCAD APIのURL
  - BUCKET_NAME: Cloud Storageバケット名
  - SECRET_MANAGER_SERVICE_ACCOUNT: Secret Managerアクセス用
  - LOGO_GCS_PATH: ロゴファイルのGCSパス
  - TORCH_WARN_ONLY: PyTorch警告の制御
  - PYTHONPATH: Pythonパスの設定

## FreeCAD API実装の詳細

FreeCAD APIでは以下のデフォルト値を使用しています：
- 壁の厚さ: 120mm (0.12m)
- 一階の壁の高さ: 2900mm (2.9m)
- 二階の壁の高さ: 2800mm (2.8m)

## 開発状況（2025年5月24日時点）

### 完了した機能
- ✅ 環境セットアップ
- ✅ コア機能開発
- ✅ FreeCAD APIのCloud Runデプロイ
- ✅ StreamlitアプリケーションのCloud Runデプロイ
- ✅ Cloud StorageでのFCStdモデル保存
- ✅ YOLOアノテーション→ベクター/グラフJSON変換システム
- ✅ CP-SAT最小PoCの開発（3LDK基本レイアウト生成）
- ✅ 建築基準法制約の基本実装（セットバック、最小部屋サイズ）
- ✅ 910mmグリッド + 採光条件 + 階段寸法の基本制約実装
- ✅ 単位の統一（m）
- ✅ YOLOv11による建物・道路セグメンテーション
- ✅ セグメンテーション結果からの建築可能エリア計算
- ✅ 基本的な間取り生成アルゴリズム
- ✅ Terraformによるインフラストラクチャのコード化
- ✅ ロゴ表示とモデルロード問題の修正
- ✅ デプロイスクリプトの最適化
- ✅ データセット分割・GCSアップロードスクリプトの実装（7:3分割）
- ✅ Vertex AI統合（Docker secret mount、ARM64→AMD64クロスビルド対応）
- ✅ セキュリティ改善（サービスアカウント認証情報の安全な処理）
- ✅ 統合ビルド＆デプロイスクリプト（build_and_run_vertex_training.sh）

### 進行中の機能
- 🟡 FreeCAD APIの完全実装
- 🟡 Vertex AI統合の実装
- 🟡 間取り生成システムの二層アーキテクチャ実装
- 🟡 建築基準法チェック機能の拡張
  - 採光基準の詳細実装
  - 避難経路の検証
  - 耐震基準の検証
- 🟡 建具記号ライブラリの作成

### 今後の開発計画（フェーズ別）

#### フェーズ4: HouseDiffusionモデル開発（2025年5月25日〜6月7日）
- HouseDiffusion実装・小規模データセットでの初期トレーニング
- 敷地形状と方位条件の埋め込みメカニズム実装
- FreeCAD出力基本システム構築
- YOLOv12への移行準備

#### フェーズ5: 制約ソルバー完成と統合（2025年6月8日〜6月21日）
- CP-SATソルバーの完全実装
- 採光、階段、1F/2F整合性など全制約条件の実装
- Diffusionモデルと制約ソルバーの統合
- ベンチマークテスト（100案生成→制約チェック→最適化）

#### フェーズ6: UI開発と最終調整（2025年6月22日〜7月5日）
- Streamlit/Three.js UIの開発
- 評価システム完成
- パフォーマンス最適化
- 実際の敷地データでのエンドツーエンドテスト

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

### Vertex AI統合（YOLO学習）

1. Vertex AIカスタムジョブでのYOLO学習（推奨）:
```bash
# 仮想環境を有効化していることを確認
source venv_base/bin/activate  # Linuxの場合

# 環境変数の設定
export PYTHONPATH=.  # Linuxの場合

# 基本実行（デフォルト設定：エポック50、バッチサイズ2、画像サイズ416）
./scripts/build_and_run_vertex_training.sh

# カスタムパラメータで実行
./scripts/build_and_run_vertex_training.sh \
  --epochs 100 \
  --batch-size 4 \
  --image-size 640 \
  --model yolo11l-seg.pt \
  --lr0 0.01 \
  --optimizer AdamW

# ビルドをスキップして既存イメージで学習のみ実行
./scripts/build_and_run_vertex_training.sh --skip-build --epochs 200
```

2. 利用可能なオプション:
- `--epochs NUM`: エポック数 (デフォルト: 50)
- `--batch-size NUM`: バッチサイズ (デフォルト: 2)
- `--image-size NUM`: 画像サイズ (デフォルト: 416)
- `--model STRING`: モデル名 (デフォルト: yolo11m-seg.pt)
- `--lr0 FLOAT`: 学習率 (デフォルト: 0.001)
- `--optimizer STRING`: オプティマイザ (デフォルト: AdamW)
- `--iou-threshold FLOAT`: IoU閾値 (デフォルト: 0.5)
- `--data-yaml STRING`: データセット設定ファイル (デフォルト: data.yaml)
- `--skip-build`: ビルドをスキップして既存イメージを使用
- `--help`: ヘルプを表示

#### セキュリティとクロスプラットフォーム対応

本プロジェクトでは以下の最新技術を採用しています：

**セキュリティ改善:**
- サービスアカウント認証情報をGitリポジトリに含めない
- Docker secret mountを使用した安全な認証情報の処理
- ビルド時のみ認証情報にアクセス、最終イメージには含まれない

**クロスプラットフォーム対応:**
- ARM64 Mac (M1/M2/M3/M4)からAMD64 Linux用イメージのビルド
- Docker buildxを使用したマルチアーキテクチャビルド
- Google Cloud Platform (AMD64)での確実な動作保証
