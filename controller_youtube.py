import logging
import json
import time
from typing import Any
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from controller_youtube_autoplay import YouTubeAutoPlay
from controller_youtube_adskip import YouTubeAdskip

#########################################################
# Config
#########################################################
youtube_playlist = True
# youtube_playlist = False
########################################################

# Sigleton
class YouTubeController:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(YouTubeController, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):  # 初期化フラグをチェック
            self.driver = None
            self.lang_id = "ja"
            self.playlist = []
            self.playlist_mode = False
            self.youtube_adskip_thread = None  # Adskip スレッドの初期化
            self.youtube_autoplay_thread = None  # Autoplay スレッドの初期化
            self.initialized = True  # 初期化済みフラグを設定

    def set_driver(self, driver):
        if self.driver is None:
            self.driver = driver
            self.youtube_adskip_thread = YouTubeAdskip(driver=self.driver)
            self.youtube_adskip_thread.start()

    @classmethod
    def get_instance(cls):
        return cls._instance if cls._instance else cls()

    def __del__(self):
        if self.youtube_adskip_thread is not None:
            logging.info(f"YouTube_Adskip: {self.youtube_adskip_thread}")
            self.youtube_adskip_thread.cancel()
        if self.youtube_autoplay_thread is not None:
            self.youtube_autoplay_thread.cancel()
        if self.driver:
            self.driver.quit()

    def get_current_url(self):
        driver_class_name = str(self.driver.__class__)
        # Appiumのドライバであるかを判定（例として"AndroidUiautomator2Driver"を使用）
        print(driver_class_name)
        if "appium" in driver_class_name:
            logging.info(self.current_url)
            return self.current_url
        else:
            return self.driver.current_url

    def search_videos_automatically_at_youtube(self, input: str) -> str:
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//a[@id="video-title"]'))
        )
        try:
            videos_elements = self.driver.find_elements(By.XPATH, '//a[@id="video-title"]')
            video_list = {"type": "video_list", "keyword": input, "list": []}

            i = 0
            limit = 15
            for video_element in videos_elements:
                if i < limit:
                    title = video_element.get_attribute("title")
                    url = video_element.get_attribute("href")
                    video_list["list"].append({"title": title, "url": url})
                    i += 1
                else:
                    break

            return json.dumps(video_list, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error selecting video link: {e}")
            return "Failed to get video list."

    def remove_numbers_from_videos(self, driver):
        script = """
		var circles = document.querySelectorAll('.video-number-circle');
		circles.forEach(function(circle) {
			circle.parentNode.removeChild(circle);
		});
		"""
        driver.execute_script(script)

    """
	Numbering process for video selection aids
	"""

    def add_numbers_to_videos_for_youtube(self, driver):
        try:
            logging.info("start WebDriverWait")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="thumbnail"]'))
            )
            # call javascript directly because taking time for seach id
            script_add_numbers_template = """
			var elements = document.querySelectorAll('[id="thumbnail"]');
			Array.from(elements).forEach(function(el, index) {
				var x = el.getBoundingClientRect().left + window.scrollX;
				var y = el.getBoundingClientRect().top + window.scrollY;
				var isDisplayed = !(el.offsetWidth === 0 && el.offsetHeight === 0);
				if (isDisplayed) {
					var circle = document.createElement('div');
					circle.className = "video-number-circle"; 
					var text = document.createElement('span');
					circle.style.zIndex = "9999";
					circle.style.fontSize = "36px"; 
					circle.style.width = '60px';
					circle.style.height = '60px';
					circle.style.lineHeight = "48px";
					circle.style.background = 'rgba(0, 128, 0, 0.5)';
					circle.style.position = 'absolute';
					circle.style.top = '0' + 'px';
					circle.style.left = '0' + 'px';
					circle.style.borderRadius = '50%';
					circle.style.display = 'flex';
					circle.style.justifyContent = 'center';
					circle.style.alignItems = 'center';
					text.innerHTML = index;
					text.style.color = 'white';
					circle.appendChild(text);
					el.appendChild(circle);
					console.log(x, y, index);
				}
			});
			"""
            logging.info("Start executing script to add numbers to video thumbnails.")
            driver.execute_script(script_add_numbers_template)
            logging.info("Numbers added to video thumbnails successfully.")
            if self.lang_id != "ja":
                response = "Moved to the link."
            else:
                response = "リンク先に移動しました"
            return response
        except TimeoutException:
            logging.error("Timed out waiting for input or textarea elements to load.")
            return "videos are not found"

    def add_numbers_to_videos(self, driver):
        url = self.get_current_url()
        logging.info(f"url: {url}")
        return self.add_numbers_to_videos_for_youtube(driver)

    """
	Called from function call of langchain
	url : VOD service to search for
	input: search string
	"""
    def play_video_in_playlist(self, num, lang_id="ja"):
        logging.info(f"num: {num}, playlist: {self.playlist}")
        try:
            self.youtube_autoplay_thread = YouTubeAutoPlay(driver=self.driver, playlist=self.playlist, playnumber=num, overlay=True)
            self.youtube_autoplay_thread.start()
            return f"プレイリストの{num}番目の動画{self.playlist['list'][num]['title']}を再生します"
        except Exception as e:
            logging.error(f"Error selecting video link: {e}")
            return f"Failed to play the video"

    def search_videos_automatically_at_youtube(self, input: str) -> str:
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//a[@id="video-title"]'))
        )
        try:
            videos_elements = self.driver.find_elements(
                By.XPATH, '//a[@id="video-title"]'
            )
            video_list = {"type": "video_list", "keyword": input, "list": []}

            i = 0
            limit = 15
            for video_element in videos_elements:
                if i < limit:
                    title = video_element.get_attribute("title")
                    url = video_element.get_attribute("href")
                    video_list["list"].append({"title": title, "url": url})
                    i += 1
                else:
                    break

            self.playlist = video_list
            logging.info(
                f"video_list: {json.dumps(self.playlist, indent=2, ensure_ascii=False)}"
            )
            return f"検索結果からプレイリストを作成しました。プレイリストを再生しますか？"
        except Exception as e:
            logging.error(f"Error selecting video link: {e}")
            return f"Failed to get video list."

    def search_videos(self, input: str, lang_id: str = "ja"):
        """
        Called from function call of Open AI
        """
        if(self.youtube_autoplay_thread is not None):
            self.youtube_autoplay_thread.cancel()
            self.youtube_autoplay_thread = None

        query_url = "https://www.youtube.com/results?search_query="
        goto_url = f"{query_url}{quote(input)}"

        self.lang_id = lang_id
        self.current_url = goto_url
        logging.info(f"get({goto_url})")
        self.driver.get(goto_url)
        time.sleep(1)

        if youtube_playlist == False:
            return self.add_numbers_to_videos(self.driver)
        else:
            self.add_numbers_to_videos(self.driver)
            return self.search_videos_automatically_at_youtube(input)
        

    """
	Select the link (video) of the selected number
	"""

    def click_link(self, link):
        logging.info(f"link = {link}")
        # 画面表示されていないと落ちるので click() を直接呼び出さない
        # videos[num].click()
        #
        # 表示しているリンク番号を削除
        self.remove_numbers_from_videos(self.driver)
        # 選択したビデオをクリック
        self.driver.execute_script("arguments[0].scrollIntoView();", link)
        self.driver.execute_script("arguments[0].click();", link)
        return

    def select_link_youtube(self, num):
        logging.info(f"Selecting video link number: {num}")
        try:
            # ビデオリンクの取得
            video_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, '//*[@id="thumbnail"]'))
            )[num]

            # error check
            if not video_element.is_displayed():
                raise Exception(f"Video element number {num} is not visible.")

            # elect link
            self.click_link(video_element)

            # add numbers at the next page after clicking the link
            time.sleep(3)
            return self.add_numbers_to_videos(self.driver)
        except Exception as e:
            logging.error(f"Error selecting video link: {e}")
            return f"Failed to move to selected linked content."

    def select_link_by_number(self, num: int, lang_id: str = "ja") -> str:
        """
        Called from function call of Open AI
        """
        if(self.youtube_autoplay_thread is not None):
            self.youtube_autoplay_thread.cancel()
            self.youtube_autoplay_thread = None
        self.lang_id = lang_id
        url = self.get_current_url()
        logging.info(f"num = {num}, url = {url}")
        return self.select_link_youtube(num)

    def youtube_shortcut_key(self, *keys: Any) -> str:
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//html"))
            )
            elements = self.driver.find_elements(By.XPATH, "//html")
            elements[0].send_keys(keys)
            return "success!!!"
        except TimeoutException:
            logging.error("Timed out waiting for input or textarea elements to load.")
            return "videos are not found"
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return f"Error"

    def play_suspend(self) -> str:
        """
        Called from function call of Open AI
        """
        url = self.get_current_url()
        logging.info(f"url = {url}")
        return self.youtube_shortcut_key("k")


    def mute(self) -> str:
        """
        Called from function call of Open AI
        """
        url = self.get_current_url()
        logging.info(f"url = {url}")
        return self.youtube_shortcut_key("m")

    def fullscreen(self) -> str:
        """
        Called from function call of Open AI
        """
        url = self.get_current_url()
        logging.info(f"url = {url}")
        # not support add_numbers
        self.remove_numbers_from_videos(self.driver)
        return self.youtube_shortcut_key("f")
  

    def fast_forward_playback(self) -> str:
        """
        Called from function call of Open AI
        """
        url = self.get_current_url()
        logging.info(f"url = {url}")
        # not support add_numbers
        self.remove_numbers_from_videos(self.driver)
        return self.youtube_shortcut_key(">")

    def slow_forward_playback(self) -> str:
        """
        Called from function call of Open AI
        """
        url = self.get_current_url()
        logging.info(f"url = {url}")
        return self.youtube_shortcut_key("<")

    def play_next_video(self) -> str:
        """
        Called from function call of Open AI
        """
        if(self.youtube_autoplay_thread is not None):
            logging.info(f" self.youtube_autoplay_thread.play_next_video()")
            self.youtube_autoplay_thread.play_next_video()
            num = self.youtube_autoplay_thread.playnumber
            return f"プレイリストの{num}番目の動画{self.playlist['list'][num]['title']}を再生します"
        url = self.get_current_url()
        logging.info(f"url = {url}")
        return self.youtube_shortcut_key("N", Keys.SHIFT)

    def play_previous_video(self) -> str:
        """
        Called from function call of Open AI
        """
        if(self.youtube_autoplay_thread is not None):
            logging.info(f" self.youtube_autoplay_thread.play_previous_video()")
            self.youtube_autoplay_thread.play_previous_video()
            num = self.youtube_autoplay_thread.playnumber
            return f"プレイリストの{num}番目の動画{self.playlist['list'][num]['title']}を再生します"
        url = self.get_current_url()
        logging.info(f"url = {url}")
        # return self.youtube_shortcut_key("P", Keys.SHIFT)
        return self.driver.back()

    def start(self):
        self.driver.get("https://www.google.com")



#########################################################
# Test Config
#########################################################
# is_termux = True
is_termux = False

# is_android_tablet = True
is_android_tablet = False
########################################################
if __name__ == "__main__":
    logging.basicConfig(
        format="[%(asctime)s] [%(process)d] [%(levelname)s] [%(filename)s:%(lineno)d %(funcName)s] [%(message)s]",
        level=logging.INFO,
    )

    options = webdriver.ChromeOptions()
    # If running on an Android tablet, set the user agent and package to use Chrome on Android
    if is_android_tablet:
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
        options.add_experimental_option("androidPackage", "com.android.chrome")
    
    # Only attempt to install and use the ChromeDriverManager if not running on Termux
    # Ensure correct handling of the service parameter
    if not is_termux:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # For Termux, the service parameter is not needed as Termux has a specific way of handling drivers
        driver = webdriver.Chrome(options=options)
    
    test = YouTubeController.get_instance()
    test.set_driver(driver=driver)
    test.start()
    test.search_videos("フリーレン")
    time.sleep(1)
    test.select_link_by_number(2)
    time.sleep(1)

    test.fullscreen()
    time.sleep(1)
    test.fullscreen()
    time.sleep(1)

    test.fast_forward_playback()
    time.sleep(2)
    test.fast_forward_playback()
    time.sleep(2)

    test.slow_forward_playback()
    time.sleep(2)
    test.slow_forward_playback()
    time.sleep(2)

    test.mute()
    time.sleep(2)
    test.mute()
    time.sleep(2)

    test.play_suspend()
    time.sleep(2)
    test.play_suspend()
    time.sleep(2)

    test.play_next_video()
    time.sleep(2)
    test.play_previous_video()
    time.sleep(2)

    time.sleep(10)
