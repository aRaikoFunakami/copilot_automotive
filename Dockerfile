# Python 3.13 の軽量イメージを使用
FROM python:3.13-slim

# 環境変数の設定（出力をバッファリングしないように設定）
ENV PYTHONUNBUFFERED=1

# 作業ディレクトリを設定
WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry \
    && rm -rf /var/lib/apt/lists/*


# アプリケーションコードをコピー
COPY . .

# 依存ライブラリをインストール
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root
COPY . .

# 環境変数を Docker 経由で設定できるようにする
ENV OPENAI_API_KEY=""
ENV TAVILY_API_KEY=""
ENV AUTH_TOKEN=""
ENV HOST_IP=""

# ポート 3000 を公開
EXPOSE 3000

# アプリケーションの実行
CMD ["poetry", "run", "python", "realtime_app.py"]