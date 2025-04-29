#!/bin/bash

# FreeCAD API curlコマンドの使用例
# このスクリプトは、FreeCAD APIを使用して3Dモデルを生成する方法をcurlコマンドで示します。

# APIのベースURL
API_URL="https://freecad-api-513507930971.asia-northeast1.run.app"

echo "FreeCAD API curlコマンドの使用例"
echo "================================"

# ヘルスチェック
echo -e "\n1. ヘルスチェック:"
curl -X GET "${API_URL}/health" \
  -H "Content-Type: application/json"

# 3Dモデル生成（基本的な例）
echo -e "\n\n2. 基本的な3Dモデル生成:"
curl -X POST "${API_URL}/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "width": 10.0,
    "length": 15.0,
    "height": 3.0,
    "parameters": {
      "wall_thickness": 0.2,
      "window_size": 1.5
    }
  }'

# 3Dモデル生成（カスタムパラメータ）
echo -e "\n\n3. カスタムパラメータを使用した3Dモデル生成:"
curl -X POST "${API_URL}/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "width": 20.0,
    "length": 25.0,
    "height": 4.0,
    "parameters": {
      "wall_thickness": 0.3,
      "window_size": 2.0
    }
  }'

# 3Dモデル生成（最小サイズ）
echo -e "\n\n4. 最小サイズの3Dモデル生成:"
curl -X POST "${API_URL}/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "width": 1.0,
    "length": 1.0,
    "height": 2.0,
    "parameters": {
      "wall_thickness": 0.1,
      "window_size": 0.5
    }
  }'

echo -e "\n" 