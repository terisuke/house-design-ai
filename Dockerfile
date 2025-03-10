# ベースイメージを指定 (NVIDIA CUDAを含むイメージ)
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04

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
RUN pip3 install --no-cache-dir -r requirements.txt

# YOLOモデルをダウンロード
# ultralyticsのモデルディレクトリを作成
RUN mkdir -p /root/.config/ultralytics/models/

# YOLO11mセグメンテーションモデルをダウンロード
RUN wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11m-seg.pt -O /root/.config/ultralytics/models/yolo11m-seg.pt && \
  chmod 644 /root/.config/ultralytics/models/yolo11m-seg.pt && \
  ls -la /root/.config/ultralytics/models/

# プロジェクトファイルをコピー
COPY src/ /app/src/
COPY streamlit/ /app/streamlit/
COPY scripts/ /app/scripts/
COPY pyproject.toml /app/
COPY app.py /app/app.py

# app.pyに実行権限を付与
RUN chmod +x /app/app.py

# configディレクトリを作成
RUN mkdir -p /app/config/
RUN mkdir -p /app/house/train /app/house/val

# サービスアカウントキーをコピー
COPY config/service_account.json /app/config/service_account.json
# data.yamlをコピー
COPY config/data.yaml /app/config/data.yaml

# 環境変数を設定
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/config/service_account.json
ENV PYTHONPATH=/app
ENV PATH="/usr/local/bin:${PATH}"

# gsutilのキャッシュを無効化（トラブルシューティング用）
ENV CLOUDSDK_PYTHON_SITEPACKAGES=1

# エントリーポイントを設定
ENTRYPOINT ["python3", "-m", "src.cli"]