from function.wyybk import WYYMusic_Boke
from function.wyysinglemusic import WYYMusic_singlemusic
from function.wyysonglist import WYYsonglist, WYYsonglist_main_download
from function.wyysonger import WYYSonger, WYYSonger_main_download
import asyncio
import os

class MainFunc:
    def __init__(self, path, cookie, user_agent,message_signal=None):
        self.path = path
        self.cookie = cookie
        self.user_agent = user_agent
        self.message_signal = message_signal
        if not os.path.exists("music") and not os.path.exists("img") and not os.path.exists("txt"):
            os.mkdir("music")
            os.mkdir("img")
            os.mkdir("txt")

    def new_print(self, message):
        if self.message_signal:
            self.message_signal.emit(str(message))
        else:
            print(message)

    def main_spider_wyy(self,url,start_num, end_num):
        self.new_print("爬取上限为1000条，超过1000条请分多次爬取")

        # 第1部分
        if "song?id=" in url:
            try:
                if "#" in url:
                    url = url.replace("#/", "")
                new_url = f"view-source:{url}"
                wyy2 = WYYMusic_singlemusic(self.path, self.cookie, self.user_agent,self.message_signal)
                wyy2.main_song(new_url)
                self.new_print("歌曲下载完成")
            except Exception as e:
                self.new_print(f"歌曲下载失败\n{e}")


        # 第2部分
        elif "playlist?id" in url:
            self.new_print("下载限制为50首歌，请分段下载，暂时不支持一首歌下载")
            try:
                wyy3 = WYYsonglist(self.path, url, self.cookie, self.user_agent, start_num, end_num,self.message_signal)
                num = wyy3.get_song_list()
                self.new_print(f"歌单下载完成，共下载了{num}首歌曲请到当前目录查看songlist.txt文件")
                if start_num == "0":
                    self.new_print("歌单已下载，请到当前目录查看songlist.txt文件")
                elif start_num != "0" and int(end_num) - int(start_num) <= 50:
                    asyncio.run(WYYsonglist_main_download(self.path, url, self.cookie, self.user_agent, start_num, end_num,self.message_signal))
                else:
                    self.new_print("为了您的账号安全，歌单太长，请分段下载")
            except:
                self.new_print("歌单下载失败，请检查网络或cookie是否失效，或歌单不存在，或输入是否为数字，逻辑是否错误。")

        # 第3部分
        elif "artist?id=" in url:
            if "#" in url:
                songer_new_url = url.replace("#/", "")
            self.new_print("下载限制为50首歌，请分段下载，暂时不支持一首歌下载")
            try:
                wyy4 = WYYSonger(songer_new_url, self.path, self.cookie, self.user_agent, start_num, end_num,self.message_signal)
                num = wyy4.get_songer_songs_list()
                self.new_print(f"歌手作品歌单下载完成，共下载了{num}首歌，请到当前目录查看songer.txt文件")
                if start_num == "0":
                    self.new_print("歌单已下载，请到当前目录查看songer.txt文件")
                elif start_num != "0" and int(end_num) - int(start_num) <= 50:
                    asyncio.run(WYYSonger_main_download(url, self.path, self.cookie, self.user_agent, start_num, end_num,self.message_signal))
                else:
                    self.new_print("为了您的账号安全，歌单太长，请分段下载")
            except:
                self.new_print("歌单作品歌单下载失败，请检查网络或cookie是否失效，或歌单不存在，或输入是否为数字，逻辑是否错误。")

        #第4部分
        elif "djradio?id=" in url:
            try:
                if "#" in url:
                    url=url.replace("#/","")
                new_url=f"view-source:{url}"
                wyy1=WYYMusic_Boke(self.path,self.cookie,self.user_agent,self.message_signal)
                wyy1.main_songs(new_url)
                self.new_print("播客下载完成")
            except Exception as e:
                self.new_print(f"播客下载失败\n{e}")

        elif "program?id=" in url:
            try:
                if "#" in url:
                    url = url.replace("#/", "")
                new_url = f"view-source:{url}"
                wyy6 = WYYMusic_Boke(self.path, self.cookie, self.user_agent, self.message_signal)
                wyy6.main_single_song(new_url)
                self.new_print("播客下载完成")
            except Exception as e:
                self.new_print(f"播客下载失败\n{e}")

