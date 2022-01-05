import os
import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from traceback import format_exception
from hdb_viewer_mem.util.logger import *

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)
win = None

from hdb_viewer_mem.module.hdb_main import *
from multiprocessing import freeze_support


def exception_hook(exctype, value, traceback):
    sys.excepthook(exctype, value, traceback)
    # sys.exit(1)
    # text = "\n" + "".join(format_exception(exctype, value, traceback))
    # win.append_log(text)

if __name__ == '__main__':
    freeze_support()
    sys.excepthook = exception_hook
    try:
        # QtCore.QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        app = QApplication([])
        # app.setFont(QFont('Microsoft YaHer UI', fontSize))
        win = hdb_main_win()
        win.show()
        win.resize(1200,800)
        win.move(200,50)
        win.showMaximized()
        app.exec()
    except Exception as e:
        logger.exception(e)