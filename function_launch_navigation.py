import json
import logging
from typing import Any, Optional, Type
from pydantic import BaseModel, Field, ValidationError
from langchain.tools import BaseTool
import asyncio


class LaunchNavigationInput(BaseModel):
    latitude: float = Field(
        default=0.0, description="Specify the Latitude of the destination."
    )
    longitude: float = Field(
        default=0.0, description="Specify the Longitude of the destination."
    )
    destination: Optional[str] = Field(
        default=None,
        description="Specify the destination as a string (e.g., a city name or address).",
    )


class LaunchNavigation(BaseTool):
    name: str = "intent_googlenavigation"
    description: str = (
        "Use this function to provide route guidance to a specified location. Use 'destination' if available, otherwise specify latitude and longitude."
    )
    args_schema: Type[BaseModel] = LaunchNavigationInput
    return_direct: bool = True

    def _generate_response(
        self, latitude: float, longitude: float, destination: Optional[str]
    ) -> dict:
        """Generate a navigation response based on input parameters."""
        if destination:
            logging.info(f"Using destination: {destination}")
            return {
                "type": "tools.launch_navigation",
                "description": """
                    This JSON describes an action where the client application should initiate navigation to a specified location.
                    The action is specified in the "intent" field, which contains either a destination name or latitude and longitude coordinates.
                    Additional details, such as the navigation application to use (e.g., Google Maps), are provided within the "intent".
                """,
                "return_direct": True,
                "intent": {
                    "navigation": {
                        "navi_application": "googlemap",
                        "destination": destination,
                    },
                },
            }
        else:
            logging.info("Using latitude and longitude")
            return {
                "type": "tools.launch_navigation",
                "return_direct": True,
                "intent": {
                    "navigation": {
                        "navi_application": "googlemap",
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                },
            }

    def _handle_error(self, error: Exception) -> dict:
        """Handle errors and return a consistent error response."""
        error_message = f"Failed to provide navigation due to an error: {str(error)}"
        logging.error(error_message)
        return {"error": error_message}

    async def _arun(
        self,
        latitude: float = 0.0,
        longitude: float = 0.0,
        destination: Optional[str] = None,
    ):
        """Asynchronous method for generating navigation response."""
        logging.info(
            f"latitude = {latitude}, longitude = {longitude}, destination = {destination}"
        )
        try:
            # Validate input
            if not destination and (latitude == 0.0 and longitude == 0.0):
                raise ValueError(
                    "Either destination or latitude/longitude must be provided."
                )

            response = self._generate_response(latitude, longitude, destination)
            logging.info(f"response: {response}")
            return response
        except (ValidationError, ValueError) as e:
            return self._handle_error(e)
        except Exception as e:
            return self._handle_error(e)

    def _run(
        self,
        latitude: float = 0.0,
        longitude: float = 0.0,
        destination: Optional[str] = None,
    ):
        """Synchronous method wrapping the async method."""
        try:
            return json.dumps(
                asyncio.run(self._arun(latitude, longitude, destination)),
                indent=4,
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps(self._handle_error(e), indent=4, ensure_ascii=False)


# モジュールの適切な使用を確保
if __name__ == "__main__":
    tool = LaunchNavigation()

    # 緯度経度を使用する場合
    try:
        result1 = tool._run(34.0522, -118.2437)  # Los Angeles, CA の緯度と経度
        print(result1)
    except Exception as e:
        print(f"Error: {str(e)}")

    # 目的地名を使用する場合
    try:
        result2 = tool._run(destination="Tokyo Tower")
        print(result2)
    except Exception as e:
        print(f"Error: {str(e)}")
