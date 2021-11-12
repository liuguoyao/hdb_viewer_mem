from hdb_py.hdb_client import *
'''

'''


class HdbRemoteLinkItem:
    def __init__(self, my_client, parent_dir, file_name):
        self.closeing = True
        self.filename = file_name
        self.parent_dir = parent_dir
        self.hdb_file_path = parent_dir + r"/" + file_name
        self.my_client = my_client
        self.using_num = 0
        self._code_info_type = None
        self._data_types = None
        self._read_task_id = None
        # self._file_id, self._code_info_type, self._data_types = self.my_client.open_file(self.hdb_file_path)
        self._file_id = None
        self._code_info_type = None
        self._data_types = None

    def __del__(self):
        if self.closeing is False:
            self.my_client.close_file(self._file_id)

    def open_link(self):
        if self.closeing is True and self.using_num >= 0:
            self._file_id, self._code_info_type, self._data_types = self.my_client.open_file(self.hdb_file_path)
            self.closeing = False
            self.using_num = self.using_num + 1
            return self._file_id
        return 404

    def close_link(self):
        if self.closeing is False and self.using_num <= 1:
            self.using_num = 0
            self.my_client.close_file(self._file_id)
            self.closeing = True
            self.using_num = self.using_num - 1

    def open_read_task(self, begin_date, begin_time, end_date, end_time,
                       symbol_list, type_list,offset=0):
        self._read_task_id = self.my_client.open_read_task(begin_date, begin_time, end_date, end_time,
                                                           symbol_list, type_list, offset, self._file_id)

    def close_read_task(self):
        self.my_client.close_read_task(self._read_task_id)

    '''
    获取指定代码信息
    '''

    def get_code_info(self, symbol):
        return self.my_client.read_code_info(symbol, self._file_id, self._code_info_type)

    '''
    获取code类型
    '''

    def get_code_info_type(self):
        return self._code_info_type

    '''
    获取 codelist 的所有code
    '''

    def get_code_infos(self, code_list_name):
        return self.my_client.read_code_table(code_list_name, False, self._file_id, self._code_info_type)

    '''
    获取所有的codelist
    '''

    def get_total_code_lists(self):
        return self.my_client.read_all_code_lists(self._file_id)

    '''
    获取datatype 的list
    '''

    def get_datatype_list(self):
        return self._data_types

    '''
    获取数据项
    '''

    def get_data_items(self, read_step):
        return self.my_client.read_data_items(read_step, None, self._read_task_id, self._data_types)
