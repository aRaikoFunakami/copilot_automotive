# refer https://github.com/luanon404/Selenium-On-Termux-Android
yes | pkg update
yes | pkg upgrade
yes | pkg install python-pip -y
pip install selenium==4.9.1
# install android-tools
yes | pkg install wget -y
cd $HOME
wget https://github.com/Lzhiyong/termux-ndk/releases/download/android-sdk/android-sdk-aarch64.zip
unzip android-sdk-aarch64.zip -d android-sdk
rm -r android-sdk-aarch64.zip
echo "export ANDROID_HOME=$HOME/android-sdk" >> $HOME/.bashrc
echo "export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/tools/bin:$ANDROID_HOME/platform-tools" >> $HOME/.bashrc
#
yes | pkg install android-tools -y
yes | pkg install x11-repo -y
yes | pkg install tur-repo -y
yes | pkg install chromium -y

# download chromium same as the chromedriver version from https://github.com/macchrome/droidchrome/tags