from starlette.responses import HTMLResponse
from starlette.applications import Starlette
from starlette.routing import Route
import uvicorn

from network_utils import get_local_ip  # Get the server IP

SERVER_IP = get_local_ip()

DUMMY_CLIENT_ID = "test1234"
connected_clients = {}

JP_PROMPT = """
あなたは日本語で応答する AI アシスタントです。
ユーザーが名前を入力し、ログインを完了したときに、
「<ユーザー名>さん、ログインありがとうございます。」という形で返答してください。

例:
- ユーザー名: たけし → 応答: 「たけしさん、ログインありがとうございます。」
- ユーザー名: Kotaro → 応答: 「Kotaroさん、ログインありがとうございます。」

以下はログインが完了したユーザー名です。
"""

EN_PROMPT = """
You are an AI assistant that responds in English.
When a user enters their name and completes the login process,
you should respond in the format: "<User Name>, thank you for logging in."

Examples:
- User Name: Takeshi → Response: "Takeshi, thank you for logging in."
- User Name: Kotaro → Response: "Kotaro, thank you for logging in."

Below is the name of the user who has completed the login process.
"""

async def dummy_login(request, connected_clients):
    """Connects the client to the WebSocket and sends a message automatically."""
    client_id = request.query_params.get("client_id")
    if not client_id or client_id not in connected_clients:
        return HTMLResponse("<h2>Invalid client ID</h2>", status_code=400)

    # Python変数を埋め込むため、単なる """ 文字列
    raw_html = r"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smart Login</title>
        <script src="https://unpkg.com/i18next@latest/dist/umd/i18next.min.js"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Arial', sans-serif;
            }
            body {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
                color: white;
                text-align: center;
            }
            .container {
                width: 90%;
                max-width: 400px;
                padding: 20px;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                box-shadow: 0 4px 10px rgba(255, 255, 255, 0.2);
            }
            h2 {
                font-size: 24px;
                margin-bottom: 20px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .button {
                display: block;
                width: 100%;
                padding: 15px;
                margin: 10px 0;
                font-size: 18px;
                font-weight: bold;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
                background: linear-gradient(45deg, #00c6ff, #0072ff);
                box-shadow: 0 4px 15px rgba(0, 198, 255, 0.5);
            }
            .button:hover {
                transform: scale(1.05);
                background: linear-gradient(45deg, #0072ff, #00c6ff);
            }
            .lang-button {
                display: inline-block;
                padding: 12px 20px;
                margin: 10px 5px;
                font-size: 16px;
                font-weight: bold;
                color: white;
                border: 2px solid white;
                border-radius: 50px;
                cursor: pointer;
                transition: all 0.3s ease;
                background: rgba(255, 255, 255, 0.1);
                box-shadow: 0 3px 10px rgba(255, 255, 255, 0.2);
            }
            .lang-button:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: scale(1.1);
            }
            #status {
                margin-top: 15px;
                font-size: 16px;
                font-weight: bold;
                color: #00c6ff;
            }
            .lang-selection {
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-bottom: 20px;
            }
        </style>
        <script>
            let ws;
            let lang = "en";  // Default language is English
            const resources = {
                en: {
                    translation: {
                        "title": "Select Your Login",
                        "login": "Logging in...",
                        "success": " logged in successfully.",
                        "names": ["Takeshi", "Akiko", "Kotaro"],
                        "message": "{{EN_PROMPT}} My name is {{name}}.",
                        "lang": "Language Selection"
                    }
                },
                ja: {
                    translation: {
                        "title": "ログインを選択してください",
                        "login": "ログインしています...",
                        "success": " でログインしました。",
                        "names": ["たけし", "あきこ", "こたろう"],
                        "message":  "{{JP_PROMPT}} 名前は {{name}} です",
                        "lang": "言語選択"
                    }
                }
            };

            window.onload = function () {
                // {SERVER_IP} と {client_id} はあとでPythonで置換
                ws = new WebSocket("ws://{SERVER_IP}:3000/ws");

                ws.onopen = function () {
                    console.log("WebSocket connected.");
                };
                ws.onmessage = function (event) {
                    document.getElementById("status").innerText = event.data;
                };
                ws.onclose = function () {
                    console.log("WebSocket closed.");
                };
                ws.onerror = function (error) {
                    console.error("WebSocket error:", error);
                };

                i18next.init({
                    lng: lang,
                    debug: true,
                    resources
                }, function (err, t) {
                    updateLanguage();
                });
            };

            function sendLogin(index) {
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    document.getElementById("status").innerText = "WebSocket connection error.";
                    return;
                }
                const nameArr = i18next.t("names", { returnObjects: true });
                const name = nameArr[index];
                document.getElementById("status").innerText = i18next.t("login");

                const message = {
                    type: "send_to_client",
                    target_id: "{client_id}",
                    message: i18next.t("message", { name: name })
                };
                ws.send(JSON.stringify(message));

                setTimeout(() => {
                    document.getElementById("status").innerText = name + i18next.t("success");
                }, 2000);
            }

            function changeLanguage(selectedLang) {
                lang = selectedLang;
                i18next.changeLanguage(lang, updateLanguage);
            }

            function updateLanguage() {
                document.getElementById("title").innerText = i18next.t("title");
                const nameArr = i18next.t("names", { returnObjects: true });
                document.getElementById("btn1").innerText = nameArr[0];
                document.getElementById("btn2").innerText = nameArr[1];
                document.getElementById("btn3").innerText = nameArr[2];
                document.getElementById("langLabel").innerText = i18next.t("lang");
            }
        </script>
    </head>
    <body>
        <div class="container">
            <h2 id="title">Select Your Login</h2>

            <p id="langLabel" style="font-size: 18px; margin-bottom: 10px;">Language Selection</p>
            <div class="lang-selection">
                <button class="lang-button" onclick="changeLanguage('en')">English</button>
                <button class="lang-button" onclick="changeLanguage('ja')">日本語</button>
            </div>

            <button id="btn1" class="button" onclick="sendLogin(0)">Takeshi</button>
            <button id="btn2" class="button" onclick="sendLogin(1)">Akiko</button>
            <button id="btn3" class="button" onclick="sendLogin(2)">Kotaro</button>

            <p id="status"></p>
        </div>
    </body>
    </html>
    """

    # Pythonで .replace() する: {SERVER_IP} と {client_id} を実際の値に置換
    final_html = raw_html.replace("{SERVER_IP}", SERVER_IP)
    final_html = final_html.replace("{client_id}", client_id)

    return HTMLResponse(final_html)


async def dummy_login_with_clients(request):
    # ダミー接続情報登録
    DUMMY_CLIENT_ID = "test1234"
    connected_clients[DUMMY_CLIENT_ID] = {
        "websocket": "dummy",
        "input_queue": "dummy",
        "ai_input_queue": "dummy",
    }
    return await dummy_login(request, connected_clients)


async def homepage(request):
    # /dummy_login に飛ぶリンク
    return HTMLResponse(
        f"<h2>Welcome</h2><p>Access the login page <a href='/dummy_login?client_id=test1234'>here</a>.</p>"
    )

app = Starlette(debug=True, routes=[
    Route("/", homepage),
    Route("/dummy_login", dummy_login_with_clients, methods=["GET"])
])

def main():
    print("Starting Dummy Login Test Server at http://localhost:8000/dummy_login?client_id=test1234")
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()