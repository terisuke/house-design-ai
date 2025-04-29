# ベースイメージを明示的にプラットフォーム指定
FROM --platform=linux/amd64 python:3.10-slim-bullseye

# 作業ディレクトリを設定
WORKDIR /app

# 環境変数を設定
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
  python3 \
  python3-pip \
  python3-dev \
  git \
  libgl1-mesa-dev \
  libglib2.0-0 \
  libgl1 \
  libglx0 \
  libglvnd0 \
  libsm6 \
  libxext6 \
  libxrender1 \
  build-essential \
  pkg-config \
  libprotobuf-dev \
  protobuf-compiler \
  libssl-dev \
  libffi-dev \
  libc-ares2 \
  gnupg \
  curl \
  wget \
  && rm -rf /var/lib/apt/lists/*

# Google Cloud SDKのインストール（gsutilを明示的に含む）
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
  curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - && \
  apt-get update && apt-get install -y google-cloud-sdk google-cloud-sdk-gke-gcloud-auth-plugin google-cloud-sdk-app-engine-python && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# gsutilが正しくインストールされたか確認
RUN gsutil --version

# pip自体をアップグレード
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# 依存関係のファイルをコピー
COPY requirements.txt /app/

# 依存関係のインストール
RUN pip3 install --default-timeout=1000 --no-cache-dir -r requirements.txt

# YOLOモデルをダウンロード
# ultralyticsのモデルディレクトリを作成
RUN mkdir -p /root/.config/ultralytics/models/

# YOLO11mセグメンテーションモデルをダウンロード
RUN wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11l-seg.pt -O /root/.config/ultralytics/models/yolo11l-seg.pt && \
  chmod 644 /root/.config/ultralytics/models/yolo11l-seg.pt && \
  ls -la /root/.config/ultralytics/models/

# 必要なディレクトリを作成
RUN mkdir -p /app/house_design_app/ /app/.streamlit/ /app/config/ /app/public/img/

# 必須ファイルの存在チェック
# 存在しない場合はビルドを失敗させる
COPY check_required_files.sh /app/
RUN chmod +x /app/check_required_files.sh

# 必須ファイルをコピー
# 存在しない場合はビルドが失敗する
COPY config/service_account.json /app/config/service_account.json
COPY public/img/logo.png /app/house_design_app/logo.png

# secrets.tomlにservice_account.jsonの内容をコピー
COPY config/service_account.json /app/.streamlit/secrets.toml

# その他のプロジェクトファイルをコピー
COPY . /app/

# Cloud Run環境でのGCP認証を設定
ENV USE_GCP_DEFAULT_CREDENTIALS=true

# ポートを公開
EXPOSE 8080

# 環境変数を設定
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/config/service_account.json
ENV PYTHONPATH=/app
ENV PATH="/usr/local/bin:${PATH}"
ENV CLOUDSDK_PYTHON_SITEPACKAGES=1

# Streamlitを起動
CMD ["streamlit", "run", "house_design_app/main.py", "--server.port=8080", "--server.address=0.0.0.0"]
