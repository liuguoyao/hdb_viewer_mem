
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import random
from hdb_viewer_mem.hdb_service.FetchData_Background_decorator import *

#行情快照 model部分,
# 处理数据功能:定时读取数据
class SnapshotTableModel(QAbstractTableModel):
    """Model"""
    def __init__(self):
        super(SnapshotTableModel, self).__init__()
        self._data = []
        self._background_color = []
        # self._headers = ['学号', '姓名', '性别', '年龄']
        self._headers = []

        self.fetchData = None
        self.reading = False

        #
        self.timer = QTimer(timeout=self.refreshData, interval=3000) # ms
        self.timer.start()

    def rowCount(self, parent=QModelIndex()):
        """返回行数量。"""
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        """返回列数量。"""
        return len(self._headers)

    def headerData(self, section, orientation, role):
        """设置表格头"""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]

    def data(self, index, role):
        """显示表格中的数据。"""
        if not index.isValid() or not 0 <= index.row() < self.rowCount():
            return QVariant()

        row = index.row()
        col = index.column()

        if role == Qt.DisplayRole:
            return str(self._data[row][col])
        elif role == Qt.BackgroundRole:
            return self._background_color[row][col]
        elif role == Qt.ForegroundRole:
            return self._foreground_color[row][col]
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        return QVariant()

    def setData(self, index, value, role):
        """编辑单元格中的数据"""
        if not index.isValid() or not 0 <= index.row() < self.rowCount():
            return QVariant()

        if role == Qt.EditRole:
            self._data[index.row()][index.column()] = str(value)
            self.layoutChanged.emit()
            return True

    def flags(self, index):
        """设置单元格的属性。"""
        if index.column() == 0 or index.column() == 1:
            # :我们设置第0、1列不可编辑，其他列可以编辑。
            return super().flags(index)

        return Qt.ItemIsEditable | super().flags(index)

    #custom
    def setheader(self,headerlist):
        self._headers = headerlist

    def setCustomData(self,data):
        self._data = data
        self._background_color = []
        self._foreground_color= []
        if len(data)>0:
            for rowdata in data:
                self._background_color.append([QBrush(QColor(255, 255, 240)) for i in range(len(rowdata))])
                self._foreground_color.append([QBrush(QColor(0, 0, 200)) for i in range(len(rowdata))])


    def refreshData(self):
        #调用FetchDataBackGround
        if self.fetchData is None or not self.reading:
            self.reading = True
            print("fetchData is None or not reading")
            self.fetchData = FetchData_Background_decorator(load2)
            self.fetchData.sigDataReturn.connect(self.set_custom_data_slot)
            # self.fetchData.sigProgressRate.connect(lambda v: print('PprogressRate emit rev:', v))
            # self.fetchData.sigProgressRate.connect(lambda v: print('sigProgressRate emit rev:', v))
        else:
            print("is reading ...")


    def set_custom_data_slot(self,result_list):
        print("slot:", len(result_list))
        if len(result_list)>1:
            self.setheader(result_list[0])
            self.setCustomData(result_list[1:])
            self.layoutChanged.emit()
        self.reading = False

    def __del__(self):
        print("snapshot tablemode del")