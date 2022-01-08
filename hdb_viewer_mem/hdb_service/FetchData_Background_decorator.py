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


# g_readTaskOpened = None
def snapCachRefresh( **kargs):
    # logger.debug("call snapCachRefresh .. ")
    if 'dic_security' not in kargs.keys() or 'lock' not in kargs.keys():  # 快照信息
        return []

    lock = kargs['lock']
    dic_snap = kargs['dic_security']
    dic_SZSetpTrade = kargs['dic_SZSetpTrade']
    dic_SHSetpTrade = kargs['dic_SHSetpTrade']

    try:
        global g_config_path
        # config_path = r"./config/system_config.ini"
        initmap = config_ini_key_value(keys=[],config_file=g_config_path)
        today = int(time.strftime("%Y%m%d"))
        curtime = 93000000
        tickname = "tick_" + time.strftime("%Y%m%d")
        file_path = "memory/marketdata/"+tickname

        today = 20200113  # test
        tickname = "tick_20230807"  # test
        file_path = "memory/marketdata/tick_20230807"  #test

        logger.debug("%s %s",today,tickname)
        symbols = initmap['symbols'].split(',')

        #先读取本地数据

        #再从服务器 读取剩余部分
        curtime_4w = time.time()
        while True:
            g_hdbclient = HdbClient(initmap['his_svr_addr'], initmap['his_srv_port'],
                                    initmap['his_user'], initmap['his_pwd'],
                                    file_path)
            ret = g_hdbclient.open_client()
            if ret <= 0:
                logger.exception("open_client ERR:")

            g_remoteLink = HdbRemoteLinkItem(g_hdbclient, "memory/marketdata", tickname)
            g_remoteLink.open_link()

            # g_remoteLink.open_read_task(0,0,0,0,['SH.688009','SH.603976','SH.603977'], ["SecurityTick","SZStepTrade","SHStepTrade"])
            g_remoteLink.open_read_task(today,curtime,today,150000000,symbols, ["SecurityTick","SZStepTrade","SHStepTrade"])
            logger.debug("open_read_task:%s",curtime)

            header = None

            dic_snap_tmp = {}
            dic_SHSetpTrade_tmp = {}
            dic_SZSetpTrade_tmp = {}
            header_sectick = None
            header_SZStepTrade = None
            header_SHStepTrade = None

            while True:
                try:
                    ret, cnt = g_remoteLink.get_data_items(1000)
                    # b = np.memmap('test.mymemmap',
                    #               dtype=np.dtype({'names': ['id', 'sin', 'cos'], 'formats': ['h', 'd', 'd']},
                    #                              align=False), mode='r+', shape=(1,), offset=4)
                    if 0 == cnt:
                        logger.debug("snapCachRefresh sleep")
                        time.sleep(1)  # wait 1 s
                    # for ind, item in enumerate(ret):
                    for ind in range(cnt):
                        item = ret[ind]
                        if item.type_id == 0: # HMDTickType_SecurityTick 0 沪深股债基快照数据
                            header_sectick = item.total_list_value_names
                            v = item.total_list_value
                            # 'recvq' in kargs.keys() and kargs['recvq'].put(int(100*ind/len(ret)))# 发送进度信息
                            symbol = v[0]
                            curtime = v[6]
                            with lock:
                                if symbol not in dic_snap_tmp.keys():
                                    dic_snap_tmp[symbol] = pd.DataFrame(columns = item.total_list_value_names)
                                dic_snap_tmp[symbol] = dic_snap_tmp[symbol].append(
                                    pd.Series(item.total_list_value,index=item.total_list_value_names),
                                    ignore_index=True)
                            # if symbol not in dic_snap_tmp.keys():
                            #     dic_snap_tmp[symbol] = []
                            # dic_snap_tmp[symbol].append(item.total_list_value)
                        if item.type_id == 4:  # HMDTickType_SHStepTrade 4 上海逐笔成交数据
                            header_SHStepTrade = item.total_list_value_names
                            v = item.total_list_value
                            symbol = v[0]
                            with lock:
                                if symbol not in dic_SHSetpTrade_tmp.keys():
                                    dic_SHSetpTrade_tmp[symbol] = pd.DataFrame(columns=item.total_list_value_names)
                                dic_SHSetpTrade_tmp[symbol] = dic_SHSetpTrade_tmp[symbol].append(
                                    pd.Series(item.total_list_value, index=item.total_list_value_names),
                                    ignore_index=True)
                            # if symbol not in dic_SHSetpTrade_tmp.keys():
                            #     dic_SHSetpTrade_tmp[symbol] = []
                            # dic_SHSetpTrade_tmp[symbol].append(item.total_list_value)
                        if item.type_id == 5:  # HMDTickType_SZStepTrade 5 深圳逐笔成交数据
                            header_SZStepTrade = item.total_list_value_names
                            v = item.total_list_value
                            symbol = v[0]
                            with lock:
                                if symbol not in dic_SZSetpTrade_tmp.keys():
                                    dic_SZSetpTrade_tmp[symbol] = pd.DataFrame(columns=item.total_list_value_names)
                                dic_SZSetpTrade_tmp[symbol] = dic_SZSetpTrade_tmp[symbol].append(
                                    pd.Series(item.total_list_value, index=item.total_list_value_names),
                                    ignore_index=True)
                            # if symbol not in dic_SZSetpTrade_tmp.keys():
                            #     dic_SZSetpTrade_tmp[symbol] = []
                            # dic_SZSetpTrade_tmp[symbol].append(item.total_list_value)
                    if time.time() - curtime_4w> 1 :
                        logger.debug("writeMem ... ")
                        with lock:
                            for symbol in dic_snap_tmp.keys():
                                if symbol not in dic_snap.keys():
                                    dic_snap[symbol] = pd.DataFrame(columns=dic_snap_tmp[symbol].columns)
                                dic_snap[symbol] = dic_snap[symbol].append(dic_snap_tmp[symbol],ignore_index=True)
                            for symbol in dic_SHSetpTrade_tmp.keys():
                                if symbol not in dic_SHSetpTrade.keys():
                                    dic_SHSetpTrade[symbol] = pd.DataFrame(columns=dic_SHSetpTrade_tmp[symbol].columns)
                                dic_SHSetpTrade[symbol] = dic_SHSetpTrade[symbol].append(dic_SHSetpTrade_tmp[symbol],ignore_index=True)
                            for symbol in dic_SZSetpTrade_tmp.keys():
                                if symbol not in dic_SZSetpTrade.keys():
                                    dic_SZSetpTrade[symbol] = pd.DataFrame(columns=dic_SZSetpTrade_tmp[symbol].columns)
                                dic_SZSetpTrade[symbol] = dic_SZSetpTrade[symbol].append(dic_SZSetpTrade_tmp[symbol],ignore_index=True)
                            dic_snap_tmp = {}
                            dic_SHSetpTrade_tmp = {}
                            dic_SZSetpTrade_tmp = {}

                            # for symbol in dic_snap_tmp.keys():
                            #     dic_snap[symbol] = pd.DataFrame(dic_snap_tmp[symbol],columns=header_sectick)
                            # for symbol in dic_SHSetpTrade_tmp.keys():
                            #     dic_SHSetpTrade[symbol] = pd.DataFrame(dic_SHSetpTrade_tmp[symbol], columns=header_SHStepTrade)
                            # for symbol in dic_SZSetpTrade_tmp.keys():
                            #     dic_SZSetpTrade[symbol] = pd.DataFrame(dic_SZSetpTrade_tmp[symbol], columns=header_SZStepTrade)


                        curtime_4w = time.time()

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

def snapCachRefresh_shareFile( **kargs):
    # logger.debug("call snapCachRefresh_shareFile .. ")
    try:
        global g_config_path
        # config_path = r"./config/system_config.ini"
        initmap = config_ini_key_value(keys=[],config_file=g_config_path)
        curdate = time.strftime("%Y%m%d")
        curtime = 93000000
        tickname = "tick_" + time.strftime("%Y%m%d")
        file_path = "memory/marketdata/" + tickname

        today = 20200113  # test
        tickname = "tick_20230807"  # test
        file_path = "memory/marketdata/tick_20230807"  #test

        symbols = initmap['symbols'].split(',')

        #先读取本地数据

        #再从服务器 读取剩余部分
        curtime_4w = time.time()
        while True:
            #create sharefile if not exist:
            # curdate = '20230807' #test
            if not os.path.exists(curdate):
                os.mkdir(curdate)
            for symbol in symbols:
                curpath = os.path.join(curdate,symbol+"_SecurityTick.data")
                if not os.path.exists(curpath):
                    open(curpath, mode='w+').close()
                curpath = os.path.join(curdate, symbol + "_SZStepTrade.data")
                if symbol[:2]=="SZ" and not os.path.exists(curpath):
                    open(curpath, mode='w+').close()
                curpath = os.path.join(curdate, symbol + "_SHStepTrade.data")
                if symbol[:2]=="SH" and not os.path.exists(curpath):
                    open(curpath,  mode='w+').close()


            g_hdbclient = HdbClient(initmap['his_svr_addr'], initmap['his_srv_port'],
                                    initmap['his_user'], initmap['his_pwd'],
                                    file_path)
            ret = g_hdbclient.open_client()
            if ret <= 0:
                logger.exception("open_client ERR:")

            g_remoteLink = HdbRemoteLinkItem(g_hdbclient, "memory/marketdata", tickname)
            g_remoteLink.open_link()

            g_remoteLink.open_read_task(today,curtime,today,150000000,symbols, ["SecurityTick","SZStepTrade","SHStepTrade"])
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

                            mm_header = np.memmap(filename, dtype=np.uint32, mode='r+', shape=(1,2), offset=0)
                            curpos,dtypelen = mm_header[0][0], mm_header[0][1]
                            if 0 == curpos:
                                typesbytes = pickle.dumps(item.total_dtypes.descr)
                                # p = pickle.loads(typesbytes)
                                mm_header[0][1] = len(typesbytes)
                                dtypelen = len(typesbytes)
                                mm = np.memmap(filename, dtype=np.byte, mode='r+', shape=(len(typesbytes),), offset=8)
                                for ind,v in enumerate(typesbytes):
                                    mm[ind]= v

                            mm = np.memmap(filename, dtype=item.total_dtypes, mode='r+', shape=(1,), offset=8+dtypelen+curpos*item.total_dtypes.itemsize)
                            mm[0] = item.total_array_data[0]
                            # mm.flush()

                            mm_header[0][0] = curpos + 1
                            # logger.debug("fp pos:%s  %s",curpos + 1,filename)

                        if item.type_id == 4:  # HMDTickType_SHStepTrade 4 上海逐笔成交数据
                            v = item.total_list_value
                            symbol = v[0]
                            filename = os.path.join(curdate, symbol + "_SHStepTrade.data")

                            mm_header = np.memmap(filename, dtype=np.uint32, mode='r+', shape=(1, 2), offset=0)
                            curpos, dtypelen = mm_header[0][0], mm_header[0][1]

                            if 0 == curpos:
                                typesbytes = pickle.dumps(item.total_dtypes.descr)
                                # p = pickle.loads(typesbytes)
                                mm_header[0][1] = len(typesbytes)
                                dtypelen = len(typesbytes)
                                mm = np.memmap(filename, dtype=np.byte, mode='r+', shape=(len(typesbytes),), offset=8)
                                for ind, v in enumerate(typesbytes):
                                    mm[ind] = v

                            mm = np.memmap(filename, dtype=item.total_dtypes, mode='r+', shape=(1,),
                                           offset=8 +dtypelen + curpos * item.total_dtypes.itemsize)
                            mm[0] = item.total_array_data[0]
                            # mm.flush()

                            mm_header[0][0] = curpos + 1

                        if item.type_id == 5:  # HMDTickType_SZStepTrade 5 深圳逐笔成交数据
                            v = item.total_list_value
                            symbol = v[0]
                            filename = os.path.join(curdate, symbol + "_SZStepTrade.data")

                            mm_header = np.memmap(filename, dtype=np.uint32, mode='r+', shape=(1, 2), offset=0)
                            curpos, dtypelen = mm_header[0][0], mm_header[0][1]

                            if 0 == curpos:
                                typesbytes = pickle.dumps(item.total_dtypes.descr)
                                # p = pickle.loads(typesbytes)
                                mm_header[0][1] = len(typesbytes)
                                dtypelen = len(typesbytes)
                                mm = np.memmap(filename, dtype=np.byte, mode='r+', shape=(len(typesbytes),), offset=8)
                                for ind, v in enumerate(typesbytes):
                                    mm[ind] = v

                            mm = np.memmap(filename, dtype=item.total_dtypes, mode='r+', shape=(1,),
                                           offset=8 +dtypelen + curpos * item.total_dtypes.itemsize)
                            mm[0] = item.total_array_data[0]
                            # mm.flush()

                            mm_header[0][0] = curpos + 1

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

def refreshUIData(**kargs):
    logger.debug("page1 call refreshUIData .. ")
    try:
        if 'lis' not in kargs.keys() or 'dic_security' not in kargs.keys() or 'lock' not in kargs.keys():  # 快照信息
            return []

        lock = kargs['lock']
        dic_snap = kargs['dic_security']
        data = kargs['lis']
        pdData = data[0]

        if len(dic_snap.keys()) == 0:
            return []

        for symbol in dic_snap.keys():
            if len(dic_snap[symbol])>0:
                v = dic_snap[symbol].iloc[-1]
                tmpdf = pd.DataFrame([v], index=[symbol])
                if symbol not in data[0].index.values:
                    data[0] = data[0].append(tmpdf)
                else:
                    # data[0].loc[symbol] = v #pd.Series(v)
                    pdData.update(tmpdf)
                    data[0] = pdData

    except Exception as e:
        logger.exception("refreshUIData Exception:")
        logger.exception(e)

    return []

# pdData = None
def refreshUIData_shareFile(**kargs):
    logger.debug("page1 call refreshUIData_shareFile .. ")
    # global pdData
    data = kargs['lis']
    pdData = data[0]
    try:
        #读取文件
        curdate = time.strftime("%Y%m%d")
        global g_config_path
        initmap = config_ini_key_value(keys=[],config_file=g_config_path)
        symbols = initmap['symbols'].split(',')

        symboll = []
        if pdData is not None and len(pdData) > 0:
            symboll = [str(v[:9], encoding="utf8") for v in pdData["symbol"].values]

        for symbol in symbols:
            filename = os.path.join(curdate, symbol + "_SecurityTick.data")
            if not os.path.exists(filename):
                continue

            mm = np.memmap(filename, dtype=np.uint32, mode='r', shape=(1, 2), offset=0)
            curpos, dtypelen = mm[0][0], mm[0][1]
            curpos -= 1
            if curpos>0:
                mm = np.memmap(filename, dtype=np.byte, mode='r', shape=(dtypelen,), offset=8)
                itemdtypes_descr = pickle.loads(mm)
                itemdtypes = np.dtype(itemdtypes_descr)
                mm = np.memmap(filename, dtype=itemdtypes, mode='r', shape=(1,1),
                               offset=8 + dtypelen + curpos * itemdtypes.itemsize)
                # while 0 == mm[0][0][0][0]:  #wait memdata write to file
                #     time.sleep(0.01)
                #     continue
                itemdf = pd.DataFrame([pd.Series(list(mm[0][0]), index=itemdtypes.names)], index=[symbol])

                # if pdData is None:
                #     pdData = pd.DataFrame(columns=itemdtypes.names)
                if symbol not in symboll:
                    pdData = pdData.append(itemdf)
                else:
                    pdData.update(itemdf)
    except Exception as e:
        logger.exception("refreshUIData Exception:")
        logger.exception(e)

    data[0] = pdData
    return []
    # return [pdData]

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