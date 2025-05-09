# ディレクトリ構成

以下のディレクトリ構造に従って実装を行ってください：

```
house-design-ai/
├── config/                   # 設定ファイル (data.yaml, service_account.json)
├── datasets/                 # データセットディレクトリ
├── deploy/                   # デプロイ関連ファイル
├── DOCS/                     # ドキュメント
│   └── 0407/                 # 2024年4月7日のドキュメント
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
│   ├── processing/           # 画像処理ロジック
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
├── FreeCAD.md                # FreeCAD統合ガイド (直接Python API使用とSTL→glTF変換)
├── GCP_DEPLOYMENT_GUIDE.md   # GCPデプロイメントガイド
├── CLOUD_DEPLOYMENT_PLAN.md  # クラウドデプロイメント計画
├── CONTRIBUTING.md           # 貢献ガイド
├── ROADMAP.md                # 開発ロードマップ
└── README.md                 # プロジェクト説明
```

### 配置ルール
- 画像処理ロジック → `src/processing/`
- クラウド連携処理 → `src/cloud/`
- ユーティリティ関数 → `src/utils/`
- 可視化ツール → `src/visualization/`
- テストコード → `tests/`
- 設定ファイル → `config/`
- データセット → `datasets/`
- FreeCAD API関連 → `freecad_api/`
- Streamlitアプリケーション → `house_design_app/`
- デプロイ関連 → `deploy/`および`terraform/`
