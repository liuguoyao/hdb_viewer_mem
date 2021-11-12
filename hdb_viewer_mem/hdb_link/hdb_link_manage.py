import os

from hdb_viewer.hdb_link.hdb_link_item import *


class HdbLinkManange:
    def __init__(self):
        self.hdb_link_dict = dict()
        # self.hdb_remote_link_dict = dict()

    def creat_link(self, file_path, file_name):
        com_file_path = file_path + "_" + file_name
        if self.get_link(file_path, file_name) is None:
            new_hdb_link = HdbLinkItem(file_path, file_name)
            self.hdb_link_dict[com_file_path] = new_hdb_link
        else:
            self.get_link(file_path, file_name).open_link()

            new_hdb_link = self.get_link(file_path, file_name)
        return new_hdb_link

    def get_link(self, file_path, file_name):
        com_file_path = file_path + "_" + file_name
        return self.hdb_link_dict.get(com_file_path)

    def del_link(self, file_path, file_name):
        com_file_path = file_path + "_" + file_name
        if self.get_link(file_path, file_name) is None:
            return
        self.get_link(file_path, file_name).close_link()
        if self.get_link(file_path, file_name).using_num <= 0:
            self.hdb_link_dict.pop(com_file_path)

    def close_all_link(self):
        for com_file_path in [i for i in self.hdb_link_dict]:
            work_link = self.hdb_link_dict.get(com_file_path)
            work_link.close_link()
            self.hdb_link_dict.pop(com_file_path)
        self.hdb_link_dict.clear()

    def show_link_list(self):
        link_list = list()
        for link_name in self.hdb_link_dict:
            link_list.append(link_name)
        return link_list
