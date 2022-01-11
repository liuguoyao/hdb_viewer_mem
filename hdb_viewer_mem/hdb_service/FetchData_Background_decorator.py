'''
Author:Lgy
Date:2021/11/12
description:因pythonGIL限制,将取数动作放到python的进程中,同时利用QThread的信号槽功能
'''

from PyQt5.QtCore import pyqtSignal, QObject, QRunnable, QThreadPool
from PyQt5.QtWidgets import QApplication,QMainWindow
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager
import time
import traceback
import sys
import threading
import pandas as pd
import pickle

# from hdb_viewer_mem.hdb_link.hdb_link_item import *
from hdb_viewer_mem.hdb_link.hdb_remote_link_item import  *
# from hdb_py.hdb_reader import *
# from hdb_py.hdb_writer import *
from hdb_py.hdb_client import *
from hdb_py.hdb_data_item import *
# from hdb_py.hdb_data_item import HDBDataItem

from hdb_viewer_mem.util.utility import *
from hdb_viewer_mem.util.logger import *
from hdb_viewer_mem.hdb_service.sharefile_memmap import *

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)

DEBUG = False

max_workers = 4
threadCount = 2


g_lock = None
g_queues = None

g_threadids = []
g_executor = None

# mutex = QMutex()

g_config_path = r"./config/system_config.ini"
if DEBUG:
    g_config_path = r"../../config/system_config.ini"

#进程初始化 根据需要改动
def ppoolinitializer(n=0):
    pass


class CreateExecutor(QRunnable):
    def __init__(self):
        super(CreateExecutor, self).__init__()

    def run(self):
        global g_executor
        if g_executor is not None:
            return
        global manager
        global g_lock
        global g_queues

        logger.debug("Manager() Init ...")
        manager = Manager()
        g_lock = manager.Lock()
        g_queues = []

        for i in range(max_workers):
            g_queues.append(manager.Queue())

        if sys.version > "3.7.0":
            # python 3.7
            g_executor = ProcessPoolExecutor(max_workers=max_workers, initializer=ppoolinitializer)
        else:
            # python 3.6
            g_executor = ProcessPoolExecutor(max_workers)

        g_executor.submit(self._fake)

    @staticmethod
    def _fake(self):
        pass


class Task(QRunnable):
    STOP = 101
    def __init__(self, sigProcessRate, sigDataReturn, fn, *args, **kargs):
        super(Task, self).__init__()
        self.sigProcessRate = sigProcessRate
        self.sigDataReturn = sigDataReturn
        self.fn = fn
        self.args = args
        self.kargs = kargs

    def run(self):
        global g_threadids
        global g_executor
        global g_lock
        global g_queues
        while g_queues is None:
            time.sleep(0.5)
            continue
        if g_queues is None or g_executor is None:
            return
        threadname = threading.currentThread().name
        threadname not in g_threadids and g_threadids.insert(0, threadname)
        # logger.debug(threadname + ' in ' + str(g_threadids))
        queue_index = g_threadids.index(threadname)
        if queue_index >= len(g_queues):
            print("queue_index >= len(g_queues)")
            return
        self.kargs['lock'] = g_lock
        self.kargs['recvq'] = g_queues[queue_index]

        r = g_executor.submit(self.fn, *self.args, **self.kargs)
        r.add_done_callback(self.cb)
        while True:
            v = self.kargs['recvq'].get()
            self.sigProcessRate.emit(v)
            if v >= self.STOP:
                break

    def cb(self, r):
        self.kargs['recvq'].put(self.STOP)
        if r.exception():
            global g_executor
            if g_executor is None:
                return
            # print('MY Process Exception:',r.exception())
            # print(traceback.format_exc())
            logger.exception('MY Process Exception:')
            logger.exception(r.exception())
            logger.exception(traceback.format_exc())
            self.sigDataReturn.emit([])

            #
            logger.exception("re create ProcessPoolExecutor ...")
            if sys.version > "3.7.0":
                # python 3.7
                g_executor = ProcessPoolExecutor(max_workers=max_workers, initializer=ppoolinitializer)
            else:
                # python 3.6
                g_executor = ProcessPoolExecutor(max_workers)
            g_executor.submit(CreateExecutor._fake)
            return
        self.sigDataReturn.emit(r.result())


class FetchData_Background_decorator(QObject):
    sigDataReturn = pyqtSignal(list)
    sigProgressRate = pyqtSignal(int)
    thread_pool = None

    def __init__(self, fn=None, *args, **kargs):
        super(FetchData_Background_decorator, self).__init__()
        self.initContext()
        if fn is not None:
            time.sleep(0.01)
            FetchData_Background_decorator.thread_pool.start(Task(self.sigProgressRate, self.sigDataReturn, fn, *args, **kargs))

    @classmethod
    def initContext(cls):
        if cls.thread_pool is None:
            cls.thread_pool = QThreadPool().globalInstance()
            cls.thread_pool.setExpiryTimeout(-1)
            cls.thread_pool.setMaxThreadCount(threadCount)
            # print(cls.thread_pool.maxThreadCount())
            logger.debug("thread_pool.maxThreadCount:"+str(cls.thread_pool.maxThreadCount()))
            cls.thread_pool.start(CreateExecutor())

    @staticmethod
    def close():
        global g_executor
        if g_executor is not None:
            for pid, process in g_executor._processes.items():
                process.terminate()
                # print('terminate:', pid, process)
                logger.debug('terminate:'+ str(pid) + str(process))
        g_executor = None


    # def __del__(self):
    #     logger.debug("FetchBackGroudD: call del .. ")
    # #     self.close()



##  test  ##
def loadtest(x, **kargs):
    logger.debug("call loadNothing ...")
    'recvq' in kargs.keys() and kargs['recvq'].put(50)  # 发送进度信息
    return [1, 2, 3]

def snapCachRefresh_shareFile( **kargs):
    # logger.debug("call snapCachRefresh_shareFile .. ")
    try:
        global g_config_path
        # config_path = r"./config/system_config.ini"
        initmap = config_ini_key_value(keys=[],config_file=g_config_path)
        curdate = time.strftime("%Y%m%d")
        today = int(curdate)
        curtime = 93000000
        tickname = "tick_" + curdate
        file_path = "memory/marketdata/" + tickname

        # today = 20200113  # test
        # tickname = "tick_20230807"  # test
        # file_path = "memory/marketdata/tick_20230807"  #test

        symbols = initmap['symbols'].split(',')

        # create sharefile if not exist:
        if not os.path.exists(curdate):
            os.mkdir(curdate)
        for symbol in symbols:
            curpath = os.path.join(curdate, symbol + "_SecurityTick.data")
            if not os.path.exists(curpath):
                open(curpath, mode='w+').close()
            curpath = os.path.join(curdate, symbol + "_SZStepTrade.data")
            if symbol[:2] == "SZ" and not os.path.exists(curpath):
                open(curpath, mode='w+').close()
            curpath = os.path.join(curdate, symbol + "_SHStepTrade.data")
            if symbol[:2] == "SH" and not os.path.exists(curpath):
                open(curpath, mode='w+').close()

        #再从服务器 读取剩余部分
        curtime_4w = time.time()
        while True:
            # 先读取本地数据 更新curtime offset
            maxpos = [93000000, 0]
            symbols_curpos = {}
            for symbol in symbols:
                filename = os.path.join(curdate, symbol + "_SecurityTick.data")
                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    itemdf = read_item_last(filename,symbol)
                    time_point_seq_no, itemtime = itemdf.time_point_seq_no.values[0], itemdf.time.values[0]
                    symbols_curpos[filename] = [symbol, "SecurityTick", itemtime, time_point_seq_no]
                    logger.debug("%s %s %s :", filename, time_point_seq_no, itemtime)  #
                    if itemtime > maxpos[0]:
                        maxpos[0] = itemtime
                        maxpos[1] = time_point_seq_no
                    elif time_point_seq_no > maxpos[1]:
                        maxpos[1] = time_point_seq_no
                else:
                    symbols_curpos[filename] = [symbol, "SecurityTick", 93000000, 0]

                if 'SH' == symbol[:2]:
                    filename = os.path.join(curdate, symbol + "_SHStepTrade.data")
                if 'SZ' == symbol[:2]:
                    filename = os.path.join(curdate, symbol + "_SZStepTrade.data")
                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    itemdf = read_item_last(filename, symbol)
                    if 'SH' == symbol[:2]:
                        time_point_seq_no, itemtime = itemdf.time_point_seq_no.values[0], itemdf.trade_time.values[0]
                        symbols_curpos[filename] = [symbol, "SHStepTrade", itemtime, time_point_seq_no]
                    if 'SZ' == symbol[:2]:
                        time_point_seq_no, itemtime = itemdf.time_point_seq_no.values[0], itemdf.transact_time.values[0]
                        symbols_curpos[filename] = [symbol, "SZStepTrade", itemtime, time_point_seq_no]
                    logger.debug("%s %s %s :", filename, time_point_seq_no, itemtime)  #
                    if itemtime > maxpos[0]:
                        maxpos[0] = itemtime
                        maxpos[1] = time_point_seq_no
                    elif time_point_seq_no > maxpos[1]:
                        maxpos[1] = time_point_seq_no
                else:
                    if 'SH' == symbol[:2]:
                        symbols_curpos[filename] = [symbol, "SHStepTrade", 93000000, 0]
                    if 'SZ' == symbol[:2]:
                        symbols_curpos[filename] = [symbol, "SZStepTrade", 93000000, 0]
            logger.debug("max:%s %s", maxpos[0], maxpos[1])

            # maxpos + 1s
            if 93000000 < maxpos[0]:
                ms = maxpos[0] % 1000
                st = time.strptime(time.strftime("%Y%m%d") + " " + str(int(maxpos[0] / 1000)), "%Y%m%d %H%M%S")
                t = time.mktime(st)
                maxpos[0] = int(time.strftime("%H%M%S", time.localtime(t + 1)))
                maxpos[0] = maxpos[0] * 1000  # +ms


            g_hdbclient = HdbClient(initmap['his_svr_addr'], initmap['his_srv_port'],
                                    initmap['his_user'], initmap['his_pwd'],
                                    file_path)
            ret = g_hdbclient.open_client()
            if ret <= 0:
                logger.exception("open_client ERR:")

            g_remoteLink = HdbRemoteLinkItem(g_hdbclient, "memory/marketdata", tickname)
            g_remoteLink.open_link()

            #load diff
            if 93000000 < maxpos[0]:
                for k in symbols_curpos.keys():
                    symbol, datatype, itemtime, time_point_seq_no = symbols_curpos[k]

                    g_remoteLink.open_read_task(today, itemtime, today, maxpos[0], [symbol], [datatype],
                                                offset=time_point_seq_no)
                    print(k,today, itemtime, today, maxpos[0], [datatype],time_point_seq_no)
                    while True:
                        ret, cnt = g_remoteLink.get_data_items(1)
                        logger.debug("%s readdiff %s", k, cnt)
                        if 0 == cnt:
                            break
                        for ind in range(cnt):
                            item = ret[ind]
                            if item.type_id == 0:  # HMDTickType_SecurityTick 0 沪深股债基快照数据
                                filename = os.path.join(curdate, symbol + "_SecurityTick.data")
                                df = pd.DataFrame([item.total_list_value],columns=list(item.total_list_value_names))
                                dftime,df_sq = df.time[0],df.time_point_seq_no[0]
                                if (itemtime==dftime and time_point_seq_no<df_sq) or (itemtime < dftime):
                                    print("Write",filename,dftime,df_sq)
                                    append_item(filename, item)
                                print(filename,dftime, df_sq)
                            if item.type_id == 4:  # HMDTickType_SHStepTrade 4 上海逐笔成交数据
                                filename = os.path.join(curdate, symbol + "_SHStepTrade.data")
                                df = pd.DataFrame([item.total_list_value], columns=list(item.total_list_value_names))
                                dftime, df_sq = df.trade_time[0],df.time_point_seq_no[0]
                                if (itemtime==dftime and time_point_seq_no<df_sq) or (itemtime < dftime):
                                    print("Write",filename,dftime,df_sq)
                                    append_item(filename, item)
                                print(filename,dftime, df_sq)
                            if item.type_id == 5:  # HMDTickType_SZStepTrade 5 深圳逐笔成交数据
                                filename = os.path.join(curdate, symbol + "_SZStepTrade.data")
                                df = pd.DataFrame([item.total_list_value], columns=list(item.total_list_value_names))
                                dftime, df_sq = df.transact_time[0],df.time_point_seq_no[0]
                                if (itemtime==dftime and time_point_seq_no<df_sq) or (itemtime < dftime):
                                    print("Write",filename,dftime,df_sq)
                                    append_item(filename, item)
                                print(filename,dftime, df_sq)
                    g_remoteLink.close_read_task()

            #load all
            g_remoteLink.open_read_task(today,maxpos[0],today,150000000,symbols, ["SecurityTick","SZStepTrade","SHStepTrade"])
            logger.debug("open_read_task:%s",curtime)

            while True:
                try:
                    ret, cnt = g_remoteLink.get_data_items(1000)
                    if 0 == cnt:
                        logger.debug("snapCachRefresh sleep")
                        time.sleep(1)  # wait 1 s

                    for ind in range(cnt):
                        item = ret[ind]
                        if item.type_id == 0: # HMDTickType_SecurityTick 0 沪深股债基快照数据
                            # 'recvq' in kargs.keys() and kargs['recvq'].put(int(100*ind/len(ret)))# 发送进度信息
                            v = item.total_list_value
                            symbol,curtime = v[0],v[6]
                            filename = os.path.join(curdate,symbol+"_SecurityTick.data")
                            append_item(filename,item)
                            # logger.debug("fp pos:%s  %s",curpos + 1,filename)

                        if item.type_id == 4:  # HMDTickType_SHStepTrade 4 上海逐笔成交数据
                            v = item.total_list_value
                            symbol = v[0]
                            filename = os.path.join(curdate, symbol + "_SHStepTrade.data")
                            append_item(filename, item)

                        if item.type_id == 5:  # HMDTickType_SZStepTrade 5 深圳逐笔成交数据
                            v = item.total_list_value
                            symbol = v[0]
                            filename = os.path.join(curdate, symbol + "_SZStepTrade.data")
                            append_item(filename,item)

                except Exception as e:
                    logger.exception("In While Exception:")
                    logger.exception(e)
                    time.sleep(2)
                    g_remoteLink.close_read_task()
                    # g_remoteLink.close_link()
                    g_hdbclient.close_client()
                    break
            # g_remoteLink.close_read_task()
    except Exception as e:
        logger.exception("snapCachRefresh Exception:")
        logger.exception(e)
    return []

def refresh_line_bar_shareFile(symbol, **kargs):
    curdate = time.strftime("%Y%m%d")
    filename = os.path.join(curdate, symbol + "_SecurityTick.data")
    mm_header = np.memmap(filename, dtype=np.uint32, mode='r', shape=(1, 2), offset=0)
    curpos, dtypelen = mm_header[0][0], mm_header[0][1]
    mm_dtype = np.memmap(filename, dtype=np.byte, mode='r', shape=(dtypelen,), offset=8)
    itemdtypes_descr = pickle.loads(mm_dtype)
    itemdtypes = np.dtype(itemdtypes_descr)
    mm_items = np.memmap(filename, dtype=itemdtypes, mode='r', shape=(curpos, ),offset=8 + dtypelen)
    data = pd.DataFrame([list(v) for v in mm_items], columns=itemdtypes.names)

    # data = data.reset_index(drop=True)
    pre_close = data['pre_close'][0] / 10000
    timelables = (data['time'].apply(lambda x: int(x / 1000))).tolist()

    x = list(range(data.shape[0]))
    y_volume = data['volume'] - data['volume'].shift(axis=0, fill_value=0)
    y_price = (data['match'] / 10000).tolist()

    #设置plot的x活动范围限制
    today = time.strftime("%Y%m%d")
    startstramp = time.mktime(time.strptime(today+" 093000","%Y%m%d %H%M%S"))
    currenttime = " {:0>6d}".format(timelables[-1])
    endstramp = time.mktime(time.strptime(today+currenttime,"%Y%m%d %H%M%S"))

    timeinterval = endstramp - startstramp
    timeinterval = timeinterval if timeinterval<=2*60*60 else timeinterval-1.5*60*60 #去除中午休市
    xMax = int(4*60*60/timeinterval*len(timelables))

    #should return
    # pre_close timelables x  y_volume  y_price xMax
    return [(pre_close, timelables, x,  y_volume,  y_price, xMax)]

if __name__ == '__main__':

    app = QApplication([])

    win = QMainWindow()

    fetchData = FetchData_Background_decorator(loadtest, "AAA")
    fetchData.sigDataReturn.connect(lambda v: print('emit rev:', v))
    fetchData.sigProgressRate.connect(lambda v: print('PprogressRate emit rev:', v))

    fetchData2 = FetchData_Background_decorator(loadtest, "AAA")
    fetchData2.sigDataReturn.connect(lambda v: print('emit rev:', v))
    fetchData2.sigProgressRate.connect(lambda v: print('PprogressRate emit rev:', v))

    fetchData3 = FetchData_Background_decorator(snapCachRefresh)
    fetchData3.sigDataReturn.connect(lambda v: print('emit rev:', v))
    fetchData3.sigProgressRate.connect(lambda v: print('PprogressRate emit rev:', v))

    win.show()
    app.exec_()