# House Design AI

建物のセグメンテーションとグリッド生成のためのYOLO11ベースのAIソリューション。Google Cloud Platform (Vertex AI)を活用したトレーニングと、Streamlitを使用した使いやすいインターフェースを提供します。

## 機能

- 📸 **セグメンテーション**: 画像内の建物と道路を検出・セグメンテーション
- 🏠 **建物解析**: 住居と道路の関係性を考慮した処理
- 📊 **グリッド生成**: 建物領域に規則的なグリッドを適用
- ☁️ **クラウド統合**: Vertex AIでのモデルトレーニングに対応
- 🖥️ **ユーザーインターフェース**: Streamlitベースの直感的なUI

## セットアップ

### 前提条件

- Python 3.9以上
- Google Cloud Platform アカウント (Vertex AI使用時のみ)

### 環境構築

1. リポジトリをクローン:

   ```bash
   git clone https://github.com/yourusername/house-design-ai.git
   cd house-design-ai
   ```

2. 仮想環境を作成:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
   ```

3. 依存関係をインストール:

   ```bash
   pip install -r requirements.txt
   ```

4. GCPサービスアカウント設定 (Vertex AI使用時のみ):
   - サービスアカウントキーを `config/service_account.json` に配置
   - または環境変数 `GOOGLE_APPLICATION_CREDENTIALS` を設定

## 使用方法

### Streamlitアプリの起動

```bash
python -m src.cli app
```

これにより、ブラウザでStreamlitアプリが開きます（デフォルトは <http://localhost:8501> ）。

### Vertex AIでのトレーニング

```bash
python -m src.cli vertex --model yolo11l-seg.pt --epochs 100
```

詳細なオプションは以下で確認できます:

```bash
python -m src.cli vertex --help
```

### ローカルでのモデルトレーニング

```bash
python -m src.cli train --data config/data.yaml --model yolo11l-seg.pt --epochs 50
```

### 推論実行

```bash
python -m src.cli inference --model_path yolo11l-seg.pt --image_path path/to/image.jpg
```

### 可視化ツール

```bash
python -m src.cli visualize --result_path path/to/results --output_dir path/to/output
```

## Docker対応

Dockerを使用して環境を構築することも可能です:

```bash
# イメージのビルド
docker build -t house-design-ai .

# コンテナの実行（Streamlitアプリ）
docker run -p 8501:8501 house-design-ai
```

### 可視化ツール

```bash
# 推論結果の可視化
python -m src.cli visualize --result_path path/to/results --output_dir path/to/output

# データセットの可視化
python -m src.visualization.dataset --data_yaml=config/data.yaml --num_samples=5 --output_dir=visualization_results

# Dockerパスとローカルパスが異なる場合、オーバーライドオプションを使用
python -m src.visualization.dataset --data_yaml=config/data.yaml --override_train_path=datasets/house/train
```

オプション:
- `--data_yaml`: データセット設定ファイルへのパス
- `--num_samples`: 視覚化するサンプル数（デフォルト: 5）
- `--output_dir`: 出力ディレクトリ（デフォルト: visualization_results）
- `--override_train_path`: data.yamlのtrainパスを上書き（Docker/クラウド用のパスをローカル環境用に変更する場合に使用）

## トラブルシューティング

### OpenCVの依存関係エラー

Docker環境で以下のようなエラーが発生した場合：

```
ImportError: libGL.so.1: cannot open shared object file: No such file or directory
```

これはOpenCVに必要なシステムライブラリが不足していることを示しています。Dockerfileに以下のライブラリを追加してください：

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
  libgl1 \
  libglx0 \
  libglvnd0 \
  libsm6 \
  libxext6 \
  libxrender1
```

その後、再度Dockerイメージをビルドしてください。

## プロジェクト構造

```
house-design-ai/
├── app.py                    # エントリーポイント
├── Dockerfile                # Dockerコンテナ定義
├── requirements.txt          # 依存パッケージ
├── config/                   # 設定ファイル
├── datasets/                 # データセットディレクトリ
├── deploy/                   # デプロイ関連ファイル
├── notebooks/                # Jupyter notebooks
├── scripts/                  # ユーティリティスクリプト
├── src/                      # ソースコード
│   ├── cloud/                # クラウド連携
│   ├── processing/           # 画像処理ロジック
│   ├── utils/                # ユーティリティ
│   ├── visualization/        # 可視化ツール
│   ├── cli.py                # コマンドラインインターフェース
│   ├── train.py              # モデルトレーニングロジック
│   └── inference.py          # 推論ロジック
├── streamlit/                # Streamlitアプリ
│   ├── pages/                # マルチページアプリのサブページ
│   └── app.py                # メインアプリケーション
└── tests/                    # テストコード
```

## 開発者向け情報

### コーディング規約

- PEP 8に準拠し、Ruffとblackでコード整形
- すべての関数に型アノテーションとDocstringを追加
- モジュール性と再利用性を重視したコード設計

### 主要な依存関係

- **ultralytics**: YOLO11モデルの実装
- **google-cloud-aiplatform**: Vertex AI連携
- **streamlit**: ウェブインターフェース
- **opencv-python**: 画像処理
- **pydantic**: データ検証

### テスト実行

```bash
pytest tests/
```

## ライセンス

[MIT License](LICENSE)

## 謝辞

- YOLO11: [Ultralytics](https://github.com/ultralytics/ultralytics)
- Streamlit: [Streamlit](https://streamlit.io/)
- Google Cloud Platform: [GCP](https://cloud.google.com/)
