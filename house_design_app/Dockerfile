FROM python:3.9-slim

WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
  libgl1-mesa-glx \
  libglib2.0-0 \
  # FreeCAD関連のライブラリ追加（注：これはAPIクライアントのみ）
  build-essential \
  python3-dev \
  libxml2-dev \
  libxslt1-dev \
  && rm -rf /var/lib/apt/lists/*

# 依存関係をコピーしてインストール
COPY requirements-streamlit.txt .
RUN pip install --no-cache-dir -r requirements-streamlit.txt

# アプリケーションコードをコピー
COPY . .

# 環境変数を設定
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
# PyTorch 2.6+ では警告だけを表示させる
ENV TORCH_WARN_ONLY=1

# ポートを公開
EXPOSE ${PORT:-8080}

# Streamlitアプリを起動
CMD streamlit run main.py --server.port=${PORT:-8080} --server.address=0.0.0.0 