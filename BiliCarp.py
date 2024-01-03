'''
coding:utf-8
@Software: PyCharm
@Time: 2023/12/30 23:32
@Author: Aocf
@versionl: 3.
'''
import time
from utils import _del_temporary, _str_clean, get_user_angent
import requests
from bs4 import BeautifulSoup
import re
import json
import cv2
import ffmpeg
import os
import av
import io
import imageio
from moviepy.editor import VideoFileClip, VideoClip, concatenate_videoclips, AudioClip,AudioFileClip,concatenate_audioclips

# TODO 一个文件夹存储100个视频 提高检索效率
# TODO 增加异常捕捉机制
# TODO 音乐和视频合并分辨率下降问题
# TODO 增加多线程提效
# TODO 增加视频信息写入检索数据库

class Craper(object):
    """
    B站视频爬取
    """

    def __init__(self, url, headers, save_path, cookies=None):
        self.url, self.headers, self.cookies = url, headers, cookies
        self.webpage = requests.get(url, headers=headers, cookies=cookies)
        self.web_parse()

        self.agent_iteration = 20
        self.save_path = save_path
        self.concate_path = r'./concate'
        if not os.path.exists(self.concate_path):
            os.mkdir(self.concate_path)  # 用于视频合成临时存储

    def web_parse(self):
        """
        获取页面所有视频的标题和网址
        :return:[(tittle, links), (), ...]
        """
        if self.webpage.status_code == 200:
            soup = BeautifulSoup(self.webpage.text, 'lxml')
            titles, links = [], []
            for link in soup.find_all('a', {'class': 'title'}):
                t = link.get('title')
                if t is not None:
                    links.append(link.get('href'))
                    titles.append(t)
            assert len(links) > 0, f'无法从网址解析出视频链接, url={self.url}'
            # 进一步清洗
            tls = list(zip(titles, links))
            self.tls = [(t, r'https://' + x[2:]) for (t, x) in tls if x[2:].startswith('www')]  # //www.***
        else:
            raise ValueError(f'网页请求失败， 失败码{self.webpage.status_code}')

    def get_per_video(self, play_url):
        """
        获得每一个视频并保存
        :param video_url: 点击标题进入的视频播放链接，注: 不是视频下载的链接
        :return:
        """
        res_video = requests.get(play_url, headers=headers, cookies=cookies)
        if res_video.status_code == 200:
            # 解析视频信息
            title = re.search('<title data-vue-meta="true">(.*?)</title>',
                              res_video.text)[0].split('>')[1].split('<')[0]
            try:
                play_info = re.findall('<script>window.__playinfo__=(.*?)</script>', res_video.text)[0]
                play_info = json.loads(play_info)  # dict
                v_ls, a_ls = self._video_audio_links_parse(play_info)
                self._dowload(v_ls, a_ls, title)
            except Exception as e:
                print(e)
                print('无法从播放网址解析出视频下载链接')  # TODO 增加新的解析方法
        else:
            raise ValueError('无法从播放网址解析出视频下载链接', play_url)

    def run(self):
        for i, (t, play_link) in enumerate(self.tls):  # 遍历所有播放链接
            if (i + 1) // self.agent_iteration == 0:
                self.headers['User-Agent'] = get_user_angent()  # 每轮迭代更新代理

            self.get_per_video(play_link)

    def _video_audio_links_parse(self, play_info: dict):
        """
        解析音频和视频网址
        :param play_info:视频属性解析字典
        :return: 视频网址和音频网址
        """
        quality_code = [112, 80, 64, 32, 16]  # 清晰度代码
        videos = play_info['data']['dash']['video']
        audios = play_info['data']['dash']['audio']
        # 返回清晰度最高的链接
        v_ls, a_ls = [], []
        i = 0
        while len(v_ls) == 0:
            v_ls = [x['base_url'] for x in videos if x['id'] == quality_code[i]]
            i += 1

        j = 0
        while len(a_ls) == 0:
            a_ls = [x['base_url'] for x in audios if int(str(x['id'])[-2:]) == quality_code[j]]
            j += 1

        return list(set(v_ls)), list(set(a_ls))  # 去重

    def _dowload(self,  v_ls, a_ls, title):
        """
        下载视频和音频
        :param v_ls:
        :param a_ls:
        :return:
        """
        print(title)
        # 发送请求
        video_ls, audio_ls = [], []
        for v in v_ls:
            video_ls.append(
                requests.get(url=v, headers=self.headers, cookies=self.cookies))

        for a in a_ls:
            audio_ls.append(
                requests.get(url=a, headers=self.headers, cookies=self.cookies))

        # 状态判断
        connect_video = 1 if sum([x.status_code for x in video_ls]) == 200 * len(video_ls) else 0
        connect_audio = 1 if sum([x.status_code for x in audio_ls]) == 200 * len(audio_ls) else 0
        video_path, audio_path = [], []
        if connect_video:
            if len(video_ls) >= 2:
                """
                多段视频:
                一个清晰度下或存在多段拼接
                """
                decode_ = [(i, av.open(io.BytesIO(x.content)))
                           for i, x in enumerate(video_ls)]
                decode_ = sorted(decode_, key=lambda x: x[1].size)  # 按size升序
                # 使用字典进行过滤
                idx_select = {}
                for d in decode_:
                    idx_select[d[1].duration] = d[0]  # 时长: 序号
                video_ls = [video_ls[x] for x in idx_select.values()]
            for i, video in enumerate(video_ls):
                p = self._make_path(f'{i}video_{title}.mp4')
                video_path.append(p)
                with open(p, mode='wb') as f:
                    f.write(video.content)
                f.close()
        else:
            print('视频下载失败，无法获取视频链接')

        if connect_audio and connect_audio:
            if len(audio_ls) >= 2:
                """
                多段音频:
                一个清晰度下或存在多段拼接
                """
                decode_ = [(i, av.open(io.BytesIO(x.content)))
                           for i, x in enumerate(audio_ls)]
                decode_ = sorted(decode_, key=lambda x: x[1].size)  # 按size升序
                # 使用字典进行过滤
                idx_select = {}
                for d in decode_:
                    idx_select[d[1].duration] = d[0]  # 时长: 序号
                audio_ls = [audio_ls[x] for x in idx_select.values()]
            for i, audio in enumerate(audio_ls):
                p = self._make_path(f'{i}_audio_{title}.mp3')
                audio_path.append(p)
                with open(p, mode='wb') as f:
                    f.write(audio.content)
                f.close()
        else:
            print('音频下载失败')

        del v_ls, a_ls, video_ls, audio_ls

        # 拼接视频和音频
        self._concate_all(video_path, audio_path, title)

    def _concate_all(self, video_path, audio_path, title):
        """
        根据存储路径拼接视频和音频
        :param video_path: 视频存储路径
        :param audio_path: 音频存储路径
        :return:
        """
        if len(video_path) == 0:
            return
        if len(audio_path) != 0:
            fv = self._concate_target(video_path)
            fa = self._concate_target(audio_path)
            fv = fv.set_audio(fa)
            # 存储
        else:
            fv = self._concate_target(video_path)  # 只拼接视频
        fv.write_videofile(f"{self._make_path(title + '.mp4', 'save')}")
        fv.close()

        # 清空临时缓存
        _del_temporary(video_path)
        _del_temporary(audio_path)

    def _concate_target(self, file_path):
        files = []
        if file_path[0].endswith('mp4'):
            for fp in file_path:
                files.append(VideoFileClip(fp))
            files = concatenate_videoclips(files)
        else:  # 合并音频
            for fp in file_path:
                files.append(AudioFileClip(fp))
            files = concatenate_audioclips(files)
        return files

    def _make_path(self, filename, mode='concat'):
        if mode == 'concat':
            return os.path.join(self.concate_path, filename)
        elif mode == 'save':
            return os.path.join(self.save_path, filename)
        else:
            return

if __name__ == '__main__':
    cookies = {}
    with open('txt.txt', encoding='utf-8') as f:
        lines = f.readlines()
        for l in lines:
            s = l.split('\t')
            cookies[s[0]] = s[1]

    headers = {'Referer': 'https://www.bilibili.com/',
               'Accept': '/',
               'Accept-Language': 'en-US,en;q=0.5',
               'User-Agent': get_user_angent()}
    url = r'https://search.bilibili.com/video?keyword=2d%E5%8A%A8%E6%BC%AB'
    save_path = r'download'
    cp = Craper(url, headers, save_path, cookies)
    cp.run()