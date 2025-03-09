# House Design AI

建物のセグメンテーションとグリッド生成のためのYOLOv8ベースのAIソリューション。Google Cloud Platform (Vertex AI)を活用したトレーニングと、Streamlitを使用した使いやすいインターフェースを提供します。

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
python -m src.cli vertex --model yolov8m-seg.pt --epochs 100
```

詳細なオプションは以下で確認できます:

```bash
python -m src.cli vertex --help
```

### ローカルでの推論

```bash
python -m src.cli inference --model_path path/to/model.pt --image_path path/to/image.jpg
```

## プロジェクト構造

```
house-design-ai/
├── config/                   # 設定ファイル
├── deploy/                   # デプロイ関連ファイル
├── notebooks/                # Jupyter notebooks
├── src/                      # ソースコード
│   ├── cloud/                # クラウド連携
│   ├── processing/           # 画像処理ロジック
│   ├── utils/                # ユーティリティ
│   └── visualization/        # 可視化ツール
├── streamlit/                # Streamlitアプリ
└── tests/                    # テストコード
```

## 開発者向け情報

### コーディング規約

- PEP 8に準拠し、Ruffでコード整形
- すべての関数に型アノテーションとDocstringを追加
- モジュール性と再利用性を重視したコード設計

### テスト実行

```bash
pytest tests/
```

## ライセンス

[MIT License](LICENSE)

## 謝辞

- YOLOv8: [Ultralytics](https://github.com/ultralytics/ultralytics)
- Streamlit: [Streamlit](https://streamlit.io/)
- Google Cloud Platform: [GCP](https://cloud.google.com/)
