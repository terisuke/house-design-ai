# House Design AI ドキュメント

## 最終更新日: 2025年5月11日

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

## 実装状況 (2025-05-11更新)

- ✅ FreeCAD APIのCloud Runデプロイ成功
- ✅ Streamlitアプリケーションの実行確認
- ✅ StreamlitアプリケーションのCloud Runデプロイ完了
- ✅ Cloud StorageでのFCStdモデル保存
- ✅ PyTorchとStreamlitの互換性問題の解決
- ✅ Terraformによるインフラストラクチャのコード化完了
- ✅ CP-SAT最小PoCの実装（3LDK基本レイアウト生成）
- ✅ 建築基準法制約の基本実装（セットバック、最小部屋サイズ）
- ✅ 単位の統一（mm）

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
FreeCAD MCPを使用した効率的なCAD操作の例は[こちら](../freecad_api/examples/mcp_client.py)を参照してください。

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

詳細については、[プロジェクトロードマップ](roadmap/roadmap.md)を参照してください。
