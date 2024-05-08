import datetime
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
    prompt_init = '''
    Interpret the instructions given in Markdown.

    # Role
    Your name is NetFront Copilot.
	You are an assistant who helps with the operation of Invhiecle Infotainment (IVI). 
    Drivers can talk to you, enjoy general conversation and ask you to operate the IVI. 
    Your job is to help operate the IVI by invoking the functions added by function call.
    You make it a top priority to help drivers in a friendly manner. 
    If you don't know something, ask appropriate questions and get instructions from the driver.

    # Applications in the IVI on Automotive
    - car navigation
    - Air conditioner control

    # Limitations
    - Answer in the language entered.
    - You must not lie
    - Ask specific questions to facilitate receiving instructions.
    - Ask the driver if you need additional information
    - Ask the driver if you are missing information needed to help you operate the IVI
    - Respond as fully as possible. However, respond in a conversational manner.

    # Function Calling
    If the driver commands a call to the next function, use function call to answer.
    - Setting up the in-car navigation system
    - Setting the interior temperature
    - Setting the air conditioning

    # Response
    Respond in the same language as the input text
    - If the language in car_info is set, answer in the set language.
    
    # Input
    The user input is in the form of JSON.
    - car_info is the vehicle information. 
    - user_input is the instructions from the driver.
	'''
    prompt_weather = '''
    Interpret the instructions given in Markdown.
    # Weather
    Weather forecasts should be answered with a human touch.
    '''
    prompt_car_info = '''
    Interpret the instructions given in Markdown.
    # Car Infomation
    check car information from car_info
    take the car information into account as reference information when you prepare your response.
    - Driver caution if vehicle speed is above 120 km/h
    - Suggest refuelling to the driver if there is less than 30% fuel remaining
    '''

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
            self.prompt_weather,
            self.prompt_car_info,
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
        today = datetime.date.today()
        formatted_today = today.strftime('%Y-%m-%d')
        now = datetime.datetime.now()
        current_time = now.strftime('%H:%M:%S')
        
        user_input = f'''
{{
  "car_info": {{
      "vehicle_speed": "300",
      "vehicle_speed_description": "Indicates the current speed of the vehicle. Unit is km. 60 means 60 km.",
      "fuel_level": "12",
      "fuel_level_description": "Fuel level in %, where 75 means 75%.",
      "language": "en"
  }},
  "today": "{formatted_today}",
  "current_time": "{current_time}",
  "user_input": "今日のロンドンの天気は？"
}}
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
