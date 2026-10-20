import sys
import os
import asyncio
import threading
import re
import random
import json
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from function.wyy_main_func_window import MainFunc
from mutagen.easyid3 import EasyID3
from mutagen import File


class DownloadThread(QThread):
    progress_signal = pyqtSignal(int)
    message_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, url, path, cookie, user_agent, start_num="1", end_num="1"):
        super().__init__()
        self.url = url
        self.path = path
        self.cookie = cookie
        self.user_agent = user_agent
        self.start_num = start_num
        self.end_num = end_num
        self.is_running = True

    def run(self):
        try:
            self.message_signal.emit("开始下载...")

            # 在单独的线程中运行异步函数
            def run_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # 这里调用您的下载函数
                    MainFunc(self.path, self.cookie, self.user_agent, self.message_signal).main_spider_wyy(self.url,self.start_num,self.end_num)
                    self.finished_signal.emit(True)
                    self.message_signal.emit("下载完成!")
                except Exception as e:
                    self.message_signal.emit(f"下载失败: {str(e)}")
                    self.finished_signal.emit(False)
                finally:
                    loop.close()

            thread = threading.Thread(target=run_async)
            thread.start()
            thread.join()

        except Exception as e:
            self.message_signal.emit(f"下载失败: {str(e)}")
            self.finished_signal.emit(False)

    def stop(self):
        self.is_running = False


class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setting_path="setting.json"
        with open(self.setting_path, "r") as f:
            config=json.load(f)
            self.music_path=config.get("music_path")
            self.cookie=config.get("cookie")
            self.user_agent=config.get("user-agent")
        self.current_song_path = None
        self.download_thread = None
        self.downloaded_songs = []

        self.play_mode = 0  # 0:cycle, 1:single, 2:random
        self.current_playlist = []  # 当前播放列表
        self.current_song_index = -1  # 当前播放歌曲在列表中的索引

        # 歌词相关
        self.lyric_panel = None
        self.is_lyric_panel_visible = False
        self.drag_start_position = None

        # 新增歌词控制相关变量
        self.lyrics_data = []  # 存储解析后的歌词数据 [(时间戳, 歌词文本), ...]
        self.current_lyric_index = -1  # 当前显示的歌词索引
        self.lrc_time_list = []  # 歌词时间戳列表（毫秒）
        self.lrc_time_index = 0  # 歌词时间戳标记

        self.initUI()

    def initUI(self):
        # 设置窗口属性
        self.setWindowTitle('wyy音乐下载播放器')
        self.setFixedSize(1200, 800)
        self.setStyleSheet("background-color: #f5f5f5;")

        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建顶部导航栏
        self.create_navbar(main_layout)

        # 创建内容区域
        self.create_content(main_layout)

        # 创建底部播放控制栏
        self.create_player_control(main_layout)

        # 初始化媒体播放器
        self.init_media_player()

    def create_navbar(self, layout):
        # 导航栏容器
        navbar = QWidget()
        navbar.setFixedHeight(60)
        navbar.setStyleSheet("""
            QWidget {
                background-color: #ec4141;
                border-bottom: 1px solid #d8d8d8;
            }
        """)

        # 导航栏布局
        navbar_layout = QHBoxLayout(navbar)
        navbar_layout.setContentsMargins(20, 0, 20, 0)

        # 左侧logo和标题
        logo_label = QLabel("wyy音乐下载器")
        logo_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
        """)

        # 中间导航菜单
        nav_menu = QHBoxLayout()
        nav_items = ["音乐下载", "本地音乐"]
        for item in nav_items:
            btn = QPushButton(item)
            btn.setStyleSheet("""
                QPushButton {
                    color: white;
                    background: transparent;
                    border: none;
                    padding: 8px 15px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                    border-radius: 4px;
                }
            """)
            btn.clicked.connect(lambda checked, x=item: self.switch_tab(x))
            nav_menu.addWidget(btn)

        # 右侧搜索框和用户信息
        search_box = QLineEdit()
        search_box.setPlaceholderText("搜索本地音乐")
        search_box.setFixedWidth(200)
        search_box.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 15px;
                padding: 5px 15px;
                color: white;
                font-size: 13px;
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.7);
            }
        """)
        search_box.textChanged.connect(self.search_local_music)

        navbar_layout.addWidget(logo_label)
        navbar_layout.addStretch(1)
        navbar_layout.addLayout(nav_menu)
        navbar_layout.addStretch(1)
        navbar_layout.addWidget(search_box)

        layout.addWidget(navbar)

    def create_content(self, layout):
        # 内容区域容器
        self.content_stack = QStackedWidget()

        # 下载页面
        self.download_page = self.create_download_page()
        self.content_stack.addWidget(self.download_page)

        # 本地音乐页面
        self.local_music_page = self.create_local_music_page()
        self.content_stack.addWidget(self.local_music_page)

        layout.addWidget(self.content_stack)

    def create_download_page(self):
        page = QWidget()
        page.setStyleSheet(
            """
            QWidget {
               background-color: #EBE8D9;
            }
            """
        )

        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        # 下载设置组
        settings_group = QGroupBox("下载设置")
        settings_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #333;
            }
        """)
        settings_layout = QVBoxLayout(settings_group)

        # 保存路径选择
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("保存路径:"))
        self.path_edit = QLineEdit(os.path.expanduser(rf"{self.music_path}"))
        self.path_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        path_layout.addWidget(self.path_edit)
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #ec4141;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d63030;
            }
        """)
        self.browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(path_layout)

        # URL输入
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("歌曲URL:"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("请输入网易云音乐歌曲/歌单/歌手URL")
        self.url_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        url_layout.addWidget(self.url_edit)
        settings_layout.addLayout(url_layout)

        # 下载范围设置
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("下载范围:"))
        self.start_num_edit = QLineEdit("1")
        self.start_num_edit.setFixedWidth(60)
        self.start_num_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        range_layout.addWidget(self.start_num_edit)
        range_layout.addWidget(QLabel("到"))
        self.end_num_edit = QLineEdit("10")
        self.end_num_edit.setFixedWidth(60)
        self.end_num_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        range_layout.addWidget(self.end_num_edit)
        range_layout.addStretch(1)
        settings_layout.addLayout(range_layout)

        # Cookie和User-Agent
        cookie_layout = QHBoxLayout()
        cookie_layout.addWidget(QLabel("Cookie:"))
        self.cookie_edit = QLineEdit(f"{self.cookie}")
        self.cookie_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        cookie_layout.addWidget(self.cookie_edit)
        settings_layout.addLayout(cookie_layout)

        user_agent_layout = QHBoxLayout()
        user_agent_layout.addWidget(QLabel("User-Agent:"))
        self.user_agent_edit = QLineEdit(f"{self.user_agent}")
        self.user_agent_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        user_agent_layout.addWidget(self.user_agent_edit)
        settings_layout.addLayout(user_agent_layout)
        layout.addWidget(settings_group)

        # 下载控制组
        control_group = QGroupBox("下载控制")
        control_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #333;
            }
        """)
        control_layout = QVBoxLayout(control_group)

        # 下载按钮
        btn_layout = QHBoxLayout()
        self.download_btn = QPushButton("开始下载")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #ec4141;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d63030;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.download_btn.clicked.connect(self.start_download)
        btn_layout.addWidget(self.download_btn)

        self.stop_btn = QPushButton("停止下载")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_download)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        control_layout.addLayout(btn_layout)

        layout.addWidget(control_group)

        # 日志输出
        log_group = QGroupBox("下载日志")
        log_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #333;
            }
        """)
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
            }
        """)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)

        return page

    def create_local_music_page(self):
        page = QWidget()
        page.setStyleSheet(
            """
            QWidget {
               background-color: #EBE8D9;
            }
            """
        )
        layout = QHBoxLayout(page)  # 改为水平布局
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 左侧歌曲列表区域
        left_widget = QWidget()
        left_widget.setFixedWidth(400)  # 固定宽度
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 刷新按钮和搜索框
        top_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新本地音乐")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #ec4141;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d63030;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_local_music)
        top_layout.addWidget(self.refresh_btn)
        top_layout.addStretch(1)

        # 歌曲数量标签
        self.song_count_label = QLabel("歌曲列表 (0)")
        self.song_count_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
            }
        """)
        top_layout.addWidget(self.song_count_label)

        left_layout.addLayout(top_layout)

        # 本地音乐列表
        self.local_music_list = QListWidget()
        self.local_music_list.setStyleSheet("""
            QListWidget {
                background-color: #f9e9cd;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 15px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #f0f7ff;
                color: #ec4141;
                border-left: 3px solid #ec4141;
            }
            QListWidget::item:hover {
                background-color: #f8f8f8;
            }
        """)
        self.local_music_list.itemDoubleClicked.connect(self.play_selected_song)
        self.local_music_list.itemSelectionChanged.connect(self.on_song_selected)
        left_layout.addWidget(self.local_music_list)

        # 右侧歌词和歌曲信息区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 歌曲信息卡片
        info_card = QWidget()
        info_card.setFixedHeight(180)
        info_card.setStyleSheet("""
            QWidget {
                background-color: #f9e9cd;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 15, 20, 15)

        # 歌曲标题
        self.current_song_title_large = QLabel("未选择歌曲")
        self.current_song_title_large.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }
        """)
        self.current_song_title_large.setWordWrap(True)

        # 歌手信息
        self.current_song_artist_large = QLabel("未知艺术家")
        self.current_song_artist_large.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666;
                margin-bottom: 10px;
            }
        """)

        # 歌曲详情
        detail_layout = QHBoxLayout()

        # 专辑封面
        self.large_cover = QLabel()
        self.large_cover.setFixedSize(80, 80)
        self.large_cover.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)

        # 歌曲元数据
        meta_layout = QVBoxLayout()

        self.song_duration = QLabel("时长: 0:00")
        self.song_duration.setStyleSheet("QLabel { color: #666; font-size: 12px; }")

        self.song_bitrate = QLabel("音质: 未知")
        self.song_bitrate.setStyleSheet("QLabel { color: #666; font-size: 12px; }")

        meta_layout.addWidget(self.song_duration)
        meta_layout.addWidget(self.song_bitrate)
        meta_layout.addStretch(1)

        detail_layout.addWidget(self.large_cover)
        detail_layout.addSpacing(15)
        detail_layout.addLayout(meta_layout)
        detail_layout.addStretch(1)

        info_layout.addWidget(self.current_song_title_large)
        info_layout.addWidget(self.current_song_artist_large)
        info_layout.addLayout(detail_layout)

        # 歌词显示区域 - 使用QListWidget替代QTextEdit
        lyric_group = QGroupBox("歌词")
        lyric_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #333;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        lyric_layout = QVBoxLayout(lyric_group)

        # 使用QListWidget显示歌词，支持平滑滚动
        self.lyric_list_widget = QListWidget()
        self.lyric_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #f9e9cd;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px 15px;
                border: none;
                text-align: center;
            }
            QListWidget::item:selected {
                background-color: transparent;
                color: #ec4141;
                font-weight: bold;
                font-size: 15px;
            }
        """)
        self.lyric_list_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.lyric_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lyric_list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.lyric_list_widget.setFrameShape(QFrame.Shape.NoFrame)

        lyric_layout.addWidget(self.lyric_list_widget)

        right_layout.addWidget(info_card)
        right_layout.addWidget(lyric_group)

        layout.addWidget(left_widget)
        layout.addWidget(right_widget)

        return page

    def create_player_control(self, layout):
        # 播放控制栏容器
        player_widget = QWidget()
        player_widget.setFixedHeight(100)
        player_widget.setStyleSheet("""
            QWidget {
                background-color: #f9e9cd;
                border-top: 1px solid #f9e9cd;
            }
        """)

        player_layout = QHBoxLayout(player_widget)
        player_layout.setContentsMargins(20, 10, 20, 10)

        # 左侧歌曲信息
        song_info = QWidget()
        song_info_layout = QHBoxLayout(song_info)

        # 小专辑封面
        self.small_cover = QLabel()
        self.small_cover.setFixedSize(50, 50)
        self.small_cover.setStyleSheet("""
            QLabel {
                background-color: #e0e0e0;
                border-radius: 5px;
            }
        """)

        # 歌曲标题和歌手
        current_song_info = QVBoxLayout()
        self.current_song_title = QLabel("未选择歌曲")
        self.current_song_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #333;
            }
        """)

        self.current_song_artist = QLabel("未知艺术家")
        self.current_song_artist.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #666;
            }
        """)

        current_song_info.addWidget(self.current_song_title)
        current_song_info.addWidget(self.current_song_artist)

        song_info_layout.addWidget(self.small_cover)
        song_info_layout.addSpacing(10)
        song_info_layout.addLayout(current_song_info)

        # 中间播放控制区域
        play_control = QWidget()
        play_control_layout = QVBoxLayout(play_control)

        # 播放控制按钮
        control_buttons = QHBoxLayout()
        control_buttons.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 创建按钮
        self.prev_btn = QPushButton()
        self.prev_btn.setStyleSheet("""
                                       QPushButton{
                                             image: url(function/images/上一曲.png);
                                             font-size: 16px;
                                        }
                                        QPushButton:hover{
                                             image: url(function/images/上一曲 深色.png);
                                             font-size: 16px;
                                        }
                                    """)
        self.prev_btn.clicked.connect(self.play_previous)

        self.play_btn = QPushButton()
        self.play_btn.setStyleSheet("""
                                       QPushButton{
                                             image: url(function/images/暂停.png);
                                             font-size: 16px;
                                        }
                                        QPushButton:hover{
                                             image: url(function/images/暂停 深色.png);
                                             font-size: 16px;
                                        }
                                    """)
        self.play_btn.setFixedSize(40, 30)
        self.play_btn.clicked.connect(self.play_music)

        self.next_btn = QPushButton()
        self.next_btn.setStyleSheet("""
                                       QPushButton{
                                             image: url(function/images/下一曲.png);
                                             font-size: 16px;
                                        }
                                        QPushButton:hover{
                                             image: url(function/images/下一曲 深色.png);
                                             font-size: 16px;
                                        }
                                    """)
        self.next_btn.clicked.connect(self.play_next)

        self.mode_btn = QPushButton()
        self.mode_btn.setToolTip('列表循环')
        self.mode_btn.setStyleSheet("""
                               QPushButton{
                                   image: url(function/images/列表循环.png);
                                   font-size: 16px;
                               }
                               QPushButton:hover{
                                   image: url(function/images/列表循环 深色.png);
                                   font-size: 16px;
                               }
                           """)
        self.mode_btn.clicked.connect(self.change_play_mode)


        control_buttons.addWidget(self.prev_btn)
        control_buttons.addWidget(self.play_btn)
        control_buttons.addWidget(self.next_btn)
        control_buttons.addWidget(self.mode_btn)

        # 进度条
        progress_layout = QHBoxLayout()

        self.current_time = QLabel("0:00")
        self.current_time.setStyleSheet("font-size: 12px; color: white;")

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: #f0f0f0;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: red;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: red;
                width: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
        """)
        self.progress_slider.setValue(0)
        self.progress_slider.sliderMoved.connect(self.seek_position)

        self.total_time = QLabel("0:00")
        self.total_time.setStyleSheet("font-size: 12px; color: white;")

        progress_layout.addWidget(self.current_time)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.total_time)

        play_control_layout.addLayout(control_buttons)
        play_control_layout.addLayout(progress_layout)

        # 右侧音量控制
        volume_control = QHBoxLayout()
        volume_control.setAlignment(Qt.AlignmentFlag.AlignRight)

        volume_icon = QPushButton("🔊")
        volume_icon.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #666;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #ec4141;
            }
        """)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: #f0f0f0;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #999;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #999;
                width: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
        """)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.set_volume)

        volume_control.addWidget(volume_icon)
        volume_control.addWidget(self.volume_slider)

        # 添加到主布局
        player_layout.addWidget(song_info)
        player_layout.addStretch(1)
        player_layout.addWidget(play_control)
        player_layout.addStretch(1)
        player_layout.addLayout(volume_control)

        layout.addWidget(player_widget)

    def init_media_player(self):
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        # 连接信号
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.playbackStateChanged.connect(self.update_play_button)
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)

    def save_setting(self):
        """保存配置文件"""
        config = {
            "music_path":self.music_path,
            "cookie":self.cookie,
            "user-agent":self.user_agent,
        }
        with open(self.setting_path, 'w') as f:
            json.dump(config, f)

    def on_song_selected(self):
        """当歌曲被选中时更新右侧信息"""
        current_item = self.local_music_list.currentItem()
        if current_item:
            song_path = current_item.data(Qt.ItemDataRole.UserRole)
            self.update_song_info(song_path)

    def update_song_info(self, song_path):
        """更新歌曲详细信息"""
        if not os.path.exists(song_path):
            return

        try:
            # 获取歌曲基本信息
            audio = EasyID3(song_path)
            song_name = os.path.splitext(os.path.basename(song_path))[0]
            artist = audio.get('artist', ['未知艺术家'])[0]

            # 更新大标题
            self.current_song_title_large.setText(song_name)
            self.current_song_artist_large.setText(artist)

            # 获取歌曲时长
            try:
                audio_file = File(song_path)
                if audio_file is not None:
                    duration = int(audio_file.info.length)
                    minutes = duration // 60
                    seconds = duration % 60
                    self.song_duration.setText(f"时长: {minutes}:{seconds:02d}")

                    # 获取比特率
                    bitrate = getattr(audio_file.info, 'bitrate', 0)
                    if bitrate:
                        self.song_bitrate.setText(f"音质: {bitrate // 1000} kbps")
                    else:
                        self.song_bitrate.setText("音质: 标准")
                else:
                    self.song_duration.setText("时长: 未知")
                    self.song_bitrate.setText("音质: 未知")
            except:
                self.song_duration.setText("时长: 未知")
                self.song_bitrate.setText("音质: 未知")

            # 更新专辑封面
            cover_path = os.path.join("img", f"{song_name}.jpg")
            if os.path.exists(cover_path):
                pixmap = QPixmap(cover_path)
                self.large_cover.setPixmap(pixmap.scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatio,
                                                         Qt.TransformationMode.SmoothTransformation))
            else:
                # 设置默认封面
                default_pixmap = QPixmap(80, 80)
                default_pixmap.fill(QColor("#ec4141"))
                self.large_cover.setPixmap(default_pixmap)

            # 加载歌词
            self.load_lyrics(song_name)

        except Exception as e:
            print(f"更新歌曲信息失败: {e}")

    def load_lyrics(self, song_name):
        """加载并解析歌词文件"""
        lyric_path = os.path.join("txt", f"{song_name}.lrc")
        self.lyrics_data = []  # 存储解析后的歌词数据
        self.lrc_time_list = []  # 歌词时间戳列表
        self.current_lyric_index = -1  # 当前显示的歌词索引

        if os.path.exists(lyric_path):
            try:
                with open(lyric_path, 'r', encoding='utf-8') as f:
                    raw_lyrics = f.read()

                # 使用新的歌词解析方法
                lrc_dict = self.get_lrc_dict(raw_lyrics)
                self.lrc_time_list = list(lrc_dict.keys())

                # 转换为歌词数据格式
                for lrc_time in self.lrc_time_list:
                    if len(lrc_dict[lrc_time])==1:
                        lyric_text = lrc_dict[lrc_time][0]
                        self.lyrics_data.append((lrc_time, lyric_text))
                    else:
                        lyric_text = lrc_dict[lrc_time][0]+"\n"+lrc_dict[lrc_time][1]
                        self.lyrics_data.append((lrc_time, lyric_text))
                # 按时间排序
                self.lyrics_data.sort(key=lambda x: x[0])
                self.lrc_time_list.sort()

                # 初始化显示所有歌词
                self.display_all_lyrics()

            except Exception as e:
                self.display_lyric_error("歌词解析失败\n\n请确保歌词文件格式正确")
                print(f"歌词解析错误: {e}")
        else:
            self.display_lyric_error("暂无歌词")
            self.lyrics_data = []
            self.lrc_time_list = []

    def get_lrc_dict(self, lyrics):
        """根据时间戳将歌词转为字典"""
        if not lyrics:
            return {}
        lrc_list = lyrics.splitlines()
        # 时间戳正则
        func = re.compile(r"\[.*?]")
        # 根据时间戳，转换成字典
        lrc_dict = {}
        for item in lrc_list:
            searched = func.search(item)
            if not searched:
                continue
            lrc_time = searched.group()
            time_str_list = lrc_time[1:-1].split(":")
            if not time_str_list[0].isdigit():
                continue
            try:
                lrc_time_int = int(time_str_list[0]) * 60000 + int(float(time_str_list[1]) * 1000)
                lrc_text = func.sub('', item)
                lrc_text = ' '.join(lrc_text.split())  # 去除多余空格
                if lrc_dict.get(lrc_time_int):
                    lrc_dict[lrc_time_int].append(lrc_text)
                else:
                    lrc_dict[lrc_time_int] = [lrc_text]
            except ValueError:
                continue
        return lrc_dict

    def display_all_lyrics(self):
        """显示所有歌词（初始状态）"""
        if not self.lyrics_data:
            self.display_lyric_error("暂无歌词")
            return

        self.lyric_list_widget.clear()

        for time_ms, lyric_text in self.lyrics_data:
            item = QListWidgetItem(lyric_text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)  # 使项目不可选中但可高亮
            self.lyric_list_widget.addItem(item)

        # 滚动到顶部
        self.lyric_list_widget.verticalScrollBar().setValue(0)

    def display_lyric_error(self, message):
        """显示歌词错误信息"""
        self.lyric_list_widget.clear()
        item = QListWidgetItem(message)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self.lyric_list_widget.addItem(item)

    def update_lyrics_display(self, position):
        """根据播放位置更新歌词显示"""
        if not self.lrc_time_list:
            return

        # 重置歌词时间索引查找
        self.lrc_time_index = 0
        while True:
            # 保证列表不超限
            if self.lrc_time_index > len(self.lrc_time_list) - 1:
                break
            # 匹配歌词时间
            elif self.lrc_time_list[self.lrc_time_index] < position:
                self.lrc_time_index += 1
            else:
                break

        # 更新当前歌词索引
        new_lyric_index = self.lrc_time_index - 1

        # 如果歌词索引发生变化，更新显示
        if new_lyric_index != self.current_lyric_index and new_lyric_index != -1:
            self.current_lyric_index = new_lyric_index
            self.highlight_current_lyric()

    def highlight_current_lyric(self):
        """高亮显示当前歌词"""
        if not self.lyrics_data or self.current_lyric_index == -1:
            return

        # 清除之前的高亮
        for i in range(self.lyric_list_widget.count()):
            item = self.lyric_list_widget.item(i)
            item.setForeground(QColor(0,0,0))

        # 高亮当前歌词
        if 0 <= self.current_lyric_index < self.lyric_list_widget.count():
            item = self.lyric_list_widget.item(self.current_lyric_index)
            item.setForeground(QColor(255, 0, 0))
            self.animated_scroll_to_lyric(item)

    def animated_scroll_to_lyric(self, item):
        """带动画地滚动到当前歌词"""
        if not item:
            return

        scroll_bar = self.lyric_list_widget.verticalScrollBar()
        item_rect = self.lyric_list_widget.visualItemRect(item)
        viewport_height = self.lyric_list_widget.viewport().height()

        # 计算目标滚动值，使当前歌词在视图中央
        target_value = scroll_bar.value() + item_rect.top() - (viewport_height - item_rect.height()) / 2

        # 创建并启动滚动动画
        self.scroll_animation = QPropertyAnimation(scroll_bar, b"value", self)
        self.scroll_animation.setDuration(400)  # 动画时长
        self.scroll_animation.setStartValue(scroll_bar.value())
        self.scroll_animation.setEndValue(int(target_value))
        self.scroll_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)  # 缓动曲线
        self.scroll_animation.start()

    def change_play_mode(self):
        """
        切换播放模式
        0 => 顺序播放
        1 => 单曲循环
        2 => 随机播放
        """
        self.play_mode += 1
        if self.play_mode > 2:
            self.play_mode = 0
        self.set_play_mode_stylesheet()

    def set_play_mode_stylesheet(self):
        """播放图标样式"""
        if self.play_mode == 0:
            self.mode_btn.setToolTip('列表循环')
            self.mode_btn.setStyleSheet("""
                       QPushButton{
                           image: url(function/images/列表循环.png);
                           font-size: 16px;
                       }
                       QPushButton:hover{
                           image: url(function/images/列表循环 深色.png);
                           font-size: 16px;
                       }
                   """)
        if self.play_mode == 1:
            self.mode_btn.setToolTip('单曲循环')
            self.mode_btn.setStyleSheet("""
                                   QPushButton{
                                       image: url(function/images/单曲循环.png);
                                       font-size: 16px;
                                   }
                                   QPushButton:hover{
                                       image: url(function/images/单曲循环 深色.png);
                                       font-size: 16px;
                                   }
                               """)
        if self.play_mode == 2:
            self.mode_btn.setToolTip('随机播放')
            self.mode_btn.setStyleSheet("""
                                   QPushButton{
                                       image: url(function/images/随机播放.png);
                                       font-size: 16px;
                                   }
                                   QPushButton:hover{
                                       image: url(function/images/随机播放 深色.png);
                                       font-size: 16px;
                                   }
                               """)


    def play_previous(self):
        """播放上一首"""
        if not self.current_playlist:
            return
        if self.play_mode == 2:
            self.current_song_index = random.randint(0, len(self.current_playlist) - 1)
        else:
            self.current_song_index = (self.current_song_index - 1) % len(self.current_playlist)
        self.play_song_by_index(self.current_song_index)

    def play_next(self):
        """播放下一首"""
        if not self.current_playlist:
            return
        if self.play_mode == 2:
            self.current_song_index = random.randint(0, len(self.current_playlist) - 1)
        else:
            self.current_song_index = (self.current_song_index + 1) % len(self.current_playlist)
        self.play_song_by_index(self.current_song_index)

    def play_song_by_index(self, index):
        """根据索引播放歌曲"""
        if 0 <= index < len(self.current_playlist):
            song_path = self.current_playlist[index]
            self.current_song_index = index
            self.play_song_file(song_path)

            # 更新列表选中状态
            for i in range(self.local_music_list.count()):
                item = self.local_music_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == song_path:
                    self.local_music_list.setCurrentItem(item)
                    break

    def seek_position(self, position):
        """跳转到指定位置"""
        if self.media_player.duration() > 0:
            new_position = int((position / 100) * self.media_player.duration())
            self.media_player.setPosition(new_position)
            # 重置歌词时间索引
            self.lrc_time_index = 0

    def handle_media_status(self, status):
        """处理媒体状态变化"""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.play_mode == 1:
                # 单曲循环，重新播放当前歌曲
                self.media_player.setPosition(0)
                self.media_player.play()
            else:
                self.play_next()

    def switch_tab(self, tab_name):
        if tab_name == "音乐下载":
            self.content_stack.setCurrentIndex(0)
        elif tab_name == "本地音乐":
            self.content_stack.setCurrentIndex(1)
            self.refresh_local_music()

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存路径", self.path_edit.text())
        if path:
            self.path_edit.setText(path)

    def start_download(self):
        url = self.url_edit.text().strip()
        self.music_path = self.path_edit.text().strip()
        self.cookie = self.cookie_edit.text().strip()
        self.user_agent = self.user_agent_edit.text()
        start_num = self.start_num_edit.text().strip()
        end_num = self.end_num_edit.text().strip()
        self.save_setting()
        if not url:
            QMessageBox.warning(self, "警告", "请输入URL!")
            return

        if not self.music_path:
            QMessageBox.warning(self, "警告", "请选择保存路径!")
            return

        # 创建下载线程
        self.download_thread = DownloadThread(url, self.music_path, self.cookie, self.user_agent, start_num, end_num)
        self.download_thread.message_signal.connect(self.update_log)
        self.download_thread.finished_signal.connect(self.download_finished)

        # 更新UI状态
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 启动下载线程
        self.download_thread.start()

    def stop_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.download_thread.wait()
            self.update_log("下载已停止")

    def download_finished(self, success):
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if success:
            self.refresh_local_music()

    def update_log(self, message):
        self.log_text.append(message)
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def refresh_local_music(self):
        self.local_music_list.clear()
        path = self.path_edit.text().strip()
        if not os.path.exists(path):
            return

        # 重建播放列表
        self.current_playlist = []

        # 查找MP3文件
        for file in os.listdir(path):
            if file.endswith('.mp3'):
                song_path = os.path.join(path, file)
                self.current_playlist.append(song_path)

                # 显示友好的文件名（去除扩展名）
                display_name = os.path.splitext(file)[0]
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, song_path)
                self.local_music_list.addItem(item)

        # 更新歌曲数量
        self.song_count_label.setText(f"歌曲列表 ({len(self.current_playlist)})")

    def search_local_music(self, text):
        for i in range(self.local_music_list.count()):
            item = self.local_music_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def play_music(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            if self.current_song_path and os.path.exists(self.current_song_path):
                self.media_player.play()

    def play_selected_song(self, item):
        song_path = item.data(Qt.ItemDataRole.UserRole)

        try:
            self.current_song_index = self.current_playlist.index(song_path)
        except ValueError:
            self.current_song_index = -1

        self.play_song_file(song_path)

    def play_song_file(self, song_path):
        """播放指定的歌曲文件"""
        # 重置歌词状态
        self.lyrics_data = []
        self.lrc_time_list = []
        self.current_lyric_index = -1
        self.lrc_time_index = 0
        self.lyric_list_widget.clear()

        self.current_song_path = song_path

        # 更新歌曲信息
        try:
            audio = EasyID3(song_path)
            author = audio.get('artist', ['未知'])[0]
            song_name = os.path.splitext(os.path.basename(song_path))[0]
            self.current_song_title.setText(song_name)
            self.current_song_artist.setText(author)
        except:
            song_name = os.path.splitext(os.path.basename(song_path))[0]
            self.current_song_title.setText(song_name)
            self.current_song_artist.setText("未知艺术家")

        # 更新右侧详细信息
        self.update_song_info(song_path)

        # 尝试加载专辑封面
        cover_path = os.path.join("img", f"{song_name}.jpg")
        if os.path.exists(cover_path):
            pixmap = QPixmap(cover_path)
            self.small_cover.setPixmap(
                pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            # 设置默认封面
            default_pixmap = QPixmap(50, 50)
            default_pixmap.fill(QColor("#ec4141"))
            self.small_cover.setPixmap(default_pixmap)

        # 播放歌曲
        self.media_player.setSource(QUrl.fromLocalFile(song_path))
        self.media_player.play()

        # 加载新歌词
        song_name = os.path.splitext(os.path.basename(song_path))[0]
        self.load_lyrics(song_name)

    def set_volume(self, value):
        self.audio_output.setVolume(value / 100.0)

    def update_position(self, position):
        if self.media_player.duration() > 0:
            progress = int((position / self.media_player.duration()) * 100)
            self.progress_slider.setValue(progress)

            # 更新时间显示
            minutes = position // 60000
            seconds = (position % 60000) // 1000
            self.current_time.setText(f"{minutes}:{seconds:02d}")

            # 更新歌词显示
            self.update_lyrics_display(position)

    def update_duration(self, duration):
        if duration > 0:
            minutes = duration // 60000
            seconds = (duration % 60000) // 1000
            self.total_time.setText(f"{minutes}:{seconds:02d}")

    def update_play_button(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setStyleSheet("""
                                           QPushButton{
                                                 image: url(function/images/播放中.png);
                                                 font-size: 16px;
                                            }
                                            QPushButton:hover{
                                                 image: url(function/images/播放中 深色.png);
                                                 font-size: 16px;
                                            }
                                        """)
        else:
            self.play_btn.setStyleSheet("""
                                           QPushButton{
                                                 image: url(function/images/暂停.png);
                                                 font-size: 16px;
                                            }
                                            QPushButton:hover{
                                                 image: url(function/images/暂停 深色.png);
                                                 font-size: 16px;
                                            }
                                        """)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 设置应用程序字体
    font_id = QFontDatabase.addApplicationFont("function/fonts/霞鹜文楷.ttf")
    font_families = QFontDatabase.applicationFontFamilies(font_id)
    font = QFont(font_families, 12)
    app.setFont(font)

    player = MusicPlayer()
    player.show()

    sys.exit(app.exec())