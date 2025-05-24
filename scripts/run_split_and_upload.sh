#!/bin/bash

# 
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
  export GOOGLE_APPLICATION_CREDENTIALS="$PROJECT_ROOT/config/service_account.json"
  echo "GOOGLE_APPLICATION_CREDENTIALS環境変数を設定: $GOOGLE_APPLICATION_CREDENTIALS"
fi

if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
  echo "エラー: GCP認証情報ファイルが見つかりません: $GOOGLE_APPLICATION_CREDENTIALS"
  echo "認証情報ファイルを配置するか、GOOGLE_APPLICATION_CREDENTIALS環境変数を設定してください。"
  exit 1
fi

echo "データセット分割・アップロードスクリプトを実行します..."
python scripts/split_and_upload_dataset.py --update-yaml

if [ $? -eq 0 ]; then
  echo "データセット分割・アップロードが正常に完了しました。"
  echo "アップロード先:"
  echo "  トレーニング画像: gs://yolo-v11-training/house/train/images/"
  echo "  トレーニングラベル: gs://yolo-v11-training/house/train/labels/"
  echo "  検証画像: gs://yolo-v11-training/house/val/images/"
  echo "  検証ラベル: gs://yolo-v11-training/house/val/labels/"
  exit 0
else
  echo "エラー: データセット分割・アップロードに失敗しました。"
  exit 1
fi
