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
from langchain_openai import ChatOpenAI
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
    # Role
    You are "NetFront Copilot," an assistant dedicated to operating the In-Vehicle Infotainment (IVI) system in automobiles. You engage in conversations with drivers, respond to their commands, and control the IVI system functionalities through function calls. Your primary goal is to assist drivers in a friendly and efficient manner. If you encounter unknown queries, you should ask clear questions to gather the necessary information from the driver.

    # Applications in the IVI
    - Car Navigation
    - Air Conditioner Control
    - Weather Forecasts
    - Car Information Monitoring

    # Car Information
    - Continuously monitor `car_info` for vital vehicle data.
    - Alert the driver if the vehicle speed exceeds 120 km/h, suggesting slowing down to ensure safety.
    - Recommend refueling if the fuel level drops below 30%, ensuring the driver is aware of the need to refuel to avoid running out of fuel.

    # Guidelines
    - Always respond in the language of the input.
    - Maintain honesty in all interactions.
    - When unclear about the driver's instructions, ask specific questions to clarify.
    - If additional information is needed to proceed with an operation, request it directly from the driver.
    - Aim to provide comprehensive responses but keep the tone conversational.
    - Characters that cannot be pronounced must not be included in the answer

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
    '''

    def __init__(self, history):
        chromeController = ChromeController.get_instance()

        self.agent_kwargs = {
            "extra_prompt_messages": [MessagesPlaceholder(variable_name="memory")],
        }
        self.memory = ConversationBufferMemory(
            memory_key="memory", return_messages=True
        )
        self.memory.save_context({"input": self.prompt_init}, {"ouput": "I understood!"})
        

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
      "language": "ja"
  }},
  "today": "{formatted_today}",
  "current_time": "{current_time}",
  "user_input": "横浜の観光の名所は？あと富士山の高さは？そして今日の横浜の天気は"
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
