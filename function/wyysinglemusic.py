import requests 
import os
import re
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC,TPE1,TIT2
from pydub import AudioSegment
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from bs4 import BeautifulSoup
from function.sercet import Secret_AES,detect_name
from function.wyylycis import WYYLYCIS
"""
    网易云音乐单曲下载
"""

class WYYMusic_singlemusic:
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
        #歌曲名字
        name=re.findall(r'og:title<\/span>"\s+<span\s+class="html-attribute-name">content<\/span>="<span\s+class="html-attribute-value">(.*?)<\/span>" ',str(soup))
        #歌曲id
        num=re.findall(r'.*?song\?id=(\d+)',url)
        #歌曲作者
        author=re.findall(r'og:music:artist<\/span>"\s+<span\s+class="html-attribute-name">content<\/span>="<span\s+class="html-attribute-value">(.*?)<\/span>"',str(soup))
        #歌曲封面
        image=re.findall(r'image<\/span>"\s+<span\s+class="html-attribute-name">content</span>="<span\s+class="html-attribute-value">(https?:\/\/.*?jpg)<\/span>"',str(soup))
        return name[0],num[0],author[0],image[0]

    def main_song(self,url):
        name,num,author,image=self.get_song_info(url)
        l,t=WYYLYCIS(url,self.user_agent).get_data(name)
        name=detect_name(name)
        url1="https://interface.music.163.com/weapi/song/enhance/player/url/v1?csrf_token="
        te=f'{{"ids":"[{num}]","level":"exhigh","encodeType":"aac","csrf_token":"{self.csrf_token}"}}'
        da=Secret_AES().get_data(te)
        headers={
            "cookie":self.cookie,
            "user-agent":self.user_agent
        }
        resp=requests.post(url1,headers=headers,data=da)
        resp=resp.json()
        song_url=resp["data"][0]["url"]
        resp=requests.get(song_url)
        with open(f"{self.path}/{name}.m4a","wb") as f:
            f.write(resp.content)

        #获取图片
        img=requests.get(image)
        with open(f"img/{name}.jpg","wb") as f:
            f.write(img.content)
        #MP3整合，加入作者封面等元素,从m4a转化为mp3
        in_file=f"{self.path}/{name}.m4a"
        out_file=f"{self.path}/{name}.mp3"
        song=AudioSegment.from_file(in_file,format="m4a")
        song.export(out_file,format="mp3")

        try:
            audio = MP3(out_file,ID3=ID3)
            try:
                audio.add_tags()
            except:
                pass
            audio["TPE1"]=TPE1(encoding=3,text=author)#设置作者
            audio["TIT2"]=TIT2(encoding=3,text=name)#设置歌名
            with open(f"img/{name}.jpg","rb") as f:
                audio["APIC"]=APIC(encoding=3,mime="image/jpeg",type=3,desc=u"Cover",data=f.read())#设置封面
            audio.save(v2_version=3)
        except Exception as e:
            self.new_print(f"歌曲修改失败,{e}")
        self.new_print(f"{name}.mp3 下载完成")
        os.remove(in_file)
        # os.remove(f"{name}.jpg")
       