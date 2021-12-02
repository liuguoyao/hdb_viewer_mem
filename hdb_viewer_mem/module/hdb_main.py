import os
import sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from hdb_viewer_mem.viewer.hdb_main_ui import *
from hdb_viewer_mem.module.SnapshotTableModel import *
from hdb_viewer_mem.module.SnapshotDelegate import *
from hdb_viewer_mem.module.sysconfigwin import *
from hdb_viewer_mem.module.HeaderConfigSnapshotTable import *

#主界面 :包含行情快照 + 多窗口分时
class hdb_main_win(QMainWindow, Ui_HdbMainWin):
    def __init__(self, parent=None):
        super(hdb_main_win, self).__init__(parent)
        self.setupUi(self)

        #安装捕获应用事件
        self.installEventFilter(self)

        # signal slot
        self.action_back.triggered.connect(self.back)
        self.action_forward.triggered.connect(self.forward)
        self.action_config.triggered.connect(self.pop_sysconfigwin)
        self.actionmulwins.triggered.connect(lambda : print("actionmulwins"))

        # stack 1
        self.snapshotTableModel = SnapshotTableModel()
        self.snapshotDelegate = SnapshotDelegate()
        self.snapshotTableView.setModel(self.snapshotTableModel)
        self.snapshotTableView.setItemDelegate(self.snapshotDelegate)

        # stack 2


    def eventFilter(self, objwatched, event):
        if(hasattr(event, "pos") ):
            viewpos = self.snapshotTableView.mapFrom(self,event.pos())
            if(self.snapshotTableView.horizontalHeader().geometry().contains(viewpos)):
                if QEvent.ContextMenu == event.type():
                    # 处理右键菜单: 定制表头
                    logger.debug("ContextMenu Proceing")
                    self.action_header_config = QAction(u'表头配置', self)
                    self.action_header_config.triggered.connect(self.pop_headerConfigWin)
                    self.pop_menu = QMenu(self)
                    self.pop_menu.addAction(self.action_header_config)
                    self.pop_menu.popup(QCursor.pos())
                pass

        return super().eventFilter(objwatched, event)

    def back(self):
        totalpages = self.stackedWidget.count()
        curIndex = self.stackedWidget.currentIndex()
        self.stackedWidget.setCurrentIndex((curIndex + 1) % totalpages)

    def forward(self):
        totalpages = self.stackedWidget.count()
        curIndex = self.stackedWidget.currentIndex()
        self.stackedWidget.setCurrentIndex((curIndex - 1) % totalpages)

    def closeEvent(self, event):
        reply = QtWidgets.QMessageBox.question(self, r"退出确认", r"确定退出当前程序？")
        if reply != QtWidgets.QMessageBox.Yes:
            event.ignore()
            return
        if hasattr(self, "headerConfigWin"):
            del self.headerConfigWin
        FetchData_Background_decorator.close()
        event.accept()

    def pop_sysconfigwin(self):
        logger.debug("pop_sysconfigwin")
        self.syswin = sysconfigwin()
        self.syswin.show()

    def pop_headerConfigWin(self):
        logger.debug("pop_headerConfigWin")
        headernames = self.snapshotTableModel.headerNames()
        logger.debug(headernames)

        self.headerConfigWin = HeaderConfigSnapshotTable(headerNames=headernames)
        self.headerConfigWin.show()


