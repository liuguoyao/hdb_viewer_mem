import os
import sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from hdb_viewer_mem.viewer.HeaderConfigSnapshotTable_ui import *
from hdb_viewer_mem.module.SnapshotTableModel import *
from hdb_viewer_mem.module.SnapshotDelegate import *


class HeaderConfigSnapshotTable(QWidget,Ui_HeaderConfigSnapshotTable):
    def __init__(self, headerNames=[], parent=None):
        super(HeaderConfigSnapshotTable,self).__init__(parent)
        self.setupUi(self)
        self.resize(self.graphicsView.hcviewRect.width()+30,self.graphicsView.hcviewRect.height()+30)

        #config windows
        self.setWindowFlags(Qt.WindowMinimizeButtonHint|Qt.WindowCloseButtonHint)
        self.setFixedSize(self.width(), self.height());

        #sig slot
        self.pushButton_OK.clicked.connect(self.slot_OK)
        self.pushButton_cancel.clicked.connect(self.slot_cancel)

        # set headernames
        for name in headerNames:
            self.graphicsView.addCustomItem(name, 1)

    def get_headers(self):
        return self.graphicsView.get_headers()

    def slot_OK(self):
        logger.debug("slot_OK ... ")
        logger.debug(self.get_headers())
        pass

    def slot_cancel(self):
        logger.debug("slot_cancel ... ")
        self.close()
        pass

if __name__ == '__main__':
    import traceback
    try:
        App = QApplication([])
        win = HeaderConfigSnapshotTable(
            headerNames=['aaaaa','bbb','ccccccccc','d','e','fffffffffffff','gg','hhhhhhhh',
                         'iiiiiiiiiiiii','jj','kk','lllllllllll','mmmmmmmmm','nn','oo','pp','qq','ll','m','n'])
        win.show()

        App.exec()
    except Exception as e:
        traceback.print_exc()
        # print(e.__traceback__)