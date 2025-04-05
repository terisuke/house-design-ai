#!/bin/bash

# アプリケーション起動スクリプト
echo "House Design AIアプリケーションを起動します..."

# 仮想環境のアクティベート
if [ -d "venv-py311" ]; then
    source venv-py311/bin/activate
elif [ -d "venv-py39" ]; then
    source venv-py39/bin/activate
else
    echo "仮想環境が見つかりません。依存関係の更新スクリプトを実行します..."
    ./scripts/update_dependencies.sh
fi

# 環境変数の設定
export PYTHONPATH=$PYTHONPATH:$(pwd)
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=localhost

# Streamlitアプリの起動
echo "Streamlitアプリを起動しています..."
streamlit run streamlit/app.py 