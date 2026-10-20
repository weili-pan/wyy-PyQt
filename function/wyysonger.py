import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from bs4 import BeautifulSoup
from function.wyydownload_async import WYYDownload
import re
import sys

"""
对于网易云歌手歌单的下载
"""

class WYYSonger:
    def __init__(self,url,path,cookie,user_agent,start_num,end_num,message_signal = None):
        self.url = url
        self.path = path
        self.cookie = cookie
        self.user_agent = user_agent
        self.start_num = int(start_num)
        self.end_num = int(end_num)
        self.message_signal = message_signal
        self.txt_path = "txt/songer.txt"
        self.wyy_download = WYYDownload(self.txt_path,self.path,self.cookie,self.user_agent,self.start_num,self.end_num,self.message_signal)
        self.total_num = 0
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        if not os.path.exists("txt"):
            os.makedirs("txt")

    def new_print(self, message):
        if self.message_signal:
            self.message_signal.emit(str(message))
        else:
            print(message)

    def get_songer_songs_list(self):
        new_url=f"view-source:{self.url}"
        driver_path = "msedgedriver.exe"
        service = Service(driver_path)

        options=Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0")
        options.add_experimental_option("excludeSwitches",["enable-automation"])
        options.add_experimental_option("useAutomationExtension",False)
        resp=webdriver.ChromiumEdge(service=service,options=options)
        resp.switch_to.window(resp.window_handles[0])
        resp.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source":
                """
                Object.defineProperty(navigator,'webdriver',{
                    get: () => undefined
                })
                """
        }
    )
        resp.get(new_url)
        resp.implicitly_wait(10)#等待页面加载完成
        soup=BeautifulSoup(resp.page_source,"html.parser")
        
        html_id=re.findall(r'href="\/song\?id=(\d+)"\s+rel="noreferrer\s+noopener"\s+target="_blank">\/song\?id=\d+<\/a>"&gt;<\/span>.*?<span\s+class="html-tag">&lt;\/a&gt;',str(soup))
        name=re.findall(r'href="\/song\?id=\d+"\s+rel="noreferrer\s+noopener"\s+target="_blank">\/song\?id=\d+<\/a>"&gt;<\/span>(.*?)<span\s+class="html-tag">&lt;\/a&gt;',str(soup))
        
        song_dict={}
        for i in range(len(html_id)):
            song_dict[i+1]=[name[i],html_id[i]]

        with open(f"{self.txt_path}","w",encoding="utf-8") as f:
            f.write(str(song_dict))
        self.total_num = len(song_dict)
        if self.total_num<self.end_num:
            self.new_print("歌单歌曲数量不足，请重新输入")
            sys.exit()
        return len(song_dict)
        
async def WYYSonger_main_download(url,path,cookie,user_agent,start_num,end_num,message_signal):
    wyy=WYYSonger(url,path,cookie,user_agent,start_num,end_num,message_signal)
    await wyy.wyy_download.download_song()
