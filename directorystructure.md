# ディレクトリ構成

以下のディレクトリ構造に従って実装を行ってください：

```
house-design-ai/
├── config/                   # 設定ファイル (data.yaml, service_account.json)
├── datasets/                 # データセットディレクトリ
│   ├── floorplans/           # 間取り図データセット
│   ├── train/                # 訓練データ
│   └── val/                  # 検証データ
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
├── models/                   # モデルディレクトリ
│   ├── diffusion/            # HouseDiffusionモデル
│   ├── yolo/                 # YOLOモデル
│   └── graph2plan/           # Graph2Planモデル
├── notebooks/                # Jupyter notebooks
├── scripts/                  # ユーティリティスクリプト
├── src/                      # ソースコード
│   ├── cloud/                # クラウド連携 (Vertex AI)
│   ├── generation/           # 間取り生成モジュール
│   │   ├── diffusion/        # HouseDiffusion実装
│   │   └── graph2plan/       # Graph2Plan実装
│   ├── constraints/          # 制約ソルバーモジュール
│   │   └── cp_sat/           # CP-SAT実装
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
├── README.md                 # プロジェクト説明
├── directorystructure.md     # ディレクトリ構造
└── technologystack.md        # 技術スタック
```

### 配置ルール
- 画像処理ロジック → `src/processing/`
- クラウド連携処理 → `src/cloud/`
- ユーティリティ関数 → `src/utils/`
- 可視化ツール → `src/visualization/`
- 間取り生成モジュール → `src/generation/`
- 制約ソルバーモジュール → `src/constraints/`
- テストコード → `tests/`
- 設定ファイル → `config/`
- データセット → `datasets/`
- モデルファイル → `models/`
- FreeCAD API関連 → `freecad_api/`
- Streamlitアプリケーション → `house_design_app/`
- デプロイ関連 → `deploy/`および`terraform/`
