
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import random
from hdb_viewer_mem.hdb_service.FetchData_Background_decorator import *
from hdb_viewer_mem.util.logger import *

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)


#行情快照 model部分,
# 处理数据功能:定时读取数据
class SnapshotTableModel(QAbstractTableModel):
    sigdatafresh = pyqtSignal()
    """Model"""
    def __init__(self):
        super(SnapshotTableModel, self).__init__()
        self._data = pd.DataFrame()

        manager = Manager()
        self.manager_dic_SecurityTick = manager.dict() #内存快照信息
        self.manager_dic_SHSetpTrade = manager.dict() #
        self.manager_dic_SZSetpTrade = manager.dict() #
        self.manager_list = manager.list() #tableview显示的快照信息
        self.manager_list.append(pd.DataFrame())

        self._background_color = []

        self.fetchData = None
        self.reading = False

        #
        self.timer = QTimer(timeout=self.refreshUIData, interval=3000) # ms
        self.timer.start()

        self.refreshData()

    def rowCount(self, parent=QModelIndex()):
        """返回行数量。"""
        return self._data.shape[0]
        # return self.manager_list[0].shape[0]

    def columnCount(self, parent=QModelIndex()):
        """返回列数量。"""
        return self._data.shape[1]
        # return self.manager_list[0].shape[1]

    def headerData(self, section, orientation, role):
        """设置表格头"""
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return list(self._data.columns)[section]
                # return list(self.manager_list[0].columns)[section]
            elif orientation == Qt.Vertical:
                return str(section+1)

    def data(self, index, role):
        """显示表格中的数据。"""
        if not index.isValid() or not 0 <= index.row() < self.rowCount():
            return QVariant()

        row = index.row()
        col = index.column()

        if role == Qt.DisplayRole:
            return str(self._data.iat[row,col])
            # return str(self.manager_list[0].iat[row,col])
        elif role == Qt.BackgroundRole:
            if row >= len(self._background_color) :
                return QBrush(QColor(255, 255, 255))
            else:
                return self._background_color[row][col]
            # return QBrush(QColor(255, 255, 255))
        elif role == Qt.ForegroundRole:
            if row >= len(self._foreground_color) :
                return QBrush(QColor(0, 100, 200))
            else:
                return self._foreground_color[row][col]
            # return QBrush(QColor(0, 100, 200))
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        return QVariant()

    # def setData(self, index, value, role):
    #     """编辑单元格中的数据"""
    #     if not index.isValid() or not 0 <= index.row() < self.rowCount():
    #         return QVariant()
    #
    #     if role == Qt.EditRole:
    #         self._data[index.row()][index.column()] = str(value)
    #         self.layoutChanged.emit()
    #         return True

    # def flags(self, index):
    #     """设置单元格的属性。"""
    #     if index.column() == 0 or index.column() == 1:
    #         # :我们设置第0、1列不可编辑，其他列可以编辑。
    #         return super().flags(index)
    #
    #     return Qt.ItemIsEditable | super().flags(index)

    def headerNames(self):
        return list(self._data.columns)

    def refreshData(self):
        #调用FetchDataBackGround
        if self.fetchData is None or not self.reading:
            self.reading = True
            logger.debug("fetchData is None or not reading")
            # self.fetchData = FetchData_Background_decorator(load2)
            self.fetchData = FetchData_Background_decorator(snapCachRefresh,
                                                            dic_security=self.manager_dic_SecurityTick,
                                                            dic_SHSetpTrade = self.manager_dic_SHSetpTrade,
                                                            dic_SZSetpTrade = self.manager_dic_SZSetpTrade)
            self.fetchData.sigDataReturn.connect(self.set_custom_data_slot)
            # self.fetchData.sigProgressRate.connect(lambda v: print('PprogressRate emit rev:', v))
            # self.fetchData.sigProgressRate.connect(lambda v: print('sigProgressRate emit rev:', v))
        else:
            logger.debug("is reading ...")

    def refreshUIData(self):
        logger.debug("refreshUIData")

        self.refreshUI = FetchData_Background_decorator(refreshUIData, dic_security=self.manager_dic_SecurityTick, lis=self.manager_list)
        self.refreshUI.sigDataReturn.connect(self.refreshUI_slot)
        pass

    def refreshUI_slot(self, result_list):

        self._background_color = []
        self._foreground_color = []
        rows, cls = self.manager_list[0].shape[0],self.manager_list[0].shape[1]
        for rowidx in range(rows):
            self._background_color.append([QBrush(QColor(255, 255, 255)) for i in range(cls)])
            self._foreground_color.append([QBrush(QColor(0, 100, 200)) for i in range(cls)])
        self._data = self.manager_list[0]
        self.layoutChanged.emit()
        self.sigdatafresh.emit()
        pass


    def set_custom_data_slot(self,result_list):
        logger.debug("slot:" + str(len(result_list)))
        self.refreshData()
        # if len(result_list)>1:
        #     self.setheader(result_list[0])
        #     self.setCustomData(result_list[1:])
        #     self.layoutChanged.emit()
        # self.reading = False

    def __del__(self):
        logger.debug("snapshot tablemode del")