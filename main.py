import os
import sys

from PyQt6.QtWidgets import QApplication

from modules.database import init_database
from ui.main_window import MainWindow


def ensure_project_folders():
    """Tạo sẵn các thư mục dữ liệu để chạy trên máy mới không bị lỗi."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    folders = [
        os.path.join(base_dir, "database"),
        os.path.join(base_dir, "dataset", "students"),
        os.path.join(base_dir, "models"),
    ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)


def main():
    ensure_project_folders()
    init_database()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
