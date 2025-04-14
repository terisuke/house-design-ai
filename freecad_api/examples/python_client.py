"""
FreeCAD API Pythonクライアントの使用例

このスクリプトは、FreeCAD APIを使用して3Dモデルを生成する方法を示します。
非同期クライアントと同期クライアントの両方の実装例を提供します。

使用方法:
    python python_client.py

環境変数:
    API_URL: FreeCAD APIのベースURL（デフォルト: http://localhost:8080）
"""

import asyncio
import json
import os
from typing import Any, Dict

import httpx
import requests
from pydantic import BaseModel

# APIのベースURL
API_URL = os.getenv(
    "API_URL", "https://freecad-api-513507930971.asia-northeast1.run.app"
)


class ModelParameters(BaseModel):
    wall_thickness: float = 0.2
    window_size: float = 1.5


class ModelRequest(BaseModel):
    width: float = 10.0
    length: float = 15.0
    height: float = 3.0
    parameters: ModelParameters = ModelParameters()


async def generate_model_async() -> Dict[str, Any]:
    """
    非同期クライアントを使用して3Dモデルを生成
    """
    request_data = ModelRequest().dict()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/generate",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()


def generate_model_sync() -> Dict[str, Any]:
    """
    同期クライアントを使用して3Dモデルを生成
    """
    request_data = ModelRequest().dict()

    response = requests.post(
        f"{API_URL}/generate",
        json=request_data,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def check_health() -> Dict[str, str]:
    """
    APIのヘルスチェックを実行
    """
    response = requests.get(f"{API_URL}/health")
    response.raise_for_status()
    return response.json()


async def main():
    """
    メイン実行関数
    """
    print("FreeCAD API クライアントの使用例\n")

    # ヘルスチェック
    try:
        health = check_health()
        print(
            f"ヘルスチェック結果: {json.dumps(health, indent=2, ensure_ascii=False)}\n"
        )
    except Exception as e:
        print(f"ヘルスチェックに失敗しました: {e}\n")
        return

    # 同期クライアントの例
    print("1. 同期クライアントを使用した3Dモデル生成:")
    try:
        result = generate_model_sync()
        print(f"結果: {json.dumps(result, indent=2, ensure_ascii=False)}\n")
    except Exception as e:
        print(f"同期クライアントでエラーが発生しました: {e}\n")

    # 非同期クライアントの例
    print("2. 非同期クライアントを使用した3Dモデル生成:")
    try:
        result = await generate_model_async()
        print(f"結果: {json.dumps(result, indent=2, ensure_ascii=False)}\n")
    except Exception as e:
        print(f"非同期クライアントでエラーが発生しました: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
