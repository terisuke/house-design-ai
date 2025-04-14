FROM ubuntu:20.04

# タイムゾーン設定
ENV TZ=Asia/Tokyo
ENV PYTHONPATH=/usr/lib/freecad-python3/lib

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
  tzdata \
  && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
  && echo $TZ > /etc/timezone \
  && apt-get install -y \
  software-properties-common \
  python3-pip \
  python3-dev \
  python3-minimal \
  python3-setuptools \
  python3-wheel \
  freecad \
  libgl1-mesa-glx \
  xserver-xorg-video-all \
  && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリの設定
WORKDIR /app

# アプリケーションのコピー
COPY . .

# 依存関係のインストール
RUN pip3 install --no-cache-dir -r requirements.txt

# 実行コマンド
CMD ["python3", "app.py"] 