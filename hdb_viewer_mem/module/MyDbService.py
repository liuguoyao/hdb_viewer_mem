import time
from hdb_viewer_mem.hdb_link.hdb_link_item import *
from hdb_viewer_mem.hdb_link.hdb_remote_link_item import  *
from hdb_py.hdb_reader import *
from hdb_py.hdb_writer import *
from hdb_py.hdb_client import *
from hdb_py.hdb_data_item import *
from hdb_py.hdb_data_item import HDBDataItem


class DataService:
    def __init__(self, link_item):
        self.hdn_link_item = link_item
        self.dbinfo_dict = dict()

    '''
    return    codetotal_list, dbinfo_dict
    '''
    def get_filelist_all(self):
        codetotal_list = self.get_total_code_lists()
        datatype_list = self.get_datatype_list()
        typename_list = list()
        for datatype in datatype_list:
            typename_list.append(datatype.type)
        return codetotal_list, typename_list

    '''
    获取指定dataType的symbol 的list
    '''
    def get_code_by_datatype(self, datatype):
        codeinfo_list = self.get_code_infos("")
        datatype_list = self.get_datatype_list()
        cur_list = list()
        type_id = None
        for i, data_type in enumerate(datatype_list):
            if data_type.type == datatype:
                type_id = i
        if type_id is None:
            return cur_list
        for datatype_from_code in codeinfo_list:  # type: HDBCodeInfo
            num = datatype_from_code.type_items_nums[type_id]
            if num is not 0 :
                cur_list.append(datatype_from_code.symbol)
        return cur_list

    '''
    获取 dict[ datatypeName,  CodeNum ],  tatolDatatypeNum
    输入参数为默认 则获取全部
    '''
    def get_datatype_num_dict(self, cl_names=""):
        datatype_num_dict = dict()
        codeinfo_list = self.get_code_infos(cl_names)
        datatype_list = self.get_datatype_list()
        index = 0
        for datatype in datatype_list:                                     # type: HDBDataType
            code_num = 0
            for datatype_from_code in codeinfo_list:                       # type: HDBCodeInfo
                num = datatype_from_code.type_items_nums[index]
                if num is not 0:
                    code_num = code_num+1
            datatype_num_dict[str(datatype.type)] = code_num
            index = index + 1
        return datatype_num_dict, len(datatype_list)

    def get_load_data_item(self, symbol, data_type,begin_date=0, begin_time=0, end_date=0, end_time=0,offset=0):
        self.hdn_link_item.open_read_task(begin_date, begin_time, end_date, end_time, [symbol], [data_type],offset)
        rcv_items = []
        read_step = 10000
        while True:
            data_items, ret_count = self.get_data_items(read_step)
            if ret_count == 0:
                break
            rcv_items.extend(data_items)
        self.hdn_link_item.close_read_task()
        return rcv_items

    '''
    获得指定symbol的所有datatype的个数
    '''
    def get_one_datatype_num_dict(self, symbol):
        datatype_dict = dict()
        # cur_code_info = self.get_code_info(symbol) #接口貌似有问题，参数为indexTick下的symbol时返回一个空list，有时导致服务器奔溃
        cur_code_info = None
        for code_info in self.get_code_infos():
            if code_info.symbol == symbol:
                cur_code_info = code_info               # type: HDBCodeInfo
                break
        if cur_code_info is None:
            pass

        for i, typeName in enumerate(self.get_datatype_list()):
            datatype_dict[typeName.type] = cur_code_info.type_items_nums[i]
        return datatype_dict

    '''
    获得数据项
    '''
    def get_data_items(self, read_step):
        return self.hdn_link_item.get_data_items(read_step)

    '''
    获取指定代码信息
    '''
    def get_code_info(self, symbol):
        return self.hdn_link_item.get_code_info(symbol)

    '''
    获取文件大小
    '''
    def get_file_size(self):
        return self.hdn_link_item.get_file_size()

    '''
    获取code类型
    '''
    def get_code_info_type(self):
        return self.hdn_link_item.get_code_info_type()

    '''
    获取 codelist 的所有code
    '''
    def get_code_infos(self, code_list_name=""):
        return self.hdn_link_item.get_code_infos(code_list_name)

    '''
    获取所有的codelist
    '''
    def get_total_code_lists(self):
        return self.hdn_link_item.get_total_code_lists()

    '''
    获取datatype 的list
    '''
    def get_datatype_list(self):
        return self.hdn_link_item.get_datatype_list()

    def get_data_by_datatype(self):
        pass

if __name__ == '__main__':
    cli = HdbClient("127.0.0.1", "8750", "admin", "admin", "marketdata/tick_20210705")
    cli.open_client()

    rli = HdbRemoteLinkItem(cli, "marketdata", "tick_20210705")
    rli.open_link()
    ret = rli.get_total_code_lists()
    print("ret:",ret)

    ret = rli.get_code_info("SH.600674")
    print("ret:",ret)

    ret = rli.get_code_infos("")
    print("ret:", ret)

    # cli.close_client()
    print("end")




    # cli = HdbClient("127.0.0.1", "8750", "admin", "admin", "marketdata/tick_20210705")
    #
    # ret = cli.open_client()
    # print("open_client:", ret)
    #
    # # in_file, code_info_type, data_types = cli.open_file("memory/marketdata/tick_20210705")
    # in_file = cli.open_file()
    # print("open_file:", in_file)
    #
    # read_task = cli.open_read_task(0, 0, 0, 0, ["SH.600674"], ["SecurityTick"])
    # print("open_read_task:", read_task)
    #
    # read_step = 1000000
    # total_count = 0
    #
    # rcv_buffer = [HDBDataItem.__new__(HDBDataItem) for _ in range(read_step)]
    # while True:
    #     data, count = cli.read_data_items(read_step, rcv_buffer)
    #     if count == 0:
    #         break
    #     total_count += count
    #     print("read_data_items:", count, total_count)
    # cli.close_read_task()
    #
    # print(cli.last_error())
    #
    # cli.close_file()
    # cli.close_client()
