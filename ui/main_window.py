from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.attendance_page import AttendancePage
from ui.history_page import HistoryPage
from ui.home_page import HomePage
from ui.register_face_page import RegisterFacePage
from ui.section_page import SectionPage
from ui.student_page import StudentPage
from ui.train_page import TrainPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Attendance Desktop")
        self.resize(1180, 720)
        self.setup_ui()

    def setup_ui(self):
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(16)

        app_title = QLabel("Face Attendance\nDesktop")
        app_title.setObjectName("appTitle")
        app_title.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.menu = QListWidget()
        self.menu.setObjectName("sidebarMenu")
        menu_names = [
            "Trang chủ",
            "Quản lý sinh viên",
            "Đăng ký khuôn mặt",
            "Huấn luyện model",
            "Môn học / Lớp học phần",
            "Điểm danh webcam",
            "Lịch sử điểm danh",
        ]
        for name in menu_names:
            self.menu.addItem(QListWidgetItem(name))

        sidebar_layout.addWidget(app_title)
        sidebar_layout.addWidget(self.menu)

        self.stack = QStackedWidget()
        self.home_page = HomePage()
        self.student_page = StudentPage()
        self.register_face_page = RegisterFacePage()
        self.train_page = TrainPage()
        self.section_page = SectionPage()
        self.attendance_page = AttendancePage()
        self.history_page = HistoryPage()

        for page in [
            self.home_page,
            self.student_page,
            self.register_face_page,
            self.train_page,
            self.section_page,
            self.attendance_page,
            self.history_page,
        ]:
            self.stack.addWidget(page)

        self.menu.currentRowChanged.connect(self.change_page)
        self.menu.setCurrentRow(0)

        root_layout.addWidget(sidebar, 0)
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.apply_style()

    def change_page(self, index):
        # Tắt webcam khi chuyển trang để tránh khóa camera.
        if self.stack.currentWidget() == self.register_face_page:
            self.register_face_page.release_camera()
        if self.stack.currentWidget() == self.attendance_page:
            self.attendance_page.release_camera()

        if index == 0:
            self.home_page.load_dashboard_data()
        if index == 2:
            self.register_face_page.load_students()
        if index == 4:
            self.section_page.load_data()
        if index == 5:
            self.attendance_page.load_sections()
            self.attendance_page.reload_model(silent=True)
        if index == 6:
            self.history_page.load_history()

        self.stack.setCurrentIndex(index)

    def closeEvent(self, event):
        self.register_face_page.release_camera()
        self.attendance_page.release_camera()
        event.accept()

    def apply_style(self):
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #f5f7fb;
                color: #1f2937;
                font-family: Segoe UI, Arial;
                font-size: 14px;
            }
            #sidebar {
                background: #172033;
                min-width: 230px;
                max-width: 230px;
            }
            #appTitle {
                color: white;
                font-size: 22px;
                font-weight: 700;
                padding: 8px;
            }
            #sidebarMenu {
                background: transparent;
                border: none;
                color: #d7deea;
                outline: none;
            }
            #sidebarMenu::item {
                padding: 12px 10px;
                border-radius: 8px;
                margin: 3px 0;
            }
            #sidebarMenu::item:selected {
                background: #2f6fed;
                color: white;
            }
            #pageTitle {
                font-size: 28px;
                font-weight: 700;
                color: #111827;
            }
            #cardTitle {
                background: transparent;
                border: none;
                color: #64748b;
                font-size: 14px;
                font-weight: 700;
            }
            #cardValue {
                background: transparent;
                border: none;
                color: #111827;
                font-size: 36px;
                font-weight: 800;
            }
            #cardNote {
                background: transparent;
                border: none;
                color: #64748b;
                font-size: 13px;
            }
            #mutedText {
                color: #5b6472;
            }
            #infoBox {
                background: #eaf1ff;
                border: 1px solid #c8d8ff;
                border-radius: 8px;
                padding: 14px;
                color: #17315f;
            }
            #cameraBox {
                background: #111827;
                color: #d1d5db;
                border-radius: 8px;
                border: 2px solid #273244;
            }
            QPushButton {
                background: #2f6fed;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #255dcc;
            }
            QLineEdit, QComboBox, QDateEdit {
                background: white;
                border: 1px solid #ccd4e0;
                border-radius: 8px;
                padding: 8px;
            }
            QTableWidget {
                background: white;
                border: 1px solid #d9e0ea;
                border-radius: 8px;
                gridline-color: #e5e7eb;
            }
            QHeaderView::section {
                background: #edf2f8;
                padding: 8px;
                border: none;
                font-weight: 700;
            }
            """
        )
