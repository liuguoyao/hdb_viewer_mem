from functools import partial
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from pyqtgraph import *
from PyQt5 import QtGui, QtCore, QtWidgets
from hdb_viewer_mem.util.logger import *

import numpy as np
import pandas as pd

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)

g_SecurityK = 0
g_SecurityK2 = 1
g_Volum = 2
g_P_L = 3
g_Position = 4

class TimeAxis(pg.AxisItem):
    def __init__(self, labels, *args, **kwargs):
        super(TimeAxis, self).__init__(*args, **kwargs)
        self.labels = labels

    def tickStrings(self, values, scale, spacing):
        strings = []
        for t in values:
            t = int(t)
            if t < 0 or t >= len(self.labels):
                s = " "
                strings.append(s)
                continue
            try:
                label = self.labels[t]
                s = str(label)
            except:
                s = " "
            strings.append(s)
        return strings

    def set_time_labels(self, labels):
        self.labels = labels


class ReturnAxis(pg.AxisItem):
    def __init__(self, pre_close, *args, **kwargs):
        super(ReturnAxis, self).__init__(*args, **kwargs)
        self.pre_close = pre_close

    def tickStrings(self, values, scale, spacing):
        strings = []
        for t in values:
            cur_return = t / self.pre_close - 1
            # s = "%8.2f%% " % (100 * cur_return)
            s = "{:<8.2%}".format(cur_return)
            strings.append(s)
        return strings


class SpaceAxis(pg.AxisItem):
    def __init__(self, text_width=0, *args, **kwargs):
        super(SpaceAxis, self).__init__(*args, **kwargs)
        self.space_width = text_width

    def tickStrings(self, values, scale, spacing):
        strings = []
        s = r' ' * self.space_width
        for _ in values:
            strings.append(s)
        return strings


class CustomViewBox(pg.ViewBox):
    key_press_sig = pyqtSignal(int, int)
    lines = []
    sigkeyPressEvent = pyqtSignal(int)

    def __init__(self, draw_line_flag=True, padding=0, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.PanMode)
        self.draw_line_flag = draw_line_flag
        self.v_line = None
        self.h_line = None
        self.padding = padding

    ## reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            return
            # self.autoRange()

    def mouseDragEvent(self, ev, axis=None):
        if ev.button() == QtCore.Qt.RightButton:
            ev.ignore()
        elif ev.button() != QtCore.Qt.LeftButton or ev.modifiers() != QtCore.Qt.ControlModifier:
            # super().mouseDragEvent(ev, axis)
            pg.ViewBox.mouseDragEvent(self, ev)
            return
        if self.draw_line_flag:
            if ev.isStart():
                p0 = self.mapDeviceToView(ev.buttonDownPos())
                p1 = self.mapDeviceToView(ev.pos())
                self.draw_line = pg.PolyLineROI([p0, p1], pen=(5),movable=False)
                self.Text = pg.TextItem(border='w', fill=(255, 255, 255, 150))
                self.Text.setAnchor((1,0))
                self.Text.setPos(p0)
                self.draw_line.setZValue(40)
                self.Text.setZValue(40)
                self.addItem(self.draw_line)
                self.addItem(self.Text,ignoreBounds=True)
                self.lines.append((self.draw_line,self.Text))
            else:
                p0 = self.mapDeviceToView(ev.buttonDownPos())
                p1 = self.mapDeviceToView(ev.pos())
                self.draw_line.movePoint(-1, p1)
                self.Text.setPos(p1)
                self.Text.setHtml('''<p> <span style="color:#000000;">{:.3f}%</span> </p>'''.format(p1.y() * 100 / p0.y() - 100))
            if ev.isFinish():
                self.draw_line.sigRegionChanged.connect(self.ROIRegionChanged)
            ev.accept()

    def ROIRegionChanged(self, v):
        for tu in self.lines:
            if v == tu[0]:
                self.Text = tu[1]
        points = v.getState()['points']
        p0, p1 = points[0], points[1]
        self.Text.setPos(p1)
        self.Text.setHtml('''<p> <span style="color:#000000;">{:.3f}%</span> </p>'''.format(p1.y() * 100 / p0.y() - 100))

    def wheelEvent(self, ev, axis=None):
        if axis in (0, 1):
            mask = [False, False]
            mask[axis] = self.state['mouseEnabled'][axis]
        else:
            mask = self.state['mouseEnabled'][:]
        s = 1.02 ** (ev.delta() * self.state['wheelScaleFactor']) # actual scaling factor
        s = [(None if m is False else s) for m in mask]
        center = self.mapDeviceToView(ev.pos())

        self._resetTarget()
        self.scaleBy(s, center)
        ev.accept()
        self.sigRangeChangedManually.emit(mask)


    def keyPressEvent(self, ev):
        mv_step = 0
        zoom_step = 0
        if ev.key() == QtCore.Qt.Key_Left:
            if ev.modifiers() == QtCore.Qt.ControlModifier:
                mv_step = - 10
            else:
                mv_step = - 1
        elif ev.key() == QtCore.Qt.Key_Right:
            if ev.modifiers() == QtCore.Qt.ControlModifier:
                mv_step = 10
            else:
                mv_step = 1
        elif ev.key() == QtCore.Qt.Key_Up:
            zoom_step = -1
        elif ev.key() == QtCore.Qt.Key_Down:
            zoom_step = 1

        self.key_press_sig.emit(mv_step, zoom_step)
        # if ev.key() in [QtCore.Qt.Key_Backspace,QtCore.Qt.Key_Delete]:
        #     self.sigkeyPressEvent.emit(ev.key())
        #     ev.accept()
        if ev.key() == QtCore.Qt.Key_Backspace:
            if len(self.lines)>0:
                itemline, textitem = self.lines.pop()
                itemline.hide()
                textitem.hide()
        if ev.key() == QtCore.Qt.Key_Delete:
            for v in self.lines:
                itemline, textitem = v
                itemline.hide()
                textitem.hide()
            self.lines.clear()

    def updateAutoRange(self):
        ## Break recursive loops when auto-ranging.
        ## This is needed because some items change their size in response
        ## to a view change.
        if self._updatingRange:
            return

        self._updatingRange = True
        try:
            targetRect = self.viewRange()
            if not any(self.state['autoRange']):
                return

            fractionVisible = self.state['autoRange'][:]
            for i in [0,1]:
                if type(fractionVisible[i]) is bool:
                    fractionVisible[i] = 1.0

            childRange = None

            order = [0,1]
            if self.state['autoVisibleOnly'][0] is True:
                order = [1,0]

            args = {}
            for ax in order:
                if self.state['autoRange'][ax] is False:
                    continue
                if self.state['autoVisibleOnly'][ax]:
                    oRange = [None, None]
                    oRange[ax] = targetRect[1-ax]
                    childRange = self.childrenBounds(frac=fractionVisible, orthoRange=oRange)

                else:
                    if childRange is None:
                        childRange = self.childrenBounds(frac=fractionVisible)

                ## Make corrections to range
                xr = childRange[ax]
                if xr is not None:
                    if self.state['autoPan'][ax]:
                        x = sum(xr) * 0.5
                        w2 = (targetRect[ax][1]-targetRect[ax][0]) / 2.
                        childRange[ax] = [x-w2, x+w2]
                    else:
                        padding = self.suggestPadding(ax)
                        wp = (xr[1] - xr[0]) * padding
                        childRange[ax][0] -= wp
                        childRange[ax][1] += wp
                    targetRect[ax] = childRange[ax]
                    args['xRange' if ax == 0 else 'yRange'] = targetRect[ax]

             # check for and ignore bad ranges
            for k in ['xRange', 'yRange']:
                if k in args:
                    if not np.all(np.isfinite(args[k])):
                        r = args.pop(k)
                        #print("Warning: %s is invalid: %s" % (k, str(r))

            if len(args) == 0:
                return
            args['padding'] = self.padding
            args['disableAutoRange'] = False

            self.setRange(**args)
        finally:
            self._autoRangeNeedsUpdate = False
            self._updatingRange = False


class leftPlotWidget(QWidget):
    mouse_move_sig = pyqtSignal(int)

    def __init__(self):
        super(leftPlotWidget, self).__init__()
        self.resize(1600,1200)

        self.plts = []
        self.vbs = []

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.symbol_label = QLabel("Symbol")
        self.layout.addWidget(self.symbol_label)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setSizePolicy(sizePolicy)

        # 画框架
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        pg.setConfigOptions(antialias=False)

        self.win = pg.GraphicsLayoutWidget(show=False, parent=self)
        market_layout = self.win.ci.addLayout(0, 0)
        other_data_layout = self.win.ci.addLayout(1, 0)

        self.win.ci.layout.setRowStretchFactor(0, 6)
        self.win.ci.layout.setRowStretchFactor(1, 4)

        self.win.ci.setSpacing(0)
        market_layout.setSpacing(0)
        other_data_layout.setSpacing(0)
        self.win.ci.setContentsMargins(0, 0, 0, 0)
        market_layout.setContentsMargins(0, 0, 0, 0)
        other_data_layout.setContentsMargins(0, 0, 0, 0)

        for i in range(2):
            vb = CustomViewBox()
            vb.v_line = pg.InfiniteLine(angle=90, movable=False)
            vb.h_line = pg.InfiniteLine(angle=0, movable=False)
            plt = pg.PlotItem(viewBox=vb)
            plt.addItem(vb.v_line, ignoreBounds=True)
            plt.addItem(vb.h_line, ignoreBounds=True)

            # plt.setLimits(xMin=0, xMax=240)
            vb.sigXRangeChanged.connect(self.set_y_range)
            vb.key_press_sig.connect(partial(self.key_press, vb=vb))
            # vb.sigkeyPressEvent.connect(partial(self.roi_del_event, vb=vb))

            self.plts.append(plt)
            self.vbs.append(vb)

        market_layout.addItem(self.plts[0])
        market_layout.nextRow()
        other_data_layout.addItem(self.plts[1])
        other_data_layout.nextRow()

        for plt in self.plts:
            plt.setClipToView(True)
            plt.setMouseEnabled(x=True, y=False)
            # plt.setAutoVisible(y=True)
            # plt.enableAutoRange(axis='y', enable=True)

            plt.showGrid(x=True, y=True, alpha=0.2)

            plt.getAxis("left").setWidth(80)
            plt.getAxis("right").setWidth(80)
            plt.showAxis("right")
            null_axis = SpaceAxis(0, orientation='top')
            null_axis.setHeight(0)
            plt.setAxisItems({"top": null_axis})
            plt.showAxis("top")

        null_axis = SpaceAxis(0, orientation='bottom')
        null_axis.setHeight(0)
        # self.plts[0].setAxisItems({"bottom": null_axis})
        self.returnAxis = ReturnAxis(1,orientation="right")
        self.plts[0].setAxisItems({"bottom": null_axis,"right":self.returnAxis})
        self.timeAxis = TimeAxis(labels=[], orientation="bottom")
        self.plts[1].setAxisItems({"bottom": self.timeAxis})
        self.plts[1].getAxis("right").setWidth(69)

        for vb in self.vbs[0:]:
            vb.setXLink(self.vbs[0])

        #float label
        self.time_item = pg.TextItem(border='w', fill=pg.mkBrush(QtGui.QColor(QtCore.Qt.darkGray)))
        self.price_text_item = pg.TextItem(border='w', fill=pg.mkBrush(QtGui.QColor(QtCore.Qt.darkGray)), anchor=(1, 1))
        self.return_item = pg.TextItem(border='w', fill=pg.mkBrush(QtGui.QColor(QtCore.Qt.darkGray)), anchor=(0, 1))
        self.time_item.setZValue(5)
        self.price_text_item.setZValue(5)
        self.return_item.setZValue(5)

        self.win.scene().addItem(self.time_item)
        self.win.scene().addItem(self.price_text_item)
        self.win.scene().addItem(self.return_item)
        self.win.proxy_mmove = pg.SignalProxy(self.win.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_move)

        self.layout.addWidget(self.win)
        #填数据

    def clear_plot(self):
        if self.plts is not None:
            for plt in self.plts:
                plt.clear()

    def mouse_move(self, evt):
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        self.update_axis_text(pos)
        self.update_cross_line(pos)

    def update_cross_line(self, scene_pos):
        vi_rect = self.vbs[0].sceneBoundingRect()
        last_vi_rect = self.vbs[-1].sceneBoundingRect()
        small_rect = QRectF(QPointF(vi_rect.left(),vi_rect.bottom()),
                          QPointF(vi_rect.right(),last_vi_rect.top()))

        if not (self.vbs[0].sceneBoundingRect().contains(scene_pos)
            or self.vbs[1].sceneBoundingRect().contains(scene_pos)
            or small_rect.contains(scene_pos)):
            for vb in self.vbs:
                vb.v_line.hide()
                vb.h_line.hide()
            return
        for vb in self.vbs:
            view_pos = vb.mapSceneToView(scene_pos)
            vb.v_line.setPos(view_pos.x())
            vb.h_line.setPos(view_pos.y())
            vb.v_line.show()
            vb.h_line.show()

    def update_axis_text(self, scene_pos):
        # scene_pos = vb.mapViewToScene(view_pos)
        vi_rect = self.vbs[0].sceneBoundingRect()
        last_vi_rect = self.vbs[-1].sceneBoundingRect()
        small_rect = QRectF(QPointF(vi_rect.left(),vi_rect.bottom()),
                          QPointF(vi_rect.right(),last_vi_rect.top()))

        if not (self.vbs[0].sceneBoundingRect().contains(scene_pos)
            or self.vbs[1].sceneBoundingRect().contains(scene_pos)
            or small_rect.contains(scene_pos)):
            self.time_item.hide()
            self.price_text_item.hide()
            self.return_item.hide()
            return

        self.time_item.show()
        self.price_text_item.show()
        self.return_item.show()

        if small_rect.contains(scene_pos):
            self.price_text_item.hide()
            self.return_item.hide()

        # place time item
        view_pos = self.vbs[0].mapSceneToView(scene_pos)
        index = int(view_pos.x())
        self.mouse_move_sig.emit(index)

        value_view_y = view_pos.y()
        value_view_x = view_pos.x()
        x_pos = scene_pos.x()
        y_pos = scene_pos.y()

        if value_view_x>=0 and value_view_x<len(self.timeAxis.labels):
            self.time_item.setHtml("<span>%s" % self.timeAxis.labels[int(value_view_x)])
            self.time_item.show()
        else:
            self.time_item.hide()
        x_pos_label = x_pos - self.time_item.sceneBoundingRect().width() / 2
        self.time_item.setPos(x_pos_label, last_vi_rect.bottom())

        if self.vbs[0].sceneBoundingRect().contains(scene_pos):  # price plot
            # place price text item
            self.price_text_item.setHtml("<span>%.3f" % value_view_y)
            y_pos_label = y_pos + self.price_text_item.sceneBoundingRect().height() / 2
            self.price_text_item.setPos(vi_rect.left(), y_pos_label)

            # place return item
            self.return_item.setHtml("<span>%.2f%%" % (value_view_y*100/self.returnAxis.pre_close - 100))
            y_pos_label = y_pos + self.return_item.sceneBoundingRect().height() / 2
            self.return_item.setPos(vi_rect.right(), y_pos_label)

        if self.vbs[1].sceneBoundingRect().contains(scene_pos): # vol plot
            view_pos = self.vbs[1].mapSceneToView(scene_pos)
            # place vol text item
            self.price_text_item.setHtml("<span>%d" % int(view_pos.y()))
            y_pos_label = y_pos + self.price_text_item.sceneBoundingRect().height() / 2
            self.price_text_item.setPos(vi_rect.left(), y_pos_label)

            #hide return item
            self.return_item.hide()
            pass

    def key_press(self, mv_step, zoom_step, vb):
        if mv_step != 0:
            x_pos = vb.v_line.getXPos()
            y_pos = vb.h_line.getYPos()

            new_x_pos = x_pos + mv_step
            new_y_pos = y_pos

            new_pos = QtCore.QPointF(new_x_pos, new_y_pos)
            scence_pos = vb.mapViewToScene(new_pos)

            self.update_cross_line(scence_pos)
            self.update_axis_text(scence_pos)

        if zoom_step != 0:
            x_pos = vb.v_line.getXPos()
            y_pos = vb.h_line.getYPos()
            center = QtCore.QPointF(x_pos, y_pos)
            factor = 1
            adj = 0.1 * zoom_step
            factor = factor + adj
            vb.scaleBy([factor, 0], center)

    @staticmethod
    def set_y_range(vb, range):
        x_range_start, x_range_end = range
        vb.enableAutoRange(axis='y')
        vb.setAutoVisible(y=True)

    # @staticmethod
    # def roi_del_event(key_value, vb):
    #     if key_value in [QtCore.Qt.Key_Backspace, QtCore.Qt.Key_Delete]:
    #         if len(vb.lines) > 0:
    #             vb.removeItem(vb.lines[len(vb.lines) - 1][0])
    #             vb.removeItem(vb.lines[len(vb.lines) - 1][1])
    #             vb.lines = vb.lines[:-1]


class MyDelegate(QStyledItemDelegate):
    def createEditor(self, QWidget, QStyleOptionViewItem, QModelIndex):
        print('createEditor')
        super(MyDelegate, self).createEditor(QWidget, QStyleOptionViewItem, QModelIndex)
        pass

    def setEditorData(self, QWidget, QModelIndex):
        print('setEditorData')
        super(MyDelegate, self).setEditorData(QWidget, QModelIndex)
        pass

    def setModelData(self, QWidget, QAbstractItemModel, QModelIndex):
        print('setModelData')
        super(MyDelegate, self).setModelData(QWidget, QAbstractItemModel, QModelIndex)
        pass

    def updateEditorGeometry(self, QWidget, QStyleOptionViewItem, QModelIndex):
        print('updateEditorGeometry')
        super(MyDelegate, self).updateEditorGeometry(QWidget, QStyleOptionViewItem, QModelIndex)
        pass

    def paint(self, painter, option, index):
        x, y, h, w = option.rect.x(), option.rect.y(), option.rect.height(), option.rect.width()
        rectleft = QRect(x, y, w / 2, h)
        rectright = QRect(x + w / 2, y, w / 2, h)
        # 三角号
        x, y, w, h = x + w / 2, y, w / 2, h / 2
        x, y, w, h = x + w / 5, y + h / 2, w, h
        point = None
        if 2 == index.column():
            painter.setRenderHint(QPainter.Antialiasing)
            if 0 == index.row() % 2:
                painter.setPen(QColor(200, 0, 0))
                painter.setBrush(QColor(200, 0, 0))
                pointsup = QPolygonF()
                pointsup.append(QPointF(w / 2 / 3 + x, 0.0 + y))
                pointsup.append(QPointF(0.0 + x, h + y))
                pointsup.append(QPointF(w / 3 + x, h + y))
                point = pointsup
            else:
                painter.setPen(QColor(0, 180, 0))
                painter.setBrush(QColor(0, 180, 0))
                pointsdown = QPolygonF()
                pointsdown.append(QPointF(0.0 + x, 0.0 + y))
                pointsdown.append(QPointF(w / 3 + x, 0.0 + y))
                pointsdown.append(QPointF(w / 2 / 3 + x, h + y))
                point = pointsdown
            painter.drawText(rectleft, QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
                             str(index.data()))
            painter.drawPolygon(point)
            # print('need pait custom',index.row(),index.column())
        else:
            super(MyDelegate, self).paint(painter, option, index)
        return


class MyTableBSDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):

        x, y, h, w = option.rect.x(), option.rect.y(), option.rect.height(), option.rect.width()
        # painter.setPen(QColor(200, 0, 0))
        # painter.setBrush(QColor(200, 0, 0))
        r = index.row()
        c = index.column()
        if c<1:
            option.rect.adjust(-3, 0, 0, 0)
        super(MyTableBSDelegate, self).paint(painter, option, index)
        if 10 == r or 0 == r or 20 == r:
            painter.drawLine(x, y, x + w, y)
        if 1 == c or 0 == c or 4 ==c:
            painter.drawLine(x, y, x, y + h)




class PandasModel(QAbstractTableModel):
    def __init__(self, data, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._data = np.array(data.values)
        self._cols = data.columns
        self.r, self.c = np.shape(self._data)

    def load(self, data):
        self.beginResetModel()
        self._data = np.array(data.values)
        self._cols = data.columns
        self.r, self.c = np.shape(self._data)
        self.endResetModel()

    def rowCount(self, parent=None):
        return self.r

    def columnCount(self, parent=None):
        return self.c

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return str(self._data[index.row(), index.column()])
        return None

    def headerData(self, p_int, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self._cols[p_int]
            elif orientation == QtCore.Qt.Vertical:
                return p_int
        return None


class PandasModelBS(QAbstractTableModel):
    def __init__(self, data, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._data = np.array(data.values)
        self._cols = data.columns
        self.r, self.c = np.shape(self._data)
        self.pre_close = 0
        self.Foregroundlist = []

    def load(self, data, pre_close):
        self.pre_close = pre_close
        self.beginResetModel()
        self._data = np.array(data.values)
        self._cols = data.columns
        self.r, self.c = np.shape(self._data)
        self.endResetModel()

        self.Foregroundlist = []
        for v in pd.DataFrame(self._data).iloc[:,2]:
            if v > self.pre_close:
                self.Foregroundlist.append(QColor(QtCore.Qt.red))
            elif v < self.pre_close:
                self.Foregroundlist.append(QColor(QtCore.Qt.green))
            else:
                self.Foregroundlist.append(QColor(QtCore.Qt.black))
        # self.layoutChanged.emit()

    def rowCount(self, parent=None):
        return self.r

    def columnCount(self, parent=None):
        return self.c

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return str(self._data[index.row(), index.column()])
            if role == QtCore.Qt.BackgroundRole:
                # br = QBrush(QtCore.Qt.red)
                br = QBrush(QColor(0xFF, 0xFF, 0xFF))
                if index.row() < 10 and index.column()>0:  # and index.column() == 0:
                    br = QBrush(QColor(0xFF, 0xFF, 0xFF))
                elif index.column()>0:
                    br = QBrush(QColor(0xFF, 0xFF, 0xFF))
                return br
            if role == QtCore.Qt.ForegroundRole:
                if index.row()>len(self.Foregroundlist):
                    return QColor(QtCore.Qt.black)
                return self.Foregroundlist[index.row()]
        return None

    def headerData(self, p_int, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self._cols[p_int]
            elif orientation == QtCore.Qt.Vertical:
                return p_int
        return None


class TableBS(QWidget):
    def __init__(self, parent=None):
        super(TableBS, self).__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        # fontheigh = QFont()

        # df2 = pd.DataFrame(np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), columns=['a', 'b', 'c'])
        n = []
        n.append(['买盘', '10', '3.9', '41'])
        n.append(['', '9', '3.8', '4'])
        n.append(['', '8', '3.7', '42'])
        n.append(['', '7', '3.6', '4'])
        n.append(['', '6', '3.5', '44'])
        n.append(['', '5', '3.4', '45'])
        n.append(['', '4', '3.3', '4'])
        n.append(['', '3', '3.2', '41'])
        n.append(['', '2', '3.1', '49'])
        n.append(['', '1', '3', '4'])
        n.append(['卖盘', '1', '3', '4'])
        n.append(['', '2', '3', '44'])
        n.append(['', '3', '3', '4'])
        n.append(['', '4', '3', '4'])
        n.append(['', '5', '3', '42'])
        n.append(['', '6', '3', '43'])
        n.append(['', '7', '3', '4'])
        n.append(['', '8', '3', '41'])
        n.append(['', '9', '3', '4'])
        n.append(['', '10', '3', '41'])
        self.df2 = pd.DataFrame(np.array(n))

        self.model = PandasModelBS(self.df2)
        self.tableView = QTableView()
        self.tableView.setSelectionBehavior(QTableView.SelectRows)
        self.tableView.setFocusPolicy(QtCore.Qt.NoFocus)
        self.tableView.setModel(self.model)
        fm = QFontMetrics(QApplication.font())

        # self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.verticalHeader().setMinimumSectionSize(fm.height())
        self.tableView.horizontalHeader().setMinimumSectionSize(fm.width('B'))
        # self.tableView.horizontalHeader().setDefaultSectionSize(fm.width('B') )
        self.tableView.verticalHeader().setDefaultSectionSize(fm.height())
        # self.tableView.setMinimumSize(QtCore.QSize(0, fm.width('B')))
        # self.tableView.setMaximumSize(QtCore.QSize(16777215, fm.width('B')))

        self.tableView.setFrameShape(QFrame.NoFrame)
        # self.tableView.horizontalHeader().setHighlightSections(False)
        self.tableView.setShowGrid(False)
        # self.tableView.setAutoScroll(False)
        self.tableView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableView.setCornerButtonEnabled(False)
        self.tableView.verticalHeader().hide()
        self.tableView.horizontalHeader().hide()
        self.tableView.setWordWrap(True)
        # self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tableView.setColumnWidth(0, fm.width('BB'))
        self.tableView.setColumnWidth(1, 100)
        self.tableView.setColumnWidth(2, 100)
        self.tableView.setColumnWidth(3, 100)
        self.setFixedSize(fm.width('BB')+300,20*fm.height())
        # for row in range(2):
        #     self.tableView.setColumnWidth(row,3)
        # self.model.item(1, 0).setBackground(QBrush(QColor(255, 0, 0)))
        self.tableView.setSpan(0, 0, 10, 1)
        self.tableView.setSpan(10, 0, 10, 1)
        # self.tableView.setShowGrid(False)
        delegate = MyTableBSDelegate()
        self.tableView.setItemDelegate(delegate)

        # 设置布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tableView)

        self.setLayout(layout)


    def refreshData(self, askprice, askvol, bidprice, bidvol,pre_close):
        if len(askprice) < 10 or len(bidprice) < 10:
            return
        reversaskprice = askprice.copy()
        reversaskvol = askvol.copy()
        reversaskprice.reverse()
        reversaskvol.reverse()
        for index in range(20):
            if index < 10:
                self.df2.iat[index, 2] = reversaskprice[index]
                self.df2.iat[index, 3] = reversaskvol[index]
            else:
                self.df2.iat[index, 2] = bidprice[index - 10]
                self.df2.iat[index, 3] = bidvol[index - 10]
        self.model.load(self.df2,pre_close)


class TableOrder(QWidget):
    def __init__(self, parent=None):
        super(TableOrder, self).__init__(parent)
        # self.resize(600, 800)
        self.setContentsMargins(0, 0, 0, 0)

        # df2 = pd.DataFrame(np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), columns=['a', 'b', 'c'])

        n = []
        n.append([])
        self.df2 = pd.DataFrame(np.array(n))

        self.model = PandasModel(self.df2)
        self.tableView = QTableView()
        self.tableView.setFocusPolicy(QtCore.Qt.NoFocus)
        self.tableView.horizontalHeader().setHighlightSections(False)
        self.tableView.setModel(self.model)

        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        # self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.verticalHeader().hide()
        self.tableView.setSelectionBehavior(QTableView.SelectRows)
        # self.tableView.setFrameShape(QFrame.NoFrame)
        # self.tableView.horizontalHeader().hide()
        # for row in range(2):
        #     self.tableView.setColumnWidth(row,3)
        # self.tableView.setShowGrid(False)
        delegate = MyDelegate()
        # self.tableView.setItemDelegate(delegate)

        # 设置布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tableView)
        self.setLayout(layout)

    def refreshData(self, df):
        # if len(price) < 10 or len(vol) < 10:
        #     return
        # for index in range(10):
        #     self.df2.iat[index, 2] = price[index]
        #     self.df2.iat[index, 3] = vol[index]
        self.df2 = df
        self.model.load(self.df2)
        self.tableView.scrollToBottom()
        # self.tableView.scrollToTop()

class rightwidget(QWidget):
    def __init__(self):
        super(rightwidget, self).__init__()
        self.vblayout = QVBoxLayout()
        self.vblayout.setContentsMargins(0,0,0,0)
        self.vblayout.setSpacing(0)

        self.symbol_label = QLabel("symbolname")
        self.vblayout.addWidget(self.symbol_label)

        self.askbidtable = TableBS()  #10档行情
        self.vblayout.addWidget(self.askbidtable)

        self.ordertable = TableOrder() #订单
        self.vblayout.addWidget(self.ordertable)

        self.setLayout(self.vblayout)

        self.symbol_label.setFixedWidth(self.askbidtable.width())
        self.ordertable.setFixedWidth(self.askbidtable.width())
        
class IntraDayPlotWidget(QWidget):
    leftwin_mouse_move_sig = pyqtSignal(object)
    def __init__(self):
        super(IntraDayPlotWidget, self).__init__()
        #添加窗口部件
        self.hblayout = QHBoxLayout()
        self.hblayout.setSpacing(0)
        self.hblayout.setContentsMargins(0,0,0,0)

        self.leftwin = leftPlotWidget()
        self.hblayout.addWidget(self.leftwin)

        self.rightwin = rightwidget()
        self.hblayout.addWidget(self.rightwin)

        self.setLayout(self.hblayout)

        #窗口比例
        self.hblayout.setStretchFactor(self.leftwin,1)

        #默认line bar
        self.price_line = self.leftwin.plts[0].plot(pen = pg.mkPen(width=2, color=(200, 0, 0)))

        #signal slot
        self.leftwin.mouse_move_sig.connect(lambda x :self.leftwin_mouse_move_sig.emit((self,x)))


    def set_symbolname(self,name):
        self.rightwin.symbol_label.setText(name)
        self.leftwin.symbol_label.setText(name)
        pass

    def set_askbid_data(self,askprice, askvol, bidprice, bidvol):
        # refreshData
        self.rightwin.askbidtable.refreshData(askprice, askvol, bidprice, bidvol,self.leftwin.returnAxis.pre_close)

    def set_order_data(self,data):
        self.rightwin.ordertable.refreshData(data)
        pass

    def set_ReturnAxis_benchmark_prcie(self,price):
        self.leftwin.returnAxis.pre_close = price

    def set_time_labels(self,labels):
        self.leftwin.timeAxis.set_time_labels(labels)
        self.leftwin.plts[1].showAxes("bottom")

    def plotline(self, x=None, y=None, *args, **kargs):
        if x is None or y is None:
            return
        # self.leftwin.plts[0].setXRange(0, 240, padding=0)

        if 'pen' in kargs.keys():
            return self.leftwin.plts[0].plot(x=x, y=y, pen=kargs['pen'])
        else:
            return self.leftwin.plts[0].plot(x=x, y=y)



    def plotbar(self, x=None, height=None, *args, **kargs):
        if hasattr(self,"pos_bar"):
            self.pos_bar.setOpts(x=x, height=height, *args, **kargs)
            return
        if x is None or height is None:
            return
        if 'color' in kargs.keys():
            self.pos_bar = pg.BarGraphItem(x=x, height=height, width=0.5,
                                      pen=pg.mkPen(kargs['color']), brush=pg.mkBrush(kargs['color']))
        else:
            self.pos_bar = pg.BarGraphItem(x=x, height=height, width=0.5)

        self.leftwin.plts[1].addItem(self.pos_bar)
        # self.leftwin.plts[1].setXRange(0, 240, padding=0)

    def setXRange(self,min,max):
        self.leftwin.plts[0].setXRange(min,max)

    def setLimits(self, xMin, xMax):
        self.leftwin.plts[0].setLimits(xMin=xMin, xMax=xMax)
        self.leftwin.plts[1].setLimits(xMin=xMin, xMax=xMax)


if __name__ == '__main__':
    try:
        app = QApplication([])

        win = IntraDayPlotWidget()
        win.resize(1400,1000)
        win.set_symbolname("7788.sh 欢乐海岸")

        #数据
        cnt = 10
        index,data = list(range(cnt*3)), np.random.rand(cnt*3)

        # pl = win.plotline(x=index, y=data, pen=pg.mkPen(width=2, color=(200, 0, 0)))
        # pl2 = win.plotline(x=index, y=data, pen=pg.mkPen(width=2, color=(0, 200, 0)))
        win.plotbar(x=index, height=data, color=QColor(153, 0, 0, 128))

        index, data = range(cnt*2), np.random.rand(cnt*2)

        # pl.setData(x=index, y=data)
        win.plotbar(x=index, height=data, color=QColor(0, 204, 0, 128))
        win.price_line.setData(x=index, y=data)

        win.set_ReturnAxis_benchmark_prcie(data[0])  #计算涨跌比例
        win.leftwin.timeAxis.set_time_labels(["01","02","03","04","005","006",5,6,7])

        # win.set_askbid_data(np.random.rand(10).tolist(),np.random.rand(10).tolist(),np.random.rand(10).tolist(),np.random.rand(10).tolist())
        win.set_askbid_data(['1', '2', '2', '2', '2', '2', '2', '2', '2', '2'],
                            ['10', '2', '2', '2', '2', '2', '2', '2', '2', '2'],
                            ['1', '2', '2', '2', '2', '2', '2', '2', '2', '2'],
                            ['10', '2', '2', '2', '2', '2', '2', '2', '2', '2']
                            )

        data = np.array([
            [915,50,2,'B'],
            [916,51,20,'B'],
            [917,48,32,'B'],
            [918,50,21,'s'],
            [919,40,62,'B'],
            [920,52,20,'B'],

        ])
        df = pd.DataFrame(data,columns=['time','order_price','vol','flag'])
        win.set_order_data(df)

        win.setXRange(0,10)
        win.setLimits(0,40)


        win.show()
        app.exec()
    except Exception as e:
        logger.debug(e)