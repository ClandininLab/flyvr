import sys
from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5 import uic

def myfunc():
    print('yo')

app = QApplication(sys.argv)
ui = uic.loadUi('main.ui')
ui.pushButton.clicked.connect(myfunc)
ui.show()
sys.exit(app.exec_())
