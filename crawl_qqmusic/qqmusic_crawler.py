# -*- coding:utf8 -*-
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from music_db import *
import requests
import time
import math
import os


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36',
}
session = requests.session()


def download(guid, songmid, cookies_dict, dir_path=os.path.dirname(os.path.abspath('__name__'))):
    """
    下载歌曲。请求ajax，获取purl，再将域名与purl进行拼接生成下载url，请求下载url并保存至本地
    :param guid: 从cookies中的pgv_pvid键获取，反爬手段之一
    :param songmid: 歌曲的唯一标识
    :param cookies_dict: cookies用于保持登录状态
    :param dir_path: mp3存储路径
    :return: bool，标识下载成功或失败，用于判断后续是否进行数据入库操作
    """
    url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?hostUin=0&format=json&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq.json&needNewCode=0&data=%7B%22req%22%3A%7B%22module%22%3A%22CDN.SrfCdnDispatchServer%22%2C%22method%22%3A%22GetCdnDispatch%22%2C%22param%22%3A%7B%22guid%22%3A%22' + guid + '%22%2C%22calltype%22%3A0%2C%22userip%22%3A%22%22%7D%7D%2C%22req_0%22%3A%7B%22module%22%3A%22vkey.GetVkeyServer%22%2C%22method%22%3A%22CgiGetVkey%22%2C%22param%22%3A%7B%22guid%22%3A%22' + guid + '%22%2C%22songmid%22%3A%5B%22' + songmid + '%22%5D%2C%22songtype%22%3A%5B0%5D%2C%22uin%22%3A%22717241432%22%2C%22loginflag%22%3A1%2C%22platform%22%3A%2220%22%7D%7D%2C%22comm%22%3A%7B%22uin%22%3A717241432%2C%22format%22%3A%22json%22%2C%22ct%22%3A24%2C%22cv%22%3A0%7D%7D'
    response = session.get(url, headers=headers, cookies=cookies_dict)
    if response.status_code == 200:
        purl = response.json().get('req_0').get('data').get('midurlinfo')[0].get('purl')
        if purl:
            path = os.path.join(dir_path, songmid + '.m4a')
            if not os.path.exists(path):
                down_url = 'http://isure.stream.qqmusic.qq.com/' + purl
                # print(f'down_url: {down_url}')
                response = requests.get(down_url, headers=headers)
                with open(path, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                print(f'music has been already downloaded, path:{path}')
        else:
            # 部分歌曲由于其版权问题，qq音乐不支持下载，无purl参数
            print(f'No copyright. No param purl！')
    else:
        print(f'Requests ERROR, URL: {url}, CODE: {response.status_code}')
    return False


def get_cookies():
    """
    用selenium获取cookies，第二次请求qq音乐才会生成cookies
    :return: cookies字典
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(chrome_options=chrome_options)
    # 第一次访问qq音乐，不会生成cookies
    driver.get('https://y.qq.com')
    time.sleep(2)
    # 第二次访问qq音乐，取cookies
    url = 'https://y.qq.com/n/yqq/singer/001kZXmE3o8iAs.html'
    driver.get(url)
    time.sleep(2)
    cookies = driver.get_cookies()
    driver.quit()
    cookies_dict = {}
    for i in cookies:
        cookies_dict[i.get('name')] = i.get('value')
    print('cookies_dict: ', cookies_dict)
    return cookies_dict


def get_singer_songs(singermid, cookie_dict, dir_path):
    """
    请求指定歌手的歌曲列表页，获取指定歌手的全部歌单，并获取每首歌曲的唯一标识参数songmid
    :param singermid: 歌手的唯一标识参数
    :param cookie_dict: 用于反反爬虫的cookies字典
    :param dir_path: 存放当前歌手所有歌曲的根目录
    :return: None
    """
    # 获取当前歌手的拥有的歌曲总数total_song
    url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?data=%7B%22comm%22%3A%7B%22ct%22%3A24%2C%22cv%22%3A0%7D%2C%22singer%22%3A%7B%22method%22%3A%22get_singer_detail_info%22%2C%22param%22%3A%7B%22sort%22%3A5%2C%22singermid%22%3A%22'\
          + '{singermid}' + '%22%2C%22sin%22%3A' + '{song_page}' + '%2C%22num%22%3A60%7D%2C%22module%22%3A%22music.web_singer_info_svr%22%7D%7D'
    response = session.get(url.format(singermid=singermid, song_page=0), headers=headers)
    total_song = response.json().get('singer', {}).get('data', {}).get('total_song', 0)

    # 通过歌曲总数计算歌曲列表的页数(每页请求最多60条数据)
    song_page = math.ceil(float(total_song)/60)
    for i in range(song_page):
        # 获取歌曲列表页的歌曲信息列表songlist
        page_url = url.format(singermid=singermid, song_page=i*60)
        response = session.get(page_url, headers=headers)
        songlist = response.json().get('singer', {}).get('data', {}).get('songlist', [])

        if songlist:
            # 遍历歌曲信息列表，提取每首歌的信息及唯一标识参数songmid，用于入库及下载
            song_dict = {}
            for song in songlist:
                songmid = song.get('ksong', {}).get('mid', '') or song.get('mid', '') or song.get('file', {}).get(
                    'media_mid', '')

                # 切片是为了避免字符串太长无法入库
                song_dict['song_name'] = song.get('name', '')[:50]
                song_dict['song_album'] = song.get('album', {}).get('name', '')[:100]
                song_dict['song_interval'] = song.get('interval', 0)
                song_dict['song_songmid'] = songmid
                song_dict['song_singer'] = song.get('singer', [{}, ])[0].get('name', '')[:50]
                if songmid:
                    info = download(cookie_dict.get('pgv_pvid', ''), songmid, cookie_dict, dir_path)
                    if info:
                        print('>'*20, 'down OK and inserting to mysql')
                        insert_data(song_dict)
                else:
                    print(f'no songmid, songlist{songlist},\npage_url: {page_url}')
        else:
            print(f'Song List is empty in URL: {page_url}')


def get_singermid(page_list, cookie_dict, index):
    """
    请求歌手列表页，获取歌手的唯一标识参数singermid，传给歌曲提取函数get_singer_songs
    :param page_list: 线程负责提取的歌手列表页页数范围，其中的元素为：当前歌手列表页的页数参数，请求url的参数之一
    :param cookie_dict: 用于反反爬虫的cookies字典
    :param index: 代表歌手首字母信息的参数，请求url的参数之一
    :return: None
    """
    url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?data=%7B%22comm%22%3A%7B%22ct%22%3A24%2C%22cv%22%3A0%7D%2C%22singerList%22%3A%7B%22module%22%3A%22Music.SingerListServer%22%2C%22method%22%3A%22get_singer_list%22%2C%22param%22%3A%7B%22area%22%3A-100%2C%22sex%22%3A-100%2C%22genre%22%3A-100%2C%22index%22%3A{index}%2C%22sin%22%3A{sin}%2C%22cur_page%22%3A{cur_page}%7D%7D%7D'
    for cur_page in page_list:
        try:
            # 构造请求singer_url，获取歌手信息列表singer_list
            singer_url = url.format(index=index, sin=(cur_page-1)*80, cur_page=cur_page)
            response = session.get(singer_url)
            singer_list = response.json().get('singerList', {}).get('data', {}).get('singerlist', [])

            for singer in singer_list:
                # 获取歌手姓名用于构建歌曲目录、唯一标识的singermid用于获取歌手歌曲
                singer_name = singer.get('singer_name', '')
                singermid = singer.get('singer_mid', '')
                # 获取当前程序的文件夹路径
                dir_path = os.path.dirname(os.path.abspath('__name__'))
                # 若当前歌手歌曲文件夹不存在则新建，并以歌手姓名命名
                if not os.path.exists(os.path.join(dir_path, 'qmusic', singer_name)):
                    os.mkdir(os.path.join(dir_path, 'qmusic', singer_name))

                # print(f'singer: {singer_name}, singer_url: {singer_url}')
                get_singer_songs(singermid, cookie_dict, os.path.join(dir_path, 'qmusic', singer_name))
        except Exception as e:
            print('ERROR: ', e)


def get_all_singer(cookie_dict, index):
    """
    获取按照26个单词字母以及#分类的所有歌手列表页，每个分类下的所有歌手列表页都用多线程进行访问
    :param cookie_dict: 用于反反爬虫的cookies字典
    :param index: 歌手姓名首字母
    :return: None
    """
    # 获取某字母开头的歌手列表总页数:singer_pages
    url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?data=%7B%22comm%22%3A%7B%22ct%22%3A24%2C%22cv%22%3A0%7D%2C%22singerList%22%3A%7B%22module%22%3A%22Music.SingerListServer%22%2C%22method%22%3A%22get_singer_list%22%2C%22param%22%3A%7B%22area%22%3A-100%2C%22sex%22%3A-100%2C%22genre%22%3A-100%2C%22index%22%3A{index}%2C%22sin%22%3A{sin}%2C%22cur_page%22%3A{cur_page}%7D%7D%7D'
    page_data = session.get(url.format(index=index, sin=0, cur_page=1), headers=headers).json()
    total_singer = page_data.get('singerList', {}).get('data', {}).get('total', 0)
    singer_pages = math.ceil(float(total_singer) / 80.0)
    page_list = [x for x in range(1, singer_pages+1)]

    # 构造多线程逻辑部分
    thread_num = 10
    # 计算每条线程执行的page平均数
    each_thread_pages = singer_pages // thread_num
    more_thread_nums = singer_pages % thread_num
    threads = ThreadPoolExecutor(max_workers=thread_num)
    for i in range(more_thread_nums):
        start = i * (each_thread_pages + 1)
        end = start + each_thread_pages + 1
        threads.submit(get_singermid, page_list[start:end], cookie_dict, index)
    for i in range(thread_num - more_thread_nums):
        start = i * each_thread_pages
        end = start + each_thread_pages
        threads.submit(get_singermid, page_list[start:end], cookie_dict, index)


def my_process():
    """
    按歌手姓名首字母分类进行多进程访问，按分类A~Z及其余字符#共27个进程数。
    :return:
    """
    with ProcessPoolExecutor(max_workers=27) as process:
        cookie_dict = get_cookies()
        if cookie_dict:
            for index in range(1, 28):
                process.submit(get_all_singer, cookie_dict, index)
        else:
            print(f'cookies false: {cookie_dict}')


if __name__ == '__main__':
    import datetime
    t1 = datetime.datetime.now()
    try:
        my_process()
    finally:
        t2 = datetime.datetime.now()
        print('花费时间：', t2-t1)



