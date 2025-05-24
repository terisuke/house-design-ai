# House Design AI ドキュメント

## 最終更新日: 2025年5月24日

## ドキュメント構造

### [アーキテクチャ](architecture/)
- [FreeCAD統合ガイド](architecture/freecad_integration.md): FreeCADの統合方法と実装状況
- [間取り生成プラン分析](architecture/plan_analysis.md): 間取り生成システムの実装プラン分析と選定
- [YOLOアノテーション変換システム](architecture/yolo_to_vector_conversion.md): YOLOアノテーションからベクター/グラフJSONへの変換システム
- [CP-SAT間取り生成システム](architecture/cp_sat_layout_generation.md): CP-SATを使用した3LDK間取り生成システム

### [デプロイメント](deployment/)
- [クラウドデプロイメント計画](deployment/cloud_deployment_plan.md): GCPへのデプロイメント計画
- [GCPデプロイメントガイド](deployment/gcp_deployment_guide.md): GCPへのデプロイ手順

### [開発](development/)
- [貢献ガイド](development/contributing.md): プロジェクトへの貢献方法
- [実装計画](development/implementation_plan.md): システム実装計画

### [ロードマップ](roadmap/)
- [プロジェクトロードマップ](roadmap/roadmap.md): 短期・中期・長期の開発計画
- [詳細ロードマップ](roadmap/detailed_roadmap.md): より詳細な開発ロードマップ

## 実装状況 (2025-05-24更新)

- ✅ FreeCAD APIのCloud Runデプロイ成功
- ✅ Streamlitアプリケーションの実行確認
- ✅ StreamlitアプリケーションのCloud Runデプロイ完了
- ✅ Cloud StorageでのFCStdモデル保存
- ✅ PyTorchとStreamlitの互換性問題の解決
- ✅ Terraformによるインフラストラクチャのコード化完了
- ✅ CP-SAT最小PoCの実装（3LDK基本レイアウト生成）
- ✅ 建築基準法制約の基本実装（セットバック、最小部屋サイズ）
- ✅ 910mmグリッド + 採光条件 + 階段寸法の基本制約実装
- ✅ 単位の統一（m）
- ✅ ロゴ表示とモデルロード問題の修正
- ✅ デプロイスクリプトの最適化
- ✅ データセット分割・GCSアップロードスクリプトの実装（7:3分割）

## 依存関係管理

本プロジェクトでは依存関係の競合（特にprotobufのバージョン）を解決するために、以下の3つの分離された依存関係ファイルを使用しています：

- `requirements-base.txt`: 基本的なパッケージ（ultralytics, streamlit, テスト・開発ツールなど）
- `requirements-gcp.txt`: Google Cloud関連のパッケージ（google-cloud-storage, google-cloud-aiplatform等）
- `requirements-ortools.txt`: 最適化関連のパッケージ（ortools等）

これらのファイルは、異なる仮想環境で使用することで、依存関係の競合を回避しています。詳細は[README](../README.md)の「依存関係の競合について」セクションを参照してください。

## FreeCAD API実装の詳細

FreeCAD APIは以下のエンドポイントで利用可能です：
```
https://freecad-api-513507930971.asia-northeast1.run.app
```

APIテスト結果：
```
✅ FreeCAD APIテスト成功
レスポンス: {
  "status": "success",
  "message": "モデルを生成しました",
  "file": "/tmp/model.FCStd",
  "storage_url": "<gs://house-design-ai-data/models/model.FCStd>"
}
```

### デフォルト設定値
FreeCAD APIでは以下のデフォルト値を使用しています：
- 壁の厚さ: 120mm (0.12m)
- 一階の壁の高さ: 2900mm (2.9m)
- 二階の壁の高さ: 2800mm (2.8m)

詳細なAPIドキュメントは[こちら](../freecad_api/docs/api_documentation.md)を参照してください。

### Model Context Protocol (MCP)統合

Model Context Protocol (MCP)は、大規模言語モデルと外部ツールを統合するためのオープンスタンダードプロトコルです。MCPを実装することで、AIアシスタントがCAD操作を理解し、実行できるようになります。

FreeCAD MCPはこのプロトコルを実装し、AI支援によるCAD操作を可能にします。これにより、自然言語による3Dモデリング指示が実現し、設計プロセスが大幅に効率化されます。

詳細は [examples/mcp_example.py](../freecad_api/examples/mcp_client.py) を参照してください。

## Streamlit実行方法

Streamlitアプリケーションは以下のコマンドで実行できます：
```bash
PYTHONPATH=. streamlit run house_design_app/main.py
```

デプロイ済みStreamlitアプリケーションは以下のURLで利用可能です：
```
https://streamlit-web-513507930971.asia-northeast1.run.app
```

## 今後の開発計画

- FreeCAD APIの完全実装
- HouseDiffusionモデルの実装と訓練
- Vertex AI統合の実装
- セグメンテーション精度の向上
- 建築基準法チェック機能の実装
- Terraformによるデプロイプロセスの完全自動化
- マルチリージョンデプロイメントの実装
- データセット管理システムの拡張

詳細については、[プロジェクトロードマップ](roadmap/roadmap.md)を参照してください。
