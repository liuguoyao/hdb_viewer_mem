import os
from datetime import datetime
from hdb_viewer.hdb_link.hdb_remote_link_item import *
from hdb_py.hdb_client import *
import copy
'''
远程连接整理，方便切换模式
'''


class HdbRemoteLinkManange:
    def __init__(self):
        self.my_client = None
        self.client_id = 0
        self.my_folder = None
        self.client_status = False
        self.hdb_link_dict = dict()
        self.using_client_num = 0
        self.hasMemoryFile = False
        self.hasHkMemoryFile = False
        self.hasBarMemoryFile = False


    def open_client(self, host, port, username, pwd):
        '''
        初始化client，open_client
        :param host:
        :param port:
        :param username:
        :param pwd:
        :return:
        '''
        if self.using_client_num == 0 and self.client_status is False:
            self.my_client = HdbClient(host, port, username, pwd)
            self.client_id = self.my_client.open_client()
            self.client_status = True
        self.using_client_num = self.using_client_num + 1

    '''
      关闭client，确保client无使用的情况下关闭
    '''
    def close_client(self):
        self.using_client_num = self.using_client_num - 1
        if self.using_client_num == 0 and self.client_status is True:
            self.client_status = False
            self.clean_all_remote_link()
            self.my_client.close_client()
        elif self.using_client_num < 0:
            self.using_client_num = 0

    def get_folder_list(self, folder):
        self.my_folder = self.my_client.get_folder_files(folder)
        return self.my_folder

    def del_link(self, parent_dir, file_name):
        com_file_path = parent_dir + "_" + file_name
        self.get_link(parent_dir, file_name).close_link()
        if self.get_link(parent_dir, file_name).using_num <= 0:
            self.hdb_link_dict.pop(com_file_path)

    '''
    新建远程连接
    '''
    def creat_link(self, parent_dir, file_name):
        # 当需要打开内存缓存数据文件时，文件路径需加上前缀memory/ .  memory/parent_dir
        dir_path = parent_dir
        com_file_path = parent_dir + "_" + file_name
        today = datetime.now().strftime("%Y%m%d")
        if today == file_name[-8:]:
            if self.hasHkMemoryFile and 'hk' == file_name[:2]:
                file_name = 'hk_tick_' + today
                dir_path = 'memory' + r"/" + parent_dir
            elif self.hasBarMemoryFile and 'min' == file_name[:3]:
                file_name = 'min_bar_' + today
                dir_path = 'memory' + r"/" + parent_dir
            elif self.hasMemoryFile and 'tick' == file_name[:4]:
                file_name = 'tick_' + today
                dir_path = 'memory' + r"/" + parent_dir
            else:
                if self.get_link(parent_dir, file_name):
                    self.del_link(parent_dir, file_name)

        if self.get_link(parent_dir, file_name) is None:
            new_hdb_link = HdbRemoteLinkItem(self.my_client, dir_path, file_name)
            self.hdb_link_dict[com_file_path] = new_hdb_link
            ret = new_hdb_link.open_link()
        else:
            ret = self.get_link(parent_dir, file_name).open_link()
            new_hdb_link = self.get_link(parent_dir, file_name)
        if ret <= 0:
            return None
        return new_hdb_link

    '''
    清理所有远程连接,close所有file
    '''
    def clean_all_remote_link(self):
        for com_file_path in [item for item in self.hdb_link_dict]:
            work_link = self.hdb_link_dict.get(com_file_path)
            work_link.close_link()
            self.hdb_link_dict.pop(com_file_path)
        self.hdb_link_dict.clear()

    def get_link(self, parent_dir, file_name):
        com_file_path = parent_dir + "_" + file_name
        return self.hdb_link_dict.get(com_file_path)

    def show_link_list(self):
        link_list = list()
        for link_name in self.hdb_link_dict:
            link_list.append(link_name)
        return link_list

    def get_read_file(self, path, offset, buffer_size=1024):
        return self.my_client.read_file(path, offset, buffer_size)