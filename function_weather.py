import os
import openai
import requests
import json
import logging
from typing import Any, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool


#
# call by openai functional calling
#

def get_weather_info(latitude:float, longitude:float):
    base_url = "https://api.open-meteo.com/v1/forecast"
    parameters = {
        "latitude": latitude,
        "longitude": longitude,
        #        "current_weather": "true",
        "hourly": "temperature_2m,relativehumidity_2m",
        "rain": "",
        "forecast_days": "3",
        "timezone": "Asia/Tokyo",
    }
    response = requests.get(base_url, params=parameters)
    if response.status_code == 200:
        data = response.json()
        logging.info(data)
        return json.dumps(data)
    else:
        return None


#
# call by openai functional calling
#
weather_function = {
    "name": "get_weather_info",
    "description": "Get current weather from latitude and longitude information",
    "parameters": {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "string",
                "description": "latitude",
            },
            "longitude": {
                "type": "string",
                "description": "longitude",
            },
        },
        "required": ["latitude", "longitude"],
    },
}


# for langchain 
class WeatherInfoInput(BaseModel):
    latitude: float = Field(description="Latitude of the location.")
    longitude: float = Field(description="Longitude of the location.")

class WeatherInfo(BaseTool):
    name = "get_weather_info"
    description = "This tool is used to fetch the weather forecast for a specified location."
    args_schema: Type[BaseModel] = WeatherInfoInput

    def _run(self, latitude: float, longitude: float):
        logging.info(f"Fetching weather info for latitude: {latitude}, longitude: {longitude}")
        try:
            weather_data = get_weather_info(latitude, longitude)
            logging.info("Weather data retrieved successfully.")
            return weather_data
        except Exception as e:
            response = {
                'error' : f"Failed to fetch weather data: {str(e)}"
            }
            logging.error(response)
            return json.dumps(response, ensure_ascii=False)

    def _arun(self, ticker: str):
        raise NotImplementedError("Asynchronous execution is not supported.")


if __name__ == "__main__":
    weather_tool = WeatherInfo()
    print(weather_tool._run(34.0522, -118.2437))  # Los Angeles, CA の緯度と経度