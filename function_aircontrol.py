import json
import logging
from typing import Any, Type
from pydantic import BaseModel, Field

from langchain.tools import BaseTool

# 温度変更（相対値）のための入力スキーマ
class AirControlDeltaInput(BaseModel):
    temperature_delta: float = Field(description="""
        Specify the temperature to be raised or lowered relative to the current temperature setting. 
        Adjust the temperature in 0.5 degree increments. 
        For example, decrease by 3 degrees if it's too hot, or increase by 1 degree if it's slightly cold.
    """)

class AirControlDelta(BaseTool):
    name: str = "intent_aircontrol_delta"
    description: str = "Adjust the air conditioner's temperature based on sensory temperature information."
    args_schema: Type[BaseModel] = AirControlDeltaInput
    return_direct: bool = True

    def _run(self, temperature_delta: float):
        logging.info(f"Requested temperature change: {temperature_delta} degrees")
        response = {
            'intent': {'aircontrol_delta': {'temperature_delta': temperature_delta}}
        }
        logging.info(f"Response: {response}")
        return json.dumps(response, ensure_ascii=False)

    def _arun(self, ticker: str):
        raise NotImplementedError("Asynchronous execution is not supported.")

# 絶対温度設定のための入力スキーマ
class AirControlInput(BaseModel):
    temperature: float = Field(description="""
        Set the temperature in absolute values.
        For example, it accepts an instruction to set the temperature to 27°C.
        Set the temperature in 0.5° increments. For example, specify 10°, 10.5° and 11°.
    """)

class AirControl(BaseTool):
    name: str = "intent_aircontrol"
    description: str = "Set the air conditioner's temperature to a specific target value."
    args_schema: Type[BaseModel] = AirControlInput
    return_direct: bool = True

    def _run(self, temperature: float):
        logging.info(f"Set temperature to: {temperature}°C")
        response = {
            'intent': {'aircontrol': {'temperature': temperature}}
        }
        logging.info(f"Response: {response}")
        return json.dumps(response, ensure_ascii=False)

    def _arun(self, ticker: str):
        raise NotImplementedError("Asynchronous execution is not supported.")

# Ensure proper module usage
if __name__ == "__main__":
    # Example usage for delta temperature control
    delta_tool = AirControlDelta()
    print(delta_tool._run(-2.0))  # Decrease temperature by 2 degrees

    # Example usage for absolute temperature control
    control_tool = AirControl()
    print(control_tool._run(22.0))  # Set temperature to 22 degrees Celsius
