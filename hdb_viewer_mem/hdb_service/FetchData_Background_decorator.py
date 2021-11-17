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

max_workers = 1

g_queues = None
g_threadids = []
# g_pool = None
g_executor = None
# g_hasInit = False
# mutex = QMutex()

g_hdbclient = None
g_remoteLink = None

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

#进程初始化 根据需要改动
def ppoolinitializer(n=0):
    try:
        global g_hdbclient
        global g_remoteLink

        config_path = r"./config/system_config.ini"
        initmap = config_ini_key_value(keys=[],config_file=config_path)
        g_hdbclient = HdbClient(initmap['his_svr_addr'], initmap['his_srv_port'],
                                initmap['his_user'], initmap['his_pwd'],
                                initmap["file_path"])
        ret = g_hdbclient.open_client()
        if ret <= 0:
            logger.exception("open_client ERR:")
        g_remoteLink = HdbRemoteLinkItem(g_hdbclient, "memory/marketdata", "tick_20230807")
        g_remoteLink.open_link()
    except Exception as e:
        logger.exception("ppoolinitializer ERR:")
        logger.exception(e)
        # print(traceback.format_exc())
    pass


class CreateExecutor(QRunnable):
    def __init__(self):
        super(CreateExecutor, self).__init__()

    def run(self):
        global g_executor
        if g_executor is not None:
            return
        global g_queues
        manager = Manager()
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
        global g_queues
        if g_queues is None:
            time.sleep(3)
        if g_queues is None or g_executor is None:
            return
        threadname = threading.currentThread().name
        threadname not in g_threadids and g_threadids.insert(0, threadname)
        # print(threadname, ' in ', g_threadids)
        logger.debug(threadname + ' in ' + str(g_threadids))
        queue_index = g_threadids.index(threadname)
        if queue_index >= len(g_queues):
            # print("queue_index >= len(g_queues)")
            return
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


    def __del__(self):
        logger.debug("FetchBackGroudD: call del .. ")
    #     self.close()



##  test  ##
def loadtest(x, **kargs):
    logger.debug("call loadNothing ...")
    'recvq' in kargs.keys() and kargs['recvq'].put(50)  # 发送进度信息
    return [1, 2, 3]

def load2( **kargs):
    global g_remoteLink
    logger.debug("call open_read_task .. ")

    ret = []
    try:
        ret = g_remoteLink.open_read_task(0,0,0,0,["SH.688009"], ["SecurityTick"])
        listv = []
        header = None
        while True:
            ret, cnt = g_remoteLink.get_data_items(30)
            logger.debug("while True cnt:" + str(cnt))
            if cnt <=0:
                break
            for ind, item in enumerate(ret):
                if ind == 0 and len(listv) == 0:
                    header = list(item.total_list_value_names)
                    listv.append(header)
                v = item.total_list_value
                listv.append(v)
                'recvq' in kargs.keys() and kargs['recvq'].put(int(100*ind/len(ret)))# 发送进度信息
        ret = listv

        g_remoteLink.close_read_task()
    except Exception as e:
        logger.exception("load2 Exception:")
        logger.exception(e)
        return []
    logger.debug("call close_read_task ... ")
    return ret


if __name__ == '__main__':
    app = QApplication([])

    win = QMainWindow()

    fetchData = FetchData_Background_decorator(loadtest, "AAA")
    fetchData.sigDataReturn.connect(lambda v: print('emit rev:', v))
    fetchData.sigProgressRate.connect(lambda v: print('PprogressRate emit rev:', v))

    win.show()
    app.exec_()