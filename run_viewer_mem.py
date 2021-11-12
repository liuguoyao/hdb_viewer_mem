import os
import sys
from traceback import format_exception
# from hdb_viewer.viewer.hdb_viewer import *
# from hdb_viewer.viewer.logger import *
#
#
# logger = get_logger(__name__)
win = None

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from hdb_viewer_mem.module.hdb_main import *


def exception_hook(exctype, value, traceback):
    # sys._excepthook(exctype, value, traceback)
    # sys.exit(1)
    text = "\n" + "".join(format_exception(exctype, value, traceback))
    win.append_log(text)


if __name__ == '__main__':
    sys.excepthook = exception_hook
    global fontSize
    try:
        # QtCore.QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        app = QApplication([])
        # app.setFont(QFont('Microsoft YaHer UI', fontSize))
        win = hdb_main_win()
        win.show()
        app.exec()
    except Exception as e:
        pass
        # logger.exception(e)