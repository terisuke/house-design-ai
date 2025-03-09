# ベースイメージを指定 (NVIDIA CUDAを含むイメージ)
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04

# 作業ディレクトリを設定
WORKDIR /app

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
  && rm -rf /var/lib/apt/lists/*

# Google Cloud SDKのインストール
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
  curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - && \
  apt-get update && apt-get install -y google-cloud-sdk && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# 依存関係のファイルをコピー
COPY requirements.txt /app/

# 依存関係のインストール
RUN pip3 install --no-cache-dir -r requirements.txt

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

# サービスアカウントキーをコピー
COPY config/service_account.json /app/config/service_account.json
# data.yamlをコピー
COPY config/data.yaml /app/config/data.yaml

# 環境変数を設定
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/config/service_account.json
ENV PYTHONPATH=/app

# エントリーポイントを設定
ENTRYPOINT ["python3", "-m", "src.cli"]