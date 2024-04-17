import threading
import time
import logging
import uuid

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException 
from selenium.webdriver.support.ui import WebDriverWait

class YouTubeAdskip(threading.Thread):
    def __init__(self, driver: webdriver):
        super().__init__()
        self.daemon = True
        self.driver = driver
        self.thread_id = uuid.uuid4() 
        self.stop_requested = False
    
    def _adskip(self):
        try:
            logging.debug(f"waiting Adskip")
            skip_button = WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ytp-ad-skip-button-modern.ytp-button"))
            )
            logging.debug(f"Adskip!!!")
            skip_button.click()
        except TimeoutException as e:
            logging.debug("Timeout: Skip button was not found within the time limit: {e}")
        except Exception as e:
            logging.debug("click error: {e}")

    def run(self):
        while not self.stop_requested:  # 条件を変更
            logging.debug(f"Thread {self.thread_id} checking for ads.")
            self._adskip()
            time.sleep(3)

    def cancel(self):
        self.stop_requested = True

    def __del__(self):
        logging.debug(f"Destructor called for thread {self.thread_id}, cleaning up...")


def main():
    logging.basicConfig(
        format="[%(asctime)s] [%(process)d] [%(levelname)s] [%(filename)s:%(lineno)d %(funcName)s] [%(message)s]",
        level=logging.INFO,
    )
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.youtube.com")
    time.sleep(2)

    adskip_thread = YouTubeAdskip(driver=driver)
    adskip_thread.start()

    # finish
    adskip_thread.join()
    time.sleep(2)

if __name__ == "__main__":
    main()

