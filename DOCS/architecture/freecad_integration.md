# FreeCAD API 統合ドキュメント

## 1. 概要

このドキュメントでは、House Design AIプロジェクトにおけるFreeCAD APIの仕様と使用方法について詳細に説明します。FreeCAD APIは、建物の3Dモデル生成、ファイル形式変換、図面生成などの機能を提供するRESTful APIです。

## 2. デプロイメント情報

### 2.1 APIエンドポイント

現在のAPIエンドポイント: `https://freecad-api-513507930971.asia-northeast1.run.app`

### 2.2 デプロイメント環境

- プラットフォーム: Google Cloud Run
- リージョン: asia-northeast1
- メモリ: 2Gi
- CPU: 2
- タイムアウト: 900秒（15分）

### 2.3 デフォルト設定値

- 壁の厚さ: 120mm（0.12m）
- 1階の壁の高さ: 2900mm（2.9m）
- 2階の壁の高さ: 2800mm（2.8m）

## 3. API エンドポイント

### 3.1 基本エンドポイント

| エンドポイント | メソッド | 説明 |
|--------------|--------|------|
| `/` | GET | APIのルートエンドポイント、基本情報を返します |
| `/health` | GET | APIのヘルスチェック |

### 3.2 モデル生成エンドポイント

| エンドポイント | メソッド | 説明 |
|--------------|--------|------|
| `/generate` | POST | 基本的な3Dモデルを生成します |
| `/process/grid` | POST | グリッドデータから詳細な3Dモデルを生成します |
| `/process/drawing` | POST | 3DモデルからCAD図面を生成します |

### 3.3 ファイル変換エンドポイント

| エンドポイント | メソッド | 説明 |
|--------------|--------|------|
| `/convert/3d` | POST | FCStdファイルをSTL形式に変換します |
| `/convert/stl-to-gltf` | POST | STLファイルをglTF形式に変換します |

## 4. API 仕様

### 4.1 基本モデル生成 (`/generate`)

**説明**: 指定されたパラメータに基づいて基本的な3Dモデルを生成します。

**リクエスト**:
```json
{
  "width": 10.0,
  "length": 15.0,
  "height": 3.0,
  "parameters": {
    "wall_thickness": 0.12,
    "window_size": 1.5,
    "include_furniture": true
  }
}
```

**リクエストパラメータ**:
| パラメータ | 型 | 必須 | 説明 |
|----------|-----|-----|------|
| width | float | はい | モデルの幅（メートル） |
| length | float | はい | モデルの長さ（メートル） |
| height | float | はい | モデルの高さ（メートル） |
| parameters | object | いいえ | 追加のパラメータ |
| parameters.wall_thickness | float | いいえ | 壁の厚さ（メートル）、デフォルト: 0.12 |
| parameters.window_size | float | いいえ | 窓のサイズ（メートル）、デフォルト: 1.5 |
| parameters.include_furniture | boolean | いいえ | 家具を含めるかどうか、デフォルト: true |

**レスポンス**:
```json
{
  "status": "success",
  "message": "3Dモデルの生成に成功しました",
  "file": "/tmp/model.fcstd",
  "storage_url": "https://storage.googleapis.com/house-design-ai-data/models/uuid.fcstd"
}
```

**レスポンスパラメータ**:
| パラメータ | 型 | 説明 |
|----------|-----|------|
| status | string | 処理結果のステータス（success/error） |
| message | string | 処理結果のメッセージ |
| file | string | 生成されたファイルのローカルパス |
| storage_url | string | 生成されたファイルのCloud Storage URL |

### 4.2 グリッドデータからのモデル生成 (`/process/grid`)

**説明**: 部屋と壁の情報を含むグリッドデータから詳細な3Dモデルを生成します。

**リクエスト**:
```json
{
  "rooms": [
    {
      "id": 1,
      "dimensions": [5.0, 4.0],
      "position": [0.0, 0.0],
      "label": "LDK"
    },
    {
      "id": 2,
      "dimensions": [3.0, 3.0],
      "position": [5.0, 0.0],
      "label": "Bedroom"
    }
  ],
  "walls": [
    {
      "start": [0.0, 0.0],
      "end": [5.0, 0.0],
      "height": 2.9,
      "floor": 1
    },
    {
      "start": [5.0, 0.0],
      "end": [8.0, 0.0],
      "height": 2.9,
      "floor": 1
    }
  ],
  "wall_thickness": 0.12,
  "include_furniture": true
}
```

**リクエストパラメータ**:
| パラメータ | 型 | 必須 | 説明 |
|----------|-----|-----|------|
| rooms | array | はい | 部屋の配列 |
| rooms[].id | integer | はい | 部屋のID |
| rooms[].dimensions | array | はい | 部屋の寸法 [幅, 奥行き]（メートル） |
| rooms[].position | array | はい | 部屋の位置 [x, y]（メートル） |
| rooms[].label | string | はい | 部屋のラベル |
| walls | array | はい | 壁の配列 |
| walls[].start | array | はい | 壁の開始位置 [x, y]（メートル） |
| walls[].end | array | はい | 壁の終了位置 [x, y]（メートル） |
| walls[].height | float | いいえ | 壁の高さ（メートル）、デフォルト: 2.9 |
| walls[].floor | integer | いいえ | 壁の階数（1または2）、デフォルト: 1 |
| wall_thickness | float | いいえ | 壁の厚さ（メートル）、デフォルト: 0.12 |
| include_furniture | boolean | いいえ | 家具を含めるかどうか、デフォルト: true |

**レスポンス**:
```json
{
  "url": "https://storage.googleapis.com/house-design-ai-data/models/uuid.fcstd"
}
```

**レスポンスパラメータ**:
| パラメータ | 型 | 説明 |
|----------|-----|------|
| url | string | 生成されたモデルのCloud Storage URL |

### 4.3 FCStdファイルからSTLへの変換 (`/convert/3d`)

**説明**: FCStdファイルをSTL形式に変換します。

**リクエスト**: マルチパートフォームデータ
- `file`: FCStdファイル

**レスポンス**:
```json
{
  "url": "https://storage.googleapis.com/house-design-ai-data/models/uuid.stl",
  "format": "stl"
}
```

**レスポンスパラメータ**:
| パラメータ | 型 | 説明 |
|----------|-----|------|
| url | string | 変換されたファイルのCloud Storage URL |
| format | string | 変換後のファイル形式 |

### 4.4 STLファイルからglTFへの変換 (`/convert/stl-to-gltf`)

**説明**: STLファイルをglTF形式に変換します。

**リクエスト**: マルチパートフォームデータ
- `file`: STLファイル

**レスポンス**:
```json
{
  "url": "https://storage.googleapis.com/house-design-ai-data/models/uuid.gltf",
  "format": "gltf"
}
```

**レスポンスパラメータ**:
| パラメータ | 型 | 説明 |
|----------|-----|------|
| url | string | 変換されたファイルのCloud Storage URL |
| format | string | 変換後のファイル形式 |

### 4.5 3DモデルからCAD図面の生成 (`/process/drawing`)

**説明**: 3DモデルからCAD図面を生成します。

**リクエスト**: フォームデータ
- `model_url`: 3DモデルのURL（FCStdファイル）
- `drawing_type`: 図面のタイプ（平面図、立面図、側面図、アイソメトリック）
- `scale`: 縮尺（1:50, 1:100, 1:200）

**レスポンス**:
```json
{
  "url": "https://storage.googleapis.com/house-design-ai-data/drawings/uuid.pdf",
  "format": "pdf"
}
```

**レスポンスパラメータ**:
| パラメータ | 型 | 説明 |
|----------|-----|------|
| url | string | 生成された図面のCloud Storage URL |
| format | string | 図面のファイル形式 |

## 5. Model Context Protocol (MCP) クライアント

FreeCAD APIは、Model Context Protocol (MCP) クライアントを通じて高度な操作も可能です。MCPは、JSON-RPCベースの標準化されたインターフェースを提供し、より効率的なモデル生成と操作を可能にします。

### 5.1 MCPの主な利点

- JSON-RPCベースの標準化されたインターフェース
- 効率的なモデル生成と操作
- 言語に依存しないアクセス（Python、JavaScriptなど）
- Webアプリケーションとの容易な統合
- カスタムコマンドによる拡張性

### 5.2 MCPクライアントの基本使用法

```python
import asyncio
from mcp_client import MCPClient

async def main():
    client = MCPClient(server_url="http://localhost:3000")
    
    try:
        await client.initialize()
        
        # 壁の作成
        await client.create_wall(
            start=[0, 0, 0],
            end=[5000, 0, 0],
            name="Wall_Front"
        )
        
        # モデルのエクスポート
        await client.export_model(
            file_path="house_model.fcstd",
            format="fcstd"
        )
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### 5.3 主なMCPコマンド

| コマンド | 説明 | パラメータ |
|---------|------|----------|
| `initialize` | MCPセッションを初期化します | なし |
| `create_box` | ボックスを作成します | width, length, height, position, name |
| `create_wall` | 壁を作成します | start, end, height, thickness, name |
| `export_model` | モデルをエクスポートします | file_path, format |
| `close` | MCPセッションを閉じます | なし |

## 6. エラー処理

### 6.1 エラーレスポンス形式

```json
{
  "error": "エラーメッセージ",
  "trace": "エラートレース（デバッグモードの場合のみ）"
}
```

### 6.2 一般的なエラーコード

| HTTPコード | 説明 |
|-----------|------|
| 400 | 不正なリクエスト（パラメータエラー） |
| 404 | リソースが見つかりません |
| 500 | サーバーエラー |

### 6.3 エラーハンドリングのベストプラクティス

- すべてのAPIレスポンスでステータスコードとエラーメッセージを確認してください
- 一時的なエラーの場合は、指数バックオフを使用したリトライを実装してください
- 大きなモデルを処理する場合は、タイムアウトを考慮してください

## 7. クライアント実装例

### 7.1 Python実装例

```python
import requests
import json

API_URL = "https://freecad-api-513507930971.asia-northeast1.run.app"

def generate_basic_model(width, length, height, parameters=None):
    """
    基本的な3Dモデルを生成する関数
    
    Args:
        width (float): モデルの幅（メートル）
        length (float): モデルの長さ（メートル）
        height (float): モデルの高さ（メートル）
        parameters (dict, optional): 追加のパラメータ
        
    Returns:
        dict: APIレスポンス
    """
    if parameters is None:
        parameters = {}
    
    response = requests.post(
        f"{API_URL}/generate",
        json={
            "width": width,
            "length": length,
            "height": height,
            "parameters": parameters
        }
    )
    return response.json()

def process_grid_data(rooms, walls, wall_thickness=0.12, include_furniture=True):
    """
    グリッドデータから3Dモデルを生成する関数
    
    Args:
        rooms (list): 部屋の配列
        walls (list): 壁の配列
        wall_thickness (float, optional): 壁の厚さ（メートル）
        include_furniture (bool, optional): 家具を含めるかどうか
        
    Returns:
        dict: APIレスポンス
    """
    response = requests.post(
        f"{API_URL}/process/grid",
        json={
            "rooms": rooms,
            "walls": walls,
            "wall_thickness": wall_thickness,
            "include_furniture": include_furniture
        }
    )
    return response.json()
```

### 7.2 cURL実装例

```bash
# 基本的な3Dモデルを生成
curl -X POST \
  https://freecad-api-513507930971.asia-northeast1.run.app/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "width": 10.0,
    "length": 15.0,
    "height": 3.0,
    "parameters": {
      "wall_thickness": 0.12,
      "window_size": 1.5,
      "include_furniture": true
    }
  }'

# グリッドデータから3Dモデルを生成
curl -X POST \
  https://freecad-api-513507930971.asia-northeast1.run.app/process/grid \
  -H 'Content-Type: application/json' \
  -d '{
    "rooms": [
      {
        "id": 1,
        "dimensions": [5.0, 4.0],
        "position": [0.0, 0.0],
        "label": "LDK"
      }
    ],
    "walls": [
      {
        "start": [0.0, 0.0],
        "end": [5.0, 0.0],
        "height": 2.9,
        "floor": 1
      }
    ],
    "wall_thickness": 0.12,
    "include_furniture": true
  }'
```

## 8. 制限事項と考慮点

### 8.1 リクエスト制限

| 項目 | 制限値 | 説明 |
|------|-------|------|
| リクエストサイズ | 最大32MB | リクエストボディの合計サイズ |
| タイムアウト | 900秒（15分） | 処理が完了しない場合はタイムアウトエラー |
| 同時リクエスト数 | Cloud Runの設定による | 同時に処理できるリクエスト数 |

### 8.2 リソース制限

| 項目 | 制限値 | 説明 |
|------|-------|------|
| メモリ | 2Gi | 処理に使用できる最大メモリ |
| CPU | 2 | 処理に使用できるCPUコア数 |
| ディスク | 一時ストレージのみ | 永続的なストレージはCloud Storageを使用 |

### 8.3 出力形式制限

| 形式 | 拡張子 | 最大サイズ | 説明 |
|------|-------|----------|------|
| FCStd | .fcstd | 100MB | FreeCADネイティブ形式 |
| STEP | .step | 100MB | 標準的な3D CAD交換形式 |
| STL | .stl | 100MB | 3Dプリント用メッシュ形式 |
| glTF | .gltf | 100MB | Web向け3D形式 |
| PDF | .pdf | 50MB | 図面出力形式 |

## 9. ベストプラクティス

### 9.1 データ準備のベストプラクティス

- **単位の一貫性**: すべての寸法はメートル単位で指定してください（例: 0.12mは120mm）
- **壁の厚さ**: 現実的な壁の厚さを設定してください（通常0.12m〜0.3m）
- **建築基準法の遵守**: 日本の建築基準法に準拠した寸法を使用してください（最小部屋面積4.5m²など）

### 9.2 パフォーマンス最適化のベストプラクティス

- **モデルの複雑さ**: 不必要に複雑なモデルは避け、処理時間を短縮してください
- **バッチ処理**: 多数のモデルを生成する場合は、バッチ処理を検討してください
- **キャッシュの活用**: 同一パラメータでの再計算を避けるため、結果をキャッシュしてください

### 9.3 セキュリティのベストプラクティス

- **入力検証**: すべての入力データを検証し、不正な値を拒否してください
- **認証**: 本番環境では適切な認証を実装してください
- **ファイルアクセス制限**: 生成されたファイルへのアクセスを制限してください

## 10. 今後のロードマップ

### 10.1 機能拡張予定

- **マルチスレッド処理**: 複雑なモデル生成の高速化
- **バッチ処理API**: 複数モデルの一括生成機能
- **新出力形式**: IFC、DXF、OBJ形式のサポート追加

### 10.2 パフォーマンス改善計画

- **処理速度**: アルゴリズム最適化による処理速度50%向上
- **メモリ使用量**: 大規模モデル処理時のメモリ使用量30%削減
- **スケーリング**: 自動スケーリングによる負荷分散機能

## 11. よくある質問（FAQ）

### 11.1 一般的な質問

**Q: APIの使用に料金はかかりますか？**  
A: 現在、APIは内部利用のみを想定しており、料金は発生しません。将来的に外部公開する場合は、利用規約を確認してください。

**Q: どのファイル形式がサポートされていますか？**  
A: 現在、FCStd（FreeCADネイティブ）、STEP、STL、glTF形式をサポートしています。将来的にIFCやDXF形式も追加予定です。

**Q: APIのレート制限はありますか？**  
A: 現在、明示的なレート制限は設けていませんが、リソース使用量に基づく暗黙的な制限があります。大量のリクエストを送信する場合は、事前にご相談ください。

### 11.2 技術的な質問

**Q: 大規模なモデルを処理する場合、どのような制限がありますか？**  
A: Cloud Runの制限により、処理時間は最大15分、メモリは2GiBに制限されています。大規模なモデルの場合は、分割して処理することをお勧めします。

**Q: カスタムスクリプトを実行できますか？**  
A: 現在、カスタムスクリプトの実行はサポートしていません。将来的にはMCPを通じて限定的なスクリプト実行をサポートする予定です。

**Q: オフラインでAPIを使用できますか？**  
A: 現在、APIはクラウドベースのみで提供しています。オフライン使用が必要な場合は、FreeCADをローカルにインストールして直接使用することをお勧めします。

## 12. サポートとフィードバック

APIの使用に関する質問やフィードバックは、以下の方法でお寄せください：

- GitHub Issues: [https://github.com/terisuke/house-design-ai/issues](https://github.com/terisuke/house-design-ai/issues)
- メール: support@example.com（サンプル）

## 13. 実装状況 (2025-05-11更新)

FreeCAD APIのCloud Run実装は成功しています。以下のテスト結果が確認されています：

```
python scripts/test_freecad_api.py
```

のテスト結果：
```
✅ FreeCAD APIテスト成功
レスポンス: {
  "status": "success",
  "message": "モデルを生成しました",
  "file": "/tmp/model.fcstd",
  "storage_url": "https://storage.googleapis.com/house-design-ai-data/models/uuid.fcstd"
}
```

FreeCADをCloud Runでデプロイし、FCStdモデルでのストレージ保存まで完了しています。現在、すべてのAPIエンドポイントが正常に動作しており、本番環境で使用可能です。
