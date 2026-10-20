import requests 
import os
import re
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC,TPE1,TIT2
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from bs4 import BeautifulSoup
from function.sercet import Secret_AES,detect_name

"""
主要是aes加密，在core.js中，window.asrea=d
通过text='{"ids":"[2123134477]","level":"exhigh","encodeType":"aac","csrf_token":""}',来加密

这个是主要针对网易云播客，因为最早编写，比较生疏
"""

class WYYMusic_Boke:
    def __init__(self,path,cookie,user_agent,message_signal = None):
        self.path=path
        #歌单处于的token
        self.csrf_token="d5173e02fd2de201b463865127ea7ad1"
        #用户信息
        self.cookie=cookie
        self.user_agent=user_agent
        self.message_signal = message_signal
        if not os.path.exists(self.path):
            os.mkdir(self.path)

    def new_print(self, message):
        if self.message_signal:
            self.message_signal.emit(str(message))
        else:
            print(message)
    
    def get_song_info(self,url):
        driver_path = "msedgedriver.exe"
        service = Service(driver_path)

        options=Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
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
        resp.get(url)
        resp.implicitly_wait(10)#等待页面加载完成
        soup=BeautifulSoup(resp.page_source,"html.parser")
        return soup

    def save_mp3(self,name,num,author,image):
        # 获取歌曲
        name_i = detect_name(name)
        url = "https://interface.music.163.com/weapi/song/enhance/player/url/v1?csrf_token="
        te = f'{{"ids":"[{num}]","level":"exhigh","encodeType":"aac","csrf_token":"{self.csrf_token}"}}'
        data = Secret_AES().get_data(te)
        headers = {
            "cookie": self.cookie,
            "user-agent": self.user_agent
        }
        resp = requests.post(url, headers=headers, data=data)
        resp = resp.json()
        song_url = resp["data"][0]["url"]
        resp = requests.get(song_url)
        with open(f"{self.path}/{name_i}.m4a","wb") as f:
            f.write(resp.content)
        # 获取图片
        img = requests.get(image)
        with open(f"img/{name_i}.jpg", "wb") as f:
            f.write(img.content)
        # MP3整合，加入作者封面等元素
        in_file = f"{self.path}/{name}.m4a"
        out_file = f"{self.path}/{name}.mp3"
        song = AudioSegment.from_file(in_file, format="m4a")
        song.export(out_file, format="mp3")
        try:
            audio = MP3(out_file, ID3=ID3)
            try:
                audio.add_tags()
            except:
                pass
            audio["TPE1"] = TPE1(encoding=3, text=author)  # 设置作者
            audio["TIT2"] = TIT2(encoding=3, text=name_i)  # 设置歌名
            with open(f"img/{name_i}.jpg", "rb") as f:
                audio["APIC"] = APIC(encoding=3, mime="image/jpeg", type=3, desc=u"Cover", data=f.read())  # 设置封面
            audio.save(v2_version=3)
        except Exception as e:
            self.new_print(f"下载失败,{e}")
        finally:
            os.remove(in_file)

        self.new_print(f"{name_i}.mp3 下载完成")

    def main_songs(self,url):
        soup=self.get_song_info(url)
        # 歌曲名字
        name = re.findall(r'\/program\?id=\d+<\/a>"\s+<span\s+class="html-attribute-name">title<\/span>="<span\s+class="html-attribute-value">(.*?)<\/span>"',str(soup))
        # 歌曲id
        num = re.findall(r'<span\s+class="html-attribute-value">songlist-(\d+)<\/span>', str(soup))
        # 歌曲作者
        author = re.findall(r'data-res-author<\/span>="<span\s+class="html-attribute-value">(.*?)<\/span>"\s+<span\s+class="html-attribute-name">data-res-pic<\/span>="',str(soup))
        # 歌曲封面
        image = re.findall(r'data-res-pic<\/span>="<span\s+class="html-attribute-value">(https?:\/\/.*?)<\/span>"',str(soup))
        for i in range(len(name)):
            self.save_mp3(name[i],num[i],author[i],image[i])

    def main_single_song(self,url):
        soup=self.get_song_info(url)
        num = re.findall(r'view-source:https://.*?id=(\d+)', url)
        # 歌曲名字
        name = re.findall(
            r'<td\s+class="line-number"\s+value="17"></td><td\s+class="line-content"><span\s+class="html-tag">&lt;title&gt;</span>(.*?)\s+-\s+.*?\s+-\s+电台节目\s+-\s+网易云音乐<span\s+class="html-tag">',
            str(soup))
        # 歌曲作者
        author = re.findall(
            r'<td\s+class="line-number"\s+value="17"></td><td\s+class="line-content"><span\s+class="html-tag">&lt;title&gt;</span>.*?\s+-\s+(.*?)\s+-\s+电台节目\s+-\s+网易云音乐<span\s+class="html-tag">',
            str(soup))
        # 歌曲封面
        image = re.findall(
            r'<span\s+class="html-attribute-value">og:image<\/span>"\s+<span\s+class="html-attribute-name">content<\/span>="<span\s+class="html-attribute-value">(https?:\/\/.*?)<\/span>"',
            str(soup))

        self.save_mp3(name[0],num[0],author[0],image[0])



            