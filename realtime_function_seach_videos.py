import json
import logging
from typing import Any, Type
from pydantic import BaseModel, Field
import asyncio

from langchain.tools import BaseTool

class SearchVideosInput(BaseModel):
    service: str = Field(
        description='Name of video website for video search. Currently, only "youtube" is supported.'
    )
    input: str = Field(description="Search string for searching videos.")


class SearchVideos(BaseTool):
    name: str = "search_videos"
    description: str = (
        "Function to search videos on a specified service via a web page."
    )
    args_schema: Type[BaseModel] = SearchVideosInput
    return_direct: bool = True

    def _generate_response(self, service: str, input: str) -> dict:
        """Generate a standardized response for video search."""
        return {
            "type": "tools.search_videos",
            "description": """
                This JSON describes an action where the client application should open a web browser and search for the specified query.
                The action is specified in the "intent" field, and additional instructions are provided in the "instructions" field.
                """,
            "return_direct": True,
            "intent": {
                "webbrowser": {
                    "search_videos": {
                        "service": service,
                        "input": input,
                    },
                },
            },
        }

    def _handle_error(self, error: Exception) -> dict:
        """Handle errors and return a consistent error response."""
        error_message = f"Error in searching videos: {str(error)}"
        logging.error(error_message)
        return {"error": error_message}

    async def _arun(self, service: str, input: str):
        """Asynchronous video search."""
        try:
            service = service.lower()
            logging.info(f"Service = {service}, Input = {input}")

            response = self._generate_response(service, input)
            logging.info(f"Response: {response}")
            return response
        except Exception as e:
            return self._handle_error(e)

    def _run(self, service: str, input: str):
        """Synchronous wrapper around async logic."""
        try:
            return json.dumps(
                asyncio.run(self._arun(service, input)), indent=4, ensure_ascii=False
            )
        except Exception as e:
            return json.dumps(self._handle_error(e), indent=4, ensure_ascii=False)


# Ensure proper module usage
if __name__ == "__main__":
    # Example usage
    tool = SearchVideos()
    result = tool._run("youtube", "funny cats")
    print(result)
