'''
coding:utf-8
@Software: PyCharm
@Time: 2023/12/30 23:32
@Author: Aocf
@versionl: 3.
'''
import time
import numpy as np
import random
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
from moviepy.editor import VideoFileClip, VideoClip, concatenate_videoclips
# from moviepy.video import VideoClip
# VideoClip.DataVideoClip()
# CompositeVideoClip()

def video_audio_paras(play_info):
    """
    解析音频和视频网址
    :param play_info:
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

def _str_clean(s):
    r = ''
    for i in s:
        if i not in '\/:*?:"<>“|':
            r += i
    return r

def get_user_angent():
    user_agents = [
                'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; AcooBrowser; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
                'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; Acoo Browser; SLCC1; .NET CLR 2.0.50727; Media Center PC 5.0; .NET CLR 3.0.04506)',
                'Mozilla/4.0 (compatible; MSIE 7.0; AOL 9.5; AOLBuild 4337.35; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
                'Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)',
                'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 2.0.50727; Media Center PC 6.0)',
                'Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 1.0.3705; .NET CLR 1.1.4322)',
                'Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 5.2; .NET CLR 1.1.4322; .NET CLR 2.0.50727; InfoPath.2; .NET CLR 3.0.04506.30)',
                'Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN) AppleWebKit/523.15 (KHTML, like Gecko, Safari/419.3) Arora/0.3 (Change: 287 c9dfb30)',
                'Mozilla/5.0 (X11; U; Linux; en-US) AppleWebKit/527+ (KHTML, like Gecko, Safari/419.3) Arora/0.6',
                'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.2pre) Gecko/20070215 K-Ninja/2.1.1',
                'Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9) Gecko/20080705 Firefox/3.0 Kapiko/3.0',
                'Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Kazehakase/0.4.5',
                'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.8) Gecko Fedora/1.9.0.8-1.fc10 Kazehakase/0.5.6',
                'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/535.20 (KHTML, like Gecko) Chrome/19.0.1036.7 Safari/535.20',
                'Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; fr) Presto/2.9.168 Version/11.52',
                'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.11 TaoBrowser/2.0 Safari/536.11',
                'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71 Safari/537.1 LBBROWSER',
                'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; LBBROWSER)',
                'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E; LBBROWSER)',
                'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.84 Safari/535.11 LBBROWSER',
                'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; QQBrowser/7.0.3698.400)',
                'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)',
                'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SV1; QQDownload 732; .NET4.0C; .NET4.0E; 360SE)',
                'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)',
                'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)',
                'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.89 Safari/537.1',
                'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.89 Safari/537.1',
                'Mozilla/5.0 (iPad; U; CPU OS 4_2_1 like Mac OS X; zh-cn) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8C148 Safari/6533.18.5',
                'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:2.0b13pre) Gecko/20110307 Firefox/4.0b13pre',
                'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0',
                'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
                'Mozilla/5.0 (X11; U; Linux x86_64; zh-CN; rv:1.9.2.10) Gecko/20100922 Ubuntu/10.10 (maverick) Firefox/3.6.10',
                'MQQBrowser/26 Mozilla/5.0 (Linux; U; Android 2.3.7; zh-cn; MB200 Build/GRJ22; CyanogenMod-7) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1',
                'Mozilla/5.0 (Linux; Android 5.1.1; Nexus 6 Build/LYZ28E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.23 Mobile Safari/537.36',
                'Mozilla/5.0 (iPod; U; CPU iPhone OS 2_1 like Mac OS X; ja-jp) AppleWebKit/525.18.1 (KHTML, like Gecko) Version/3.1.1 Mobile/5F137 Safari/525.20',
                'Mozilla/5.0 (Linux;u;Android 4.2.2;zh-cn;) AppleWebKit/534.46 (KHTML,like Gecko) Version/5.1 Mobile Safari/10600.6.3 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)',
                'Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html）'
    ]
    agnet = random.choice(user_agents)
    return agnet

headers = {'Referer': 'https://www.bilibili.com/',
           'Accept': '/',
           'Accept-Language': 'en-US,en;q=0.5'
           }
headers['User-Agent'] = get_user_angent()
cookies = {}
with open('txt.txt',encoding='utf-8') as f:
    lines = f.readlines()
    for l in lines:
        s = l.split('\t')
        cookies[s[0]] = s[1]

url = 'https://search.bilibili.com/video?keyword=2d%E5%8A%A8%E6%BC%AB'
res = requests.get(url, headers=headers, cookies=cookies)




# 解析并下载相关视频以及对应的标题
if res.status_code == 200:
    soup = BeautifulSoup(res.text, 'html.parser')  # bts解析html元素 lxml
    links = []
    titles = []
    for link in soup.find_all('a', {'class': 'title'}):
        t = link.get('title')
        if t is not None:
           links.append(link.get('href'))
           titles.append(t)
    # 进行网址清洗
    if len(links) > 0:
        tls = [(t, x[2:]) for (t, x) in list(zip(titles, links)) if x[2:].startswith('www')]
        for jj, (t, l) in enumerate(tls):
            print(f'开始下载{t}')
            # 下载对应视频
            l = r'https://' + l
            time.sleep(1)
            res_video = requests.get(l, headers=headers, cookies=cookies)
            if res_video.status_code == 200:
                # 解析视频信息
                play_info = re.findall('<script>window.__playinfo__=(.*?)</script>', res_video.text)[0]
                play_info = json.loads(play_info)

                # 解析视频音频网址
                v_ls, a_ls = video_audio_paras(play_info)


                # 视频请求
                video_ls, audio_ls = [], []
                # debug
                print(v_ls)

                for v in v_ls:
                    video_ls.append(
                        requests.get(url=v, headers=headers, cookies=cookies))
                # 音频请求
                for a in a_ls:
                    audio_ls.append(
                        requests.get(url=a, headers=headers, cookies=cookies))
                # 请求状态判断
                connect_video = 1 if sum([x.status_code for x in video_ls]) == 200*len(video_ls) else 0
                connect_audio = 1 if sum([x.status_code for x in audio_ls]) == 200*len(audio_ls) else 0

                # 下载视频音频
                t = _str_clean(t)
                if connect_video:
                    # 多个视频链接采用保存后写入对比
                    # debug
                    if len(video_ls) >= 2:
                        decode_ = [av.open(io.BytesIO(x.content)) for x in video_ls]
                        decode_ = sorted(decode_, key=lambda x: x.size)  # 按size升序
                        # 使用字典进行过滤
                        decode_filter_ = {}
                        for d in decode_:
                            decode_filter_[d.duration] = d
                        decode_filter_video = list(decode_filter_.values())
                    else:
                        pass  # 直接转换
                    # 合并视频 concatenate_videoclips(decode_filter_)

                    # print('下载视频')
                    # for i, video in enumerate(video_ls):
                    #     with open(f'video{i}_{t}' + '.mp4', mode='wb') as f:
                    #         f.write(video.content)

                    # output = av.open('output.mp3', 'w')
                    # audio_streams = []
                    # for audio_file in ['audio1.mp3', 'audio2.mp3']:
                    #     container = av.open(audio_file)
                    #     stream = container.streams.get(audio=0)[0]
                    #     audio_streams.append(stream)
                    #     output.add_stream(copy=stream)
                    # for streams in zip(*audio_streams):
                    #     frames = [packet.decode()[0] for packet in container.demux(stream)]
                    #     for frame in frames:
                    #         output.mux(frame)
                    # output.close()

                if connect_audio:
                    if len(audio_ls) >= 2:
                        decode_ = [av.open(io.BytesIO(x.content)) for x in audio_ls]
                        decode_ = sorted(decode_, key=lambda x: x.size)  # 按size升序
                        # 使用字典进行过滤
                        decode_filter_ = {}
                        for d in decode_:
                            decode_filter_[d.duration] = d
                        decode_filter_audio = list(decode_filter_.values())
                    else:
                        pass  # 直接转换

                    # 合并音频


                # 合并音频和视频

                    # for i, audio in enumerate(audio_ls):
                    #     with open(f'audio{i}_{t}' + '.mp3', mode='wb') as f:
                    #         f.write(audio.content)

                # 合并视频和音频
                # output_path = 'merged_video.mp4'
                #
                # ffmpeg.input(video_path, audio=audio_path).output(output_path, format='mp4').run()


            else:
                print('下载失败', t)

            # TODO 日志保存 sql保存
