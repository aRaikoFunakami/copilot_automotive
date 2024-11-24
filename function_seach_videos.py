"""
The implementation is made using Selenium for demonstration purposes. 
Normally, Selenium is not used to control the browser, but sends JSON 
commands to the client to control the browser, and the client 
communicates with the browser to control the browser.
"""

import json
import logging
from typing import Any, Type
from pydantic import BaseModel, Field

from langchain.tools import BaseTool
from controller_chrome import ChromeController

# Define the input schema using Pydantic for type validation and settings
class SearchVideosInput(BaseModel):
    service: str = Field(
        description='Name of video website for video search. Currently, only "youtube" is supported.'
    )
    input: str = Field(
        description="Search string for searching videos."
    )

class SearchVideos(BaseTool):
    name: str = "search_videos"
    description: str = "Function to search videos on a specified service via a web page."
    args_schema: Type[BaseModel] = SearchVideosInput
    return_direct: bool = True  # Indicates that the tool returns output directly without further user interaction

    def _run(self, service: str, input: str):
        service = service.lower()
        logging.info(f"Service = {service}, Input = {input}")
        try:
            # DEMO code
            chrome_controller = ChromeController.get_instance()
            import remote_chat
            response = chrome_controller.search_videos(service=service, input=input, lang_id=remote_chat.lang_id)  # Example fixed lang_id
            # example
            response = {
                'intent' : {
                    'webbrowser' : {
                        'search_videos': {
                            'service' : service,
                            'input' : input,
                        },
                    },
                },
            }
            logging.info(f"response: {response}")
            return json.dumps(response, ensure_ascii=False)
        except Exception as e:
            response = {
                'error' : f"Error in searching videos: {str(e)}"
            }
            logging.error(response)
            return json.dumps(response, ensure_ascii=False)

    def _arun(self, ticker: str):
        raise NotImplementedError("Asynchronous execution is not supported.")

# Ensure proper module usage
if __name__ == "__main__":
    # Example usage
    tool = SearchVideos()
    result = tool._run("youtube", "funny cats")
    print(result)