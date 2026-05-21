# Python 3.11 の軽量ベースイメージを使用する
FROM python:3.11-slim

# .pyc を作らず、標準出力を即時反映し、pip のキャッシュを残さない
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# コンテナ内の作業ディレクトリを /workspace に設定する
WORKDIR /workspace

# パッケージのインストールに必要な最低限のビルドツールと取得用コマンドを入れ、APT のキャッシュを削除する
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl wget && rm -rf /var/lib/apt/lists/*

# 依存関係を先にコピーしてインストールし、Docker のレイヤーキャッシュを活かす
COPY requirements.txt /workspace/requirements.txt
RUN pip install -r /workspace/requirements.txt

# アプリ本体とデータをコンテナへコピーする
COPY app /workspace/app
COPY data /workspace/data

# Streamlit などで使う 8501 番ポートを公開する
EXPOSE 8501
