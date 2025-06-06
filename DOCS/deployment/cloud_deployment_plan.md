# House Design AI: GoogleCloud構築計画

## 概要

このドキュメントは、House Design AIプロジェクトのGoogleCloud環境への構築計画を詳細に説明します。FreeCADとの統合を目的とし、Terraform管理も実装済みの設計となっています。

## 目次

1. [全体アーキテクチャ](#1-全体アーキテクチャ)
2. [主要コンポーネント](#2-主要コンポーネント)
3. [実装状況](#3-実装状況)
4. [CI/CDパイプライン](#4-cicd-パイプライン)
5. [Terraform実装](#5-terraform-実装)
6. [実装ロードマップ](#6-実装ロードマップ)
7. [予算と運用コスト見積もり](#7-予算と運用コスト見積もり)
8. [結論と次のステップ](#8-結論と次のステップ)

## 1. 全体アーキテクチャ

```
[ユーザー] → [Cloud Run: Streamlit WebUI]
                      ↑↓
         ┌───────────┴┬───────────┐
         ↓            ↓           ↓
[Cloud Run: FreeCAD API] ← [Vertex AI モデル] → [Cloud Storage]
         ↑                      ↑
         └─────────────┬────────┘
                       ↓
               [Artifact Registry]
```

### 1.1 システムコンポーネント間の通信フロー

1. ユーザーはStreamlit WebUIを通じて画像をアップロード
2. Streamlitアプリは画像をVertex AIモデルに送信
3. モデルは建物セグメンテーションとグリッド生成を実行
4. 結果はFreeCAD APIに送信され、3Dモデルを生成
5. 生成されたモデルはCloud Storageに保存
6. ユーザーは生成されたモデルをダウンロード可能

## 2. 主要コンポーネント

### 2.1 アプリケーションサービス

| サービス                    | 目的         | 技術スタック                               | 実装状況  |
|-------------------------|--------------|----------------------------------------|--------|
| **Streamlit WebUI**     | ユーザーインターフェース | Cloud Run, Streamlit, Python           | ✅ 実装済み |
| **FreeCAD API Service** | CAD処理機能  | Cloud Run, FreeCAD Python API, FastAPI | ✅ 実装済み |
| **ML Model Service**    | YOLO推論処理 | Vertex AI, YOLOv11                     | 🟡 進行中 |

### 2.2 データストレージ

| サービス                   | 目的         | データタイプ             | 実装状況  |
|------------------------|--------------|--------------------|--------|
| **Cloud Storage**      | 永続データ保存  | 画像、CADモデル、ML結果 | ✅ 実装済み |
| **Firebase/Firestore** | ユーザーデータ、設定 | JSON, メタデータ        | 🟡 進行中 |
| **Artifact Registry**  | コンテナイメージ     | Docker images      | ✅ 実装済み |

## 3. 実装状況

### 3.1 実装済みコンポーネント

#### 3.1.1 Streamlit WebUI
- ✅ マルチページアプリケーション構造
- ✅ 画像アップロード機能
- ✅ 建物セグメンテーション結果の表示
- ✅ FreeCAD APIとの連携
- ✅ Cloud Storage連携

#### 3.1.2 FreeCAD API Service
- ✅ FastAPIベースのRESTful API
- ✅ グリッドデータ処理エンドポイント
- ✅ 3Dモデル生成機能
- ✅ Cloud Storage連携
- ✅ Dockerコンテナ化
- ✅ Cloud Runへのデプロイ
  - サービスURL: https://freecad-api-513507930971.asia-northeast1.run.app
  - 設定: メモリ2GB、CPU 2、タイムアウト300秒

#### 3.1.3 Terraform
- ✅ モジュール化されたインフラストラクチャ
- ✅ 環境別（dev/prod）設定
- ✅ Cloud Run設定
- ✅ Cloud Storage設定
- ✅ Artifact Registry設定

### 3.2 進行中のコンポーネント

#### 3.2.1 ML Model Service
- 🟡 Vertex AIエンドポイントのセットアップ
- 🟡 モデルの最適化
- 🟡 推論パイプラインの構築

#### 3.2.2 Firebase/Firestore
- 🟡 ユーザー認証
- 🟡 データモデル設計
- 🟡 セキュリティルール設定

#### 3.2.3 運用管理
- 🟡 Cloud Loggingの設定
- 🟡 Cloud Monitoringのメトリクス設定
- 🟡 APIドキュメント（Swagger UI）の整備
- 🟡 エラーハンドリングの強化

## 4. CI/CD パイプライン

### 4.1 実装済みのCI/CD機能

- ✅ Cloud Build設定
- ✅ 自動ビルド・デプロイ
- ✅ 環境別デプロイメント
- ✅ イメージの自動プッシュ

### 4.2 進行中のCI/CD機能

- 🟡 テスト自動化
- 🟡 品質ゲート
- 🟡 ロールバック機能

## 5. Terraform実装

### 5.1 実装済みモジュール

- ✅ Cloud Run
- ✅ Cloud Storage
- ✅ Artifact Registry
- ✅ IAM設定

### 5.2 進行中のモジュール

- 🟡 Vertex AI
- 🟡 Firebase/Firestore
- 🟡 モニタリング設定

## 6. 実装ロードマップ

### フェーズ1: 基本インフラストラクチャのセットアップ（✅ 完了）

1. ✅ Google Cloud プロジェクト作成
2. ✅ 必要なAPIの有効化
3. ✅ ストレージバケットと権限の設定
4. ✅ Artifactリポジトリの設定

### フェーズ2: FreeCAD APIサービスの開発（✅ 完了）

1. ✅ FreeCAD Python APIを使用した処理モジュール開発
2. ✅ FastAPIベースのRESTfulエンドポイント実装
3. ✅ Dockerイメージのビルドとテスト
   ```bash
   # FreeCAD APIイメージのビルド
   cd freecad_api
   docker build -t asia-northeast1-docker.pkg.dev/yolov8environment/house-design-ai/freecad-api:latest -f Dockerfile.freecad .
   
   # Artifact Registryへのプッシュ
   docker push asia-northeast1-docker.pkg.dev/yolov8environment/house-design-ai/freecad-api:latest
   ```
4. ✅ Cloud Runへのデプロイ
   - メモリ: 2GB
   - CPU: 2
   - タイムアウト: 300秒
   - 環境変数:
     - `PYTHONPATH`: `/usr/lib/freecad/lib`
     - `QT_QPA_PLATFORM`: `offscreen`

### フェーズ3: Streamlitアプリの拡張とクラウド対応（✅ 完了）

1. ✅ Cloud Runに対応するStreamlitアプリの修正
2. ✅ FreeCAD APIとの連携実装
3. ✅ Cloud Storage連携の強化
4. ✅ UIの改良とユーザーフローの最適化

### フェーズ4: Vertex AIモデルの最適化と統合（🟡 進行中）

1. 🟡 Vertex AIエンドポイントのセットアップ
2. 🟡 推論結果をFreeCAD形式に変換する機能
3. 🟡 エンドツーエンドのパイプラインテスト

### フェーズ5: Terraform対応（✅ 完了）

1. ✅ 現状環境のTerraform IaCへの移行
2. ✅ モジュール化とベストプラクティスの適用
3. ✅ CI/CDパイプラインの整備

### フェーズ6: 運用管理の強化（🟡 進行中）

1. 🟡 Cloud Loggingの設定
2. 🟡 Cloud Monitoringのメトリクス設定
3. 🟡 APIドキュメントの整備
4. 🟡 エラーハンドリングの強化

## 7. 予算と運用コスト見積もり

| コンポーネント                 | 想定使用量                        | 月額概算 (USD) | 実装状況 |
|-------------------------|-----------------------------------|----------------|----------|
| Cloud Run (Streamlit)   | 1インスタンス、1 CPU、1GB RAM、月間150時間 | $15-25         | ✅        |
| Cloud Run (FreeCAD API) | オンデマンド、2 CPU、2GB RAM              | $20-40         | ✅        |
| Cloud Storage           | 10GB データ + 1000操作/月            | $1-3           | ✅        |
| Vertex AI               | 推論エンドポイント、小規模モデル             | $40-80         | 🟡       |
| Artifact Registry       | 5GB ストレージ                         | $1-2           | ✅        |
| Cloud Build             | 120ビルド分/月                       | $0-5           | ✅        |
| **合計**                |                                   | **$77-155**    |          |

## 8. 結論と次のステップ

このGoogleCloud構築計画は、House Design AIプロジェクトのクラウドネイティブな環境への移行とFreeCAD統合を実現するための包括的なロードマップです。Terraformによるインフラストラクチャのコード化も完了しており、高い拡張性と保守性を確保しています。

### 次のステップ

1. **運用管理の強化（1-2週間）**
   - Cloud Loggingの設定
   - Cloud Monitoringのメトリクス設定
   - APIドキュメントの整備
   - エラーハンドリングの強化

2. **Vertex AI統合の完了（2週間）**
   - モデルの最適化
   - エンドポイントのセットアップ
   - パイプラインのテスト

3. **Firebase/Firestore実装（1週間）**
   - ユーザー認証の実装
   - データモデルの設計
   - セキュリティルールの設定

### 期待される効果

1. **アーキテクチャ依存の問題解消** ✅
   - M1 Macなどのアーキテクチャに依存しない環境の実現
   - 一貫した開発・運用環境の提供

2. **スケーラビリティの向上** ✅
   - オンデマンドでのリソース拡張
   - 負荷に応じた柔軟な対応

3. **保守性の向上** ✅
   - インフラストラクチャのコード化
   - 標準化されたデプロイメントプロセス

4. **開発効率の向上** 🟡
   - CI/CDパイプラインの自動化
   - 迅速なフィードバックループ  