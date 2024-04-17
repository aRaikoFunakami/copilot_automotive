import threading
import time
import logging
import uuid

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class YouTubeAutoPlay(threading.Thread):
    def __init__(
        self, driver: webdriver, playlist: [], playnumber: int, overlay: bool = True # type: ignore
    ):
        super().__init__()
        self.daemon = True
        self.driver = driver
        self.playlist = playlist
        self.playnumber = playnumber
        self.overlay = overlay
        self.thread_id = uuid.uuid4()
        self.cancel_flag = False
        self.nextprevious_flag = False

    def __del__(self):
        logging.debug(f"Destructor called for thread {self.thread_id}, cleaning up...")
        self._hide_titles()

    def _hide_titles(self):
        try:
            if self.driver.execute_script(
                "return document.getElementById('overlay') !== null;"
            ):
                self.driver.execute_script(
                    "document.getElementById('overlay').remove();"
                )
        except Exception as e:
            logging.error(f"execute_script: {e}")

    def _overlay_titles(self, num):
        if self.overlay == False:
            return
        try:
            list = self.playlist["list"]
            titles = [i["title"] for i in list]
            progress_titles = titles[num:]

            html_content = """
                <div id="overlay" style="
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    width: 100%;
                    height: 30%;
                    background-color: rgba(0, 0, 0, 0.7);
                    z-index: 9999;
                    pointer-events: none;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                ">
                    <div style="
                        background-color: rgba(255, 255, 255, 0.7); 
                        padding: 20px;
                        width: 70%;
                        text-align: center;
                    ">
                        <div style="font-size: 28px;">Now Playing: {}</div>
                        <div style="font-size: 21px;">Up Next: {}</div>
                    </div>
                </div>
                <!---
                <div style="
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 70%;
                    background-color: rgba(0, 0, 0, 0.7);
                    z-index: 9999;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                "> --->
            """.format(
                progress_titles[0],  # 現在のタイトル
                progress_titles[1] if len(progress_titles) > 1 else "None"  # 次のタイトル（存在する場合）
            )

            self.driver.execute_script(
                "document.body.insertAdjacentHTML('beforeend', arguments[0]);",
                html_content,
            )
        except Exception as e:
            logging.error(f"execute_script: {e}")

    def play_next_video(self):
        logging.debug(f"num: {self.playnumber}, playlist: {self.playlist}")
        self.nextprevious_flag = True
        self._play()
        return

    def play_previous_video(self):
        logging.debug(f"num: {self.playnumber}, playlist: {self.playlist}")
        self.nextprevious_flag = True
        self.playnumber -= 2
        self._play()
        return

    def _play_next_video(self):
        try:
            WebDriverWait(self.driver, 60).until(
                EC.url_changes(self.driver.current_url)
            )
            if self.cancel_flag == True:
                return
            if self.nextprevious_flag == True:
                self.nextprevious_flag = False
                return
            self._play()
        except Exception as e:
            logging.error(f"WebDriverWait: {e}")

    def _play(self):
        logging.debug(f"num: {self.playnumber}, playlist: {self.playlist}")
        try:
            num = self.playnumber
            url = self.playlist["list"][num]["url"]
            self.driver.get(url)
            self.playnumber += 1
            time.sleep(2)
            self._overlay_titles(num)
        except Exception as e:
            logging.error(f"Error selecting video link: {e}")
            self.cancel()

    def run(self):
        self._play()
        while True:
            if self.cancel_flag == True:
                logging.debug(f"Stopping thread {self.thread_id}.")
                break
            logging.debug(
                f"Thread {self.thread_id} received cancel_message: {self.cancel_flag}"
            )
            self._play_next_video()
        self._hide_titles()

    def cancel(self):
        self.cancel_flag = True
        self._hide_titles()

def main():
    playlist = {
        "type": "video_list",
        "keyword": "フリーレン",
        "list": [
            {
                "title": "YOASOBI「勇者」 Official Music Video／TVアニメ『葬送のフリーレン』オープニングテーマ",
                "url": "https://www.youtube.com/watch?v=OIBODIPC_8Y&pp=ygUP44OV44Oq44O844Os44Oz",
            },
            {
                "title": "『葬送のフリーレン』第7話「おとぎ話のようなもの」次回予告／10月20日(金)よる11:20放送",
                "url": "https://www.youtube.com/watch?v=IbXI9LU5gZQ&pp=ygUP44OV44Oq44O844Os44Oz",
            },
        ],
    }

    logging.basicConfig(
        format="[%(asctime)s] [%(process)d] [%(levelname)s] [%(filename)s:%(lineno)d %(funcName)s] [%(message)s]",
        level=logging.INFO,
    )
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.youtube.com")
    time.sleep(2)

    # dummy operation for automatic video playback
    driver.execute_script("window.scrollBy(0, 100);")
    time.sleep(2)
    autoplay_thread = YouTubeAutoPlay(driver=driver, playlist=playlist, playnumber=0)
    autoplay_thread.start()

    # finish
    autoplay_thread.join()
    time.sleep(2)
    logging.info(f"finish!")


if __name__ == "__main__":
    main()
