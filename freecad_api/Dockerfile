FROM python:3.11-slim

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
  freecad \
  && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /app

# 必要なPythonパッケージをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコードをコピー
COPY . .

# 環境変数を設定
ENV PYTHONPATH=/usr/lib/freecad-python3/lib:$PYTHONPATH
ENV LD_LIBRARY_PATH=/usr/lib/freecad-python3/lib:$LD_LIBRARY_PATH

# アプリケーションを起動
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"] 