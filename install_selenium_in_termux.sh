# refer https://github.com/luanon404/Selenium-On-Termux-Android
yes | pkg update
yes | pkg upgrade
yes | pkg install python-pip -y
pip install selenium==4.9.1
yes | pkg install x11-repo -y
yes | pkg install tur-repo -y
yes | pkg install chromium -y

# download chromium same as the chromedriver version from https://github.com/macchrome/droidchrome/tags