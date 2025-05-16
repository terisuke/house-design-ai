# House Design AI プロジェクトへの貢献ガイド

このドキュメントでは、House Design AIプロジェクトへの貢献方法について説明します。

## 目次

1. [開発環境のセットアップ](#開発環境のセットアップ)
2. [開発ワークフロー](#開発ワークフロー)
3. [コーディング規約](#コーディング規約)
4. [テスト](#テスト)
5. [ドキュメント](#ドキュメント)
6. [プルリクエストプロセス](#プルリクエストプロセス)
7. [コミュニケーション](#コミュニケーション)

## 開発環境のセットアップ

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
# 基本的な依存関係のインストール
pip install -r requirements-base.txt

# Google Cloud関連の依存関係のインストール（必要に応じて）
pip install -r requirements-gcp.txt

# 開発用依存関係のインストール（開発者向け）
pip install -r requirements-dev.txt
```

注意: CP-SAT最適化機能を使用する場合は、別の仮想環境を作成し、`requirements-ortools.txt`をインストールしてください。詳細は以下の「依存関係の競合について」セクションを参照してください。

### 依存関係の競合について

本プロジェクトでは、ortoolsとGoogle Cloud関連パッケージ間で深刻なprotobufバージョン競合があります。これらのパッケージを同じ環境にインストールすると正常に動作しません。そのため、依存関係を以下の3つのファイルに分割しています：

- `requirements-base.txt`: 基本的なパッケージ（ultralytics, streamlit, テスト・開発ツールなど）
- `requirements-gcp.txt`: Google Cloud関連のパッケージ（google-cloud-storage, google-cloud-aiplatform等）
- `requirements-ortools.txt`: 最適化関連のパッケージ（ortools等）

#### 環境セットアップ手順

##### 1. 基本環境 + Google Cloud（Streamlit UI、クラウド連携機能用）

```bash
# 基本環境のセットアップ
python -m venv venv_base
source venv_base/bin/activate  # Linux / macOS
# または
.\venv_base\Scripts\Activate.ps1  # Windows PowerShell
# または
.\venv_base\Scripts\activate.bat  # Windows CMD

# 基本パッケージのインストール
pip install -r requirements-base.txt

# Google Cloud関連パッケージをインストール
pip install -r requirements-gcp.txt
```

##### 2. 最適化環境（CP-SAT最適化機能用）

```bash
# ortools用の完全に分離された環境
python -m venv venv_ortools
source venv_ortools/bin/activate  # Linux / macOS
# または
.\venv_ortools\Scripts\Activate.ps1  # Windows PowerShell
# または
.\venv_ortools\Scripts\activate.bat  # Windows CMD

# 基本パッケージとortoolsのインストール
pip install -r requirements-base.txt
pip install -r requirements-ortools.txt
```

## 開発ワークフロー

1. 新しい機能の開発:
   - `feature/機能名`の形式でブランチを作成
   - 例: `feature/freecad-integration`

2. バグ修正:
   - `fix/バグの説明`の形式でブランチを作成
   - 例: `fix/memory-leak`

3. ドキュメント更新:
   - `docs/更新内容`の形式でブランチを作成
   - 例: `docs/api-documentation`

## コーディング規約

1. **Pythonスタイルガイド**
   - PEP 8に準拠
   - Ruffを使用したコード整形
   - 行の長さは88文字以内

2. **型ヒント**
   - すべての関数に型アノテーションを付ける
   - 複雑な型は`typing`モジュールを使用

3. **ドキュメント**
   - Googleスタイルのdocstringを使用
   - すべての公開関数とクラスにドキュメントを付ける

4. **命名規則**
   - クラス名: PascalCase
   - 関数名と変数名: snake_case
   - 定数: UPPER_CASE

## テスト

1. **テストの実行**
```bash
pytest tests/
```

2. **テストカバレッジの確認**
```bash
pytest --cov=src tests/
```

3. **テストの書き方**
   - テストファイル名: `test_*.py`
   - テスト関数名: `test_機能名`
   - テストクラス名: `Test機能名`

## ドキュメント

1. **コードドキュメント**
   - 関数の目的、パラメータ、戻り値を明確に記述
   - 複雑なロジックにはコメントを追加

2. **APIドキュメント**
   - エンドポイントの説明
   - リクエスト/レスポンスの例
   - エラーケースの説明

3. **READMEの更新**
   - 新機能の追加時はREADMEを更新
   - セットアップ手順の変更を反映

## プルリクエストプロセス

1. **プルリクエストの作成**
   - 明確なタイトルと説明を付ける
   - 関連するIssue番号を参照
   - 変更内容を箇条書きで記載

2. **レビュー前のチェック**
   - すべてのテストが通過
   - コード整形が適用済み
   - ドキュメントが更新済み

3. **レビュー後の対応**
   - レビューコメントに応答
   - 必要な修正を実施
   - 変更をプッシュ

## コミュニケーション

1. **Issueの報告**
   - バグ報告は再現手順を記載
   - 機能リクエストは目的と期待する動作を説明
   - スクリーンショットやログを添付

2. **ディスカッション**
   - 技術的な議論はIssueで行う
   - 重要な決定はドキュメントに記録
   - コミュニティガイドラインに従う

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。貢献する際は、このライセンスに同意したものとみなされます。                