# 技術スタック

## コア技術
- **Python バージョン:** Python 3.9+
- **依存関係管理:** pip (requirements.txt)
- **コード整形:** Ruff (black併用)
- **型ヒント:** typingモジュールを厳格に使用
- **テストフレームワーク:** pytest
- **ドキュメント:** Googleスタイルのdocstring
- **環境管理:** venv
- **コンテナ化:** docker
- **バージョン管理:** git

## フロントエンド
- **デモフレームワーク:** streamlit
- **UI/UX:** Streamlitコンポーネント

## バックエンド
- **コンピュータビジョン:** ultralytics (YOLO v8)
- **画像処理:** OpenCV, PIL, numpy, matplotlib
- **データ処理:** PyYAML, numpy
- **データ検証:** pydantic
- **3Dモデリング:** FreeCAD API

## クラウドインフラ
- **プラットフォーム:** Google Cloud Platform
- **AIサービス:** Vertex AI
- **ストレージ:** Cloud Storage
- **インフラストラクチャコード:** Terraform

---

# バージョン管理
## 重要な制約事項
- Python 3.9+の機能を活用する
- 型ヒントは厳格に使用する
- コード整形にはRuffを使用する
- ドキュメントはGoogleスタイルのdocstringを使用する

## 実装規則
- すべての関数には型アノテーションを含める
- 明確なGoogleスタイルのドキュメント文字列を提供する
- 主要なロジックにはコメントでアノテーションを付ける
- エラー処理を含める
- コード整形にRuffを使用する