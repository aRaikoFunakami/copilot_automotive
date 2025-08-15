# Realtime API 対応アプリサーバーのセットアップと使用方法

このプロジェクトでは、`uv` を使用してライブラリを管理しています。

## セットアップ手順

以下の手順でリポジトリをクローンし、必要な依存関係をインストールしてください。

```bash
git clone https://github.com/aRaikoFunakami/copilot_automotive.git
cd copilot_automotive
./setup.sh
uv sync
```

## 認証トークンの設定

アプリケーションは `AUTH_TOKEN` を使用してアクセス制限を行います。以下の手順で環境変数に `AUTH_TOKEN` を設定してください。

```bash
export AUTH_TOKEN="<your AUTH_TOKEN>"
```

サーバー側とクライアント側で同じ値を設定する必要があります。

## アプリサーバーの起動

OpenAI の Realtime API に対応したアプリサーバーをテキストモードで起動するには、以下のコマンドを実行します。

```bash
OPENAI_VOICE_TEXT_MODE=1 uv run python realtime_app.py
```

音声モードの場合

```bash
uv run python realtime_app.py
```

## WebSocket サーバーへの接続

起動したサーバーに WebSocket を使用して接続するには、以下のコマンドを使用します。

```bash
wscat -c "ws://localhost:3000/ws?token=${AUTH_TOKEN}"
```

接続が成功すると、以下のようなメッセージが表示されます。

```bash
Connected (press CTRL+C to quit)
< {"type": "client_id", "client_id": "0baa5e51-2708-43e8-8700-321a8ffffcfd"}
> what can you do
< I can assist you with a variety of tasks, such as answering questions, providing information, helping with language translation, offering recommendations, and controlling certain smart devices like air conditioning. I can also perform searches on the internet, guide you to a location, and find videos on YouTube. Let me know how I can help!
>
```

## 機能概要

このアプリケーションは以下の機能を提供します：

- 質問への回答
- 情報提供
- 言語翻訳の支援
- 推薦の提供
- スマートデバイス（例: エアコン）の制御
- インターネット検索
- ナビゲーション案内
- YouTube 動画の検索
- TMDB検索
