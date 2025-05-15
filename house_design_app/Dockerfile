FROM python:3.9-slim

WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
  libgl1-mesa-glx \
  libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# 依存関係をコピーしてインストール
COPY requirements-streamlit.txt .
RUN pip install --no-cache-dir -r requirements-streamlit.txt

# アプリケーションコードをコピー
COPY . .

# 環境変数を設定
ENV PYTHONUNBUFFERED=1

# ポートを公開
EXPOSE 8501

# Streamlitアプリを起動
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"] 