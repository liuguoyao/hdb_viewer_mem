
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import random

#行情快照 model部分,
# 处理数据功能:定时读取数据
class SnapshotTableModel(QAbstractTableModel):
    """Model"""
    def __init__(self):
        super(SnapshotTableModel, self).__init__()
        self._data = []
        self._background_color = []
        self._headers = ['学号', '姓名', '性别', '年龄']

        self._generate_data()

    def _generate_data(self):
        """填充表格数据"""
        name_list = ['张三', '李四', '王五', '王小二', '李美丽', '王二狗']

        for id_num, name in enumerate(name_list):
            self._data.append([str(id_num), name, '男', str(random.randint(20, 25))])

            # :默认单元格颜色为白色
            self._background_color.append([QColor(255, 255, 255) for i in range(4)])

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
            return self._data[row][col]
        elif role == Qt.BackgroundColorRole:
            return self._background_color[row][col]
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        return QVariant()

    def setData(self, index, value, role):
        """编辑单元格中的数据"""
        if not index.isValid() or not 0 <= index.row() < self.rowCount():
            return QVariant()

        if role == Qt.EditRole:
            if index.column() == 2:
                self._data[index.row()][index.column()] = value
                self.layoutChanged.emit()       # 更新数据后要通知表格刷新数据
                return True
            elif index.column() == 3:
                self._data[index.row()][index.column()] = str(value)
                self.layoutChanged.emit()
                return True
            else:
                return False

    def flags(self, index):
        """设置单元格的属性。"""
        if index.column() == 0 or index.column() == 1:
            # :我们设置第0、1列不可编辑，其他列可以编辑。
            return super().flags(index)

        return Qt.ItemIsEditable | super().flags(index)
