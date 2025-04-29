# FreeCAD API サンプルコード

このディレクトリには、FreeCAD APIを使用して3Dモデルを生成するためのサンプルコードが含まれています。

## ファイル構成

- `python_client.py`: Pythonクライアントの実装例（同期・非同期）
- `curl_examples.sh`: curlコマンドを使用した例
- `requirements-examples.txt`: Pythonクライアントの依存関係

## セットアップ

1. 仮想環境を作成してアクティベート:
```bash
python -m venv venv
source venv/bin/activate  # Unix/macOS
# または
.\venv\Scripts\activate  # Windows
```

2. 依存関係をインストール:
```bash
pip install -r requirements-examples.txt
```

## 使用方法

### Pythonクライアント

```bash
# APIのURLを環境変数で設定（オプション）
export API_URL="https://freecad-api-513507930971.asia-northeast1.run.app"

# スクリプトを実行
python python_client.py
```

### curlコマンド

```bash
# 実行権限を付与
chmod +x curl_examples.sh

# スクリプトを実行
./curl_examples.sh
```

## APIエンドポイント

1. ヘルスチェック
   - エンドポイント: `/health`
   - メソッド: GET

2. 3Dモデル生成
   - エンドポイント: `/generate`
   - メソッド: POST
   - パラメータ:
     - width: 建物の幅（1.0m ～ 100.0m）
     - length: 建物の長さ（1.0m ～ 100.0m）
     - height: 建物の高さ（2.0m ～ 50.0m）
     - parameters:
       - wall_thickness: 壁の厚さ（0.1m ～ 1.0m）
       - window_size: 窓のサイズ（0.5m ～ 3.0m）

## レスポンス例

```json
{
  "status": "success",
  "message": "モデルを生成しました",
  "file": "/tmp/model.FCStd",
  "storage_url": "gs://bucket-name/models/model.FCStd"
}
```

## エラーハンドリング

サンプルコードには以下のエラーハンドリングが含まれています：

1. APIの接続エラー
2. 無効なパラメータ
3. サーバーエラー

エラーが発生した場合は、適切なエラーメッセージが表示されます。 