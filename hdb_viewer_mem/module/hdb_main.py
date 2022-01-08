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
from hdb_viewer_mem.module.intraday_plot_widget import *

from hdb_viewer_mem.hdb_service.FetchData_Background_decorator import *

import time

#主界面 :包含行情快照 + 多窗口分时
class hdb_main_win(QMainWindow, Ui_HdbMainWin):
    def __init__(self, parent=None):
        super(hdb_main_win, self).__init__(parent)
        self.setupUi(self)
        self.page2_refresh_timer = None

        inimap = config_ini_key_value(keys=[], config_file=r"./config/system_config.ini")
        self.symbollist = inimap["symbols"].split(',')
        self.symbollist_showind = 0
        self.cur_refresh_pos = 0

        #安装捕获应用事件
        self.installEventFilter(self)

        # signal slot
        self.action_back.triggered.connect(self.back)
        self.action_forward.triggered.connect(self.forward)
        self.action_config.triggered.connect(self.pop_sysconfigwin)
        self.actionmulwins.triggered.connect(self.slot_actionmulwins)
        self.action_up.triggered.connect(self.slot_action_up)
        self.action_down.triggered.connect(self.slot_action_down)
        self.action_up.setVisible(False)
        self.action_down.setVisible(False)

        # stack 1
        self.snapshotTableModel = SnapshotTableModel()
        self.snapshotDelegate = SnapshotDelegate()
        self.snapshotTableView.setModel(self.snapshotTableModel)
        self.snapshotTableView.setItemDelegate(self.snapshotDelegate)
        #slot
        self.snapshotTableView.doubleClicked.connect(self.page1_tableview_doubleclicked)

        # stack 2
        self.mutiwidgets = False
        self.gridLayout_2.setContentsMargins(0,0,0,0)
        self.gridLayout_2.setSpacing(3)
        self.gridLayout_2.addWidget(IntraDayPlotWidget(),0,0)
        self.gridLayout_2.addWidget(IntraDayPlotWidget(),0,1)
        self.gridLayout_2.addWidget(IntraDayPlotWidget(),1,0)
        self.gridLayout_2.addWidget(IntraDayPlotWidget(),1,1)
        self.gridLayout_2.itemAtPosition(0, 0).widget().rightwin.hide()
        self.gridLayout_2.itemAtPosition(0, 1).widget().rightwin.hide()
        self.gridLayout_2.itemAtPosition(1, 0).widget().rightwin.hide()
        self.gridLayout_2.itemAtPosition(1, 1).widget().rightwin.hide()

        #timer
        self.page2_refresh_timer = QTimer(timeout=self.page2_UIdata_refresh, interval=500)

        #slot
        # self.snapshotTableModel.sigdatafresh.connect(self.page2_refresh_timer_start)
        self.widgetpos = [(0,0),(0,1),(1,0),(1,1)]
        self.sigproxylist = []
        for ind in range(self.gridLayout_2.count()):
            intradayplot:IntraDayPlotWidget = self.gridLayout_2.itemAtPosition(*self.widgetpos[ind]).widget()
            proxy = pg.SignalProxy(intradayplot.leftwin_mouse_move_sig, rateLimit=30, slot=self.mousemove_refresh_askbid_order_table_slot)
            self.sigproxylist.append(proxy)

        self.stackedWidget.currentChanged.connect(self.page_changed)

    def page_changed(self, page_ind):
        if 0 == page_ind:
            self.page2_refresh_timer.stop()
            self.snapshotTableModel.timer.start()
        if 1 == page_ind:
            self.page2_refresh_timer.start()
            self.snapshotTableModel.timer.stop()

    def slot_actionmulwins(self):
        self.action_up.setVisible(True)
        self.action_down.setVisible(True)
        self.mutiwidgets = True
        self.gridLayout_2.itemAtPosition(0, 0).widget().rightwin.hide()
        self.gridLayout_2.itemAtPosition(0, 1).widget().rightwin.hide()
        self.gridLayout_2.itemAtPosition(1, 0).widget().rightwin.hide()
        self.gridLayout_2.itemAtPosition(1, 1).widget().rightwin.hide()
        self.gridLayout_2.itemAtPosition(0, 1).widget().show()
        self.gridLayout_2.itemAtPosition(1, 0).widget().show()
        self.gridLayout_2.itemAtPosition(1, 1).widget().show()

        # if 1==self.stackedWidget.currentIndex():
        #     return
        logger.debug("slot_actionmulwins")
        self.stackedWidget.setCurrentIndex(1)

        # symbollist = self.snapshotTableModel.manager_list[0]
        # symbollist = symbollist['symbol'].tolist()
        for ind in range(4):
            intrplot: IntraDayPlotWidget = self.gridLayout_2.itemAtPosition(*self.widgetpos[ind]).widget()
            intrplot.leftwin.symbol_label.setText("")
            intrplot.plotbar(x=[], height=[])
            intrplot.price_line.setData(x=[], y=[])
        for ind, symbol in enumerate(self.symbollist[self.symbollist_showind:self.symbollist_showind+4]):
            if ind>=4:
                return
            # self.refresh_line_bar(ind,symbol,resetxrange=True)
            # self.refresh_line_bar_shareFile(ind,symbol,resetxrange=True)
            intrplot: IntraDayPlotWidget = self.gridLayout_2.itemAtPosition(*self.widgetpos[ind]).widget()
            intrplot.leftwin.symbol_label.setText(symbol)

    def slot_action_up(self):
        if 0 == self.symbollist_showind:
            return
        self.symbollist_showind -= 4
        self.slot_actionmulwins()
        pass

    def slot_action_down(self):
        if len(self.symbollist) - self.symbollist_showind <=4:
            return
        self.symbollist_showind += 4
        self.slot_actionmulwins()
        pass

    def refresh_askbid_order_table(self,symbol,ind=0):
        intrplot: IntraDayPlotWidget = self.gridLayout_2.itemAtPosition(*self.widgetpos[ind]).widget()
        # symbol = intrplot.rightwin.symbol_label.text()
        #
        if symbol not in self.snapshotTableModel.manager_dic_SecurityTick.keys():
            return

        # 获取快照数据
        data: pd.DataFrame = self.snapshotTableModel.manager_dic_SecurityTick[symbol]
        # data = data[data['time']>=93000000]  #开盘前数据去掉
        if len(data) < 1:
            return
        # data = data.reset_index(drop=True)
        pre_close = data['pre_close'][0]/10000
        intrplot.set_time_labels((data['time'].apply(lambda x:int(x/1000))).tolist())

        x = list(range(data.shape[0]))
        y_volume = data['volume'] - data['volume'].shift(axis=0, fill_value=0)
        y_price = (data['match'] / 10000).tolist()
        intrplot.set_ReturnAxis_benchmark_prcie(pre_close)
        intrplot.price_line.setData(x=x, y=y_price)
        intrplot.plotbar(x=x, height=y_volume.tolist(), color=QColor(0, 204, 0, 128))

        # 获取askbid快照数据
        ask_price = (data["ask_price"].values[-1]/10000).tolist()
        ask_vol = data["ask_vol"].values[-1].tolist()
        bid_price = (data["bid_price"].values[-1]/10000).tolist()
        bid_vol = data["bid_vol"].values[-1].tolist()
        intrplot.set_askbid_data(ask_price,ask_vol,bid_price,bid_vol)

        # 获取 trade快照数据
        if symbol[:2] == 'SH':
            data_order: pd.DataFrame = self.snapshotTableModel.manager_dic_SHSetpTrade[symbol]
            data_order = data_order[['trade_time', 'trade_price', 'trade_qty', 'bs_flag']]
            # data_order = data_order[
            #     (data_order['trade_time'] >= 93000000) & (data_order['trade_time'] <= data['time'].values[-1])]
            data_order.loc[:, 'trade_price'] = data_order['trade_price'].apply(lambda x: x / 10000)
            data_order.loc[:, 'trade_time'] = data_order['trade_time'].apply(lambda x: int(x / 1000))
            data_order.loc[:, 'bs_flag'] = data_order['bs_flag'].map({66: 'B', 83: 'S'})
            # data_order = data_order.reset_index(drop=True)
        elif symbol[:2] == 'SZ':
            data_order: pd.DataFrame = self.snapshotTableModel.manager_dic_SZSetpTrade[symbol]
            data_order = data_order[['transact_time', 'last_px', 'last_qty', 'exec_type']]
        else:
            return

        intrplot.set_order_data(data_order)
        pass

    def refresh_line_bar(self,ind,symbol,resetxrange=False):
        if symbol not in self.snapshotTableModel.manager_dic_SecurityTick.keys():
            return
        data: pd.DataFrame = self.snapshotTableModel.manager_dic_SecurityTick[symbol]
        # data = data[data['time'] >= 93000000]  # 开盘前数据去掉
        if len(data) < 1:
            return
        # data = data.reset_index(drop=True)
        pre_close = data['pre_close'][0] / 10000
        intrplot:IntraDayPlotWidget = self.gridLayout_2.itemAtPosition(*self.widgetpos[ind]).widget()
        intrplot.rightwin.symbol_label.setText(symbol)
        timelables = (data['time'].apply(lambda x: int(x / 1000))).tolist()
        intrplot.set_time_labels(timelables)

        x = list(range(data.shape[0]))
        y_volume = data['volume'] - data['volume'].shift(axis=0, fill_value=0)
        y_price = (data['match'] / 10000).tolist()
        intrplot.set_ReturnAxis_benchmark_prcie(pre_close)
        intrplot.price_line.setData(x=x, y=y_price)
        intrplot.plotbar(x=x, height=y_volume.tolist(), color=QColor(0, 204, 0, 128))

        #设置plot的x活动范围限制
        today = time.strftime("%Y%m%d")
        startstramp = time.mktime(time.strptime(today+" 093000","%Y%m%d %H%M%S"))
        currenttime = " {:0>6d}".format(timelables[-1])
        endstramp = time.mktime(time.strptime(today+currenttime,"%Y%m%d %H%M%S"))

        timeinterval = endstramp - startstramp
        timeinterval = timeinterval if timeinterval<=2*60*60 else timeinterval-1.5*60*60 #去除中午休市
        xMax = int(4*60*60/timeinterval*len(timelables))
        intrplot.setLimits(0,xMax)

        if resetxrange:
            intrplot.setXRange(0,xMax)

    def refresh_line_bar_shareFile(self,ind,symbol,resetxrange=False):
        self.fetchData_refresh_line_bar = FetchData_Background_decorator(refresh_line_bar_shareFile,symbol)
        self.fetchData_refresh_line_bar.sigDataReturn.connect(lambda r:self.refresh_line_bar_shareFile_slot(ind,symbol,r,resetxrange))

    def refresh_line_bar_shareFile_slot(self,ind,symbol,r,resetxrange=False):
        try:
            pre_close, timelables, x, y_volume, y_price, xMax = r[0]

            intrplot:IntraDayPlotWidget = self.gridLayout_2.itemAtPosition(*self.widgetpos[ind]).widget()
            intrplot.rightwin.symbol_label.setText(symbol)
            intrplot.set_time_labels(timelables)

            intrplot.set_ReturnAxis_benchmark_prcie(pre_close)
            intrplot.price_line.setData(x=x, y=y_price)
            intrplot.plotbar(x=x, height=y_volume.tolist(), color=QColor(0, 204, 0, 128))

            #设置plot的x活动范围限制
            intrplot.setLimits(0,xMax)

            # if resetxrange:
            #     intrplot.setXRange(0,xMax)
            intrplot.setXRange(0,xMax)
        except Exception as e:
            logger.debug("refresh_line_bar_shareFile_slot")
            logger.debug(e)

    # def mousemove_refresh_askbid_order_table_slot(self,intradayplot:IntraDayPlotWidget,ind):
    def mousemove_refresh_askbid_order_table_slot(self,*args):
        intradayplot, ind = args[0][0]
        if self.mutiwidgets:
            return
        symbol = intradayplot.rightwin.symbol_label.text()
        if symbol not in self.snapshotTableModel.manager_dic_SecurityTick.keys():
            return
        #获取 askbid快照数据
        data: pd.DataFrame = self.snapshotTableModel.manager_dic_SecurityTick[symbol]
        # data = data[data['time'] >= 93000000]  # 开盘前数据去掉
        if len(data) < 1 or ind>(len(data)-1) or ind<0:
            return
        # data = data.reset_index(drop=True)

        ask_price = (data["ask_price"][ind]/10000).tolist()
        ask_vol = data["ask_vol"][ind].tolist()
        bid_price = (data["bid_price"][ind]/10000).tolist()
        bid_vol = data["bid_vol"][ind].tolist()
        intradayplot.set_askbid_data(ask_price,ask_vol,bid_price,bid_vol)

        #获取 trade快照数据
        if symbol[:2] == 'SH':
            data_order: pd.DataFrame = self.snapshotTableModel.manager_dic_SHSetpTrade[symbol]
            data_order = data_order[['trade_time', 'trade_price', 'trade_qty', 'bs_flag']]
            # data_order = data_order[(data_order['trade_time']>=93000000) & (data_order['trade_time']<=data['time'][ind])]
            # data_order.loc[:, 'trade_price'] = data_order['trade_price'].apply(lambda x:x/10000)
            # data_order.loc[:, 'trade_time'] = data_order['trade_time'].apply(lambda x: int(x / 1000))
            # data_order.loc[:, 'bs_flag'] = data_order['bs_flag'].map({66: 'B', 83: 'S'})
            # data_order = data_order.reset_index(drop=True)
        elif symbol[:2] == 'SZ':
            data_order: pd.DataFrame = self.snapshotTableModel.manager_dic_SZSetpTrade[symbol]
            data_order = data_order[['transact_time', 'last_px', 'last_qty', 'exec_type']]
        else:
            return

        intradayplot.set_order_data(data_order)

    def eventFilter(self, objwatched, event):
        if(hasattr(event, "pos") ):
            viewpos = self.snapshotTableView.mapFrom(self,event.pos())
            if(self.snapshotTableView.horizontalHeader().geometry().contains(viewpos)):
                if QEvent.ContextMenu == event.type():
                    # 处理右键菜单: 定制表头
                    logger.debug("ContextMenu Proceing %s %s",event.pos(), viewpos)
                    self.action_header_config = QAction(u'表头配置', self)
                    self.action_header_config.triggered.connect(self.pop_headerConfigWin)
                    self.pop_menu = QMenu(self)
                    self.pop_menu.addAction(self.action_header_config)
                    self.pop_menu.popup(QCursor.pos())
                pass
        return super().eventFilter(objwatched, event)

    def page1_tableview_doubleclicked(self,modelIndex:QModelIndex):
        self.mutiwidgets = False
        symbol = modelIndex.sibling(modelIndex.row(),0).data()

        #页面跳转
        self.stackedWidget.setCurrentIndex(1)

        #页面多窗口显示设置
        self.gridLayout_2.itemAtPosition(0, 0).widget().rightwin.show()
        self.gridLayout_2.itemAtPosition(0, 1).widget().hide()
        self.gridLayout_2.itemAtPosition(1, 0).widget().hide()
        self.gridLayout_2.itemAtPosition(1, 1).widget().hide()

        #page2 数据设置
        #PlotWidget 设置label数据
        intrplot:IntraDayPlotWidget = self.gridLayout_2.itemAtPosition(0, 0).widget()
        intrplot.set_symbolname(symbol)

        # self.page2_UIdata_refresh(resetxrange=True)
        pass

    def page2_UIdata_refresh(self,resetxrange=False):
        logger.debug("page2_UIdata_refresh ...")
        if self.stackedWidget.currentIndex() != 1:
            return
        ind = self.cur_refresh_pos
        symbol = self.symbollist[self.symbollist_showind+ind]
        self.refresh_line_bar_shareFile(ind, symbol, resetxrange=resetxrange)
        if 0 == ind and not self.mutiwidgets:
            self.refresh_askbid_order_table(symbol)
        intrplot: IntraDayPlotWidget = self.gridLayout_2.itemAtPosition(*self.widgetpos[ind]).widget()
        intrplot.leftwin.symbol_label.setText(symbol)
        intrplot.rightwin.symbol_label.setText(symbol)
        self.cur_refresh_pos +=1
        self.cur_refresh_pos = self.cur_refresh_pos%4

        # for ind, symbol in enumerate(self.symbollist[self.symbollist_showind:self.symbollist_showind+4]):
        #     # self.refresh_line_bar(ind,symbol,resetxrange=resetxrange)
        #     self.refresh_line_bar_shareFile(ind,symbol,resetxrange=resetxrange)
        #     if 0 == ind and not self.mutiwidgets:
        #         self.refresh_askbid_order_table(symbol)
        #     intrplot: IntraDayPlotWidget = self.gridLayout_2.itemAtPosition(*self.widgetpos[ind]).widget()
        #     intrplot.leftwin.symbol_label.setText(symbol)
        #     intrplot.rightwin.symbol_label.setText(symbol)

            # time.sleep(0.1)
        pass

    def back(self):
        totalpages = self.stackedWidget.count()
        curIndex = self.stackedWidget.currentIndex()
        if (curIndex - 1) % totalpages == 0:
            self.action_up.setVisible(False)
            self.action_down.setVisible(False)
        if (curIndex - 1) % totalpages == 1:
            self.action_up.setVisible(True)
            self.action_down.setVisible(True)
        self.stackedWidget.setCurrentIndex((curIndex + 1) % totalpages)
        self.show_page2()

    def forward(self):
        totalpages = self.stackedWidget.count()
        curIndex = self.stackedWidget.currentIndex()
        if (curIndex - 1) % totalpages == 0:
            self.action_up.setVisible(False)
            self.action_down.setVisible(False)
        if (curIndex - 1) % totalpages == 1:
            self.action_up.setVisible(True)
            self.action_down.setVisible(True)
        self.stackedWidget.setCurrentIndex((curIndex - 1) % totalpages)
        self.show_page2()

    def show_page2(self):
        if self.stackedWidget.currentIndex() == 1:
            logger.debug("itemAtPosition(0,1).hide()")
            # self.gridLayout_2.itemAtPosition(0,1).widget().hide()
            pass

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

        configfile_path = r"./config/system_config.ini"
        initmap = config_ini_key_value(keys=[], config_file=configfile_path)
        self.headerConfigWin = HeaderConfigSnapshotTable(headerNames=initmap['header_show'].split(","), headerNames_hide=initmap['header_hide'].split(","))
        self.headerConfigWin.show()

