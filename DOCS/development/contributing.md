# House Design AI プロジェクト貢献ガイド

## 目次

1. [はじめに](#はじめに)
2. [開発環境のセットアップ](#開発環境のセットアップ)
3. [開発ワークフロー](#開発ワークフロー)
4. [コーディング規約](#コーディング規約)
5. [テスト](#テスト)
6. [プルリクエスト](#プルリクエスト)
7. [コミュニケーション](#コミュニケーション)
8. [ライセンス](#ライセンス)

## はじめに

House Design AIプロジェクトへの貢献に興味をお持ちいただき、ありがとうございます。このドキュメントでは、プロジェクトへの貢献方法について説明します。

## 開発環境のセットアップ

### 前提条件

- Python 3.9以上
- Docker
- Git
- Google Cloud SDKのインストール（クラウド機能を使用する場合）

### リポジトリのクローン

```bash
git clone https://github.com/terisuke/house-design-ai.git
cd house-design-ai
```

### 仮想環境のセットアップ

```bash
# 仮想環境の作成
python -m venv venv

# 仮想環境のアクティベート
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 開発用の依存関係
```

### 環境変数の設定

```bash
# Google Cloud認証情報の設定（クラウド機能を使用する場合）
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"

# Streamlit用の設定
mkdir -p .streamlit
cat > .streamlit/secrets.toml << EOF
[gcp]
credentials = """
{
  "type": "service_account",
  ...
}
"""
EOF
```

### FreeCADのセットアップ（オプション）

FreeCAD APIの開発に貢献する場合は、FreeCADをインストールする必要があります。

```bash
# Ubuntuの場合
sudo apt-get update
sudo apt-get install -y freecad

# macOSの場合
brew install --cask freecad

# または、Dockerを使用する（推奨）
cd freecad_api
docker build -t freecad-api:local -f Dockerfile.freecad .
```

## 開発ワークフロー

### ブランチ戦略

- `main`: 安定版のリリースブランチ
- `develop`: 開発ブランチ（主要な開発はここから分岐）
- `feature/*`: 新機能の開発用ブランチ
- `bugfix/*`: バグ修正用ブランチ
- `docs/*`: ドキュメント更新用ブランチ

### 開発の流れ

1. 最新の`develop`ブランチから新しいブランチを作成
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/your-feature-name
   ```

2. 変更を実装

3. テストを実行
   ```bash
   pytest
   ```

4. コードの品質チェック
   ```bash
   ruff check .
   ruff format .
   ```

5. 変更をコミット
   ```bash
   git add .
   git commit -m "feat: 機能の説明"
   ```

6. 変更をプッシュ
   ```bash
   git push -u origin feature/your-feature-name
   ```

7. プルリクエストを作成

## コーディング規約

### Pythonスタイルガイドライン

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)に従う
- [PEP 8](https://www.python.org/dev/peps/pep-0008/)に準拠
- [Ruff](https://github.com/charliermarsh/ruff)を使用してコードをフォーマット

### 型ヒント

- すべての関数とメソッドに型ヒントを追加
- `typing`モジュールを使用して複雑な型を表現

```python
from typing import Dict, List, Optional, Tuple

def process_image(image_path: str, params: Dict[str, float]) -> Tuple[np.ndarray, Optional[str]]:
    """画像を処理する関数。

    Args:
        image_path: 処理する画像のパス
        params: 処理パラメータ

    Returns:
        処理された画像と、エラーメッセージ（エラーがある場合）
    """
    # 実装
```

### ドキュメンテーション

- すべての関数、クラス、モジュールにDocstringを追加
- Googleスタイルのドキュメンテーションを使用

```python
def calculate_setback(mask: np.ndarray, distance_mm: float, px_per_mm: float) -> np.ndarray:
    """指定された距離だけマスクを縮小する。

    Args:
        mask: 入力マスク（2D配列、0または1）
        distance_mm: 縮小する距離（mm単位）
        px_per_mm: 1mmあたりのピクセル数

    Returns:
        縮小されたマスク

    Raises:
        ValueError: マスクが空の場合
    """
    # 実装
```

## テスト

### テストフレームワーク

- [pytest](https://docs.pytest.org/)を使用
- テストファイルは`tests/`ディレクトリに配置
- テストファイル名は`test_*.py`の形式

### テストの実行

```bash
# すべてのテストを実行
pytest

# 特定のテストを実行
pytest tests/test_processing/test_mask.py

# カバレッジレポートの生成
pytest --cov=src
```

### テスト作成のガイドライン

- 各モジュールに対応するテストモジュールを作成
- ユニットテストとインテグレーションテストを分離
- モックを使用して外部依存関係を分離
- エッジケースとエラーケースをテスト

## プルリクエスト

### プルリクエストの作成

1. GitHubでプルリクエストを作成
2. プルリクエストのタイトルと説明を明確に記述
3. 関連するIssueがある場合は、プルリクエストの説明で言及

### プルリクエストのレビュー

- コードレビューのコメントに対応
- 必要に応じて変更を追加
- すべてのCIチェックが通過していることを確認

### マージ基準

- 少なくとも1人のレビュアーの承認
- すべてのCIチェックの通過
- コーディング規約への準拠
- 適切なテストの追加

## コミュニケーション

### 問題の報告

- GitHubのIssueを使用して問題を報告
- 問題の再現手順を明確に記述
- 可能であれば、スクリーンショットや関連するログを添付

### ディスカッション

- 大きな変更や新機能の提案はGitHubのDiscussionsで議論
- 技術的な質問はIssueまたはDiscussionsで行う

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。プロジェクトに貢献することにより、あなたの貢献物もこのライセンスの下で公開されることに同意したものとみなされます。
