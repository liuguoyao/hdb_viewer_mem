from hdb_py.hdb_reader import *
'''
hbd   本地连接项
'''


class HdbLinkItem:
    def __init__(self, file_path, file_name):
        self.closeing = False
        self.using_num = 1
        self.filepath = file_path
        self.filename = file_name
        self.hdb_reader = HdbReader(self.filepath, self.filename)
        self.hdb_reader.open_db()
        self.hdb_reader.open_file()


    def __del__(self):
        if self.closeing is False:
            self.hdb_reader.close_file()
            self.hdb_reader.close_db()

    def open_link(self):
        self.using_num = self.using_num + 1
        if self.closeing is True and self.using_num >= 1:
            self.closeing = False
            self.hdb_reader.open_db()
            self.hdb_reader.open_file()

    def close_link(self):
        self.using_num = self.using_num - 1
        if self.closeing is False and self.using_num <= 0:
            self.closeing = True
            self.using_num = 0
            self.hdb_reader.close_file()
            self.hdb_reader.close_db()

    def open_read_task(self, begin_date, begin_time, end_date, end_time,
                       symbol_list, type_list,offset=0):
        self.hdb_reader.open_read_task(begin_date, begin_time, end_date, end_time,
                                       symbol_list, type_list,offset)

    def close_read_task(self):
        self.hdb_reader.close_read_task()

    '''
    获取指定代码信息
    '''
    def get_code_info(self, symbol):
        return self.hdb_reader.read_code_info(symbol)

    '''
    获取文件大小
    '''
    def get_file_size(self):
        file_size = os.path.getsize(self.filepath + "\\" + self.filename + r".hdat")
        file_size = float(file_size / (float(1024)*float(1024)))
        return file_size

    '''
    获取code类型
    '''
    def get_code_info_type(self):
        return self.hdb_reader.code_info_type

    '''
    获取 codelist 的所有code
    '''
    def get_code_infos(self, code_list_name=""):
        return self.hdb_reader.read_code_table(code_list_name)

    '''
    获取所有的codelist
    '''
    def get_total_code_lists(self):
        return self.hdb_reader.read_all_code_lists()

    '''
    获取datatype 的list
    '''
    def get_datatype_list(self):
        return self.hdb_reader.data_item_types

    '''
    获取数据项
    '''
    def get_data_items(self, read_step):
        return self.hdb_reader.read_data_items(read_step)
