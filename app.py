from flask import Flask, render_template, request, jsonify
import openai
import os, json, tempfile
import logging
import threading
import config
from remote_chat import SimpleConversationRemoteChat

language = 'ja'
openai.api_key = "YOUR_API_KEY"
app = Flask(__name__, static_folder="./templates", static_url_path="")

@app.route("/set", methods=["GET"])
def set_language():
    global language
    language = request.args.get('language')
    return language

@app.route("/upload-audio", methods=["POST"])
def upload_audio():
    try:
        audio_data = request.files["audio"].read()
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=True, suffix=".wav"
        ) as temp_file:
            temp_file.write(audio_data)
            with open(temp_file.name, "rb") as temp_read_file:
                response = openai.Audio.transcribe("whisper-1", temp_read_file, language=language)
                #response = openai.Audio.transcribe("whisper-1", temp_read_file)

        transcription = response["text"]
        logging.info(f"transcription {transcription}, language: {language}")
        global remote_chat
        response = remote_chat.llm_run(transcription)
        return jsonify({"transcription": transcription,
                        "response": response,
                        })
    except Exception as e:
        logging.info(f"Exception: {str(e)}")
        return jsonify({"error": "Server Error"}), 500


@app.route("/")
def index():
    return render_template("index.html")


"""
Bodyの形式
{
  "text": "会話文",
  "carinfo": {
    "language": "ja",
    "fuel_level": "0",
    "vehicle_speed": "0"
  }
}
"""
@app.route('/input', methods=['POST'])
def input_text():
    # JSON データをリクエストから取得
    if request.is_json:
        data = request.get_json()
        text_value = data.get('user_input', '')
        carinfo = data.get('car_info', {})
        # 車情報が辞書であることを確認
        if not isinstance(carinfo, dict):
            return jsonify({'error': 'Invalid carinfo data'}), 400
    else:
        return jsonify({"error": "Request must be JSON"}), 400
    
    # JSON形式でLLMに入力する
    input_json_string = json.dumps(data, indent=2, ensure_ascii=False)
    logging.info(f"input_json_string: {input_json_string}")

    global remote_chat
    response = remote_chat.llm_run(input_json_string)

    # 返り値が文字列の場合、JSONかどうかをチェック
    if isinstance(response, str):
        try:
            # 文字列をJSONとして解析
            parsed_response = json.loads(response)
            # 解析に成功した場合、返り値はJSON形式の文字列
            # response_dataを辞書で更新
            response_data = {
                'received_text': text_value,
                'response_text': ""
            }
            response_data.update(parsed_response)
        except json.JSONDecodeError:
            # JSONとして解析できない場合、通常の文字列として処理
            response_data = {
                'received_text': text_value,
                'response_text': response  # 元の文字列をそのまま使用
            }
    else:
        # 返り値が文字列でない場合の処理
        response_data = {
            'received_text': text_value,
            'response_text': "Invalid response type"
        }

    logging.debug(response_data)
    return jsonify(response_data) 

def run_server():
    app.run(host="0.0.0.0", port=8080, debug=True, use_reloader=False)

def chat():
    global remote_chat
    chat = remote_chat
    while True:
        user_input = input("Enter the text to search (or 'exit' to quit): ")
        if user_input.lower() == "exit":
            break
        chat.llm_run(user_input)

if __name__ == "__main__":
    logging.basicConfig(
        format="[%(asctime)s] [%(process)d] [%(levelname)s] [%(filename)s:%(lineno)d %(funcName)s] [%(message)s]",
        level=logging.INFO,
    )
    # Start the web server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    openai.api_key = config.keys["openai_api_key"]
    remote_chat = SimpleConversationRemoteChat(history=None)

    # debug
    chat()


