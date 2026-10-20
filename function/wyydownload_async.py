from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Playwright
import asyncio
import aiofiles
import aiohttp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC,TPE1,TIT2
from pydub import AudioSegment
from bs4 import BeautifulSoup
import re
from function.sercet import Secret_AES,detect_name
import json
import os
from function.wyylycis import WYYLYCIS
"""
网易云多首音乐异步下载器
"""

class WYYDownload:
    def __init__(self,txt_path,path,cookie,user_agent,start_num,end_num,message_signal = None,
                 re_name=r'em\s+<span\s+class="html-attribute-name">class<\/span>="<span\s+class="html-attribute-value">f-ff2<\/span>"&gt;<\/span>(.*?)<span\s+class="html-tag">',
                 re_num=r'.*?song\?id=(\d+)',
                 re_author=r'og:music:artist<\/span>"\s+<span\s+class="html-attribute-name">content<\/span>="<span\s+class="html-attribute-value">(.*?)<\/span>"',
                 re_image=r'image<\/span>"\s+<span\s+class="html-attribute-name">content</span>="<span\s+class="html-attribute-value">(https?:\/\/.*?jpg)<\/span>"'
                 ):
        self.txt_path = txt_path#歌曲列表txt路径
        self.path = path
        self.cookie = cookie
        self.user_agent = user_agent
        self.start_num = int(start_num)#开始数
        self.end_num = int(end_num)#结束数
        self.message_signal = message_signal
        self.re_name=re_name
        self.re_num=re_num
        self.re_author=re_author
        self.re_image=re_image

        self.csrf_token="d5173e02fd2de201b463865127ea7ad1"

    def new_print(self, message):
        if self.message_signal:
            self.message_signal.emit(str(message))
        else:
            print(message)

    async def download_MP3(self,url,playwright:Playwright):
        name,num,author,image=await self.get_song_info(url,playwright=playwright)
        name=detect_name(name)
        url1="https://interface.music.163.com/weapi/song/enhance/player/url/v1?csrf_token="
        te=f'{{"ids":"[{num}]","level":"exhigh","encodeType":"aac","csrf_token":"{self.csrf_token}"}}'
        da=Secret_AES().get_data(te)
        headers={
            "cookie":self.cookie,
            "user-agent":self.user_agent
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url1,headers=headers,data=da) as response:
                resp_data=await response.text()
                data=json.loads(resp_data)
                song_url=data["data"][0]["url"]

            async with session.get(song_url) as resp:
                song_data=await resp.read()
                async with aiofiles.open(f"{self.path}/{name}.m4a","wb") as f:
                    await f.write(song_data)
    
            async with session.get(image) as resp:
                img_data = await resp.read()
                async with aiofiles.open(f"img/{name}.jpg", "wb") as f:
                    await f.write(img_data)

        #MP3整合，加入作者封面等元素,从m4a转化为mp3
        in_file=f"{self.path}/{name}.m4a"
        out_file=f"{self.path}/{name}.mp3"
        try:
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
        except Exception as e:
            self.new_print(f"{name}.m4a 下载失败,{e}")
    
    async def get_song_info(self,url,playwright:Playwright):
        browser =await playwright.chromium.launch()
        page =await browser.new_page()
        try:
            try:
                await page.goto(url,timeout=40000)
            except PlaywrightTimeoutError:
                self.new_print(f"{url} 连接超时")
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            #歌曲名字
            name=re.findall(rf'{self.re_name}',str(soup))
            #歌曲id
            num=re.findall(rf'{self.re_num}',url)
            #歌曲作者
            author=re.findall(rf'{self.re_author}',str(soup))
            #歌曲封面
            image=re.findall(rf'{self.re_image}',str(soup))
            l,t=WYYLYCIS(url,self.user_agent).get_data(name[0])
            return name[0],num[0],author[0],image[0]
        finally:
            await browser.close()
        
    
    async def download_song(self):
        async with async_playwright() as playwright:
            tasks=[]
            async with aiofiles.open(f"{self.txt_path}","r",encoding="utf-8") as f:
               songs_dict=await f.read()
               
            songs_dict=eval(songs_dict)
            for i in range(self.start_num,self.end_num+1):
               url=f"view-source:https://music.163.com/song?id={songs_dict[i][1]}"
               tasks.append(asyncio.create_task(self.download_MP3(url,playwright)))
            await asyncio.gather(*tasks)
