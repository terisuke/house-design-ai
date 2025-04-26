# 土地図からの一軒家CAD図自動生成システム システム構造図

## システム全体構成

```mermaid
graph TB
    subgraph "ユーザーインターフェース層"
        A[Streamlit Webアプリケーション]
        B[Google Forms]
        C[Google Drive]
    end

    subgraph "分析処理層"
        D[YOLOv11 セグメンテーション]
        E[建物形状解析]
        F[間取り生成]
        G[建築基準法チェック]
    end

    subgraph "CAD生成層"
        H[FreeCAD API]
        I[図面生成エンジン]
        J[建具記号ライブラリ]
    end

    subgraph "データストレージ層"
        K[Google Cloud Storage]
        L[Vertex AI]
        M[Cloud SQL]
    end

    subgraph "管理・監視層"
        N[Cloud Monitoring]
        O[Cloud Logging]
        P[Cloud Trace]
    end

    A --> D
    B --> A
    C --> A
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
    I --> J
    D --> L
    E --> L
    F --> L
    G --> L
    H --> K
    I --> K
    J --> K
    A --> N
    D --> O
    E --> O
    F --> O
    G --> O
    H --> P
    I --> P
```

## コンポーネント詳細

### 1. ユーザーインターフェース層
- **Streamlit Webアプリケーション**
  - Cloud Run上で動作
  - ユーザー認証・認可
  - インタラクティブなUI
  - リアルタイムフィードバック
- **Google Forms/Drive連携**
  - データ入力フォーム
  - ファイル管理
  - 自動データ同期

### 2. 分析処理層
- **YOLOv8 セグメンテーション**
  - Vertex AI上で動作
  - 高精度な建物検出
  - リアルタイム処理
- **建物形状解析**
  - 建築可能エリアの特定
  - 形状最適化
  - 制約条件の適用
- **間取り生成**
  - 自動レイアウト生成
  - 最適化アルゴリズム
  - カスタマイズオプション
- **建築基準法チェック**
  - 建蔽率・容積率チェック
  - 日影規制チェック
  - 高さ制限チェック

### 3. CAD生成層
- **FreeCAD API**
  - Cloud Run上で動作
  - ヘッドレスモード
  - 高性能な3D処理
- **図面生成エンジン**
  - 自動図面生成
  - レイヤー管理
  - 寸法線生成
- **建具記号ライブラリ**
  - 標準記号セット
  - カスタム記号対応
  - バージョン管理

### 4. データストレージ層
- **Google Cloud Storage**
  - モデルファイル
  - 生成された図面
  - 一時データ
- **Vertex AI**
  - モデルトレーニング
  - 推論エンドポイント
  - モデル管理
- **Cloud SQL**
  - ユーザーデータ
  - プロジェクト管理
  - 設定情報

### 5. 管理・監視層
- **Cloud Monitoring**
  - システムメトリクス
  - アラート設定
  - ダッシュボード
- **Cloud Logging**
  - アプリケーションログ
  - エラートレース
  - 監査ログ
- **Cloud Trace**
  - パフォーマンス分析
  - ボトルネック特定
  - 分散トレース

## データフロー

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant UI as Streamlit UI
    participant Forms as Google Forms
    participant Drive as Google Drive
    participant AI as Vertex AI
    participant CAD as FreeCAD API
    participant Storage as Cloud Storage
    participant DB as Cloud SQL

    User->>Forms: 土地図アップロード
    Forms->>Drive: データ保存
    Drive->>UI: データ同期
    UI->>AI: セグメンテーション要求
    AI->>Storage: モデル読み込み
    AI->>UI: セグメンテーション結果
    UI->>AI: 形状解析要求
    AI->>UI: 解析結果
    UI->>CAD: CAD生成要求
    CAD->>Storage: テンプレート読み込み
    CAD->>UI: 生成された図面
    UI->>Storage: 図面保存
    UI->>DB: プロジェクト情報保存
    UI->>User: 結果表示
```

## セキュリティ構成

```mermaid
graph TB
    subgraph "認証・認可"
        A1[Cloud IAM]
        A2[Firebase Auth]
        A3[API Key]
    end

    subgraph "データ保護"
        B1[Cloud KMS]
        B2[Secret Manager]
        B3[VPC]
    end

    subgraph "監視・ログ"
        C1[Cloud Audit]
        C2[Security Command Center]
        C3[Cloud Armor]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> C1
    C1 --> C2
    C2 --> C3
```

## スケーリング構成

```mermaid
graph TB
    subgraph "自動スケーリング"
        D1[Cloud Run]
        D2[Vertex AI]
        D3[Cloud SQL]
    end

    subgraph "負荷分散"
        E1[Cloud Load Balancing]
        E2[CDN]
        E3[Cloud Storage]
    end

    subgraph "キャッシュ"
        F1[Memorystore]
        F2[Cloud CDN]
        F3[Cloud Storage]
    end

    D1 --> E1
    D2 --> E1
    D3 --> E1
    E1 --> E2
    E2 --> E3
    E3 --> F1
    F1 --> F2
    F2 --> F3
```
