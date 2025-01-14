import datetime
import json
import logging
from typing import Any, Type
from pydantic import BaseModel, Field
import threading
import queue
import langid
import time
from flask import Flask, render_template, request, jsonify

#
# LangChain related test codes
#
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from controller_chrome import ChromeController
import function_seach_videos
import function_play_video
import function_weather
import function_launch_navigation
import function_aircontrol

# init openai
import config

model_name = config.keys["model_name"]
lang_id = "ja"


class ThreadedGenerator:
    def __init__(self):
        self.queue = queue.Queue()

    def __iter__(self):
        return self

    def __next__(self):
        item = self.queue.get()
        if item is StopIteration:
            raise item
        return item

    def send(self, data):
        self.queue.put(data)

    def close(self):
        self.queue.put(StopIteration)


class ChainStreamHandler(StreamingStdOutCallbackHandler):
    def __init__(self, gen):
        super().__init__()
        self.gen = gen

    def on_llm_new_token(self, token: str, **kwargs):
        self.gen.send(token)


class SimpleConversationRemoteChat:
    tools = [
        # Get current weather from latitude and longitude information
        # function_weather.WeatherInfo(), covered by TavilySearchResults
        function_launch_navigation.LaunchNavigation(),
        function_aircontrol.AirControl(),
        function_aircontrol.AirControlDelta(),
        function_seach_videos.SearchVideos(),
        function_play_video.SelectLinkByNumber(),  # Play Video by Number
        # Get the latest informaion : export TAVILY_API_KEY="tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        TavilySearchResults(
            max_results=2,
            include_images=False,
            include_raw_content=False,
            search_depth="advanced",
        ),
    ]
    prompt_init = """
    # Role
    You are "NetFront Copilot," an assistant dedicated to operating the In-Vehicle Infotainment (IVI) system in automobiles. You engage in conversations with drivers, respond to their commands, and control the IVI system functionalities through function calls. Your primary goal is to assist drivers in a friendly and efficient manner. If you encounter unknown queries, you should ask clear questions to gather the necessary information from the driver.

    # Applications in the IVI
    - Car Navigation
    - Air Conditioner Control
    - Weather Forecasts
    - Interneet seach by TavilySearchResults
    - Car Information Monitoring

    # Car Information
    - Continuously monitor `car_info` for vital vehicle data.
    - Alert the driver if the vehicle speed exceeds 120 km/h, suggesting slowing down to ensure safety.
    - Alert refueling if the fuel level drops below 30%, ensuring the driver is aware of the need to refuel to avoid running out of fuel.

    # Guidelines
    - Always respond in the language of the input.
    - Maintain honesty in all interactions.
    - When unclear about the driver's instructions, ask specific questions to clarify.
    - If additional information is needed to proceed with an operation, request it directly from the driver.
    - Aim to provide comprehensive responses but keep the tone conversational.
    - Characters that cannot be pronounced must not be included in the answer
    - Please provide your response in plain text, without using Markdown or any special formatting.

    # Function Calling
    Invoke specific functions based on the driver's commands to control:
    - The car's navigation system.
    - The interior temperature settings.
    - The air conditioning system.
    - Display relevant weather forecasts.
    - Monitor and report car performance and safety features.

    # Response Protocol
    - Respond in the same language as the received input.
    - If the car_info specifies a language, use that language for responses.

    # Input Format
    User input is provided in JSON format, which includes two main components:

    - `car_info`: This object contains various details about the vehicle. Examples of the data fields in `car_info` include:
    - `vehicle_speed`: The current speed of the vehicle expressed in kilometers per hour.
    - `fuel_level`: The current fuel level as a percentage, where 100% indicates a full tank.
    - `language`: The preferred language setting for IVI responses, specified as an ISO language code (e.g., "en" for English, "ja" for Japanese).
    - `vehicle_model`: The model of the car.
    - `vehicle_year`: The manufacturing year of the car.
    - `engine_type`: Type of engine, such as diesel, petrol, electric, or hybrid.
    - `gps_coordinates`: Current GPS coordinates of the vehicle, formatted as latitude and longitude.
    
    - `user_input`: Direct instructions or queries from the driver, provided as a string. This might include requests for navigation directions, climate control adjustments, or general queries about the vehicle or driving conditions.
    """

    def __init__(self, history):
        self.chromeController = ChromeController.get_instance()
        # ChatModel
        self.memory = MemorySaver()
        self.model = ChatOpenAI(
            temperature=0,
            model=model_name,
        )
        self.agent_executor = create_react_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=self.memory,
        )
        # Model for speech
        self.model_speech = ChatOpenAI(
            temperature=0.3,
            model=model_name,
        )

    def __del__(self):
        self.quit()

    def quit(self):
        try:
            self.chromeController.quit()
        except Exception as e:
            logging.warning(f"Failed to quit ChromeController: {e}")
        print("quit")

    def generator(self, user_message):
        g = ThreadedGenerator()
        threading.Thread(target=self.llm_thread, args=(g, user_message)).start()
        return g

    def llm_thread(self, g, user_message):
        try:
            global lang_id
            lang_id = langid.classify(user_message)[0]
            logging.debug(f"memory: {self.memory}")
            logging.info(f"lang_id: {lang_id}")

            # set thread_id for each thread for MemorySaver
            thread_config = {
                "configurable": {
                    "thread_id": "this shall be managed for each connection"
                }
            }
            response = self.agent_executor.invoke(
                {"messages": [HumanMessage(content=user_message)]}, thread_config
            )
            content = response["messages"][-1].content
            logging.info(
                f"===content===content===content===content===content===content==="
            )
            logging.info(f"content: {content}")
            logging.info(
                f"===content===content===content===content===content===content==="
            )

            # 返り値が文字列の場合、JSONかどうかをチェック
            if isinstance(content, str):
                try:
                    # agentの回答がJSON形式の場合には何もしない
                    json.loads(content)
                except json.JSONDecodeError:
                    # agentの回答が通常の文字列の場合には機械で読み上げるためのテキストに変換
                    messages = [
                        SystemMessage(
                            content="""Transform the following text into a format suitable for machine reading. Ensure the text is concise, clear, and uses appropriate punctuation for natural reading. Remove unnecessary references, links, or metadata that are not essential for understanding. Simplify abbreviations, symbols, or terms like "km" or "%" by converting them into their full forms. If the text includes bullet points or lists, adjust the structure to create a natural flow for reading aloud. Ensure the output is optimized for natural-sounding speech."""
                        ),
                        HumanMessage(content=response["messages"][-1].content),
                    ]
                    message = self.model_speech.invoke(messages)
                    content = message.content
                    logging.info(
                        f"===content_for_speech===content_for_speech===content_for_speech==="
                    )
                    logging.info(f"content for speach: {content}")
                    logging.info(
                        f"===content_for_speech===content_for_speech===content_for_speech==="
                    )
            else:
                # 返り値が文字列でない場合の処理
                logging.exception("content is not string")

            return content
        finally:
            g.close()

    def llm_run(self, user_message):
        """sync call llm_thread directly instead of chat.generator(user_input)"""
        g = ThreadedGenerator()
        return self.llm_thread(g, user_message)


test_user_input = {
    "car_info": {
        "vehicle_speed": "300",
        "vehicle_speed_description": "Indicates the current speed of the vehicle. Unit is km. 60 means 60 km.",
        "fuel_level": "12",
        "fuel_level_description": "Fuel level in %, where 75 means 75%.",
        "language": "ja",
    },
    "today": datetime.date.today().strftime("%Y-%m-%d"),
    "current_time": datetime.datetime.now().strftime("%H:%M:%S"),
    "user_input": "横浜の観光の名所は？あと富士山の高さは？そして今日の横浜の天気は",
}


auto_test = True

auto_test_queries = [
    "今日は、私の名前はボブです。あなたの名前は？",
    "今日の日付は",
    "今何時？",
    "私の名前を覚えていますか？",
    "エアコンの温度を二度上げて",
    "明日の横浜の天気は？",
    "横浜の観光名所は？",
    "山下公園の緯度と軽度は？",
    "山下公園までのルートを教えて",
    "フリーレンの動画を検索して",
]

if __name__ == "__main__":
    logging.basicConfig(
        format="[%(asctime)s] [%(process)d] [%(levelname)s] [%(filename)s:%(lineno)d %(funcName)s] [%(message)s]",
        level=logging.INFO,
    )

    def chat():
        chat = SimpleConversationRemoteChat("")

        # auto test
        if auto_test == True:
            for query in auto_test_queries:
                test_user_input["user_input"] = query
                print("query = ", test_user_input)
                chat.llm_run(json.dumps(test_user_input, ensure_ascii=False))
            time.sleep(10)
            return

        # manual test
        while True:
            user_input = input("Enter the text to search (or 'exit' to quit): ")
            if user_input.lower() == "exit":
                break
            test_user_input["user_input"] = user_input
            chat.llm_run(json.dumps(test_user_input, ensure_ascii=False))
        # return chat.llm_run(test_user_input)

    # Run the chat in the main thread
    chat()
