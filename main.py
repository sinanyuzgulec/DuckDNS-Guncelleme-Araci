import sys
import os
import json
import platform
import threading
import requests
import psutil
from datetime import datetime

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from pystray import Icon, Menu, MenuItem
from PIL import Image

SETTINGS_FILE = "settings.json"

class SingleInstanceChecker(QtCore.QObject):
    def __init__(self, key):
        super().__init__()
        self.key = key
        self.is_running = False
        self.server = None
        self.check_instance()

    def check_instance(self):
        socket = QLocalSocket()
        socket.connectToServer(self.key)
        if socket.waitForConnected(500):  # 500 ms
            self.is_running = True
            socket.disconnectFromServer()
        else:
            self.server = QLocalServer()
            try:
                QLocalServer.removeServer(self.key)
            except Exception:
                pass
            self.server.listen(self.key)
            self.is_running = False

class SettingsPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.domain_edit = QtWidgets.QLineEdit()
        self.token_edit = QtWidgets.QLineEdit()
        self.save_button = QtWidgets.QPushButton("Kaydet")

        layout = QtWidgets.QFormLayout()
        layout.addRow("Domain:", self.domain_edit)
        layout.addRow("Token:", self.token_edit)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

        self.save_button.clicked.connect(self.save_settings)

    def load_settings(self, config):
        self.domain_edit.setText(config.get("domain", ""))
        self.token_edit.setText(config.get("token", ""))

    def save_settings(self):
        domain = self.domain_edit.text().strip()
        token = self.token_edit.text().strip()
        if not domain or not token:
            QtWidgets.QMessageBox.warning(self, "Uyarı", "Domain ve token boş olamaz!")
            return
        parent = self.window()
        if hasattr(parent, 'config'):
            parent.config['domain'] = domain
            parent.config['token'] = token
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(parent.config, f, indent=4, ensure_ascii=False)
            parent.log("Ayarlar kaydedildi.", success=True)
            QtWidgets.QMessageBox.information(self, "Başarılı", "Ayarlar kaydedildi.")
        else:
            QtWidgets.QMessageBox.critical(self, "Hata", "Ana pencere bulunamadı!")

class DuckDNSUpdater(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("pyDuckTimer - DuckDNS Updater")
        self.setGeometry(300, 300, 480, 260)

        self.load_config()

        self.tabs = QtWidgets.QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.main_widget = QtWidgets.QWidget()
        self.tabs.addTab(self.main_widget, "Ana Sayfa")

        self.settings_page = SettingsPage(self)
        self.tabs.addTab(self.settings_page, "Ayarlar")
        self.settings_page.load_settings(self.config)

        self.main_layout = QtWidgets.QGridLayout()
        self.main_widget.setLayout(self.main_layout)

        self.clock_label = QtWidgets.QLabel()
        self.main_layout.addWidget(self.clock_label, 0, 0)

        self.last_update_label = QtWidgets.QLabel("Son Güncelleme: Henüz yapılmadı")
        self.main_layout.addWidget(self.last_update_label, 1, 0)

        self.interface_label = QtWidgets.QLabel("Ağ Arayüzü: Tespit ediliyor...")
        self.main_layout.addWidget(self.interface_label, 2, 0)

        self.manual_update_button = QtWidgets.QPushButton("Manuel Güncelle")
        self.main_layout.addWidget(self.manual_update_button, 3, 0)
        self.manual_update_button.clicked.connect(self.update_duckdns)

        self.exe_button = QtWidgets.QPushButton("Windows için .exe oluştur")
        self.main_layout.addWidget(self.exe_button, 4, 0)
        self.exe_button.clicked.connect(self.build_exe)

        if platform.system() != "Windows" or getattr(sys, 'frozen', False):
            self.exe_button.hide()

        self.log_box = QtWidgets.QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background-color: #f0f0f0;")
        self.log_box.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.main_layout.addWidget(self.log_box, 0, 1, 6, 1)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_duckdns)
        self.update_timer.start(60 * 60 * 1000)

        self.get_active_interface()
        self.update_duckdns()

        self.tray_icon = None
        self.tray_thread = None
        self.tray_icon_setup()

    def load_config(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {"domain": "", "token": ""}
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)

    def update_clock(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.setText(f"Saat: {now}")

    def get_active_interface(self):
        interfaces = psutil.net_if_stats()
        active = [name for name, stat in interfaces.items() if stat.isup and not name.startswith("lo")]
        name = active[0] if active else "Bulunamadı"
        self.interface_label.setText(f"Ağ Arayüzü: {name}")

    def update_duckdns(self):
        domain = self.config.get("domain")
        token = self.config.get("token")
        if not domain or not token:
            msg = "Hatalı domain/token"
            self.log(msg, success=False)
            # Güncelleme zamanı değişmesin
            return

        url = f"https://www.duckdns.org/update?domains={domain}&token={token}&ip="
        try:
            response = requests.get(url, timeout=10)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if response.text.strip() == "OK":
                msg = "Güncelleme başarılı: OK"
                self.last_update_label.setText("Son Güncelleme: " + now)
                self.log(msg, success=True)
            else:
                msg = f"Güncelleme hatalı: {response.text}"
                self.log(msg, success=False)
                # Hatalıysa zaman değişmesin
        except Exception as e:
            err = f"Hata: {str(e)}"
            self.log(err, success=False)
            # Hatalıysa zaman değişmesin

    def log(self, message, success=True):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = "green" if success else "red"
        # HTML olarak ekle, yeni satır ile
        self.log_box.insertHtml(f'<span style="color:{color};">[{timestamp}] {message}</span><br>')
        self.log_box.ensureCursorVisible()

    def tray_icon_setup(self):
        icon_path = os.path.join(os.path.dirname(__file__), "tray_icon.png")
        if not os.path.exists(icon_path):
            print("Uyarı: tray_icon.png bulunamadı, tray simgesi yüklenemedi.")
            return

        image = Image.open(icon_path)

        def on_clicked(icon, item):
            QtCore.QMetaObject.invokeMethod(self, "toggle_visibility", QtCore.Qt.QueuedConnection)

        def quit_app(icon, item):
            icon.stop()
            QtWidgets.qApp.quit()

        self.tray_icon = Icon("duckdns", image, "DuckDNS", menu=Menu(
            MenuItem("Göster / Gizle", on_clicked),
            MenuItem("Çık", quit_app)
        ))

        def run_tray():
            self.tray_icon.run()

        self.tray_thread = threading.Thread(target=run_tray, daemon=True)
        self.tray_thread.start()

    @QtCore.pyqtSlot()
    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()
            self.raise_()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.WindowStateChange:
            if self.isMinimized():
                QtCore.QTimer.singleShot(0, self.hide)
                self.log("Pencere minimize edildi, gizlendi.", success=True)
        super().changeEvent(event)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.log("Uygulama gizlendi. Sistem tepsisinde çalışmaya devam ediyor.", success=True)

    def build_exe(self):
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            subprocess.check_call(["pyinstaller", "--onefile", "--noconsole", os.path.basename(__file__)])
            QtWidgets.QMessageBox.information(self, "Başarılı", "EXE oluşturuldu: dist klasörüne bak.")
            self.exe_button.hide()
            self.log("EXE oluşturuldu ve buton gizlendi.", success=True)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Hata", str(e))
            self.log(f"EXE oluşturma hatası: {str(e)}", success=False)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    single_checker = SingleInstanceChecker("DuckDNSUpdaterUniqueKey1234")

    if single_checker.is_running:
        QtWidgets.QMessageBox.warning(None, "Uygulama Zaten Açık",
                                      "Bu uygulama zaten çalışıyor!")
        sys.exit(0)

    win = DuckDNSUpdater()
    win.show()
    sys.exit(app.exec_())
