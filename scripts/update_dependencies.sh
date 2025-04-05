#!/bin/bash

# スクリプトのディレクトリを取得（スクリプトが直接実行された場合）
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    # スクリプトがsourceされた場合
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
else
    # スクリプトが直接実行された場合
    SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
fi

# プロジェクトルートを取得
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# プロジェクトルートに移動
cd "$PROJECT_ROOT"

# 依存関係の更新スクリプト
echo "依存関係の更新を開始します..."
echo "プロジェクトルート: $PROJECT_ROOT"
echo "現在のPythonバージョン: $(python --version)"

# pyenvが利用可能な場合は、pyenvのPythonを使用
if command -v pyenv &> /dev/null; then
    echo "pyenvが検出されました。pyenvのPythonを使用します。"
    # pyenvのPythonを使用
    eval "$(pyenv init -)"
    # 現在のpyenvバージョンを表示
    echo "pyenvバージョン: $(pyenv version)"
fi

# 仮想環境のアクティベート
if [ -d "venv-py311" ]; then
    source venv-py311/bin/activate
elif [ -d "venv-py39" ]; then
    source venv-py39/bin/activate
else
    echo "仮想環境が見つかりません。新しく作成します..."
    # pyenvのPythonを使用して仮想環境を作成
    python -m venv venv-py311
    source venv-py311/bin/activate
fi

# pipのアップグレード
echo "pipをアップグレードしています..."
python -m pip install --upgrade pip

# 依存関係の更新
echo "依存関係を更新しています..."
pip install -r "$PROJECT_ROOT/requirements.txt"

# 開発用依存関係の更新（存在する場合）
if [ -f "$PROJECT_ROOT/requirements-dev.txt" ]; then
    echo "開発用依存関係を更新しています..."
    pip install -r "$PROJECT_ROOT/requirements-dev.txt"
fi

# 依存関係の状態を確認
echo "現在の依存関係の状態:"
pip freeze

echo "依存関係の更新が完了しました。" 