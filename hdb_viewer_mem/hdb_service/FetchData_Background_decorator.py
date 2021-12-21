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

max_workers = 2


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
        if g_queues is None:
            time.sleep(3)
        if g_queues is None or g_executor is None:
            return
        threadname = threading.currentThread().name
        threadname not in g_threadids and g_threadids.insert(0, threadname)
        # logger.debug(threadname + ' in ' + str(g_threadids))
        queue_index = g_threadids.index(threadname)
        if queue_index >= len(g_queues):
            # print("queue_index >= len(g_queues)")
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
            FetchData_Background_decorator.thread_pool.start(Task(self.sigProgressRate, self.sigDataReturn, fn, *args, **kargs))

    @classmethod
    def initContext(cls):
        if cls.thread_pool is None:
            cls.thread_pool = QThreadPool().globalInstance()
            cls.thread_pool.setExpiryTimeout(-1)
            cls.thread_pool.setMaxThreadCount(max_workers)
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

    try:
        global g_config_path
        # config_path = r"./config/system_config.ini"
        initmap = config_ini_key_value(keys=[],config_file=g_config_path)
        g_hdbclient = HdbClient(initmap['his_svr_addr'], initmap['his_srv_port'],
                                initmap['his_user'], initmap['his_pwd'],
                                initmap["file_path"])
        ret = g_hdbclient.open_client()
        if ret <= 0:
            logger.exception("open_client ERR:")
        g_remoteLink = HdbRemoteLinkItem(g_hdbclient, "memory/marketdata", "tick_20230807")
        g_remoteLink.open_link()

        # g_remoteLink.open_read_task(0,0,0,0,['SH.688009'], ["SecurityTick"])
        g_remoteLink.open_read_task(0,0,0,0,['SH.688009','SH.603976','SH.603977'], ["SecurityTick","SZStepTrade","SHStepTrade"])

        header = None
        while True:
            ret, cnt = g_remoteLink.get_data_items(1)
            time.sleep(0.1) #debug
            # logger.debug("snapCachRefresh get cnt:" + str(cnt))
            if 0 == cnt:
                logger.debug("snapCachRefresh sleep")
                time.sleep(1)  # wait 1 s
            for ind, item in enumerate(ret):
                logger.debug("Type_id:%s",item.type_id)
                if item.type_id == 0: # HMDTickType_SecurityTick 0 沪深股债基快照数据
                    if ind == 0 :
                        header = list(item.total_list_value_names)
                    v = item.total_list_value
                    'recvq' in kargs.keys() and kargs['recvq'].put(int(100*ind/len(ret)))# 发送进度信息
                    symbol = v[0]
                    with lock:
                        if symbol not in dic_snap.keys():
                            dic_snap[symbol] = pd.DataFrame(columns = header)
                        tmp = pd.DataFrame([item.total_list_value],columns=header,index=[symbol])
                        dic_snap[symbol] = dic_snap[symbol].append(tmp,ignore_index=True)
            # if item.type_id == 4:  # HMDTickType_SHStepTrade 4 上海逐笔成交数据
            #     if ind == 0:
            #         header = list(item.total_list_value_names)
            #     v = item.total_list_value
            #     'recvq' in kargs.keys() and kargs['recvq'].put(int(100 * ind / len(ret)))  # 发送进度信息
            #     symbol = v[0]
            #     with lock:
            #         if symbol not in dic_snap.keys():
            #             dic_snap[symbol] = pd.DataFrame(columns=header)
            #         tmp = pd.DataFrame([item.total_list_value], columns=header, index=[symbol])
            #         dic_snap[symbol] = dic_snap[symbol].append(tmp, ignore_index=True)
            # if item.type_id == 5:  # HMDTickType_SZStepTrade 5 深圳逐笔成交数据
            #     if ind == 0:
            #         header = list(item.total_list_value_names)
            #     v = item.total_list_value
            #     'recvq' in kargs.keys() and kargs['recvq'].put(int(100 * ind / len(ret)))  # 发送进度信息
            #     symbol = v[0]
            #     with lock:
            #         if symbol not in dic_snap.keys():
            #             dic_snap[symbol] = pd.DataFrame(columns=header)
            #         tmp = pd.DataFrame([item.total_list_value], columns=header, index=[symbol])
            #         dic_snap[symbol] = dic_snap[symbol].append(tmp, ignore_index=True)

        # g_remoteLink.close_read_task()
    except Exception as e:
        logger.exception("snapCachRefresh Exception:")
        logger.exception(e)
    return []

def refreshUIData(**kargs):
    logger.debug("call refreshUIData .. ")
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