import json
import logging
from typing import Any, Type
from pydantic import BaseModel, Field
import threading
import queue
import langid
from flask import Flask, render_template, request, jsonify

#
# LangChain related test codes
#
from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain.prompts import MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_models import ChatOpenAI
from langchain.tools import BaseTool
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

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
        function_weather.WeatherInfo(),
        function_launch_navigation.LaunchNavigation(),
        function_aircontrol.AirControl(),
        function_aircontrol.AirControlDelta(),
        function_seach_videos.SearchVideos(),
        function_play_video.SelectLinkByNumber(), #Play Video by Number
        
    ]
    prompt_init = """
	You are an assistant who helps with the operation of Invhiecle Infotainment (IVI). Drivers can talk to you, enjoy general conversation and ask you to operate the IVI. Your job is to help operate the IVI by invoking the functions added by function call.
    Your name is NetFront Copilot.

    #Applications included in the IVI
    - car navigation
    - Air conditioner control

    #Limitations
    - Answer in the language entered.
    - You must not lie
    - Explain your function in a way that makes it easy to receive instructions
    - Ask specific questions to facilitate receiving instructions.
    - Ask the driver if you need additional information
    - Ask the driver if you are missing information needed to help you operate the IVI
    - Respond as fully as possible. However, respond in a conversational manner.

    #Function Calling
    If the driver commands a call to the next function, use function call to answer.
    - Setting up the in-car navigation system
    - Setting the interior temperature
    - Setting the air conditioning

    Respond in the same language as the input text
	"""

    def __init__(self, history):
        chromeController = ChromeController.get_instance()

        self.agent_kwargs = {
            "extra_prompt_messages": [MessagesPlaceholder(variable_name="memory")],
        }
        self.memory = ConversationBufferMemory(
            memory_key="memory", return_messages=True
        )
        prompts = [
            self.prompt_init,
        ]
        for prompt in prompts:
            self.memory.save_context({"input": prompt}, {"ouput": "I understood!"})

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

            llm = ChatOpenAI(
                temperature=0,
                model=model_name,
                openai_api_key=config.keys["openai_api_key"],
            )

            agent_chain = initialize_agent(
                tools=self.tools,
                llm=llm,
                agent=AgentType.OPENAI_FUNCTIONS,
                verbose=True,
                agent_kwargs=self.agent_kwargs,
                memory=self.memory,
            )
            response = agent_chain.run(input=user_message)
            return response
        finally:
            g.close()

    def llm_run(self, user_message):
        """sync call llm_thread directly instead of chat.generator(user_input)"""
        g = ThreadedGenerator()
        return self.llm_thread(g, user_message)


if __name__ == "__main__":
    logging.basicConfig(
        format="[%(asctime)s] [%(process)d] [%(levelname)s] [%(filename)s:%(lineno)d %(funcName)s] [%(message)s]",
        level=logging.INFO,
    )

    def chat():
        
        chat = SimpleConversationRemoteChat("")
        user_input = '''
あなたはIVIに組み込まれたユーザーをサポートとするエージェントです。
現在の車両状況を解釈して条件に従い必要な提案を行いなさい。
車両情報はCOVESAのVehicle Signal Specification(VSS)の仕様に基づいて解釈しなさい
# 車両情報
{
    "VehicleLanguage": {
        "path": "Vehicle.Cabin.Infotainment.LanguageSetting",
        "value": "Japanese"
    },
    "VehicleSpeed": {
        "path": "Vehicle.Speed",
        "value": 80
    },
    "FuelLevel": {
        "description" : "100 means 100%. This car drive 500km with full filled fuel."
        "path": "Vehicle.Fuel.Level",
        "value": 10
    }
}
# 条件
車両情報を確認しユーザーにアドバイスする
- 燃料が少ない場合には燃料の補給を促す
- 速度が早すぎる場合には安全運転を促す
- 言語設定にしたがって回答言語を選択する
# ユーザーのインプット

おはようございます。あなたのお名前は？いま東京にいるのですが、北海道までくるまで1000kmドライブして向かいます。
'''
        chat.llm_run(user_input)
        """
        while True:
            user_input = input("Enter the text to search (or 'exit' to quit): ")
            if user_input.lower() == "exit":
                break
            chat.llm_run(user_input)
        """

    # Run the chat in the main thread
    chat()
