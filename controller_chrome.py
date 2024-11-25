"""
The implementation is made using Selenium for demonstration purposes. 
Normally, Selenium is not used to control the browser, but sends JSON 
commands to the client to control the browser, and the client 
communicates with the browser to control the browser.
"""

import json
import logging
from typing import Any
import time

from selenium import webdriver
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import quote

from controller_youtube import YouTubeController


#########################################################
# Config
#########################################################
#is_termux = True
is_termux = False

#is_android_tablet = True
is_android_tablet = False

# termuxの場合
# chromedriver のバージョンに合わせたchromiumのバイナリをAndroidにインストールしておく
# https://github.com/macchrome/droidchrome/tags
#########################################################


# Singleton
class ChromeController:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(ChromeController, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.lang_id = "ja"
        options = webdriver.ChromeOptions()
        # If running on an Android tablet, set the user agent and package to use Chrome on Android
        if is_android_tablet:
            options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            options.add_experimental_option("androidPackage", "com.android.chrome")

        # Only attempt to install and use the ChromeDriverManager if not running on Termux
        # Ensure correct handling of the service parameter
        if not is_termux:
            #service = Service(ChromeDriverManager().install())
            #self.driver = webdriver.Chrome(service=service, options=options)
            self.driver = webdriver.Chrome(options=options)
        else:
            # For Termux, the service parameter is not needed as Termux has a specific way of handling drivers
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_experimental_option("androidPackage", "org.chromium.chrome.stable") 
            self.driver = webdriver.Chrome(options=options)

        self.youtube_controller = YouTubeController().get_instance()
        self.youtube_controller.set_driver(self.driver)

    def __del__(self):
        self.quit()

    def quit(self):
        self.driver.close()
        self.driver.quit()

    def search_videos(self, service: str, input: str, lang_id: str = "ja"):
        self.lang_id = lang_id
        if "youtube" in service.lower():
            return self.youtube_controller.search_videos(input, lang_id)
        else:
            response = {
                'error' : "Unsupported video service"
            }
            logging.error(response)
            return json.dumps(response, ensure_ascii=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    controller = ChromeController.get_instance()
    controller.search_videos("youtube", "フリーレン")
    time.sleep(1)
    controller.quit()
