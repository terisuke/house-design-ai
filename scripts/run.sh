#!/bin/bash

# このスクリプトのディレクトリを取得
SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

# スクリプトの引数を取得
COMMAND="$1"
shift

# コマンドに基づいて適切なスクリプトを実行
case "$COMMAND" in
    "update")
        "$SCRIPT_DIR/scripts/update_dependencies.sh" "$@"
        ;;
    "start")
        "$SCRIPT_DIR/scripts/start_app.sh" "$@"
        ;;
    *)
        echo "使用方法: $0 [update|start]"
        echo "  update: 依存関係を更新します"
        echo "  start: アプリケーションを起動します"
        exit 1
        ;;
esac 