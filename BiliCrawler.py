'''
coding:utf-8
@Software: PyCharm
@Time: 2023/12/30 23:32
@Author: Aocf
@versionl: 3.
'''
import pandas as pd

from sql import SqlUtils
from logger import Logger
from utils import _del_temporary, _str_clean, get_user_angent
import requests
from bs4 import BeautifulSoup
import re
import json
import os
import av
import io
from moviepy.editor import VideoFileClip, VideoClip, concatenate_videoclips, AudioClip,AudioFileClip,concatenate_audioclips

# TODO 一个文件夹存储100个视频 提高检索效率
# TODO 增加异常捕捉机制 -- 50%
# TODO 音乐和视频合并分辨率下降问题 -- 暂时无法解决
# TODO 增加多线程提效 -- v2.0
# TODO 增加视频信息写入检索数据库 100%


class PerVideoCrawler(object):
    """
    从播放链接爬取视频
    """
    def __init__(self, url, headers, save_path, cookies=None, log_path='./log'):
        self.url, self.headers, self.cookies = url, headers, cookies
        self.save_path = save_path
        self.concate_path = r'./concate'
        if not os.path.exists(self.concate_path):
            os.mkdir(self.concate_path)
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)

        # log工具
        self.log = Logger(path=log_path)

    def _make_path(self, filename, mode='concat'):
        """
        生成视频存储路径、暂存路径
        :param filename:
        :param mode:
        :return:
        """
        if mode == 'concat':
            return os.path.join(self.concate_path, filename)
        elif mode == 'save':
            return os.path.join(self.save_path, filename)
        else:
            return

    def _video_audio_links_parse(self, play_info: dict):
        """
        解析音频和视频网址
        :param play_info:视频属性解析字典
        :return: 视频网址和音频网址
        """
        quality_code = [112, 80, 64, 32, 16]  # 清晰度代码
        videos = play_info['data']['dash']['video']
        audios = play_info['data']['dash']['audio']

        """
        获取清晰度最高的链接
        """
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

    def _concate(self, file_path):
        """
        依次合并多个视频或音频
        :param file_path:视频或音频pathList
        :return:
        """
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
            fv = self._concate(video_path)
            fa = self._concate(audio_path)
            fv = fv.set_audio(fa)
        else:
            fv = self._concate(video_path)
        save_path = f"{self._make_path(title + '.mp4', 'save')}"
        fv.write_videofile(save_path,
                           codec='libx264',
                           )
        res = {'save_path': save_path, 'fps': fv.fps,
               'duration': fv.duration, 'resolution': str(fv.size),
               'storage': os.path.getsize(save_path)/1024}
        # 清空临时缓存
        fv.close()
        _del_temporary(video_path)
        _del_temporary(audio_path)
        return res

    def _dowload(self, v_ls, a_ls, title):
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
                多段视频: 一个清晰度存在多个链接或存在多段拼接
                """
                decode_ = [(i, av.open(io.BytesIO(x.content)))
                           for i, x in enumerate(video_ls)]
                decode_ = sorted(decode_, key=lambda x: x[1].size)  # 按size升序

                # 使用字典进行过滤，保留唯一序号
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
            print('视频下载失败，无法获取视频视频链接')

        if connect_audio and connect_audio:
            if len(audio_ls) >= 2:
                """
                多段音频:
                一个清晰度下或存在多段拼接
                """
                decode_ = [(i, av.open(io.BytesIO(x.content)))
                           for i, x in enumerate(audio_ls)]
                decode_ = sorted(decode_, key=lambda x: x[1].size)
                idx_select = {}
                for d in decode_:
                    idx_select[d[1].duration] = d[0]
                audio_ls = [audio_ls[x] for x in idx_select.values()]
            for i, audio in enumerate(audio_ls):
                p = self._make_path(f'{i}audio_{title}.mp3')
                audio_path.append(p)
                with open(p, mode='wb') as f:
                    f.write(audio.content)
                f.close()
        else:
            print('音频下载失败')

        del v_ls, a_ls, video_ls, audio_ls

        # 拼接视频和音频
        self.info.update(self._concate_all(video_path, audio_path, title))

    def get_video(self, play_url, title):
        """
        获得每一个视频并保存
        :param video_url: 点击标题进入的视频播放链接，注: 不是视频下载的链接
        :return:
        """
        res_video = requests.get(play_url,
                                 headers=self.headers,
                                 cookies=self.cookies)
        if res_video.status_code == 200:
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

    def loader(self, play_url, title):
        """
        获得每一个视频并保存
        :param video_url: 点击标题进入的视频播放链接，注: 不是视频下载的链接
        :return:
        """
        self.info = {}
        try:
            self.get_video(play_url, title)
            sucess = 1
        except Exception as e:
            print(e)
            sucess = 0
        finally:
            pass
        self.info['states'] = sucess
        return self.info


class DownloadFromWebpage(PerVideoCrawler):
    """
    从视频搜索页面下载视频
    """
    def __init__(self, url, headers, save_path, cookies=None, log_path='./log'):
        super(DownloadFromWebpage, self).__init__(url, headers, save_path, cookies, log_path)
        self.url, self.headers, self.cookies = url, headers, cookies
        self.web_parse()
        self.agent_iteration = 20

        # sql工具
        self.sql_config = {"host": "localhost",
                           "port": 3306,
                           "database": "aocf",
                           "charset": "utf8",
                           "user": "root",
                           "passwd": "w0haizai"}
        self.sql_tablename = 'bilicrawl'
        self.sqltool = SqlUtils(self.sql_config)

    def web_parse(self):
        """
        获取页面所有视频的标题和网址
        :return: [(tittle, link), (tittle, link), ...]
        """
        self.webpage = requests.get(self.url, headers=self.headers, cookies=self.cookies)
        if self.webpage.status_code == 200:
            soup = BeautifulSoup(self.webpage.text, 'lxml')
            titles, links = [], []
            for link in soup.find_all('a', {'class': 'title'}):
                t = link.get('title')
                if t is not None:
                    t = _str_clean(t)
                    links.append(link.get('href'))
                    titles.append(t)
            assert len(links) > 0, self.log(f'无法从网址解析出视频链接, url={self.url}')

            tls = list(zip(titles, links))
            self.tls = [(t, r'https://' + x[2:]) for (t, x) in tls if x[2:].startswith('www')]  # //www.***
            self.log(f'解析网页{self.url}')
            self.log(f'获取网址信息: 链接数{len(self.tls)} {str(self.tls)}')
        else:
            info = f'网页请求失败， 失败码{self.webpage.status_code}'
            self.log(info)
            raise ValueError(info)

    def _info_parse(self, info: dict):
        """
        解析中间过程信息字典
        :param info:
        :return:
        """
        return pd.DataFrame({'title': info.get('title', ''),
                             'url': info.get('url', ''),
                             'states': info.get('states', 0),
                             'save_path': info.get('save_path', ''),
                             'storage': info.get('storage', 0),
                             'fps': info.get('fps', 0),
                             'resolution': info.get('resolution', 0),
                             'duration': info.get('duration', 0)
                             }, index=[0])

    def run(self):
        # TODO 多线程下载 多进程下载
        df_sql = pd.DataFrame()
        creat_tabl = 1
        for i, (title, play_url) in enumerate(self.tls):
            info = {'title': title, 'url': play_url}
            if (i + 1) // self.agent_iteration == 0:
                self.headers['User-Agent'] = get_user_angent()  # 更新代理
            # 下载
            self.log('---'*5 + f'开始下载视频【{title}】' + '---'*5)
            self.log(f'播放链接【{play_url}】')
            info.update(self.loader(play_url, title))
            # 解析中间信息上传sql
            df_sql = pd.concat([df_sql, self._info_parse(info)], axis=0)
            if creat_tabl:
                self.sqltool.creat_table(table_name=self.sql_tablename,
                                         df=df_sql,
                                         text_col=['title', 'url', 'save_path'],
                                         fixed_drop=True)
                creat_tabl = 0
            if df_sql.shape[0] > 100:
                self.sqltool.put_data(df_sql, table_name=self.sql_tablename)
                df_sql = pd.DataFrame()
        self.sqltool.put_data(df_sql, table_name=self.sql_tablename)
        del self.sqltool


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
    cp = DownloadFromWebpage(url, headers, save_path, cookies)
    cp.run()