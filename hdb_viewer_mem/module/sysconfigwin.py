import os
from PyQt5.Qt import *
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog
from hdb_viewer_mem.viewer.sysconfig_ui import *
from hdb_viewer_mem.util.utility import *


class sysconfigwin(QWidget, Ui_sysconfig_Form):
    def __init__(self, parent=None):
        super(sysconfigwin, self).__init__(parent)
        self.setupUi(self)

        self.resize(400,200)

        config_path = r"./config"
        # config_path = r"../../config"
        self.path = config_path + "/system_config.ini"
        self.initmap = config_ini_key_value(keys=[],config_file=self.path)

        self.lineEdits = {'his_svr_addr':self.lineEdit_svr_addr,
                          'his_srv_port':self.lineEdit_srv_port,
                          'his_user':self.lineEdit_user ,
                          'his_pwd':self.lineEdit_pwd,
                          }

        self.pushButton_OK.clicked.connect(self.save)
        self.pushButton_Cancel.clicked.connect(lambda x: self.close())

        for k in self.lineEdits.keys():
            self.lineEdits[k].setText(self.initmap[k])
            self.lineEdits[k].textChanged.connect(lambda x: self.pushButton_OK.setEnabled(True))
            self.lineEdits[k].textChanged.connect(lambda x: self.pushButton_Cancel.setEnabled(True))

    def select_folder_path(self,lineEdit):
        path = lineEdit.text()
        isabspath = os.path.isabs(path)
        if not isabspath:
            path = os.path.abspath(path)
        path_select_dialog = QtWidgets.QFileDialog()
        select_path = path_select_dialog.getExistingDirectory(caption='请选择', directory=path)
        if len(select_path) > 0:
            if not isabspath:
                select_path = os.path.relpath(select_path)
                if not select_path.startswith('.'):
                    select_path = "./"+select_path
            lineEdit.setText(select_path)

    def select_file_path(self,lineEdit):
        abspath = os.path.abspath(lineEdit.text())
        path_select_dialog = QtWidgets.QFileDialog()
        select_path = path_select_dialog.getOpenFileName(caption='请选择', directory=abspath)
        if len(select_path[0]) > 0:
            lineEdit.setText(select_path[0])

    def save(self):
        for k in self.lineEdits.keys():
            self.initmap[k] = self.lineEdits[k].text()
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                for k in self.initmap.keys():
                    f.write("{}={}\n".format(k,self.initmap[k]))
        except FileNotFoundError:
            raise FileNotFoundError
        self.pushButton_OK.setEnabled(False)
        self.pushButton_Cancel.setEnabled(False)
        self.close()


if __name__ == '__main__':
    app = QApplication([])
    win = sysconfigwin()
    win.show()
    app.exec_()