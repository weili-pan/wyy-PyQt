import requests
import re
import time
import random
import sys
import os
from function.wyydownload_async import WYYDownload

"""
网易云歌单的下载，可以自己设置下载的歌曲范围
"""

class WYYsonglist:
    def __init__(self,path,url,cookie,user_agent,start_num,end_num,message_signal = None):
        self.txt_path = "songlist.txt"
        self.path = path
        self.url = url
        self.cookie = cookie
        self.user_agent = user_agent
        self.start_num = int(start_num)#开始数
        self.end_num = int(end_num)#结束数
        self.message_signal = message_signal
        self.total_num = 0
        self.csrf_token="d5173e02fd2de201b463865127ea7ad1"
        self.wyy_download = WYYDownload(self.txt_path,self.path,self.cookie,self.user_agent,self.start_num,self.end_num,self.message_signal)
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        if not os.path.exists("txt"):
            os.makedirs("txt")

    def new_print(self, message):
        if self.message_signal:
            self.message_signal.emit(str(message))
        else:
            print(message)

    def get_song_list(self):
        name_list = []
        id_list = []
        number=re.findall(r'.*?id=(\d+)',self.url)[0]
        tt1=True
        while tt1:
            new_url = f"http://music.163.com/api/playlist/detail?id={number}"
            headers = {"User-Agent": self.user_agent,"Cookie": self.cookie}
            response = requests.get(new_url, headers=headers)
            random_num=random.randint(1,2)
            time.sleep(random_num)
            data =response.json()
            if str(data)=="{'msg': '服务器忙碌，请稍后再试！', 'code': -447, 'message': '服务器忙碌，请稍后再试！'}":
                self.new_print("服务器忙碌，请稍后再试！")
            else:
                songs_info_list=data["result"]["tracks"]
                for n,song_info in enumerate(songs_info_list):
                    name_list.append(song_info["name"])
                    id_list.append(song_info["id"])
                tt1=False
            
        songs_dict={}
        for i in range(len(name_list)):
            songs_dict[i+1]=[name_list[i],id_list[i]]
        
        with open(f"{self.txt_path}","w",encoding="utf-8") as f:
            f.write(str(songs_dict))
        self.total_num = len(songs_dict)
        if self.total_num<self.end_num:
            self.new_print("歌单歌曲数量不足，请重新输入")
            sys.exit()
        return len(songs_dict)
    

async def WYYsonglist_main_download(path,url,cookie,user_agent,start_num,end_num,message_signal):
    wyy=WYYsonglist(path,url,cookie,user_agent,start_num,end_num,message_signal)
    await wyy.wyy_download.download_song()
   
           
