import json
import logging
from typing import Any, Optional, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import asyncio


# ベースクラス
class AirControlBase(BaseTool):
    return_direct: bool = True

    def _generate_response(self, intent_name: str, intent_data: dict) -> dict:
        """Generate a standard response for air control tools."""
        return {
            "type": f"tools.{intent_name}",
            "description": """
                This JSON describes an action where the client application should interact with an air conditioning system.
                The action is specified in the "intent" field, which can either adjust the temperature by a relative value (delta) or set it to an absolute value.
                Additional details, such as the specific temperature change or target temperature, are provided in the corresponding fields within the "intent".
            """,
            "return_direct": True,
            "intent": {intent_name: intent_data},
        }

    def _handle_error(self, error: Exception) -> dict:
        """Handle errors and return a consistent error response."""
        error_message = f"Failed to process air control request due to: {str(error)}"
        logging.error(error_message)
        return {"error": error_message}

    async def _arun(self, **kwargs):
        """Abstract method to be implemented by subclasses."""
        raise NotImplementedError("This method should be implemented by subclasses.")

    def _run(self, **kwargs):
        """Sync wrapper around async logic."""
        try:
            return json.dumps(
                asyncio.run(self._arun(**kwargs)), indent=4, ensure_ascii=False
            )
        except Exception as e:
            return json.dumps(self._handle_error(e), indent=4, ensure_ascii=False)


# 温度変更（相対値）のためのツール
class AirControlDeltaInput(BaseModel):
    temperature_delta: float = Field(
        description="""
        Specify the temperature to be raised or lowered relative to the current temperature setting. 
        Adjust the temperature in 0.5 degree increments. 
        For example, decrease by 3 degrees if it's too hot, or increase by 1 degree if it's slightly cold.
    """
    )


class AirControlDelta(AirControlBase):
    name: str = "intent_aircontrol_delta"
    description: str = (
        "Adjust the air conditioner's temperature based on sensory temperature information."
    )
    args_schema: Type[BaseModel] = AirControlDeltaInput

    async def _arun(self, temperature_delta: float):
        logging.info(f"Requested temperature change: {temperature_delta} degrees")
        try:
            response = self._generate_response(
                "aircontrol_delta", {"temperature_delta": temperature_delta}
            )
            logging.info(f"Response: {response}")
            return response
        except Exception as e:
            return self._handle_error(e)


# 絶対温度設定のためのツール
class AirControlInput(BaseModel):
    temperature: float = Field(
        description="""
        Set the temperature in absolute values.
        For example, it accepts an instruction to set the temperature to 27°C.
        Set the temperature in 0.5° increments. For example, specify 10°, 10.5° and 11°.
    """
    )


class AirControl(AirControlBase):
    name: str = "intent_aircontrol"
    description: str = (
        "Set the air conditioner's temperature to a specific target value."
    )
    args_schema: Type[BaseModel] = AirControlInput

    async def _arun(self, temperature: float):
        logging.info(f"Set temperature to: {temperature}°C")
        try:
            response = self._generate_response(
                "aircontrol", {"temperature": temperature}
            )
            logging.info(f"Response: {response}")
            return response
        except Exception as e:
            return self._handle_error(e)


# モジュールの適切な使用を確保
if __name__ == "__main__":
    # Example usage for delta temperature control
    delta_tool = AirControlDelta()
    print(delta_tool._run(temperature_delta=-2.0))  # Decrease temperature by 2 degrees

    # Example usage for absolute temperature control
    control_tool = AirControl()
    print(control_tool._run(temperature=22.0))  # Set temperature to 22 degrees Celsius
