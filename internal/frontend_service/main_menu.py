import sys
from PyQt5.QtWidgets import QApplication
from viewers.main_menu_viewer import MainMenu

if __name__ == "__main__":
    app = QApplication(sys.argv)
    menu = MainMenu()
    menu.show()
    sys.exit(app.exec_())