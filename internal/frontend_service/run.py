import sys

from PyQt5.QtWidgets import QApplication

from utils.api_client import ApiClient
from viewers.login_viewer import LoginWindow
from viewers.main_menu_viewer import MainMenu


def main() -> int:
    app = QApplication(sys.argv)

    api_client = ApiClient()
    login_window = LoginWindow(api_client)
    main_window_holder = {"window": None}

    def handle_login_success() -> None:
        main_menu = MainMenu(api_client)
        main_window_holder["window"] = main_menu
        main_menu.show()

    login_window.login_successful.connect(handle_login_success)
    login_window.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
