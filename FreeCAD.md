# FreeCAD API 統合ガイド

## 概要

House Design AIは、FreeCADのPython APIを直接使用して3Dモデルを生成および操作します。
このドキュメントでは、FreeCAD APIの使用方法と統合方法について説明します。

## FreeCAD Python API

FreeCADはPython APIを提供しており、Python経由で3Dモデリング機能にアクセスできます。
House Design AIでは、次のモジュールを使用しています：

- FreeCAD: コアモジュール
- Part: パート操作用モジュール
- Mesh: メッシュ操作用モジュール
- MeshPart: パートからメッシュへの変換用モジュール
- TechDraw: 図面生成用モジュール

## API実装

FreeCAD APIは以下のように実装されています：

1. 直接Python API呼び出し:
   - 3Dモデル生成
   - STLへの変換
   - 図面生成

2. STLからglTFへの変換:
   - trimeshライブラリを使用してSTLをglTFに変換

## 主要エンドポイント

- `/process/grid`: グリッドデータを処理して3Dモデルを生成
- `/convert/3d`: FCStdファイルをSTL形式に変換
- `/convert/stl-to-gltf`: STLファイルをglTF形式に変換
- `/process/drawing`: 3DモデルからCAD図面を生成
- `/generate/model`: 指定されたパラメータに基づいて建物の3Dモデルを生成

## 依存関係

- FreeCAD 0.20以上
- trimesh（STL→glTF変換用）
- その他の依存関係はrequirements-freecad-api.txtに記載

## エラーハンドリング

FreeCAD APIはエラーハンドリングを強化し、詳細なエラートレースを提供します。
DEBUGモードが有効な場合は、完全なトレースが返されます。
