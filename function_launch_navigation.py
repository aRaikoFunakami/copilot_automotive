import json
import logging
from typing import Any, Type
from pydantic import BaseModel, Field

from langchain.tools import BaseTool

class LaunchNavigationInput(BaseModel):
    latitude: float = Field(description="Specify the Latitude of the destination.")
    longitude: float = Field(description="Specify the longitude of the destination.")

class LaunchNavigation(BaseTool):
    name = "intent_googlenavigation"
    description = "Use this function to provide route guidance to a specified location."
    args_schema: Type[BaseModel] = LaunchNavigationInput
    return_direct = True  # if True, Tool returns output directly

    def _run(self, latitude: float, longitude: float):
        logging.info(f"lat, lon = {latitude}, {longitude}")
        try:
            # ここで外部のナビゲーションサービスへのリクエストを想定
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
        except Exception as e:
            response = {
                "error",
                "Failed to provide navigation due to an error: {0}".format(str(e))
            }
            logging.error(response)
            return json.dumps(response, ensure_ascii=False)

    def _arun(self, ticker: str):
        raise NotImplementedError("Asynchronous execution is not supported.")

# モジュールの適切な使用を確保
if __name__ == "__main__":
    # 使用例
    tool = LaunchNavigation()
    result = tool._run(34.0522, -118.2437)  # Los Angeles, CA の緯度と経度
    print(result)
