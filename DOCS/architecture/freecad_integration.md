# FreeCAD Docker化とクラウドデプロイメントガイド

## 1. 概要

このガイドでは、FreeCADをDockerコンテナ化し、Google Cloud Platform（GCP）上で実行する方法について説明します。

## 2. 前提条件

- Docker Desktop
- Google Cloud SDK
- GCPプロジェクト
- 必要なGCP APIの有効化
- サービスアカウントの設定

## 3. Dockerfileの作成

```dockerfile
# ベースイメージとしてUbuntu 22.04を使用
FROM ubuntu:22.04

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    freecad \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリの設定
WORKDIR /app

# 必要なPythonパッケージのインストール
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# 環境変数の設定
ENV PYTHONPATH=/app
ENV FREECAD_PATH=/usr/lib/freecad/lib

# コマンドの実行
CMD ["python3", "src/cli.py"]
```

## 4. ビルドとプッシュ

### 4.1 イメージのビルド（buildx推奨）
```bash
docker buildx build --platform linux/amd64 -t asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:<TAG> -f Dockerfile.freecad . --push
```

### 4.2 スクリプトによる自動化
```bash
bash scripts/build_and_push_docker.sh
```

## 5. Cloud Runへのデプロイ

### 5.1 サービスの作成
```bash
gcloud run deploy freecad-api \
  --image asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:<TAG> \
  --platform managed \
  --region asia-northeast1 \
  --memory 2Gi \
  --cpu 2 \
  --allow-unauthenticated
```

## 6. 動作テスト

```bash
python3 scripts/test_freecad_api.py
```

- テスト成功例:
```
✅ FreeCAD APIテスト成功
レスポンス: {
  "status": "success",
  "message": "モデルを生成しました",
  "file": "/tmp/model.FCStd",
  "storage_url": "gs://house-design-ai-data/models/model.FCStd"
}
```

## 7. トラブルシューティング

### 7.1 一般的な問題
- FreeCADのバージョンの互換性
- メモリ不足
- GPUアクセラレーションの制限

### 7.2 ログの確認
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=house-design-ai" --limit 50
```

## 8. ベストプラクティス

### 8.1 パフォーマンス最適化
- 適切なメモリとCPUの設定
- キャッシュの活用
- バッチ処理の実装

### 8.2 セキュリティ
- 最小権限の原則
- セキュアな環境変数の管理
- 定期的なセキュリティアップデート

### 8.3 コスト最適化
- インスタンス数の適切な設定
- リソース使用量の監視
- 不要なリソースの削除

## 9. 制限事項

- GUIモードはサポートされていません
- 一部のFreeCAD機能は制限される可能性があります
- ストレージの制限があります

## 10. 今後の改善点

- GPUサポートの追加
- パフォーマンスの最適化
- エラーハンドリングの強化
- モニタリングの改善

## 11. 実装状況 (2025-04-28更新)

FreeCAD APIのCloud Run実装は成功しています。以下のテスト結果が確認されています：

```
PYTHONPATH=. streamlit run house_design_app/main.py
```
でstreamlitの実行成功を確認しました。また、

```
python scripts/test_freecad_api.py
```

のテスト結果：
```
✅ FreeCAD APIテスト成功
レスポンス: {
  "status": "success",
  "message": "モデルを生成しました",
  "file": "/tmp/model.FCStd",
  "storage_url": "<gs://house-design-ai-data/models/model.FCStd>"
}
```

FreeCADをCloud Runでデプロイし、FCStdモデルでのストレージ保存まで完了しています。

### 11.1 FreeCAD API仕様

APIエンドポイント: https://freecad-api-513507930971.asia-northeast1.run.app

リクエスト形式:
```json
{
  "width": 10.0,
  "length": 15.0,
  "height": 3.0,
  "parameters": {"wall_thickness": 0.2, "window_size": 1.5}
}
```

レスポンス形式:
```json
{
  "status": "success",
  "message": "モデルを生成しました",
  "file": "/tmp/model.FCStd",
  "storage_url": "<gs://house-design-ai-data/models/model.FCStd>"
}
```

# FreeCADのDocker化とGKE・Cloud Runへのデプロイ手順

FreeCADをコマンドライン（CLI）で実行して自動CAD図面を生成するシステムを構築するために、FreeCADをDockerコンテナ化し、それを Google Kubernetes Engine (GKE) と Cloud Run 上で動かす方法を解説します。以下では、それぞれの環境での手順（Dockerイメージ作成、ビルド＆プッシュ、GKE/Cloud Runへのデプロイ、FreeCADスクリプトの実行方法）、必要なIAM権限やAPI、制限事項（タイムアウトやメモリなど）、および各アプローチの利点・課題について、初心者にも分かりやすいように詳しく説明します。

FreeCADをDockerコンテナ化する（CLIモードでの利用）

まず両アプローチ共通の前提として、FreeCADをGUIなしでコンテナ内で動作させるDockerイメージを用意します。FreeCADは通常GUIアプリケーションですが、**FreeCADCmd（freecadcmd）**というコマンドライン専用の実行ファイルを使うことで、GUIなしのヘッドレスモードで動作させることができます ￼。FreeCADCmdを使えば、Pythonスクリプトを実行してCADモデルの処理や図面出力が可能です（※GUIモジュールであるFreeCADGuiはヘッドレス環境では利用できないため、スクリプト内で使用しないよう注意します）。

Dockerfileの作成

コンテナ化のためにDockerfileを作成します。基本的にはLinux（Ubuntuなど）ベースのイメージにFreeCADをインストールし、エントリポイントでFreeCADCmdを実行できるようにします。例えば以下のようなDockerfileになります。

# ベースイメージとしてUbuntuを使用（バージョンはLTS版を推奨）
FROM ubuntu:22.04

# FreeCADインストールに必要なパッケージをインストール
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y software-properties-common \ 
    && add-apt-repository ppa:freecad-maintainers/freecad-stable \ 
    && apt-get update && apt-get install -y freecad python3 && apt-get clean

# 作業ディレクトリを設定
WORKDIR /app

# FreeCADで実行するスクリプトをコンテナにコピー（例としてscript.py）
COPY script.py /app/script.py

# FreeCADCmdを使ってスクリプトを実行するコマンドを指定
# この例では、コンテナ起動時にscript.pyを実行
ENTRYPOINT ["FreeCADCmd", "/app/script.py"]

ポイント: 上記ではUbuntu公式のFreeCADパッケージを利用しています。Ubuntuの標準リポジトリのFreeCADは古い可能性があるため、最新安定版を入れるためにFreeCAD公式のPPAを追加しています ￼。apt install freecadによりFreeCAD本体および必要なライブラリ（OpenCascadeやQt等）がインストールされ、CLI用のFreeCADCmdコマンドも利用可能になります。GUIは不要なので表示サーバ（X11など）の設定は省略していますが、念のため環境変数QT_QPA_PLATFORM=offscreenを設定しておくとQtがディスプレイを要求しないモードで動作します（必要に応じて設定してください）。

Dockerイメージのビルドとプッシュ

Dockerfileが用意できたら、次にイメージをビルドしてGCPのコンテナレジストリにプッシュします。GCPでは従来の Container Registry (GCR) か、より新しい Artifact Registry (AR) にコンテナイメージを保存できます。現在はArtifact Registryの使用が推奨されています ￼。ここでは例としてArtifact Registryを使います（GCRを使う場合はgcr.io/[PROJECT_ID]/[IMAGE_NAME]形式のイメージ名にします）。
	1.	Dockerビルド: ターミナルでDockerfileのあるディレクトリに移動し、以下のようにビルドします（[PROJECT_ID]はGCPプロジェクトIDに置き換え）。例えば:

docker build -t us-central1-docker.pkg.dev/[PROJECT_ID]/my-repo/freecad:latest .

これは、リージョンus-central1に作成したArtifact Registryリポジトリmy-repoにfreecad:latestというタグでイメージをビルドする例です。MacのM1チップなどARM環境で開発している場合、このコマンドはARMアーキテクチャのイメージを作成します。GCP上（Cloud RunやGKE標準ノード）では通常AMD64アーキテクチャが用いられるため、必要に応じてプラットフォーム指定をしてビルドします。例えば:

docker buildx build --platform linux/amd64 -t us-central1-docker.pkg.dev/[PROJECT_ID]/my-repo/freecad:latest .

のようにするか、後述するCloud Buildを使ってビルドすると良いでしょう。

	2.	Artifact Registryへのプッシュ: イメージビルド時にタグをArtifact RegistryのURLにした場合、そのままpushできます：

docker push us-central1-docker.pkg.dev/[PROJECT_ID]/my-repo/freecad:latest

事前にArtifact Registry APIを有効化し、my-repoというリポジトリを作成しておく必要があります。Container Registry (GCR) を使う場合は、イメージ名をgcr.io/[PROJECT_ID]/freecad:latestのようにタグ付けしてdocker push gcr.io/[PROJECT_ID]/freecad:latestでプッシュします。初めて使用する場合はGCRのAPI有効化と、gcloud auth configure-dockerで認証設定を行ってください。
※開発環境にDockerが無い場合やCIを使いたい場合は、Cloud Buildを利用してGCP上でビルド＆プッシュすることもできます（gcloud builds submit --tag us-central1-docker.pkg.dev/[PROJECT_ID]/my-repo/freecad:latest .）。

これで、GCP上にFreeCADのDockerイメージが用意できました。以下では、このイメージを使ってGKEおよびCloud Runにデプロイする方法を順に説明します。

1. GKEにFreeCADコンテナをデプロイする方法

GKEはGoogle CloudのマネージドKubernetesサービスです。Kubernetesクラスタ上でコンテナを柔軟に実行でき、ジョブのスケジューリングや複数コンテナの連携など高度な制御が可能です。FreeCADコンテナをGKEにデプロイすれば、Kubernetes上でバッチジョブとしてCAD図面生成を行ったり、必要に応じてスケーリングや他サービスとの統合も行えます。

GKEにデプロイする際の主な手順は以下の通りです。

1-1. GKEクラスタの作成 (Terraformを使用)

まずKubernetesクラスタを用意します。GKEクラスタは手動でCloud Consoleやgcloudコマンドから作成できますが、TerraformでIaC（インフラ構成コード）として定義・作成することも可能です ￼ ￼。Terraformを使う場合、事前にGoogle Kubernetes Engine API (container.googleapis.com) を有効にしておきます（Terraformでgoogle_project_serviceリソースを使ってAPI有効化も可能です）。

以下はTerraformでシンプルなGKE Autopilotクラスタを作成する例です（必要に応じて値を変更してください）。

# GCPプロバイダ設定（認証情報は別途指定）
provider "google" {
  project = "<Your-GCP-Project-ID>"
  region  = "asia-northeast1"  # 任意のリージョン
}

# GKE Autopilotクラスタ作成
resource "google_container_cluster" "freecad_cluster" {
  name            = "freecad-cluster"
  location        = "asia-northeast1"        # リージョン or ゾーン指定
  enable_autopilot = true                    # Autopilotモード有効（ノード自動管理）
  network         = "default"               # VPCネットワーク（defaultを使用）
}

上記は最小限の設定でAutopilotクラスタを作成する例です。Autopilotクラスタはノード管理が不要で、ワークロードに応じて自動でリソースが割り当てられるため、初心者には扱いやすいでしょう。標準（Standard）クラスタを使う場合はnode_configやinitial_node_countなどを指定してノードプールを構成する必要があります。

Terraformを適用するとクラスタが作成され、kubectl用の認証情報を取得できます。Terraformでは続けてKubernetesプロバイダを使い、クラスタ上にリソース（DeploymentやJobなど）を作成することも可能です ￼ ￼。ただし、ここではTerraformでクラスタ作成まで行い、アプリケーションのデプロイはkubectlで行う方法を説明します（必要であればTerraformのKubernetesプロバイダでDeployment定義を記述することもできます）。

1-2. Kubernetes上にFreeCADコンテナジョブをデプロイ

クラスタが用意できたら、FreeCADコンテナをKubernetes上で実行します。今回はバッチ処理として1回限りで実行し完了するJobリソースを使う方法を紹介します。Jobを使うとコンテナが処理終了後に自動で停止し、成功/失敗の状態が記録されます。定期実行したい場合はCronJobリソースにすることも可能です。

まず、FreeCADコンテナが実行する内容（Pythonスクリプト）はDockerイメージ内に組み込んであります（前述のDockerfileではscript.pyをコピーしENTRYPOINTで実行）。これにより、コンテナを起動するだけで自動的にCAD図面生成処理が走る構成とします。

KubernetesのJobを定義するマニフェストファイルの例を以下に示します（freecad-job.yamlなどの名前で保存）。

apiVersion: batch/v1
kind: Job
metadata:
  name: freecad-job
spec:
  template:
    spec:
      containers:
      - name: freecad
        image: us-central1-docker.pkg.dev/<Your-Project>/my-repo/freecad:latest
        # コンテナ内でscript.pyがENTRYPOINTで実行される想定
        # （追加のコマンドや環境変数が必要なら here に記述可能）
      restartPolicy: Never

上記では、イメージフィールドに先ほどプッシュしたFreeCADコンテナのArtifact Registryパスを指定しています。restartPolicy: Neverにより、コンテナ完了後に再起動しない設定です。必要に応じてactiveDeadlineSecondsでタイムアウト時間を設定したり、completionsやparallelismで実行タスク数を増やすこともできます。

このJobをクラスタに適用するには、kubectlを使います。Terraformでクラスタ作成後であればgcloud container clusters get-credentialsコマンド等でkubectlが使えるよう認証コンテキストを設定してください。そして以下を実行します。

kubectl apply -f freecad-job.yaml

これにより、Kubernetes上でFreeCADコンテナが1つ起動し、script.pyを実行して処理を行います。処理内容（CAD図面の生成結果）は、例えばファイルとして出力する場合は事前にPVC（永続ボリューム）をマウントしておいてその中に保存する、あるいはスクリプト内からCloud Storageにアップロードするといった方法で取得できます。単純に動作確認する場合は、FreeCADスクリプト内で標準出力にログや結果情報を出し、kubectl logs <pod名>で確認するとよいでしょう。

1-3. 必要なIAM権限とAPI (GKE)

GKEを利用するにあたり、プロジェクトレベルで有効にすべきAPIと必要権限を整理します。
	•	有効にすべきAPI:
	•	Kubernetes Engine API（container.googleapis.com） - クラスタ作成のため ￼
	•	Artifact Registry API（artifactregistry.googleapis.com） - Artifact Registryを使用する場合
	•	Cloud Storage API（storage.googleapis.com） - （オプション）生成したファイルをCloud Storageに保存する場合
	•	Cloud Build API（cloudbuild.googleapis.com） - （オプション）Cloud Buildでコンテナビルドする場合
	•	IAMロール/権限:
GKEクラスタをTerraformやgcloudで作成するユーザーには、少なくとも以下のロールが必要です ￼。
	•	Kubernetes Engine Admin（roles/container.admin） – GKEクラスタやリソースの管理権限
	•	Compute Network Admin（roles/compute.networkAdmin） – デフォルトネットワークや関連リソースの管理権限（新規VPCやIP割り当てを行う場合）
	•	Service Account User（roles/iam.serviceAccountUser） – GKEが内部で使用するサービスアカウントの利用権限
	•	（Artifact Registryにイメージをプッシュ/Pullする権限）Artifact Registry Writer/Reader 権限 – Artifact Registryを操作する権限（ビルドやデプロイ時に必要）。例えばデプロイ時にクラスタのノードサービスアカウントがイメージをPullできるよう、roles/artifactregistry.readerを付与するか、イメージを同一プロジェクト内に配置します ￼。
Terraformでクラスタを構築する場合、Terraform実行者が上記ロールを持っている必要があります。また、Terraformでgoogle_container_clusterを作成する際に明示的にサービスアカウントを指定しない場合、デフォルトでCompute Engineデフォルトサービスアカウントがノードに使われます。デフォルトサービスアカウントには必要な権限（roles/container.nodeServiceAccountなど）が付与されていますが、Artifact Registryを使う場合はこのサービスアカウントにコンテナイメージ閲覧権限を与えておくと確実です。

1-4. GKEにおける利点・課題・制限

利点:
	•	柔軟なリソースと長時間ジョブ: GKE上ではコンテナの実行時間に制限がなく、必要なら長時間の処理や大きなメモリ・CPUを要するジョブもノードをスケールアップして対応可能です。例えばFreeCADで非常に複雑なモデルを処理する場合でも、タイムアウトを気にせず完了まで動かせます（クラスタのノードに十分なリソースがある限り）。
	•	高度なスケジューリングと連携: KubernetesのJobやCronJob、あるいはカスタムコントローラを用いて、FreeCADによる処理をスケジュール実行したり、他のサービス（例: 他のPodやデータベース）と組み合わせたワークフローを構築できます。複数のコンテナを連携させるワークロードや並列分散処理も容易です。
	•	同一イメージの再利用: GKEとCloud Runはいずれも標準的なコンテナイメージをデプロイ単位として使用するため、一度作成したFreeCADイメージは両方のプラットフォームでそのまま利用できます ￼。開発・ビルドしたイメージを使い回せるので、環境間の移行もスムーズです。

課題・考慮点:
	•	クラスタ管理のオーバーヘッド: GKEはマネージドサービスとはいえ、Kubernetesクラスタ自体の運用管理が必要です。Autopilotモードを使えばノード管理は自動化されますが、それでもクラスタの作成・設定、アップグレード、モニタリングなどの知識は求められます。小規模な用途で常時クラスタを動かしておくコストも考慮が必要です（クラスタは起動している限り基本料金が発生します。Autopilotでは使った分のPodリソース課金ですが、最小リソースに対する料金もあります）。
	•	初期セットアップの手間: Cloud Runに比べると、クラスタの構築や権限設定など初期準備に手間がかかります。ただ一度テンプレートを作ってTerraform管理すれば、その後は繰り返しデプロイが容易になります。
	•	権限周りの設定: Kubernetes内部で動くコンテナから他のGCPサービス（例えばCloud StorageやArtifact Registry）にアクセスする場合、Workload Identityの設定やサービスアカウントの権限管理が必要になります ￼。これは柔軟である反面、初心者には少し難しく感じるかもしれません。

以上がGKEにデプロイする場合の流れです。次に、よりサーバーレスで手軽に使えるCloud Runへのデプロイ方法を見てみましょう。

2. Cloud RunにFreeCADコンテナをデプロイする方法

Cloud Runはコンテナをサーバーレスで実行できるGCPのサービスです。イベントやHTTPリクエストに応じてコンテナが起動し、処理を行った後自動でスケールダウン（アイドル時は0インスタンス）するため、使うときだけ課金されます。短時間のバッチ処理であればCloud Runを使うことでクラスタ不要でコンテナ実行が可能です。

FreeCADコンテナをCloud Runで動かすには、Cloud Runサービスとしてデプロイする方法と、Cloud Runジョブとして実行する方法があります。Cloud Runサービスは通常HTTPリクエストを処理する常駐型ですが、工夫すればリクエストごとに任意の処理を実行してすぐ終了させることもできます。一方、Cloud Runジョブはリクエストを受け付けず、起動すると指定したタスクを実行して完了するバッチ実行専用の仕組みです ￼。ここでは主にサービスとしてのデプロイ方法を説明し、必要に応じてジョブについても触れます。

2-1. Cloud Runサービスの作成・デプロイ

まず、Cloud RunにデプロイするにはプロジェクトでCloud Run API (run.googleapis.com) を有効にします。コンテナイメージは既にArtifact Registryにプッシュ済みとします。Cloud RunサービスはGUIのコンソールやgcloudCLI、Terraformで作成可能です。ここではTerraformの例を示します ￼（手動で行う場合はコンソールの「Cloud Runにデプロイ」からイメージを選択して進めることもできます）。

TerraformでCloud Runサービスを作成する例:

# Cloud Runサービス作成（Terraform）
resource "google_cloud_run_service" "freecad_service" {
  name     = "freecad-service"
  location = "asia-northeast1"  # 任意のリージョン（Cloud Runはリージョン単位）

  template {
    spec {
      containers {
        image = "us-central1-docker.pkg.dev/<Your-Project>/my-repo/freecad:latest"
        # FreeCADCmdはENTRYPOINTで実行される想定
        resources {
          limits = {
            memory = "2Gi"     # 必要に応じてメモリ/CPU制限
            cpu    = "2"
          }
        }
      }
      # タイムアウト（デフォルト300秒）を延長（必要なら）
      timeoutSeconds = 900    # 15分に設定（最大3600秒=60分まで可能 [oai_citation_attribution:14‡cloud.google.com](https://cloud.google.com/run/docs/configuring/request-timeout#:~:text=The%20timeout%20is%20set%20by,3600%20seconds)）
    }
  }
  traffic { 
    percent         = 100
    latest_revision = true
  }
}

上記では、Cloud Runにfreecad-serviceというサービスを作成し、先ほどのコンテナイメージを使ってデプロイしています。コンテナにリクエストが来た際のタイムアウトを15分に設定し（デフォルト5分。Cloud Runサービスでは最大60分まで延長可能 ￼）、メモリ2GiB・CPU2コアを割り当てています。FreeCADの処理内容に合わせて適切にリソース設定してください（Cloud Runでは最大で8 vCPU・32GiBメモリまで割り当て可能です ￼）。

Terraformを適用（terraform apply）すると、Cloud Runサービスが作成・デプロイされます。この段階でサービスはデフォルトでは認証必須のHTTPエンドポイントとして動作します（後述のIAM設定で変更可能）。

メモ: gcloudCLIでデプロイする場合は、例えば次のようなコマンドになります:

gcloud run deploy freecad-service \
   --image us-central1-docker.pkg.dev/[PROJECT_ID]/my-repo/freecad:latest \
   --region asia-northeast1 \
   --no-allow-unauthenticated \
   --memory 2Gi --cpu 2 --timeout 900

これにより同様のサービスが作成されます。--no-allow-unauthenticatedは認証無しアクセスを禁止するオプションです（デフォルトでは認証必須）。

2-2. FreeCADコンテナの実行方法（リクエスト handling またはジョブ）

Cloud Runサービスとしてデプロイした場合、HTTPリクエストが来るとコンテナが起動してリクエストを処理します。しかし、我々のFreeCADコンテナは特定のスクリプトを実行して終了する構成であり、通常のウェブサービスのようにリクエストを待ち受けるサーバを動かしていません。このままではリクエストを受け取ってもすぐにコンテナが終了してしまう可能性があります。

Cloud Runサービスでバッチ処理を行うには、いくつか方法があります。
	•	方法1: コンテナ起動時に処理を実行し、終了後すぐコンテナを停止させる – Cloud Runではリクエスト処理中にレスポンスを返さずコンテナが終了するとエラーになります。そのため、エントリポイントのスクリプト実行後に適当なHTTPサーバを起動し、処理完了を通知するまで待機する、といった工夫が必要です。例えば、FreeCADの処理完了後に結果をCloud Storageに保存し、最後にHTTPレスポンスを返すようなPythonの簡易サーバーを書く方法が考えられます。ただしこの方法は実装の手間がかかります。
	•	方法2: Cloud Runジョブを使う – Cloud Runには「ジョブ」としてコンテナを実行するモードがあります ￼。ジョブはHTTPリクエストを必要とせず、命令によりすぐコンテナを立ち上げて処理が終われば自動で停止します。今回のような短時間バッチ処理にはCloud Runジョブが適しています。Cloud Runジョブを作成するには、コンソールでCloud Runの「ジョブ」を選んでデプロイするか、gcloudコマンドで gcloud run jobs create を使用します。例えば:

gcloud run jobs create freecad-job \
    --image us-central1-docker.pkg.dev/[PROJECT_ID]/my-repo/freecad:latest \
    --region asia-northeast1 --tasks 1 --max-retries 0 --timeout 900

これでfreecad-jobというジョブが作成されます。実行は:

gcloud run jobs execute freecad-job --region asia-northeast1

で手動実行できます。Terraformでもgoogle_cloud_run_v2_jobリソースを使ってジョブを定義可能です。
Cloud Runジョブは処理完了まで待機でき、1ジョブあたり最大60分（デフォルト10分）まで実行可能です。さらに必要なら**最大24時間（Previewでは最大7日間！）**までタイムアウトを延ばすことも設定できます ￼。今回の「短時間バッチ処理」程度であれば十分な上限でしょう。ジョブ実行のスケジューリングもCloud Schedulerと連携して cron 的に行うことができます。

以上より、バッチ用途であれば Cloud Runジョブを使うのが簡潔でおすすめです。対して、何らかのトリガーに対してHTTP経由で実行したい（例えばシステムの他の部分からREST APIとして呼び出したい）場合はCloud Runサービスとしてデプロイし、リクエスト時に処理を行う構成にすると良いでしょう。

2-3. 必要なIAM権限とAPI (Cloud Run)

Cloud Runを使うにあたり必要な権限や設定をまとめます。
	•	有効にすべきAPI:
	•	Cloud Run Admin API（run.googleapis.com） – Cloud Runサービス/ジョブのデプロイに必要
	•	Artifact Registry API（artifactregistry.googleapis.com） – AR上のイメージを使用する場合
	•	（Cloud Runジョブをスケジュールする場合）Cloud SchedulerやWorkflowsのAPI – 必要に応じて
	•	IAMロール/権限（デプロイと実行）:
Cloud Runサービスやジョブをデプロイするユーザーには以下のロールが必要です ￼:
	•	Cloud Run 開発者（roles/run.developer） – Cloud Runサービスの作成・更新権限
	•	サービスアカウント利用者（roles/iam.serviceAccountUser） – デプロイ時に実行サービスアカウントを指定する場合に必要
	•	Artifact Registry リーダー（roles/artifactregistry.reader） – 使用するコンテナイメージへの読み取り権限（Artifact Registryにプライベート格納の場合） ￼
（デプロイ元がContainer Registryの場合はroles/storage.objectViewerなどが必要になることがあります）
デフォルトでは、同一プロジェクト内のArtifact Registryイメージを使う場合、Cloud Runのデフォルトのランタイムサービスアカウント（PROJECT_NUMBER-compute@developer.gserviceaccount.com）にArtifact Registryへの読み取り権限が付与されています。念のため確認し、必要なら明示的にroles/artifactregistry.readerを付与してください。
	•	Cloud Runサービスの呼び出し権限:
デプロイ後、Cloud Runサービスを誰が実行できるか制御するIAMも重要です。デフォルトでは認証された呼び出しのみ許可となり、自分がコンソールやgcloudからアクセスする際はプロジェクトの編集者などの権限で可能ですが、外部からHTTPで呼び出すにはIDトークンなどが必要です。もし匿名（認証無し）で呼び出したい場合は、そのサービスに対して「全ユーザー」にCloud Run Invoker（roles/run.invoker）ロールを付与して未認証アクセスを許可します。Terraformではgoogle_cloud_run_service_iam_policy等で設定できます。
Cloud Runジョブの場合はHTTPではなくコマンド実行なので、ジョブ実行権限としてCloud Run Invoker（ジョブの場合はroles/run.invokerは不要で、代わりにroles/run.runnerが必要なケースがあります）を付与することで、gcloudやCloud Schedulerからジョブを実行できます。

2-4. Cloud Run利用時の制限事項と考慮点

制限事項:
	•	実行時間の制約: Cloud Runサービスでは1リクエストあたりの実行時間がデフォルト5分で、**最大でも60分（3600秒）**に制限されています ￼。長時間かかるFreeCAD処理の場合、サービスとしては適しません。その場合はCloud Runジョブを利用し、**最大24時間（あるいは7日間）**までタスクタイムアウトを延長できます ￼。今回の「短時間バッチ」であれば大きな問題にはならないでしょうが、将来的に重い処理をする場合はこの点を念頭に置いてください。
	•	同時実行とスケーリング: Cloud Runサービスはデフォルトで同時に複数のリクエストを1コンテナで処理できます（最大同時処理コンテナ数: 1〜1000並列）。バッチ処理では並列実行させる必要は基本ないので、必要に応じてConcurrencyを1に設定するとよいです。自動スケーリングによりリクエスト数に応じてコンテナインスタンス数が増減します。一方、Cloud Runジョブでは--tasksで指定した個数のコンテナが並列実行できます（デフォルト1）。数十〜数百のCADジョブを並列に走らせることも可能ですが、その分リソース上限に注意が必要です。
	•	GPU未対応: 2025年時点でCloud RunではGPUを利用できません。FreeCADは主にCPUで動作しますが、もし将来的にGPUアクセラレーションが必要な処理（例えばレンダリング）が出てくる場合、Cloud Runでは対応できず、GKEならばGPUノードを使って対応可能です。
	•	ファイル永続化: Cloud Runの各コンテナインスタンスには一時ストレージ（/tmpなど）しかありません。コンテナが停止すると消えるため、生成したCAD図面ファイル等は外部ストレージに書き出す必要があります。例えば、スクリプト内で直接Cloud Storageにアップロードするか、結果をHTTPレスポンスとして返す（サービスの場合）ようにします。GKEの場合はPodに永続ボリュームをマウントすることもできます。

利点:
	•	サーバーレスの手軽さとコスト効率: Cloud Runは使われていないときは料金が発生しません。バッチ処理をたまに実行する程度であれば、常時稼働のクラスタを維持するより遥かにコスト効率が良くなります。リクエストやジョブ実行に応じて自動で必要なコンテナのみ起動し、処理後はスケールダウンしてリソースを解放します。
	•	デプロイの容易さ: クラスタのセットアップ不要で、コンテナイメージさえあれば即座にデプロイできます。Terraformの設定項目も最小限で済み、またGCPコンソールからGUI操作でデプロイすることもできます。
	•	スケーラビリティ: 短時間で多数のジョブを処理したい場合、Cloud Runは自動でインスタンス数をスケールアウトできます。例えば多数のCADファイルを連続で処理する場合も、自動的に並列処理され全体のスループットが向上します。最大同時インスタンス数の上限はプロジェクト設定で調整可能です。

課題・考慮点:
	•	デバッグ/開発時の制約: Cloud Run上でのデバッグはログ（Cloud Logging）を通して行うことになります。対話的にコンテナ内に入って調査する、といったことはできないため、ローカルで再現してテストを十分に行うか、必要に応じてGKEなどでデバッグ環境を用意することも検討してください。
	•	コールドスタート: Cloud Runはリクエストやジョブ実行時にコンテナを起動しますが、コンテナ初回起動（コールドスタート）には数秒程度の時間がかかる場合があります。FreeCADコンテナはサイズが大きく起動に時間がかかる可能性がありますが、Batch用途で多少遅延しても問題なければ許容範囲です。頻繁に呼び出すのであれば、稼働インスタンスを0にしない設定（最小インスタンス数の指定）も可能です。

⸻

以上、FreeCADをDocker化してGKEおよびCloud Runにデプロイする方法を詳述しました。それぞれ一長一短がありますが、
	•	GKEは柔軟性とパワー重視（長時間・高負荷ジョブや複雑な連携に対応）、
	•	Cloud Runは手軽さと効率重視（必要なときだけ動かしコスト最適化、サーバーレス運用）、

という特徴があります。両者はコンテナイメージを共通化できるため、まず開発はDockerコンテナで行い、軽量なジョブはCloud Runで、本格運用や特殊要件が出てきたらGKEに移行、といったハイブリッドな運用も可能です ￼ ￼。プロジェクトの要件に合わせて適切な方法を選択してください。各ステップで触れたIAMや設定も、Terraformでコード化しておくことで再現性高く管理できます。ぜひ本ガイドを参考に、自動CAD図面生成システムの構築を進めてみてください。

# 参考資料

- GKEクラスタとTerraformに関する公式ドキュメント
- Cloud Runへのコンテナデプロイ手順（公式）
- Cloud Runのタイムアウト設定に関する説明
- Cloud Runジョブの利用に関するドキュメント
- FreeCADのコマンドライン利用（freecadcmdに関するUbuntu Manpage）

# FreeCAD API仕様書

## API概要

このドキュメントでは、House Design AIプロジェクトにおけるFreeCAD APIの仕様を詳細に説明します。このAPIは、セグメンテーションデータから3Dモデルを生成し、建物や道路の情報を処理するための機能を提供します。

## ベースURL

```
https://freecad-api-513507930971.asia-northeast1.run.app
```

## デプロイ済みサービス情報

### FreeCAD API
- **環境**: Google Cloud Run
- **リソース設定**:
  - メモリ: 2GB
  - CPU: 2コア
  - タイムアウト: 300秒
- **環境変数**:
  - `PYTHONPATH=/usr/lib/freecad/lib`
  - `QT_QPA_PLATFORM=offscreen`

## API仕様詳細

### エンドポイント一覧

| メソッド | パス                          | 説明                     |
|------|-----------------------------|------------------------|
| POST | `/api/v1/generate-model`    | セグメンテーションデータから3Dモデルを生成 |
| GET  | `/api/v1/models/{model_id}` | 生成済みモデルの情報を取得     |

### エンドポイント詳細

#### 1. 3Dモデル生成

**エンドポイント**: `POST /api/v1/generate-model`

**説明**: セグメンテーションデータと設定パラメータを受け取り、3Dモデルを生成します。

**リクエストボディ**:
```json
{
  "segmentation_data": {
    "buildings": [
      {
        "id": "building_1",
        "coordinates": [[x1, y1], [x2, y2], ...],
        "height": 10.0,
        "type": "residential"
      }
    ],
    "roads": [
      {
        "id": "road_1",
        "coordinates": [[x1, y1], [x2, y2], ...],
        "width": 5.0
      }
    ]
  },
  "parameters": {
    "building_height": 10.0,
    "road_width": 5.0,
    "grid_size": 2.0
  }
}
```

**パラメータ説明**:
| パラメータ                                     | 型     | 必須 | 説明                                |
|-------------------------------------------|--------|------|-------------------------------------|
| segmentation_data                         | Object | はい   | 建物と道路のセグメンテーションデータ              |
| segmentation_data.buildings               | Array  | はい   | 建物オブジェクトの配列                     |
| segmentation_data.buildings[].id          | String | はい   | 建物の一意識別子                     |
| segmentation_data.buildings[].coordinates | Array  | はい   | 建物の頂点座標の配列 [[x,y], ...]     |
| segmentation_data.buildings[].height      | Number | はい   | 建物の高さ（メートル）                      |
| segmentation_data.buildings[].type        | String | いいえ  | 建物のタイプ（residential, commercial等） |
| segmentation_data.roads                   | Array  | いいえ  | 道路オブジェクトの配列                     |
| parameters                                | Object | はい   | モデル生成のパラメータ                       |
| parameters.building_height                | Number | いいえ  | デフォルトの建物高さ（メートル）                 |
| parameters.road_width                     | Number | いいえ  | デフォルトの道路幅（メートル）                  |
| parameters.grid_size                      | Number | いいえ  | グリッドサイズ（メートル）                       |

**レスポンス**:
```json
{
  "status": "success",
  "model_url": "https://storage.googleapis.com/house-design-ai/models/building_1.step",
  "metadata": {
    "building_count": 1,
    "road_count": 1,
    "total_area": 100.0,
    "generation_time": 5.2
  }
}
```

**レスポンスパラメータ**:
| パラメータ                    | 型     | 説明                          |
|--------------------------|--------|------------------------------|
| status                   | String | 処理結果のステータス（success/error） |
| model_url                | String | 生成されたモデルファイルのURL            |
| metadata                 | Object | モデルに関するメタデータ                 |
| metadata.building_count  | Number | 処理された建物の数                |
| metadata.road_count      | Number | 処理された道路の数                |
| metadata.total_area      | Number | 総面積（平方メートル）              |
| metadata.generation_time | Number | 生成処理にかかった時間（秒）         |

**ステータスコード**:
| コード | 説明                 |
|-----|----------------------|
| 200 | 成功                 |
| 400 | 不正なリクエスト（パラメータエラー） |
| 500 | サーバーエラー              |

#### 2. モデル情報取得

**エンドポイント**: `GET /api/v1/models/{model_id}`

**説明**: 生成済みの3Dモデルの情報を取得します。

**パスパラメータ**:
| パラメータ    | 型     | 必須 | 説明                 |
|----------|--------|------|--------------------|
| model_id | String | はい   | 取得するモデルの一意識別子 |

**レスポンス**:
```json
{
  "model_id": "building_1",
  "status": "completed",
  "created_at": "2024-04-01T12:00:00Z",
  "file_url": "https://storage.googleapis.com/house-design-ai/models/building_1.step",
  "metadata": {
    "building_count": 1,
    "road_count": 1,
    "total_area": 100.0
  }
}
```

**レスポンスパラメータ**:
| パラメータ      | 型     | 説明                                  |
|------------|--------|---------------------------------------|
| model_id   | String | モデルの一意識別子                        |
| status     | String | モデルの状態（completed/processing/failed） |
| created_at | String | モデル作成日時（ISO 8601形式）             |
| file_url   | String | モデルファイルのダウンロードURL                     |
| metadata   | Object | モデルに関するメタデータ                         |

**ステータスコード**:
| コード | 説明        |
|-----|-------------|
| 200 | 成功        |
| 404 | モデルが見つからない |
| 500 | サーバーエラー     |

## クライアント実装例

### Python実装例
```python
import requests
import json

API_URL = "https://freecad-api-513507930971.asia-northeast1.run.app"

def generate_3d_model(segmentation_data, parameters):
    """
    FreeCAD APIを使用して3Dモデルを生成する関数
    
    Args:
        segmentation_data (dict): 建物と道路のセグメンテーションデータ
        parameters (dict): モデル生成のパラメータ
        
    Returns:
        dict: APIレスポンス（成功時はモデルURL、失敗時はエラー情報）
    """
    response = requests.post(
        f"{API_URL}/api/v1/generate-model",
        json={
            "segmentation_data": segmentation_data,
            "parameters": parameters
        }
    )
    return response.json()

# 使用例
segmentation_data = {
    "buildings": [
        {
            "id": "building_1",
            "coordinates": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "height": 10.0,
            "type": "residential"
        }
    ],
    "roads": [
        {
            "id": "road_1",
            "coordinates": [[-5, 5], [15, 5]],
            "width": 5.0
        }
    ]
}

parameters = {
    "building_height": 10.0,
    "road_width": 5.0,
    "grid_size": 2.0
}

result = generate_3d_model(segmentation_data, parameters)
print(result)
```

### cURL実装例
```bash
curl -X POST \
  https://freecad-api-513507930971.asia-northeast1.run.app/api/v1/generate-model \
  -H 'Content-Type: application/json' \
  -d '{
    "segmentation_data": {
      "buildings": [
        {
          "id": "building_1",
          "coordinates": [[0, 0], [10, 0], [10, 10], [0, 10]],
          "height": 10.0,
          "type": "residential"
        }
      ],
      "roads": [
        {
          "id": "road_1",
          "coordinates": [[-5, 5], [15, 5]],
          "width": 5.0
        }
      ]
    },
    "parameters": {
      "building_height": 10.0,
      "road_width": 5.0,
      "grid_size": 2.0
    }
  }'
```

## エラー処理仕様

### エラーレスポンス形式
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_INPUT",
    "message": "Invalid segmentation data format",
    "details": {
      "field": "coordinates",
      "issue": "Missing required field"
    }
  }
}
```

### エラーコード一覧
| コード                | 説明              | 対処方法                                            |
|--------------------|-----------------|-------------------------------------------------|
| `INVALID_INPUT`    | 入力データの形式が不正 | リクエストパラメータを確認し、必須フィールドが正しく設定されているか確認してください |
| `PROCESSING_ERROR` | モデル生成中のエラー     | 入力データの複雑さを減らすか、サポートに問い合わせてください               |
| `STORAGE_ERROR`    | ファイル保存時のエラー    | 一時的な問題の可能性があります。再試行するか、サポートに問い合わせてください |
| `TIMEOUT`          | 処理時間超過      | 入力データの複雑さを減らすか、より小さなモデルに分割してください            |

## API制限事項

### 1. リクエスト制限
| 項目      | 制限値     | 説明                   |
|-----------|----------|----------------------|
| リクエストサイズ  | 最大10MB   | リクエストボディの合計サイズ       |
| 建物数    | 最大100    | 1リクエストあたりの建物オブジェクト数 |
| 道路数    | 最大50     | 1リクエストあたりの道路オブジェクト数 |
| リクエスト頻度 | 1分あたり60回 | APIキーごとの制限           |

### 2. 処理時間制限
| 項目       | 制限値 | 説明                       |
|------------|-------|--------------------------|
| タイムアウト     | 300秒  | 処理が完了しない場合はタイムアウトエラー |
| 推奨建物数 | 20以下 | 最適なパフォーマンスのための推奨値     |

### 3. 出力形式制限
| 形式 | 拡張子 | 最大サイズ | 説明                  |
|------|--------|---------|---------------------|
| STEP | .step  | 50MB    | 標準的な3D CAD交換形式 |
| STL  | .stl   | 50MB    | 3Dプリント用メッシュ形式      |

## 実装ベストプラクティス

### 1. データ準備のベストプラクティス
- **座標指定**: 建物の座標は時計回りに指定してください
- **高さ設定**: 建物の高さは現実的な値（2〜100メートル）を設定してください
- **道路幅**: 道路幅は適切な値（3〜30メートル）を設定してください
- **座標系**: すべての座標は同一の座標系で指定してください

### 2. エラーハンドリングのベストプラクティス
- **タイムアウト対策**: 処理時間が長くなる可能性がある場合は、非同期処理を検討してください
- **エラー処理**: すべてのAPIレスポンスでステータスコードとエラーメッセージを確認してください
- **リトライ戦略**: 一時的なエラーの場合は、指数バックオフを使用したリトライを実装してください

### 3. パフォーマンス最適化のベストプラクティス
- **バッチ処理**: 多数のモデルを生成する場合は、バッチ処理を活用してください
- **キャッシュ**: 同一パラメータでの再計算を避けるため、結果をキャッシュしてください
- **非同期処理**: 長時間実行される処理は非同期で実行し、完了通知を受け取る仕組みを実装してください

## 今後のロードマップ

### 1. 機能拡張予定
- **マルチスレッド処理**: 複雑なモデル生成の高速化（2025年Q2予定）
- **バッチ処理API**: 複数モデルの一括生成機能（2025年Q3予定）
- **新出力形式**: IFC、DXF形式のサポート追加（2025年Q4予定）

### 2. パフォーマンス改善計画
- **処理速度**: アルゴリズム最適化による処理速度50%向上（進行中）
- **メモリ使用量**: 大規模モデル処理時のメモリ使用量30%削減（計画中）
- **スケーリング**: 自動スケーリングによる負荷分散機能（検討中）

### 3. 監視・運用強化
- **詳細メトリクス**: API使用状況と処理時間の詳細メトリクス提供
- **アラート機能**: 異常検知時の自動通知システム
- **ログ分析**: 高度なログ分析ツールの導入
