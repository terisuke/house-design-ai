# 3Dモデルビューアー実装計画

## 概要
FreeCAD APIを使用して生成されたFCStdファイルをWebブラウザ上で表示可能な形式に変換し、3Dモデルビューアーで表示する機能を実装します。

## 実装ステップ

### 1. FreeCAD APIの拡張
- `/convert/3d`エンドポイントの実装
  - 入力: FCStdファイル
  - 出力: glTF形式のファイル
  - 処理: FreeCADのPython APIを使用してFCStdからglTFへの変換を実行

### 2. フロントエンド（Streamlit）の実装
- 3Dモデル生成ボタンの下にキャンバスを追加
- モデル生成成功時に自動的に3Dビューアーを表示
- エラーハンドリングとローディング表示の実装

### 3. テスト環境
- Cloud RunにデプロイされたFreeCAD APIを使用
- テスト用のエンドポイント: `https://freecad-api-513507930971.asia-northeast1.run.app`

## 実装詳細

### FreeCAD APIの実装
```python
@app.post("/convert/3d")
async def convert_to_gltf(file: UploadFile):
    try:
        # 一時ファイルとして保存
        with tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_fcstd_path = temp_file.name

        # FreeCADでglTFに変換
        import FreeCAD
        doc = FreeCAD.open(temp_fcstd_path)
        gltf_path = temp_fcstd_path.replace(".fcstd", ".gltf")
        doc.export(gltf_path)

        # GCSにアップロード
        storage_client = storage.Client()
        bucket = storage_client.bucket("house-design-ai-data")
        blob = bucket.blob(f"models/{os.path.basename(gltf_path)}")
        blob.upload_from_filename(gltf_path)

        # 一時ファイルの削除
        os.unlink(temp_fcstd_path)
        os.unlink(gltf_path)

        return {
            "status": "success",
            "url": f"gs://house-design-ai-data/models/{os.path.basename(gltf_path)}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Streamlitの実装
```python
# 3Dモデル生成ボタンの下に追加
if st.button("3Dモデルを生成", key="generate_3d_model"):
    with st.spinner("3Dモデルを生成中..."):
        try:
            # 既存のモデル生成処理
            response = requests.post(
                f"{freecad_api_url}/generate",
                json=grid_data_obj,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            response.raise_for_status()
            cad_model_result = response.json()

            if "storage_url" in cad_model_result:
                # FCStdファイルをglTFに変換
                fcstd_url = cad_model_result["storage_url"]
                with tempfile.NamedTemporaryFile(suffix=".fcstd", delete=False) as temp_file:
                    storage_client = storage.Client()
                    bucket = storage_client.bucket("house-design-ai-data")
                    blob = bucket.blob(fcstd_url.replace("gs://house-design-ai-data/", ""))
                    blob.download_to_filename(temp_file.name)
                    
                    # 変換リクエスト
                    files = {'file': ('model.fcstd', open(temp_file.name, 'rb'))}
                    convert_response = requests.post(
                        f"{freecad_api_url}/convert/3d",
                        files=files,
                        timeout=180
                    )
                    convert_response.raise_for_status()
                    gltf_result = convert_response.json()

                    if "url" in gltf_result:
                        st.session_state.gltf_url = gltf_result["url"]
                        st.success("3Dモデルの生成と変換に成功しました")
                        
                        # 3Dビューアーの表示
                        components.html(f'''
                        <model-viewer src="{gltf_result['url']}" alt="3D model" auto-rotate camera-controls 
                            style="width: 100%; height: 500px;" shadow-intensity="1" 
                            environment-image="neutral" exposure="0.5" camera-orbit="45deg 60deg 3m">
                        </model-viewer>
                        <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
                        ''', height=520)
                    else:
                        st.error("3Dモデルの変換に失敗しました")
            else:
                st.error("3Dモデルの生成に失敗しました")
        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")
```

## テスト計画
1. ローカル環境でのテスト
   - FreeCAD APIの`/convert/3d`エンドポイントの動作確認
   - 変換処理の正確性確認
   - エラーハンドリングの確認

2. Cloud Run環境でのテスト
   - デプロイ後のエンドポイントの動作確認
   - 変換処理のパフォーマンス確認
   - エラーハンドリングの確認

## STLからglTFへの変換

3Dモデルをウェブブラウザで表示するために、STLファイルをglTF形式に変換できます。
この変換はFreeCAD APIの新しいエンドポイント `/convert/stl-to-gltf` を使用して行われます。

### 変換方法

```python
# STLファイルをglTFに変換するコード例
import requests
import os

def convert_stl_to_gltf(stl_file_path, api_url="https://freecad-api-513507930971.asia-northeast1.run.app"):
    """STLファイルをglTF形式に変換する"""
    
    with open(stl_file_path, 'rb') as f:
        files = {'file': (os.path.basename(stl_file_path), f, 'application/octet-stream')}
        response = requests.post(f"{api_url}/convert/stl-to-gltf", files=files)
    
    if response.status_code == 200:
        return response.json()["url"]
    else:
        raise Exception(f"Error: {response.json()['error']}")
```

### 注意点

- glTF形式はウェブブラウザでのレンダリングに最適化されています
- 変換後のURLはCloud Storageの一時URLであり、有効期限があります

## 注意点
- FreeCADのPython APIの依存関係の管理
- 一時ファイルの適切な削除
- エラーハンドリングの徹底
- パフォーマンスの最適化（特に大きなモデルの変換時）
### セキュリティ考慮事項
  
- **ファイルサイズ制限**: アップロードされるファイルサイズを10MB以下に制限し、DoS攻撃を防止
- **認証要件**: すべてのAPI呼び出しに有効なセッショントークンを要求
- **入力検証**: すべてのユーザー入力に対して厳格な検証を実施
  - サポートされるファイル形式のみを許可（.obj, .stl, .step, .stp）
  - ファイル拡張子とMIMEタイプの両方を検証
  - ファイル内容のマジックバイトチェックによる追加検証
- **一時ファイル管理**: 
  - 一時ファイルに一意のランダム名を使用
  - 処理完了後の確実な削除
  - ファイルハンドルのリークを防ぐcontext managerの使用
- **クロスサイトスクリプティング(XSS)対策**: 
  - 出力エンコーディングの適用
  - Content-Security-Policy headerの設定
- **脆弱性対策**:
  - 依存関係の定期的な更新
  - OWASP Top 10脆弱性に対する対策
  - 定期的なセキュリティスキャンの実施
- **アクセス制御**:
  - 最小権限の原則に基づくリソースアクセス
  - APIエンドポイントごとの詳細なアクセス制御    