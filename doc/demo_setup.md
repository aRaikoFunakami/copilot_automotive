# デモ実施前の設定

## **!!! 課金に注意 !!!**

OpenAI の Realtime API を利用しています。クライアントアプリの "START SERVICE"を押すと "STOP SERVICE"を押すまで音声データが OpenAI とやりとりされ続けています。

デモ終了時にアプリやサービスを終了させないと思わぬ課金が発生してしまう可能性があるので注意が必要です。

## 必要なアプリの確認

### Chromium
[Android向けの最新のChromiumパッケージ](https://github.com/macchrome/droidchrome/tags)をダウンロードしてインストールする。

```
adb install <package>.apk
```


## デモ実施前の確認

デモに不具合が発生した場合はこの処理から再確認すること。


ホストPCからAndroid機器で動作するtermuxにsshでログインする

```terminal:host
ssh -p 8022 u0_a177@192.168.1.81
```

デモに必要な環境変数が設定されていることを確認する. API_KEYが設定されていなかったり、有効期限が切れている場合にはサーバーの起動時にエラーが発生します。

**!!! この API_KEY は秘密情報なので他人と共有しないこと !!!**

```terminal:termux
echo LANGCHAIN_TRACING_V2: $LANGCHAIN_TRACING_V2
echo LANGCHAIN_API_KEY: $LANGCHAIN_API_KEY
echo OPENAI_API_KEY: $OPENAI_API_KEY
echo TAVILY_API_KEY: $TAVILY_API_KEY
```

古いデモ用のプロセスが動作していないかをチェック

```terminal: termux
ps auxw | grep copilot
```

残っていた場合はそのプロセスをKILLする

```terminal: termux
kill <PID>
```

## IPアドレスの確認

デモサーバーが動作するAndroid機器のIPアドレスを確認しておく。
下記の場合には `192.168.1.81` となる

```terminal: termux
ifconfig | grep broadcast
        inet 192.168.1.81  netmask 255.255.255.0  broadcast 192.168.1.255
```

## デモサーバーの起動

デモサーバーのディレクトリに移動

```terminal: termux
cd copilot_automotive/
```

デモサーバーを起動する

```terminal: termux
poetry run python realtime_app.py 
```

次の出力が終了するまで待つ

```
INFO:     Started server process [27945]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:3000 (Press CTRL+C to quit)
```

## デモクライアントの起動

Androidのアプリ選択画面で `AIClient` アプリを起動する

![icon](/doc/img/aiclient_icon.png)

## デモクライアントの初期設定

### デモサーバーのIPアドレスを指定する

先ほど確認したIPアドレスをURLに指定する。変更した場合は更新ボタンを押す。

`192.168.1.81` の場合には `ws://192.168.1.81:3000/ws` となる

### 車載センター情報を指定する

つぎの３つのデータを設定する。
値を変更した場合は次のサーバーとのやりとりから自動で反映される。

- 車内温度 (°C)
- 車両速度 (km/h)
- 燃料レベル (%)

### 現在地を指定する

つぎの３つから選択可能する。
選択を変更した場合は次のサーバーとのやりとりから自動で反映される。

- ACCESS本社
- ラスベガスのコンベンションセンター
- GPSで取得した緯度経度

![icon](/doc/img/main.png)


## デモ開始

`START SERVICE` ボタンを押す

![icon](/doc/img/start.png)


## デモ終了

### クライアント側をSTOP
`STOP SERVICE` ボタンを押す

![icon](/doc/img/stop.png)


### サーバー側をSTOP

Termuxで　`[Ctrl-C]` でデモサーバーを終了する
