FROM ubuntu:20.04

WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
  software-properties-common \
  python3-pip \
  python3-dev \
  freecad \
  libgl1-mesa-glx \
  && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
COPY requirements-freecad-api.txt .
RUN pip3 install --no-cache-dir -r requirements-freecad-api.txt

# FreeCADのPythonパスを環境変数に設定
ENV PYTHONPATH="${PYTHONPATH}:/usr/lib/freecad/lib"
ENV PORT=8000

# APIコードをコピー
COPY . /app/

# FastAPIサーバー起動
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 