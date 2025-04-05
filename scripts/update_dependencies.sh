#!/bin/bash

# 依存関係の更新スクリプト
echo "依存関係の更新を開始します..."

# 仮想環境のアクティベート
if [ -d "venv-py311" ]; then
    source venv-py311/bin/activate
elif [ -d "venv-py39" ]; then
    source venv-py39/bin/activate
else
    echo "仮想環境が見つかりません。新しく作成します..."
    python3.11 -m venv venv-py311
    source venv-py311/bin/activate
fi

# pipのアップグレード
echo "pipをアップグレードしています..."
python -m pip install --upgrade pip

# 依存関係の更新
echo "依存関係を更新しています..."
pip install -r requirements.txt

# 開発用依存関係の更新（存在する場合）
if [ -f "requirements-dev.txt" ]; then
    echo "開発用依存関係を更新しています..."
    pip install -r requirements-dev.txt
fi

# 依存関係の状態を確認
echo "現在の依存関係の状態:"
pip freeze

echo "依存関係の更新が完了しました。" 