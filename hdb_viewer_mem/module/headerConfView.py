from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from hdb_viewer_mem.util.logger import *
logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)

import threading
import random
import math

class headerConfView(QGraphicsView):
    def __init__(self, parent=None):
        super(headerConfView, self).__init__(parent)

        # self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.hcviewRect = QRectF(0, 0, 600, 600)

        maigin = 8
        self.nameShowRect = QRectF(0+maigin, 0+maigin, 600-maigin*2, 300-maigin*2)
        self.nameHideRect = QRectF(0+maigin, 300+maigin, 600-maigin*2, 300-maigin*2)

        self.scene = QGraphicsScene(self.hcviewRect)
        self.setScene(self.scene)

        self.drag_item = None
        self.itemsInf = {} #items的位置信息
        self.itemsList = [] #items的位置顺序

        logger.debug("sceneRect():%s",self.sceneRect())

        self.init()

    def setScene(self,scene):
        self.scene = scene
        super(headerConfView, self).setScene(scene)

    def init(self):
        self.setRenderHints(QPainter.Antialiasing |
                            QPainter.HighQualityAntialiasing |
                            QPainter.TextAntialiasing |
                            QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(self.AnchorUnderMouse)
        self.setDragMode(self.RubberBandDrag)

        # setting scene and draw Rect
        self.setBackgroundBrush(QColor('#F0F0F0'))
        self.drawNameRect(rect=self.hcviewRect)
        self.drawNameRect(rect=self.nameShowRect)
        self.drawNameRect(rect=self.nameHideRect)


        # self.timer = QTimer(self, timeout=self.fun_timer, interval=50)
        # self.timer.start()
        self.drawcont = 0

        # for i in range(10):
        #     self.addCustomItem(str(i))

    # def fun_timer(self):
    #     self.drawcont -= 1
    #     item = customItem(str(self.drawcont))
    #     item.setPos(random.random() * 300, random.random() * 300)
    #     self.scene.addItem(item)
    #     self.update()
    #     if self.drawcont <= 0:
    #         self.timer.stop()  # 启用定时器

    def drawNameRect(self,rect=None,name=None):
        if rect is not None:
            self.scene.addItem(
                QGraphicsLineItem(QLineF(QPointF(rect.x(), rect.y()), QPointF(rect.width()+rect.x(), rect.y())))
            )
            self.scene.addItem(
                QGraphicsLineItem(QLineF(QPointF(rect.x(), rect.y()), QPointF(rect.x(), rect.height()+rect.y())))
            )
            self.scene.addItem(QGraphicsLineItem(
                QLineF(QPointF(rect.x(), rect.height()+rect.y()), QPointF(rect.width()+rect.x(), rect.height()+rect.y())))
            )
            self.scene.addItem(QGraphicsLineItem(
                QLineF( QPointF(rect.width()+rect.x(), rect.y()), QPointF(rect.width()+rect.x(), rect.height()+rect.y())) )
            )


    def addCustomItem(self,text):
        item = customItem(text)
        xpos = 0 + self.nameShowRect.x() + 5
        ypos = 30 + self.nameShowRect.y()
        if len(self.itemsList)>0:
            preitem = self.itemsList[-1]
            xpos = self.itemsInf[preitem][0]
            xpos += preitem.boundingRect().width() + 5
            ypos = self.itemsInf[preitem][1]
            if xpos+item.boundingRect().width() + 5 > self.nameShowRect.width():
                xpos = 0 + self.nameShowRect.x() + 5
                ypos += 30
        self.itemsInf[item] = [xpos,ypos]
        self.itemsList.insert(len(self.itemsList),item)
        item.setPos(xpos, ypos)
        self.scene.addItem(item)

    '''
    view 中 第startpos个textitem开始,到 endpos个textitem 结束,更新位置
    '''
    def updateItemsPos(self, startpos, endpos):
        logger.debug("star:%s end:%s",startpos,endpos)
        if startpos == endpos:
            return
        if startpos < endpos:
            rowitemcnt = math.floor(self.nameShowRect.width()/(self.drag_item.boundingRect().width()+5))
            for ind in range(int(startpos+1), int(endpos+1)):
                if ind >= len(self.itemsList) or ind < 0:
                    return
                item = self.itemsList[ind]
                self.itemsInf[item][0] -= (item.boundingRect().width() + 5)
                if self.itemsInf[item][0] < 0:
                    self.itemsInf[item][0] = (rowitemcnt-1)*(item.boundingRect().width()+5) + self.nameShowRect.x() + 5
                    self.itemsInf[item][1] -= 30
                item.setPos(self.itemsInf[item][0],self.itemsInf[item][1])
            self.itemsList.remove(self.drag_item)
            self.itemsList.insert(endpos,self.drag_item)
            self.itemsInf[self.drag_item][0] = ((startpos + endpos - startpos)%rowitemcnt)*(item.boundingRect().width() + 5)+self.nameShowRect.x() + 5
            self.itemsInf[self.drag_item][1] = math.floor((startpos + endpos - startpos)/rowitemcnt)*30 + self.nameShowRect.y() +30
            return
        if startpos > endpos:
            # return
            rowitemcnt = math.floor(self.nameShowRect.width() / (self.drag_item.boundingRect().width() + 5))
            for ind in range(int(endpos ), int(startpos)):
                if ind >= len(self.itemsList) or ind < 0:
                    return
                item = self.itemsList[ind]
                self.itemsInf[item][0] += (item.boundingRect().width() + 5)
                if self.itemsInf[item][0]+item.boundingRect().width() + 5 >= self.nameShowRect.x()+self.nameShowRect.width():
                    self.itemsInf[item][0] = self.nameShowRect.x() + 5
                    self.itemsInf[item][1] += 30
                item.setPos(self.itemsInf[item][0], self.itemsInf[item][1])
            self.itemsList.remove(self.drag_item)
            self.itemsList.insert(endpos, self.drag_item)
            # self.itemsInf[self.drag_item][0] += (endpos - startpos) * (item.boundingRect().width() + 5)
            self.itemsInf[self.drag_item][0] = ((startpos + endpos - startpos)%rowitemcnt)*(item.boundingRect().width() + 5)+self.nameShowRect.x() + 5
            self.itemsInf[self.drag_item][1] = math.floor((startpos + endpos - startpos)/rowitemcnt)*30 + self.nameShowRect.y() +30
            return

    def keyPressEvent(self, event):
        # if event.key() == Qt.Key_N:
        #     import random
        #     # item = GraphicItem()
        #     item = customItem()
        #     item.setPos(random.random()*300, random.random()*300)
        #     if self.scene is not None:
        #         self.scene.addItem(item)
        #     return
        super(headerConfView, self).keyPressEvent(event)

    def mousePressEvent(self, event):
        self.drag_item = self.itemAt(event.pos())
        if self.drag_item is not None:
            if event.button() == Qt.LeftButton:
                # if isinstance(self.drag_item, GraphicItem):
                print("Press Item", self.drag_item)
                self.drag_item.setZValue(2)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.drag_item is not None:
            self.drag_item.setZValue(1)
            self.drag_item.setPos(self.itemsInf[self.drag_item][0], self.itemsInf[self.drag_item][1])
            self.drag_item = None
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        try:
            if self.drag_item is not None:
                print("mouseMoveEvent", event.pos())
                print("drag_item.pos()", self.mapFromScene(self.drag_item.pos()), self.drag_item.scenePos(), self.drag_item.pos())
                # startpos = self.itemsInf[self.drag_item][0]/(self.drag_item.boundingRect().width()+5)
                # endpos = math.ceil(self.drag_item.pos().x()/(self.drag_item.boundingRect().width()+5))
                startpos = None
                endpos = None
                for item in self.itemsList:
                    if self.drag_item == item:
                        continue
                    itemrectInParentCor = item.mapRectToParent(item.boundingRect())
                    if itemrectInParentCor.contains(event.pos()):
                        startpos = self.itemsList.index(self.drag_item)
                        endpos = self.itemsList.index(item)
                if startpos is not None:
                    self.updateItemsPos(startpos,endpos)
                # 处理其他items移动
        except Exception as e:
            logger.exception("mouseMoveEvent Exception:")
            logger.exception(e)

        super().mouseMoveEvent(event)

    # def get_items_at_rubber(self):
    #     """ Get group select items. """
    #     area = self.rubberBandRect()
    #     return self.items(area)





class customItem(QGraphicsItem):
    def __init__(self,text="", parent=None):
        super(customItem, self).__init__(parent)
        self.text = text
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)

        self.timer = None
        self.pathSlips = 15

        #字体 高度宽度
        fm = QFontMetricsF(QApplication.font())
        ##item宽度随文本变化
        # self.textRect = fm.boundingRect(self.text)
        # self.textWith = self.textRect.width()
        # self.textHeigh  = self.textRect.height()
        #item固定宽度
        self.textRect = fm.boundingRect('a')
        self.textWith = self.textRect.width()*8
        self.textHeigh  = self.textRect.height()

    def boundingRect(self):
        return QRectF(0, 0, self.textWith+self.textHeigh, self.textHeigh+self.textHeigh/2)

    def paint(self, painter, option, widget):
        painter.setPen(QColor(0, 0, 0))
        painter.setBrush(QColor(200, 200, 200))
        painter.drawRect(self.boundingRect())
        painter.drawText(5, 15, self.text)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # update selected node and its edge
        if self.isSelected():
            # print("isSelected")
            pass
            # for gr_edge in self.scene().edges:
            #     gr_edge.edge_wrap.update_positions()
        
    def setPos(self, x, y):
        self.curstep = 0
        startpos = self.pos()
        xsteplen = (x - startpos.x())/self.pathSlips
        ysteplen = (y - startpos.y())/self.pathSlips
        self.path = []
        for ind in range(self.pathSlips):
            self.path.insert(ind,[startpos.x()+ind*xsteplen, startpos.y()+ind*ysteplen])
        self.path[self.pathSlips-1] = [x, y]
        self.timer = QTimer( timeout=self.Animation, interval=16)
        self.timer.start()


    def Animation(self):
        self.curstep += 1
        if self.curstep < self.pathSlips:
            super(customItem, self).setPos(self.path[self.curstep][0], self.path[self.curstep][1])
        else:
            self.timer.stop()
        pass

# class customItem2(QGraphicsItem):
#     def __init__(self,text="", parent=None):
#         super().__init__(parent)
#         self.text = text
#         self.setFlag(QGraphicsItem.ItemIsSelectable)
#         self.setFlag(QGraphicsItem.ItemIsMovable)
#
#     def boundingRect(self):
#         return QRectF(0, 0, 40, 30)
#
#     def paint(self, painter, option, widget):
#         painter.setPen(QColor(0, 250, 0))
#         painter.setBrush(Qt.blue)
#         painter.drawRect(self.boundingRect())
#         painter.drawText(5, 15, "LED"+self.text)
#
#     def mouseMoveEvent(self, event):
#         super().mouseMoveEvent(event)
#         # update selected node and its edge

# class GraphicItem(QGraphicsPixmapItem):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.pix = QPixmap("Model.png")
#         self.width = 85
#         self.height = 85
#         self.setPixmap(self.pix)
#         self.setFlag(QGraphicsItem.ItemIsSelectable)
#         self.setFlag(QGraphicsItem.ItemIsMovable)
#
#     def mouseMoveEvent(self, event):
#         super().mouseMoveEvent(event)
#         # update selected node and its edge
#         if self.isSelected():
#             print("isSelected")
#         #     for gr_edge in self.scene().edges:
#         #         gr_edge.edge_wrap.update_positions()