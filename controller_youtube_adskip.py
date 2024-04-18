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
    def __init__(self, driver):
        super().__init__()
        self.daemon = True
        self.driver = driver
        self.thread_id = uuid.uuid4()
        self.stop_requested = False

    def _adskip(self):
        try:
            logging.debug("Waiting for YouTubeAdskip")
            # Check if there's an ad element and it has children
            adElement = WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".video-ads.ytp-ad-module"))
            )
            if adElement and len(self.driver.find_elements(By.CSS_SELECTOR, ".video-ads.ytp-ad-module > *")) > 0:
                video = self.driver.find_element(By.CSS_SELECTOR, 'video')
                if video:
                    logging.info("Ad detected with content, speeding up video")
                    self.driver.execute_script("arguments[0].muted = true;", video)
                    self.driver.execute_script("arguments[0].playbackRate = 16.0;", video)
                    self.driver.execute_script("arguments[0].play();", video)

            # Check for the skip button and click it if found
            logging.debug("Waiting for skipButton")
            skipButton = WebDriverWait(self.driver, 1).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.ytp-ad-skip-button, .ytp-ad-skip-button-modern, .ytp-skip-ad-button'))
            )
            if skipButton:
                skipButton.click()

        except TimeoutException as e:
            logging.debug(f"Timeout: {e}")
        except Exception as e:
            logging.debug(f"Error: {e}")

    def run(self):
        while not self.stop_requested:
            logging.info(f"Thread {self.thread_id} checking for videos.")
            self._adskip()
            time.sleep(1)

    def cancel(self):
        self.stop_requested = True

    def __del__(self):
        logging.info(f"Destructor called for thread {self.thread_id}, cleaning up...")




def main():
    logging.basicConfig(
        format="[%(asctime)s] [%(process)d] [%(levelname)s] [%(filename)s:%(lineno)d %(funcName)s] [%(message)s]",
        level=logging.INFO,
    )
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.youtube.com/results?search_query=%E3%83%95%E3%83%AA%E3%83%BC%E3%83%AC%E3%83%B3")
    time.sleep(2)

    adskip_thread = YouTubeAdskip(driver=driver)
    adskip_thread.start()

    # finish
    adskip_thread.join()

if __name__ == "__main__":
    main()

