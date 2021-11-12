'''
Author:Lgy
Date:2021/11/12
description:因pythonGIL限制,将取数动作放到python的进程中,同时利用QThread的信号槽功能
'''

from PyQt5.QtCore import pyqtSignal, QObject, QRunnable, QThreadPool
from PyQt5.QtWidgets import QApplication
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager
import time
import traceback
import sys
import threading

max_workers = 2

g_queues = None
g_threadids = []
# g_pool = None
g_executor = None
# g_hasInit = False
# mutex = QMutex()


def ppoolinitializer(n=0):
    # if sys.version <= "3.7.0":
    #     time.sleep(1)
    # if __name__ == '__mp_main__':
    #     config_path = r"../../config"
    # else:
    #     config_path = r"./config"
    # print('Process initializer', config_path)
    # sys_config_path = os.path.join(config_path, "system_config.ini")
    # for i in range(3):
    #     try:
    #         # system_config = config_ini_key_value([], sys_config_path)
    #         # StrategyManager.init_hft_bt(system_config, log_dir="./log/data_process")
    #         pass
    #         break
    #     except Exception as e:
    #         print('Process initializer:',e)
    #         time.sleep(1)
    # return n
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
            print('Process Exception:',r.exception())
            print(traceback.format_exc())
            self.sigDataReturn.emit([])
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
            print(cls.thread_pool.maxThreadCount())
            cls.thread_pool.start(CreateExecutor())

    @staticmethod
    def close():
        global g_executor
        if g_executor is not None:
            for pid, process in g_executor._processes.items():
                process.terminate()
                print('terminate:', pid, process)
        g_executor = None
        # global g_hasInit
        # g_hasInit = False



##  test  ##
def loadtest(x, **kargs):
    print("call loadNothing ...")
    print(x, kargs)
    'recvq' in kargs.keys() and kargs['recvq'].put(50)  # 发送进度信息
    return [1, 2, 3]
if __name__ == '__main__':
    app = QApplication([])

    fetchData_thread_decorator = FetchData_Background_decorator(loadtest, "AAA")
    fetchData_thread_decorator.sigDataReturn.connect(lambda v: print('emit rev:', v))
    fetchData_thread_decorator.sigProgressRate.connect(lambda v: print('PprogressRate emit rev:', v))

    app.exec_()