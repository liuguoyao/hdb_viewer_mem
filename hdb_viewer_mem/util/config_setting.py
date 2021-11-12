import sys

# from viewer.hdb_viewer import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from hdb_viewer.viewer.config_setting_ui import *
from hdb_viewer.config.hdb_config import *
from hdb_viewer.viewer_module.hdb_fileoper import FileOperationService


class HdbConfigPage(QDialog, Ui_ConfigPage):
    updateTreeSignal = pyqtSignal(str)
    modeSignal = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(HdbConfigPage, self).__init__(parent)
        self.setupUi(self)
        self.setWindowModality(Qt.ApplicationModal)
        # self.setWindowModality(Qt.NonModal)
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.setWindowTitle("network_config")
        self.edt_pswd.setEchoMode(QtWidgets.QLineEdit.Password)
        self.textBrowser.setFontPointSize(15)
        self.closing = False
        self.cons = None
        self.on_custom()

    def get_main_ui(self, mainui):
        self.main_ui = mainui

    # custom design
    def on_custom(self):
        self.pushButton.clicked.connect(self.open_dir_slot)
        self.chooseButton.clicked.connect(self.choose_dir_slot)
        self.button_box.clicked.connect(self.on_button_click)
        self.tool_btn_load.clicked.connect(self.on_user_load_config)
        self.tool_btn_load.setHidden(True) #load btn隐藏,

        # ip rule
        ip_rx = QRegExp("((2[0-4]\\d|25[0-5]|[01]?\\d\\d?)\\.){3}(2[0-4]\\d|25[0-4]|[01]?\\d\\d?)")
        ip_reg = QRegExpValidator(ip_rx, self)
        self.edt_ip.setValidator(ip_reg)

        # port rule
        port_rx = QRegExp('[0-9]|[1-9]\d|[1-9]\d{2}|[1-9]\d{3}|[1-5]\d{4}' \
                          '|6[0-4]\d{3}|65[0-4]\d{2}|655[0-2]\d|6553[0-5]')
        port_reg = QRegExpValidator(port_rx, self)
        self.edt_port.setValidator(port_reg)

        # tab sequence
        self.setTabOrder(self.edt_ip, self.edt_port)
        self.setTabOrder(self.edt_port, self.edt_user)
        self.setTabOrder(self.edt_user, self.edt_pswd)
        self.config_to_load()

    # Manual load
    def on_user_load_config(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setFilter(QDir.Files)
        file_dialog.setDirectory(".")
        file_dialog.setNameFilter("*.ini, *.xml")
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()
            self.cons = ini_read_config(file_path[0])
            self.config_to_load()

    # close db
    def close_dialog(self):
        self.closing = True
        self.cons = None
        self.close()

    # config write
    def config_to_write(self, ip, port, user, psw):
        self.cons_set(NETWORK_IP, ip)
        self.cons_set(NETWORK_PORT, port)
        self.cons_set(NETWORK_USER, user)
        self.cons_set(NETWORK_PSWD, psw)

        with open(CONFIG_FILE_PATH, "w+") as update_file:
            self.cons.write(update_file)

    # conifg load
    def config_to_load(self):
        if self.cons is None:
            self.cons = ini_read_config()
            if self.cons is None:
                return

        if not self.cons.has_section(NETWORK_SECTION):
            print("please check config file")
            return

        self.edt_ip.setText(self.cons_get(NETWORK_IP))
        self.edt_port.setText(self.cons_get(NETWORK_PORT))
        self.edt_user.setText(self.cons_get(NETWORK_USER))
        self.edt_pswd.setText(self.cons_get(NETWORK_PSWD))
        self.textBrowser.setText(self.cons_get(NETWORK_LOCAL_DB_PATH))

    def cons_get(self, value, section=NETWORK_SECTION):
        return self.cons.get(section, value)

    def cons_set(self, option, value, section=NETWORK_SECTION):
        self.cons.set(section, option, value)

    def choose_dir_slot(self):
        open_dir_dialog = FileOperationService(self.main_ui)
        dir_path = open_dir_dialog.get_file_dir()
        if dir_path == "":
            self.raise_()
            return
        self.cons_set(NETWORK_LOCAL_DB_PATH, dir_path)
        with open(CONFIG_FILE_PATH, "w+") as update_file:
            self.cons.write(update_file)
        self.textBrowser.setText(dir_path)
        self.updateTreeSignal.emit(dir_path)
        self.close_dialog()

    def open_dir_slot(self):
        text = str(self.textBrowser.toPlainText())
        if text == "":
            return
        else:
            self.updateTreeSignal.emit(text)
            self.close_dialog()

    # button_box
    def on_button_click(self, button):
        # write config
        if button == self.button_box.button(0x00000400):  # OK
            self.config_to_write(self.edt_ip.text(), self.edt_port.text(),
                                 self.edt_user.text(), self.edt_pswd.text())
            self.modeSignal.emit(True)
            self.close_dialog()
        elif button == self.button_box.button(0x00400000):  # Cancel
            self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = HdbConfigPage()
    win.show()
    win.config_to_load()
    sys.exit(app.exec())
