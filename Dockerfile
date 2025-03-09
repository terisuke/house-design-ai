# ベースイメージを指定 (NVIDIA CUDAを含むイメージ)
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04

# 作業ディレクトリを設定
WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
  python3 \
  python3-pip \
  git \
  libgl1-mesa-dev \
  libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# 依存関係のファイルをコピー
COPY requirements.txt /app/

# 依存関係のインストール
RUN pip3 install --no-cache-dir -r requirements.txt

# プロジェクトファイルをコピー
COPY src/ /app/src/
COPY streamlit/ /app/streamlit/
COPY scripts/ /app/scripts/
COPY pyproject.toml /app/

# configディレクトリを作成
RUN mkdir -p /app/config/

# サービスアカウントキーをコピー
COPY config/service_account.json /app/config/service_account.json

# 環境変数を設定
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/config/service_account.json
ENV PYTHONPATH=/app

# エントリーポイントを設定
ENTRYPOINT ["python3", "-m", "src.cli"]