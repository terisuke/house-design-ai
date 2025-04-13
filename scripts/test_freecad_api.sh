#!/bin/bash
set -e

# 環境変数の設定
PROJECT_ID="yolov8environment"
REGION="asia-northeast1"
SERVICE_NAME="freecad-api"

# Cloud RunサービスのURLを取得
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format="value(status.url)")

echo "FreeCAD APIのテストを開始します..."
echo "APIエンドポイント: ${SERVICE_URL}"

# テストデータの作成
cat > test_data.json << EOF
{
  "rooms": [
    {
      "id": 1,
      "dimensions": [5.0, 4.0],
      "position": [0.0, 0.0],
      "label": "リビング"
    },
    {
      "id": 2,
      "dimensions": [3.0, 3.0],
      "position": [5.0, 0.0],
      "label": "寝室"
    }
  ],
  "walls": [
    {
      "start": [0.0, 0.0],
      "end": [8.0, 0.0],
      "height": 2.5
    },
    {
      "start": [0.0, 0.0],
      "end": [0.0, 4.0],
      "height": 2.5
    },
    {
      "start": [8.0, 0.0],
      "end": [8.0, 4.0],
      "height": 2.5
    },
    {
      "start": [0.0, 4.0],
      "end": [8.0, 4.0],
      "height": 2.5
    }
  ]
}
EOF

# グリッドデータの処理をテスト
echo "グリッドデータの処理をテストします..."
curl -X POST "${SERVICE_URL}/process/grid" \
  -H "Content-Type: application/json" \
  -d @test_data.json

echo "テストが完了しました。" 