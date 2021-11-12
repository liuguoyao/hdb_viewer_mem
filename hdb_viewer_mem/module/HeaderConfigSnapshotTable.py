import os
import sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from hdb_viewer_mem.viewer.HeaderConfigSnapshotTable_ui import *
from hdb_viewer_mem.module.SnapshotTableModel import *
from hdb_viewer_mem.module.SnapshotDelegate import *


class HeaderConfigSnapshotTable(QWidget,Ui_HeaderConfigSnapshotTable):
    def __init__(self, parent=None):
        super(HeaderConfigSnapshotTable,self).__init__(parent)
        self.setupUi(self)


if __name__ == '__main__':
    App = QApplication([])

    win = HeaderConfigSnapshotTable()
    win.show()

    App.exec()