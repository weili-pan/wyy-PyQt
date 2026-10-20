import requests
import json
import re
import os
from function.sercet import detect_name
"""
获取歌词
"""

class WYYLYCIS:
    def __init__(self,url,user_agent):
        self.url=url
        self.user_agent=user_agent
        if not os.path.exists("txt"):
            os.makedirs("txt")

    def get_data(self,name):
        id=re.findall(r'.*?id=(\d+)',self.url)[0]
        new_url=f'http://music.163.com/api/song/lyric?id={id}&lv=1&kv=1&tv=-1'
        headers={
            'User-Agent': self.user_agent,
        }
        resp=requests.get(new_url,headers=headers)
        data=json.loads(resp.text)
        lyric=data['lrc']['lyric']
        if lyric=="":
            return None,None
        else:
            tlyric=data['tlyric']['lyric']
            name=detect_name(name)
            with open(f"txt/{name}.lrc",'w',encoding='utf-8') as f:
                f.write(lyric+tlyric)
            return lyric,tlyric


