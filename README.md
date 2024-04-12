# copilot_automotive

Android Automotive OS(AAOS)をLLM(ChatGPT)を通して音声操作するデモを構築する。
現時点ではAndroid Tablet向けで動作するコンセプトデモであるため、AAOSで動作させる場合には修正が必要となる。

## AOSPとAAOSとGASの関係

### [Android Open Source Project(AOSP)](https://source.android.com/?hl=ja)
オープンソースとしてAndroid OSを開発するプロジェクト。オープンソースのAndroid OSを指してAOSPと呼ばれる場合がある。

### [Android Auto](https://developer.android.com/cars?hl=ja)
ユーザーのスマートフォン上で動作するプラットフォーム。AndroidOSが搭載されたスマートフォンをUSB接続を介して互換性のある車載インフォテインメントシステム(IVI)に接続しAndroid OSのアプリをを車載画面で動作させる。IVIにはAndroid Autoの描画とイベントを管理する特殊なプリケーションを予め組み込んでおく。アプリケーションを動作させrているのはあくまでスマホ側の機器である。Android Automotive OS(AAOS)とAndroid Autoは名前が似ていることもあり適切に用語を使わないと議論が混乱することもある。

### [Android Automotive OS(AAOS)](https://source.android.com/docs/devices/automotive/start/what_automotive?hl=ja)
AOSPの一部として開発されている車載向けのOSである。Googleのアプリやサービスが組み込まれてない状況であればOSSのOSである。
Androidを拡張して車載向けに機能を拡張・カスタマイズしたもの。基本的にはスマホやタブレット向けAndroidと同等だが一部機能が特殊であったり車載向けにはサポートしない機能があったりする。

### [Google Automotive Services(GAS)](https://source.android.com/docs/devices/automotive/start/what_automotive?hl=ja#google-automotive-services-gas)
GASは、AAOSにおけるGoogleのサービスパッケージ。これは、Google Play ストア、Google マップ、Google アシスタントなど、Googleのブランドサービスを含む一連のアプリケーションとサービスを提供する。

# 動作確認環境
- Android Tablet: SAMSUNG Tab S5e (SM-T720)
- Android OS: 9
- ホストPC: M3 Macbook Pro (macOS:14.2.1)

# デモ環境構築 

デモを動作させる環境の構築方法を示す。デモ環境として２種類用意した。
1. Android機器とホストPC
2. Android機器のみ

## 1. Android機器とホストPCの組み合わせでのデモ環境

開発中に利用している環境だ。

### ホストPCにCopilotサーバーを用意する

ソースコードの取得とpython環境のインストールを行う。git, python, poetry などはすでにインストールされていることを前提とする。
```terminal
git clone https://github.com/aRaikoFunakami/copilot_automotive.git
cd copilot_automotive
poetry install
```

Copilotサーバーを実行する
```terminal
poetry run python app.py
```

### Android機器にクライアントアプリケーションを用意する

Android StudioでGithubの設定を行い、クライアントアプリケーションの[ソースコード](https://github.com/aRaikoFunakami/MyServiceApp.git)を取得しビルドする


## 2. Android機器のみのデモ環境

客先でデモを実施する場合に利用する。

### Android上にCopilotサーバーを用意する

Android上でLinux環境を実現するTermuxをインストールする
- https://qiita.com/rairaii/items/c45d19179cda01054a0e

TermuxにFlask環境を用意する
- https://qiita.com/rairaii/items/183bab10869ab52c0531

Copilotサーバーを用意する

```terminal:Termuxで実行する
pkg install git
git clone https://github.com/aRaikoFunakami/copilot_automotive.git
cd copilot_automotive
```

必要なライブラリをインストールする (Poetryのnumpyがpython3.11で動作しないため現状ではpipを使う)。その他必要なライブラリをインストールする
```terminal:Termuxで実行する
pkg install -y rust binutils python-cryptography flask openai langid langchain python-numpy
```

#### デモ用のSelenium環境をインストールする
Chromeの音声コントロールデモで利用しているSeleniumをインストールする。
- [TermuxへのSeleniumとWebDriverのインストールと設定方法](https://github.com/luanon404/Selenium-On-Termux-Android)

Seleniumのインストール

```terminal:Termuxで実行する
yes | pkg update -y && yes | pkg upgrade -y
yes | pkg install python-pip -y
pip install selenium==4.9.1
```
Android SDKのインストール

```terminal:Termuxで実行する
yes | pkg install wget -y
cd $HOME
wget https://github.com/Lzhiyong/termux-ndk/releases/download/android-sdk/android-sdk-aarch64.zip
unzip android-sdk-aarch64.zip -d android-sdk
rm -r android-sdk-aarch64.zip
echo "export ANDROID_HOME=$HOME/android-sdk" >> $HOME/.bashrc
echo "export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/tools/bin:$ANDROID_HOME/platform-tools" >> $HOME/.bashrc
```

WebDriverのインストール
```terminal:Termuxで実行する
yes | pkg install android-tools -y
yes | pkg install x11-repo -y
yes | pkg install tur-repo -y
yes | pkg install chromium -y
```

glibの依存関係でchromiumのインストールに失敗した場合は依存関係を解決する
```terminal:Termuxで実行する
pkg install glib=2.78.1-1
pkg install chromium
```

ホストPC側からAndroidをUSB接続からtcpip接続に変更する。tcpip接続に変更しないとTermulのホストのAndroidデバイスを認識しない。
```terminal: ホストPC
adb tcpip 5555
```

Termux側でAndroidに接続
```terminal: Termuxで実行
adb kill-server
adb devices
```

デバイスが emulator として見える
```terminal
List of devices attached
emulator-5554	unauthorized
```

#### Copilotサーバーを実行する
```terminal:Termuxで実行する
python app.py
```

### Android機器にクライアントアプリケーションを用意する

1. Android機器とホストPCと同じ作業を行う


# デモの実施方法


