
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import random
from hdb_viewer_mem.hdb_service.FetchData_Background_decorator import *
from hdb_viewer_mem.util.logger import *
# from multiprocessing import Manager

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

        self._background_color = []
        self._data_bak = pd.DataFrame()

        self.fetchData = None
        self.reading = False

        self.timer = QTimer(timeout=self.refreshUIData, interval=1000) # ms

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
            self.fetchData = FetchData_Background_decorator(snapCachRefresh_shareFile)
        else:
            logger.debug("is reading ...")

        self.timer.start()

    def refreshUIData(self):
        logger.debug("snap shot refreshUIData ...")
        try:
            # 读取文件
            curdate = time.strftime("%Y%m%d")
            global g_config_path
            initmap = config_ini_key_value(keys=[], config_file=g_config_path)
            symbols = initmap['symbols'].split(',')

            symboll = []
            if self._data_bak is not None and len(self._data_bak) > 0:
                symboll = [str(v[:9], encoding="utf8") for v in self._data_bak.symbol.values]

            for symbol in symbols:
                filename = os.path.join(curdate, symbol + "_SecurityTick.data")
                if not os.path.exists(filename):
                    continue

                itemdf = read_item_last(filename)

                if symbol not in symboll:
                    self._data_bak = self._data_bak.append(itemdf)
                else:
                    self._data_bak.update(itemdf)

            if len(self._data_bak) == 0:
                return

            self._data = self._data_bak[initmap["header_show"].split(',')]
            symbol_Ser = self._data['symbol'].apply(lambda x : str(x[:9],encoding="utf-8"))
            self._data.loc[:,'symbol'] = symbol_Ser
            self._background_color = []
            self._foreground_color = []
            rows, cls = self._data.shape[0], self._data.shape[1]
            for rowidx in range(rows):
                pre_close = self._data_bak.iloc[rowidx]['pre_close']
                match = self._data_bak.iloc[rowidx]['match']
                self._background_color.append([QBrush(QColor(255, 255, 255)) for i in range(cls)])
                if pre_close<match:
                    self._foreground_color.append([QBrush(QColor(200, 10, 10)) for i in range(cls)])
                elif pre_close==match:
                    self._foreground_color.append([QBrush(QColor(10, 10, 10)) for i in range(cls)])
                else:
                    self._foreground_color.append([QBrush(QColor(10, 200, 10)) for i in range(cls)])

            self.layoutChanged.emit()

        except Exception as e:
            logger.exception("refreshUIData Exception:")
            logger.exception(e)
        return

    def __del__(self):
        logger.debug("snapshot tablemode del")