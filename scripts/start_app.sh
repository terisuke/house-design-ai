#!/bin/bash

# スクリプトのディレクトリを取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# アプリケーション起動スクリプト
echo "House Design AIアプリケーションを起動します..."
echo "プロジェクトルート: $PROJECT_ROOT"

# 仮想環境のアクティベート
if [ -d "venv-py311" ]; then
    source venv-py311/bin/activate
elif [ -d "venv-py39" ]; then
    source venv-py39/bin/activate
else
    echo "仮想環境が見つかりません。依存関係の更新スクリプトを実行します..."
    "$SCRIPT_DIR/update_dependencies.sh"
fi

# 環境変数の設定
export PYTHONPATH=$PYTHONPATH:$PROJECT_ROOT
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=localhost

# Streamlitアプリの起動
echo "Streamlitアプリを起動しています..."
streamlit run "$PROJECT_ROOT/streamlit/app.py" 