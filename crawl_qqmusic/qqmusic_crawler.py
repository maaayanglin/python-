# -*- coding:utf8 -*-
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import requests
import time
import math
import os

count_singer = 0
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
    :return: bool，标识下载成果或失败
    """
    # 获取下载歌曲所需参数的API链接
    url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?hostUin=0&format=json&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq.json&needNewCode=0&data=%7B%22req%22%3A%7B%22module%22%3A%22CDN.SrfCdnDispatchServer%22%2C%22method%22%3A%22GetCdnDispatch%22%2C%22param%22%3A%7B%22guid%22%3A%22' + guid + '%22%2C%22calltype%22%3A0%2C%22userip%22%3A%22%22%7D%7D%2C%22req_0%22%3A%7B%22module%22%3A%22vkey.GetVkeyServer%22%2C%22method%22%3A%22CgiGetVkey%22%2C%22param%22%3A%7B%22guid%22%3A%22' + guid + '%22%2C%22songmid%22%3A%5B%22' + songmid + '%22%5D%2C%22songtype%22%3A%5B0%5D%2C%22uin%22%3A%22717241432%22%2C%22loginflag%22%3A1%2C%22platform%22%3A%2220%22%7D%7D%2C%22comm%22%3A%7B%22uin%22%3A717241432%2C%22format%22%3A%22json%22%2C%22ct%22%3A24%2C%22cv%22%3A0%7D%7D'
    response = session.get(url, headers=headers, cookies=cookies_dict)
    if response.status_code == 200:
        # 从API中提取purl参数用于构造下载链接进行下载
        purl = response.json().get('req_0').get('data').get('midurlinfo')[0].get('purl')
        if purl:
            path = os.path.join(dir_path, songmid + '.m4a')
            if not os.path.exists(path):
                down_url = 'http://isure.stream.qqmusic.qq.com/' + purl
                print(f'down_url: {down_url}')
                header = headers
                header['Connection'] = 'close'
                response = requests.get(down_url, headers=header, cookies=cookies_dict)
                with open(path, 'wb') as f:
                    print(f'downing ... url: {down_url}')
                    f.write(response.content)
                    print('down FINISH !')
                print('False Finish')
            else:
                print(f'music has been already downloaded, path:{path}')
            return True
        else:
            # 部分歌曲由于其版权问题，qq音乐不支持下载，无purl参数
            print(f'No copyright. No param purl！URL: {url}')
    else:
        print(f'Requests ERROR, URL: {url}, CODE: {response.status_code}')
    return False


# 用selenium获取cookies
def get_cookies():
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
    return cookies_dict


# 获取歌手全部歌单
def get_singer_songs(singermid, cookie_dict, dir_path):
    global count_singer
    count_singer += 1
    # 获取歌手总歌曲数目total_song
    url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?data=%7B%22comm%22%3A%7B%22ct%22%3A24%2C%22cv%22%3A0%7D%2C%22singer%22%3A%7B%22method%22%3A%22get_singer_detail_info%22%2C%22param%22%3A%7B%22sort%22%3A5%2C%22singermid%22%3A%22'\
          + '{singermid}' + '%22%2C%22sin%22%3A' + '{song_page}' + '%2C%22num%22%3A60%7D%2C%22module%22%3A%22music.web_singer_info_svr%22%7D%7D'
    songs_message = session.get(url.format(singermid=singermid, song_page=0), headers=headers).json()
    total_song = songs_message.get('singer', {}).get('data', {}).get('total_song', 0)

    if total_song:
        # 每次调用API最多获取60条数据，计算需要调用API的次数即歌曲页数song_page
        song_page = math.ceil(float(total_song)/60.0)
        for i in range(song_page):
            # 获取每页的歌单
            page_url = url.format(singermid=singermid, song_page=i*60)
            songs_message = session.get(page_url, headers=headers).json()
            songlist = songs_message.get('singer', {}).get('data', {}).get('songlist', [])

            if songlist:
                for song in songlist:
                    # 下载歌曲
                    songmid = song.get('ksong', {}).get('mid', '') or song.get('mid', '') or song.get('file', {}).get('media_mid', '')
                    if songmid:
                        # print('go to download')
                        download(cookie_dict.get('pgv_pvid', ''), songmid, cookie_dict, dir_path)
                    else:
                        print(f'no songmid, songlist{songlist},\npage_url: {page_url}')
            else:
                print(f'Song List is empty in URL: {page_url}')
    else:
        print(f'No Songs with url: {url.format(singermid=singermid, song_page=0)}')


def get_singermid(page_list, cookie_dict, index):
    url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?data=%7B%22comm%22%3A%7B%22ct%22%3A24%2C%22cv%22%3A0%7D%2C%22singerList%22%3A%7B%22module%22%3A%22Music.SingerListServer%22%2C%22method%22%3A%22get_singer_list%22%2C%22param%22%3A%7B%22area%22%3A-100%2C%22sex%22%3A-100%2C%22genre%22%3A-100%2C%22index%22%3A{index}%2C%22sin%22%3A{sin}%2C%22cur_page%22%3A{cur_page}%7D%7D%7D'
    for cur_page in page_list:
        try:
            singer_url = url.format(index=index, sin=(cur_page-1)*80, cur_page=cur_page)
            singers_messages = session.get(singer_url).json()
            singermid_list = singers_messages.get('singerList', {}).get('data', {}).get('singerlist', [])
            if singermid_list:
                for singer in singermid_list:
                    # 获取歌手姓名、唯一标识的singermid
                    singer_name = singer.get('singer_name', '')
                    singermid = singer.get('singer_mid', '')
                    print('>' * 20, f'singer: {singer_name}, singer_mid: {singermid}', '<' * 20)

                    # 获取当前文件的文件夹路径
                    dir_path = os.path.dirname(os.path.abspath('__name__'))
                    # 若不存在则创建文件夹并以歌手姓名命名
                    if not os.path.exists(os.path.join(dir_path, 'qmusic', singer_name)):
                        # print('created direction !')
                        os.mkdir(os.path.join(dir_path, 'qmusic', singer_name))

                    get_singer_songs(singermid, cookie_dict, os.path.join(dir_path, 'qmusic', singer_name))
        except Exception as e:
            print('ERROR: ', e)


def get_all_singer(cookie_dict, index):
    # 获取某字母开头的歌手列表总页数:singer_pages
    url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?data=%7B%22comm%22%3A%7B%22ct%22%3A24%2C%22cv%22%3A0%7D%2C%22singerList%22%3A%7B%22module%22%3A%22Music.SingerListServer%22%2C%22method%22%3A%22get_singer_list%22%2C%22param%22%3A%7B%22area%22%3A-100%2C%22sex%22%3A-100%2C%22genre%22%3A-100%2C%22index%22%3A{index}%2C%22sin%22%3A{sin}%2C%22cur_page%22%3A{cur_page}%7D%7D%7D'
    page_data = session.get(url.format(index=index, sin=0, cur_page=1), headers=headers).json()
    total_singer = page_data.get('singerList', {}).get('data', {}).get('total', 0)
    singer_pages = math.ceil(float(total_singer) / 80.0)
    page_list = [x for x in range(1, singer_pages+1)]

    # 非多线程
    get_singermid(page_list, cookie_dict, index)

    # # 多线程版
    # thread_num = 10
    #
    # # 计算每条线程执行的page平均数
    # each_thread_pages = singer_pages // thread_num
    # more_thread_nums = singer_pages % thread_num
    # threads = ThreadPoolExecutor(max_workers=thread_num)
    #
    # for i in range(more_thread_nums):
    #     start = i * (each_thread_pages + 1)
    #     end = start + each_thread_pages + 1
    #     threads.submit(get_singermid, page_list[start:end], cookie_dict, index)
    # for i in range(thread_num - more_thread_nums):
    #     start = i * each_thread_pages
    #     end = start + each_thread_pages
    #     threads.submit(get_singermid, page_list[start:end], cookie_dict, index)


def my_process():
    # myprocess = ProcessPoolExecutor(max_workers=27)
    cookie_dict = get_cookies()
    if cookie_dict:
        for index in range(1, 28):
            get_all_singer(cookie_dict, index)
            # myprocess.submit(get_all_singer, cookie_dict, index)
    else:
        print(f'cookies false: {cookie_dict}')
    print('Process DOWN')


if __name__ == '__main__':
    import datetime
    t1 = datetime.datetime.now()
    try:
        print('con')
        my_process()
    finally:
        t2 = datetime.datetime.now()
        print('花费时间：', t2-t1)
        print(f'count_singer = {count_singer}')
