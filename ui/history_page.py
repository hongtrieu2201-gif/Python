import os

import pandas as pd
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.database import get_attendance_history


class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_history()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        controls = QHBoxLayout()
        self.filter_checkbox = QCheckBox("Lọc theo ngày")
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.refresh_button = QPushButton("Làm mới")
        self.export_button = QPushButton("Xuất CSV")
        controls.addWidget(self.filter_checkbox)
        controls.addWidget(self.date_edit)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.export_button)
        controls.addStretch()

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Mã SV", "Họ tên", "Lớp", "Ngày", "Giờ", "Trạng thái"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.refresh_button.clicked.connect(self.load_history)
        self.export_button.clicked.connect(self.export_csv)
        self.filter_checkbox.stateChanged.connect(self.load_history)
        self.date_edit.dateChanged.connect(self.load_history)

        layout.addLayout(controls)
        layout.addWidget(self.table)

    def current_date_filter(self):
        if not self.filter_checkbox.isChecked():
            return None
        return self.date_edit.date().toString("yyyy-MM-dd")

    def load_history(self):
        rows = get_attendance_history(self.current_date_filter())
        self.table.setRowCount(len(rows))
        for row_index, row_data in enumerate(rows):
            for col_index, value in enumerate(row_data):
                self.table.setItem(row_index, col_index, QTableWidgetItem(value or ""))

    def export_csv(self):
        rows = get_attendance_history(self.current_date_filter())
        if not rows:
            QMessageBox.warning(self, "Không có dữ liệu", "Không có lịch sử điểm danh để xuất.")
            return

        default_name = "attendance_history.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu file CSV",
            os.path.join(os.getcwd(), default_name),
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        df = pd.DataFrame(rows, columns=["Mã sinh viên", "Họ tên", "Lớp", "Ngày", "Giờ", "Trạng thái"])
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        QMessageBox.information(self, "Xuất CSV", f"Đã xuất file: {file_path}")
