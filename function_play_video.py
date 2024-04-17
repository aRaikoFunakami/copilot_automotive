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
from controller_youtube import YouTubeController

# 動画を番号で選択するための入力スキーマ
class SelectLinkByNumberInput(BaseModel):
    num: int = Field(description="Select the link you want to select by number.")

class SelectLinkByNumber(BaseTool):
    name = "select_link_by_number"
    description = "Use this function to select the link by number."
    args_schema: Type[BaseModel] = SelectLinkByNumberInput
    return_direct = True  # Tool returns output directly

    def _run(self, num: int):
        logging.info(f"Selecting link by number: {num}")
        try:
            # DEMO code
            controller = YouTubeController.get_instance()
            response = controller.select_link_by_number(num=num)
            # example
            response = {
                'intent' : {
                    'webbrowser' : {
                        'select_link' :{
                            'number' : num,
                        },
                    },
                },
            }
            logging.info(f"response: {response}")
            return json.dumps(response, ensure_ascii=False)
        except Exception as e:
            response = {
                'error' : f"Failed to select link due to an internal error ({num}: {str(e)})"
            }
            logging.error(response)
            return json.dumps(response, ensure_ascii=False)

    def _arun(self, ticker: str):
        raise NotImplementedError("Asynchronous execution is not supported yet.")

# モジュールの適切な使用を確保
if __name__ == "__main__":
    # 使用例
    from function_seach_videos import SearchVideos
    tool = SearchVideos()
    result = tool._run("youtube", "funny cats")
    tool = SelectLinkByNumber()
    result = tool._run(3)  # 例として「3番目のリンクを選択」
    print(result)
