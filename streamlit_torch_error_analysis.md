# Streamlit × PyTorch '__path__._path' エラー分析・対策まとめ

## エラー内容

```
Traceback (most recent call last):
  File "/opt/homebrew/lib/python3.11/site-packages/streamlit/watcher/local_sources_watcher.py", line 217, in get_module_paths
    potential_paths = extract_paths(module)
                      ^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/lib/python3.11/site-packages/streamlit/watcher/local_sources_watcher.py", line 210, in <lambda>
    lambda m: list(m.__path__._path),
                   ^^^^^^^^^^^^^^^^
  File "/opt/homebrew/lib/python3.11/site-packages/torch/_classes.py", line 13, in __getattr__
    proxy = torch._C._get_custom_class_python_wrapper(self.name, attr)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
RuntimeError: Tried to instantiate class '__path__._path', but it does not exist! Ensure that it is registered via torch::class_
```

---

## 主な原因

1. **依存関係の問題だけでなく、ディレクトリ構造やコードの問題も絡むことが多い**
2. **ディレクトリ名やファイル名がPyTorchの内部クラス名や予約語と衝突している**
   - 例: `torch`や`vision`などの名前のディレクトリやファイルがプロジェクト内に存在
3. **importパスの誤りや多重import**
   - sys.pathの操作や、同名のモジュールが複数パスに存在
4. **Streamlitのホットリロード機能とPyTorchのカスタムクラスの相性問題**
   - Streamlitのファイル監視がPyTorchの特殊なクラスを誤って監視しようとする

---

## チェックリスト・推奨アクション

1. **プロジェクト直下やPYTHONPATH上に `torch` や `vision` という名前のディレクトリ・ファイルがないか確認**
2. **sys.pathの操作や、importの重複がないか確認**
3. **Streamlitの`--server.runOnSave false`オプションでホットリロードを無効化してみる**
   - 例:  
     ```sh
     PYTHONPATH=. streamlit run house_design_app/main.py --server.runOnSave false
     ```
4. **それでも解決しない場合は、sys.pathの操作やimport構造を再点検**

---

## 備考
- ultralytics==8.3.81 などの「実績のあるrequirements.txt」を使い、pipに依存解決を任せるのが基本方針
- 依存関係の問題だけでなく、**ディレクトリ・ファイル名やimport構造の見直しも重要** 