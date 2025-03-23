- [x] ビデオProposalのときに喋るようにする
  
- シナリオ切り替え
  - [x]ユーザー切り替えページにデモ切り替えを追加する
  - そこからシナリオ切り替える（ログインのときと同じ仕組み）
    - [x] realtime_app.py で demo_action を受け取るとクライアントにそのデータを転送する
    - [x] 転送と平行してにそのactionにあったダミーデータをアシストAIにわたす
    - [x] クライアントは demo_action を受け取ると、
      - [x] Intent で demo_template を見に行かせる
        - [x] Demo Page: http://localhost:3000/demo_action/start_autonomous
        - [x] Demo Page: http://localhost:3000/demo_action/start_ev_charge
    - [x] クライアント側ではデモ時のダミーデータは扱わない
- [x] 動画表示のアップデート
  - [x] 動画表示中は音声入力を切る
  - [x] 動画表示のChromeがKILLされたら音声入力を入れる
  - [x] 動画表示以外の場合は音声入力を入れたまま


