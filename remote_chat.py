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
from langchain_community.vectorstores import Chroma
from langchain.tools import BaseTool
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

# init openai
import config


LAUNCHER_HTML = config.keys["launcher"]
model_name = config.keys["model_name"]
test = None
lang_id = "ja"


# Weather
from openai_function_weather import get_weather_info
class WeatherInfoInput(BaseModel):
    latitude: float = Field(descption="latitude")
    longitude: float = Field(descption="longitude")

class WeatherInfo(BaseTool):
    name = "get_weather_info"
    description = "This is useful when you want to know the weather forecast. Enter longitude in the latitude field and latitude in the longitude field."
    args_schema: Type[BaseModel] = WeatherInfoInput

    def _run(self, latitude: float, longitude: float):
        logging.info(f"get_weather_info(latitude, longitude)")
        return get_weather_info(latitude, longitude)

    def _arun(self, ticker: str):
        raise NotImplementedError("not support async")

# Googla Map Navigationを起動する
class LaunchNavigationInput(BaseModel):
    latitude: float = Field(descption="Specify the Latitude of the destination.")
    longitude: float = Field(description="Specify the longitude of the destination")


class LaunchNavigation(BaseTool):
    name = "intent_googlenavigation"
    description = (
        "Use this function to provides route guidance to a specified location."
    )
    args_schema: Type[BaseModel] = LaunchNavigationInput
    return_direct = True  # if True, Tool returns output directly

    def _run(self, latitude: float, longitude: float):
        logging.info(f"lat, lon = {latitude}, {longitude}")
        response = {
            'intent' : {
                'navigation' : {
                    'navi_application' : "googlemap",
                    'latitude' : latitude,
                    'longitude' : longitude,
                },
            },
        }
        logging.info(f"response: {response}")
        return json.dumps(response, ensure_ascii=False)
        #return response

    def _arun(self, ticker: str):
        raise NotImplementedError("not support async")

# AirControl
class AirControlInput(BaseModel):
    temperature_delta: float = Field(descption="""Specify the temperature to be raised or lowered relative to the current temperature setting. 
                            Specify the value at which the temperature is to be raised or lowered in 0.5 degree increments according to the content of the conversation. 
                            For example, if the temperature in the room feels very hot, lower the temperature by 3 degrees.
                            If you feel the temperature in the room is a little cold, increase the temperature by 1 degree.
                            """)

class AirControl(BaseTool):
    name = "intent_aircontrol"
    description = (
        "Use this function to adjust the temperature of an air conditioner based on sensory temperature information."
    )
    args_schema: Type[BaseModel] = AirControlInput
    return_direct = True  # if True, Tool returns output directly

    def _run(self, temperature_delta: float):
        logging.info(f"temperature_delta = {temperature_delta}")
        response = {
            'intent' : {
                'aircontrol' : {
                    'temperature_delta' : temperature_delta,
                },
            },
        }
        logging.info(f"response: {response}")
        return json.dumps(response, ensure_ascii=False)

    def _arun(self, ticker: str):
        raise NotImplementedError("not support async")
    
# AirControl with absolute value
class AirControlAbsoluteValueInput(BaseModel):
    temperature: float = Field(descption="""Set the temperature in absolute values.
                            For example, it accepts an instruction to set the temperature to 27°C.
                            Set the temperature in 0.5° increments. For example, specify 10°, 10.5° and 11°.
                            """)

class AirControlAbsoluteValue(BaseTool):
    name = "intent_aircontrol_absolute_value"
    description = (
        "Use this function to set the temperature of the air conditioner based on the target temperature."
    )
    args_schema: Type[BaseModel] = AirControlAbsoluteValueInput
    return_direct = True  # if True, Tool returns output directly

    def _run(self, temperature: float):
        logging.info(f"temperature = {temperature}")
        response = {
            'intent' : {
                'aircontrol' : {
                    'temperature' : temperature,
                },
            },
        }
        logging.info(f"response: {response}")
        return json.dumps(response, ensure_ascii=False)
        #return response

    def _arun(self, ticker: str):
        raise NotImplementedError("not support async")


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
        WeatherInfo(),
        LaunchNavigation(),
        AirControl(),
        AirControlAbsoluteValue(),
    ]
    prompt_init = """
	You are an assistant who helps with the operation of Invhiecle Infotainment (IVI). Drivers can talk to you, enjoy general conversation and ask you to operate the IVI. Your job is to help operate the IVI by invoking the functions added by function call.

    #Applications included in the IVI
    - car navigation applications
    - Air conditioner control application

    #Limitations.
    - Answer in the language entered.
    - You must not lie
    - Ask the driver if you need additional information
    - Ask the driver if you are missing information needed to help you operate the IVI

    Respond in the same language as the input text
	"""

    def __init__(self, history):
        config.load()
        global test
        #test = RemoteChrome()
        #test.set_start_url(LAUNCHER_HTML)
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
                # request_timeout=15,
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
        while True:
            user_input = input("Enter the text to search (or 'exit' to quit): ")
            if user_input.lower() == "exit":
                break
            chat.llm_run(user_input)

    # Run the chat in the main thread
    chat()
