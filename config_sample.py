import os

keys = {
    "openai_api_key": "<YOUR OPENAI ID>",
    "launcher": "http://<YOUR IP ADDRESS>:8080/launcher.html",
    "model_name": "gpt-3.5-turbo-0613",
}

def load():
    os.environ["OPENAI_API_KEY"] = keys["openai_api_key"]