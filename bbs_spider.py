#coding:utf-8
import requests
from bs4 import BeautifulSoup
import getpass
import os
import time
import re
import subprocess
import logging
import datetime
import threading
import shutil

class bbs_spider():
    site = 'http://bbs.seu.edu.cn'
    def __init__(self, user, pswd):
        self.__user = user
        self.__pswd = pswd
        self.__site = 'http://bbs.seu.edu.cn'
        self.__urls = {
			'login': bbs_spider.site + '/bbslogin.php',
			'logout': bbs_spider.site + '/bbslogout.php',
			'torrent': bbs_spider.site + '/pt/torrents.php',
			'download': bbs_spider.site + '/pt/download.php'
			}
        self.__session = requests.Session()
        self.__page = ''

    def login(self):
        data = {'id': self.__user,
			 'passwd': self.__pswd,
			 'webtype': 'www2'}
        try:
            res = self.__session.post(self.__urls['login'], data)
            if res.status_code != 200:
                return False
            text = res.text
            if text.find('confirm') > 0:
                data.pop('webtype')
                data['kick_multi'] = '1'
                res = self.__session.post(self.__urls['login'], data)
                if res.status_code != 200:
                    return False
            return True
        except requests.ConnectionError:
            return False
        except requests.RequestException:
            return False

    def logout(self):
        try:
            self.__session.get(self.__urls['logout'])
            self.__session.close()
            return True
        except requests.ConnectionError:
            return False
        except requests.RequestException:
            return False

    def __get_page(self):
        try:
            res = self.__session.get(self.__urls['torrent'])
            if res.status_code != 200:
                return False
            self.__page = res.text
            return True
        except requests.ConnectionError:
            return False
        except requests.RequestException:
            return False

    def get_free_torrent_id(self):
        self.__get_page()
        ids = []
        id_rex = r'id=(.*?)&'
        soup = BeautifulSoup(self.__page, 'html.parser')
        torrent_tables = soup.find_all('table', 'torrentname')
        for item in torrent_tables:
            torrent_table = str(item)
            if torrent_table.find('pro_free') > 0:
                id = re.findall(id_rex, torrent_table, re.S)
                ids.append(id[0])
        return ids

    def download_torrent(self, id=''):
        url = self.__urls['download'] + '?id=' + id
        res = self.__session.get(url)
        if res.status_code != 200:
            return False
        data = res.content
        try:
            with open(id+'.torrent', 'wb') as torrent:
                torrent.write(data)
                return True
        except IOError:
            return False


def get_ids_form_file(filename=''):
    with open(filename, 'r') as f:
        text = f.read()
    return text.split()


def add_id_to_file(filename='', id=''):
    with open(filename, 'a+') as f:
      f.write(id+' ')


def query_id(id_file='', id=''):
    if id in get_ids_form_file(id_file):
        return True
    else:
        return False


def get_login_info():
    user = input('Username:')
    pswd = getpass.getpass('Password(password will not show):')
    return (user, pswd)


def delete_files(dir='', days=3):
    try:
        flist = os.listdir(dir)
        ct = int(time.time())
        for f in flist:
            fname = os.path.join(dir, f)
            if os.path.isfile(fname):
                ft = int(os.path.getmtime(fname))
                dt = ct-ft
                if dt > days*24*3600:
                    try:
                        os.remove(fname)
                        logging.info('Remove file: '+fname+' success!')
                    except:
                        logging.info('Remove file: '+fname+' error!')
            else:
                delete_files(fname, days)
    except:
        pass


def check_network(url=''):
    cmd = 'ping ' + url
    code = os.system(cmd)
    return not bool(code)


def run(userinfo, period=5):
    id_file = 'ids'
    file_dir = 'files/'
    save_day = 3
    logging.info('*********** bbs spider ***********')
    logging.info(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    if not check_network(bbs_spider.site[7:]):
        logging.info('Network error')
    else:
        logging.info('Begin to remove files......')
        delete_files(file_dir, save_day)
        logging.info('Begin to search free torrent......')
        spider = bbs_spider(userinfo[0], userinfo[1])
        if spider.login():
            ids = spider.get_free_torrent_id()
            for id in ids:
                if not query_id(id_file, id):
                    spider.download_torrent(id)
                    add_id_to_file(id_file, id)
                    print('New free torrent, id='+id)
            spider.logout()

    logging.info('Next search will begin at '+ str(period) + ' minutes later.')
    spider = threading.Timer(60*period, run, (userinfo, period))
    spider.start()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        filename='spider.log',
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    user_info = get_login_info()
    run(user_info)