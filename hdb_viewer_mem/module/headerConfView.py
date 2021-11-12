from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import threading
import random
import math

class headerConfView(QGraphicsView):
    sceneWidth = 494
    sceneHeight = 238
    def __init__(self, parent=None):
        super(headerConfView, self).__init__(parent)
        self.scene = QGraphicsScene(0, 0, self.sceneWidth, self.sceneHeight)
        self.setScene(self.scene)

        self.drag_item = None
        self.itemsInf = {}
        self.itemsList = []
        print("sceneRect()",self.sceneRect())

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

        # setting scene
        self.setBackgroundBrush(QColor('#39A0A0'))
        self.scene.addItem(QGraphicsLineItem(QLineF(QPointF(0,0),QPointF(self.scene.width(),0))))
        self.scene.addItem(QGraphicsLineItem(QLineF(QPointF(0,0),QPointF(0,self.scene.height()))))
        self.scene.addItem(QGraphicsLineItem(QLineF(QPointF(0,self.scene.height()),QPointF(self.scene.width(),self.scene.height()))))
        self.scene.addItem(QGraphicsLineItem(QLineF(QPointF(self.scene.width(),0),QPointF(self.scene.width(),self.scene.height()))))


        # self.timer = QTimer(self, timeout=self.fun_timer, interval=50)
        # self.timer.start()
        self.drawcont = 0

        for i in range(10):
            self.addCustomItem(str(i))

    def fun_timer(self):
        self.drawcont -= 1
        item = customItem(str(self.drawcont))
        item.setPos(random.random() * 300, random.random() * 300)
        self.scene.addItem(item)
        self.update()
        if self.drawcont <= 0:
            self.timer.stop()  # 启用定时器

    def addCustomItem(self,text):
        item = customItem(text)
        xpos = (item.boundingRect().width()+5)*len(self.itemsInf)
        self.itemsInf[item] = [xpos,30]
        self.itemsList.insert(len(self.itemsList),item)
        item.setPos(xpos, 30)
        self.scene.addItem(item)

    def updateItemsPos(self, startpos, endpos):
        if startpos == endpos:
            return
        if startpos < endpos:
            for ind in range(int(startpos+1), int(endpos+1)):
                item = self.itemsList[ind]
                self.itemsInf[item][0] -= (item.boundingRect().width() + 5)
                item.setPos(self.itemsInf[item][0],30)
            self.itemsList.remove(self.drag_item)
            self.itemsList.insert(endpos,self.drag_item)
            self.itemsInf[self.drag_item][0] += (endpos - startpos)*(item.boundingRect().width() + 5)
            return
        if startpos > endpos:
            for ind in range(int(endpos ), int(startpos)):
                item = self.itemsList[ind]
                self.itemsInf[item][0] += (item.boundingRect().width() + 5)
                item.setPos(self.itemsInf[item][0], 30)
            self.itemsList.remove(self.drag_item)
            self.itemsList.insert(endpos, self.drag_item)
            self.itemsInf[self.drag_item][0] += (endpos - startpos) * (item.boundingRect().width() + 5)
            return


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_N:
            import random
            # item = GraphicItem()
            item = customItem()
            item.setPos(random.random()*300, random.random()*300)
            if self.scene is not None:
                self.scene.addItem(item)
            return
        super(headerConfView, self).keyPressEvent(event)

    def mousePressEvent(self, event):
        self.drag_item = self.itemAt(event.pos())
        print("itemInf:item No.", self.itemsInf[self.drag_item][0]/(self.drag_item.boundingRect().width()+5))
        if self.drag_item is not None and event.button() == Qt.LeftButton:
            # if isinstance(self.drag_item, GraphicItem):
            print("Press Item", self.drag_item)
            self.drag_item.setZValue(2)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.drag_item is not None:
            self.drag_item.setZValue(1)
            endpos = math.ceil(self.drag_item.pos().x() / (self.drag_item.boundingRect().width() + 5))
            self.drag_item.setPos(self.itemsInf[self.drag_item][0], 30)
            self.drag_item = None
        print("mouseReleaseEvent")
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        # print("mouseMoveEvent", event.pos())
        if self.drag_item is not None:
            print("mouseMoveEvent", event.pos())
            print("drag_item.pos()", self.mapFromScene(self.drag_item.pos()), self.drag_item.scenePos(), self.drag_item.pos())
            starpos = self.itemsInf[self.drag_item][0]/(self.drag_item.boundingRect().width()+5)
            endpos = math.ceil(self.drag_item.pos().x()/(self.drag_item.boundingRect().width()+5))
            self.updateItemsPos(starpos,endpos)
            # 处理其他items移动


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

    def boundingRect(self):
        return QRectF(0, 0, 40, 30)

    def paint(self, painter, option, widget):
        painter.setPen(QColor(100, 66, 250))
        painter.setBrush(QColor(255, 150, 150))
        # painter.drawEllipse(0, 0, 20, 20)
        # painter.drawLine(2, 5, 17, 17)
        # painter.drawLine(2, 17, 17, 5)
        # painter.setPen(QColor(245, 12, 231))
        # painter.drawText(0, -10, "LED")
        painter.drawRect(self.boundingRect())
        painter.drawText(5, 15, "LED"+self.text)

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

class customItem2(QGraphicsItem):
    def __init__(self,text="", parent=None):
        super().__init__(parent)
        self.text = text
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def boundingRect(self):
        return QRectF(0, 0, 40, 30)

    def paint(self, painter, option, widget):
        painter.setPen(QColor(0, 250, 0))
        painter.setBrush(Qt.blue)
        painter.drawRect(self.boundingRect())
        painter.drawText(5, 15, "LED"+self.text)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # update selected node and its edge

class GraphicItem(QGraphicsPixmapItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pix = QPixmap("Model.png")
        self.width = 85
        self.height = 85
        self.setPixmap(self.pix)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # update selected node and its edge
        if self.isSelected():
            print("isSelected")
        #     for gr_edge in self.scene().edges:
        #         gr_edge.edge_wrap.update_positions()