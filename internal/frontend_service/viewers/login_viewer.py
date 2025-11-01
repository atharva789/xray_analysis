from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)
import requests

from utils.api_client import ApiClient, ApiClientError


class LoginWindow(QWidget):
    """Simple login window that authenticates the user via the API."""

    login_successful = pyqtSignal()

    def __init__(self, api_client: ApiClient):
        super().__init__()
        self.api_client = api_client

        self.setWindowTitle("CT DICOM Viewer - Login")
        self.setFixedSize(320, 220)

        layout = QVBoxLayout()

        self.status_label = QLabel("Enter your credentials")
        layout.addWidget(self.status_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        layout.addWidget(self.email_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.attempt_login)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    # ------------------------------------------------------------------
    def attempt_login(self) -> None:
        email = self.email_input.text().strip()
        password = self.password_input.text()

        if not email or not password:
            QMessageBox.warning(self, "Missing information", "Email and password are required.")
            return

        self.login_button.setEnabled(False)
        self.status_label.setText("Authenticating...")
        try:
            self.api_client.login(email, password)
        except requests.HTTPError as exc:
            self.status_label.setText("Enter your credentials")
            QMessageBox.critical(self, "Login failed", f"Authentication failed: {exc.response.text}")
            self.login_button.setEnabled(True)
            return
        except ApiClientError as exc:
            self.status_label.setText("Enter your credentials")
            QMessageBox.critical(self, "Login failed", str(exc))
            self.login_button.setEnabled(True)
            return
        except requests.RequestException as exc:
            self.status_label.setText("Enter your credentials")
            QMessageBox.critical(self, "Login failed", f"Network error: {exc}")
            self.login_button.setEnabled(True)
            return

        self.status_label.setText("Login successful")
        self.login_successful.emit()
        self.hide()
