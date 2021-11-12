
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

#行情快照 delegate渲染部分,
# 数据渲染功能: 涨跌颜色不同,以及背景变色
class SnapshotDelegate(QAbstractItemDelegate):
    """Delegate"""
    def __init__(self):
        super(SnapshotDelegate, self).__init__()

    def paint(self, painter, option, index):
        """绘制单元格。"""
        if index.column() == 0:
            # :表格第一列是ID，单元格中绘制一个图片和ID。
            p = QStyleOptionViewItem()
            p.index = index
            p.rect = option.rect
            p.features = QStyleOptionViewItem.HasDecoration | QStyleOptionViewItem.HasDisplay
            p.text = str(index.data())
            p.decorationSize = QSize(44, 44)      # 设置装饰图标的大小。
            p.icon = QIcon('../image/id.png')     # 设置装饰图标路径名
            p.state = option.state
            p.showDecorationSelected = True     # 开启选中时，单元格高亮显示
            # :若项目被选择，则高亮绘制其矩形

            p.decorationPosition = QStyleOptionViewItem.Left        # 图片在文字的左边
            p.displayAlignment = Qt.AlignLeft | Qt.AlignCenter      # 设置文字的位置
            QApplication.style().drawControl(QStyle.CE_ItemViewItem, p, painter)
        else:
            # :向表格中渲染数据，如果缺少下面代码，表格中数据不能正常显示。
            # :这里应该在model的data函数之后调用，此时通过index可以获取要显示。
            # :的数据。
            p = QStyleOptionViewItem()
            p.features = QStyleOptionViewItem.HasDisplay
            p.index = index                     # 表格QModelIndex索引
            p.rect = option.rect
            p.state = option.state

            p.showDecorationSelected = True     # 开启选中时，单元格高亮显示
            p.text = str(index.data())          # 表格中的数据
            QApplication.style().drawControl(QStyle.CE_ItemViewItem, p, painter)

    def createEditor(self, parent, option, index):
        """给单元格创建编辑器(点击单元格的时候调用)"""
        if index.column() == 2:
            # :第2列性别设置为lineEdite编辑器。
            # :注意，在创建编辑控件的时候传入parent防止在编辑时新弹出窗口来进行编辑。
            p = QLineEdit(parent)
            p.setFocusPolicy(Qt.TabFocus)
            # :设置控件的位置，如果忽略此句，控件会出现在窗体的左上角。
            p.setGeometry(option.rect)
            return p
        elif index.column() == 3:
            # :第3列年龄设置为spinBox编辑器。
            p = QSpinBox(parent)
            p.setMaximum(150)       # 年龄最大值为150
            p.setGeometry(option.rect)
            return p
        else:
            return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        """把model中的数据填充到编辑器当中(点击单元格的时候调用但晚于createEditor)"""
        if index.column() == 2:
            # :lineEdit编辑器。
            editor.setText(index.data())
        elif index.column() == 3:
            editor.setValue(int(index.data()))
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        """把编辑器中的数据填充到model当中(编辑完成时调用)"""
        if index.column() == 2:
            model.setData(index, editor.text(), role=Qt.EditRole)
        elif index.column() == 3:
            model.setData(index, editor.value(), role=Qt.EditRole)
        else:
            super().setModelData(editor, model, index)
