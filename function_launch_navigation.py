import json
import logging
from typing import Any, Optional, Type
from pydantic import BaseModel, Field

from langchain.tools import BaseTool


class LaunchNavigationInput(BaseModel):
    latitude: float = Field(default=0.0, description="Specify the Latitude of the destination.")
    longitude: float = Field(default=0.0, description="Specify the Longitude of the destination.")
    destination: Optional[str] = Field(default=None, description="Specify the destination as a string (e.g., a city name or address).")


class LaunchNavigation(BaseTool):
    name: str = "intent_googlenavigation"
    description: str = "Use this function to provide route guidance to a specified location. Use 'destination' if available, otherwise specify latitude and longitude."
    args_schema: Type[BaseModel] = LaunchNavigationInput
    return_direct: bool = True  # if True, Tool returns output directly

    def _run(self, latitude: float = 0.0, longitude: float = 0.0, destination: Optional[str] = None):
        logging.info(f"latitude = {latitude}, longitude = {longitude}, destination = {destination}")
        try:
            # Use destination if provided
            if destination:
                logging.info(f"Using destination: {destination}")
                response = {
                    'type': "tools.launchnavigation",
                    'intent': {
                        'navigation': {
                            'navi_application': "googlemap",
                            'destination': destination
                        },
                    },
                }
            else:
                logging.info("Using latitude and longitude")
                response = {
                    'type': "tools.launchnavigation",
                    'intent': {
                        'navigation': {
                            'navi_application': "googlemap",
                            'latitude': latitude,
                            'longitude': longitude,
                        },
                    },
                }
            logging.info(f"response: {response}")
            return json.dumps(response, indent=4, ensure_ascii=False)
        except Exception as e:
            response = {
                "error": f"Failed to provide navigation due to an error: {str(e)}"
            }
            logging.error(response)
            return json.dumps(response, indent=4, ensure_ascii=False)

    async def _arun(self, latitude: float = 0.0, longitude: float = 0.0, destination: Optional[str] = None):
        logging.info(f"latitude = {latitude}, longitude = {longitude}, destination = {destination}")
        try:
            # Use destination if provided
            if destination:
                logging.info(f"Using destination: {destination}")
                response = {
                    'type': 'tools.launchnavigation',
                    'return_direct': True,
                    'intent': {
                        'navigation': {
                            'navi_application': "googlemap",
                            'destination': destination
                        },
                    },
                }
            else:
                logging.info("Using latitude and longitude")
                response = {
                    'type': 'tools.launchnavigation',
                    'return_direct': True,
                    'intent': {
                        'navigation': {
                            'navi_application': "googlemap",
                            'latitude': latitude,
                            'longitude': longitude,
                        },
                    },
                }
            logging.info(f"response: {response}")
            return response
        except Exception as e:
            response = {
                "error": f"Failed to provide navigation due to an error: {str(e)}"
            }
            logging.error(response)
            return response


# モジュールの適切な使用を確保
if __name__ == "__main__":
    # 使用例
    tool = LaunchNavigation()

    # 緯度経度を使用する場合
    result1 = tool._run(34.0522, -118.2437)  # Los Angeles, CA の緯度と経度
    print(result1)

    # 目的地名を使用する場合
    result2 = tool._run(0.0, 0.0, destination="Tokyo Tower")
    print(result2)