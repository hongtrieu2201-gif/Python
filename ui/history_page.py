import os
from datetime import datetime

import pandas as pd
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.database import (
    delete_all_attendance,
    delete_attendance_by_date,
    get_attendance_history,
    get_course_sections,
    recalculate_attendance_statuses,
)


class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_sections()
        self.load_history()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        controls = QHBoxLayout()
        self.section_label = QLabel("Lớp học phần")
        self.section_combo = QComboBox()
        self.section_combo.setMinimumWidth(260)
        self.section_combo.setPlaceholderText("Chọn lớp học phần")

        self.filter_checkbox = QCheckBox("Lọc theo ngày")
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        self.refresh_button = QPushButton("Làm mới")
        self.export_button = QPushButton("Xuất CSV")
        self.recalculate_status_button = QPushButton("Cập nhật trạng thái trễ")
        self.delete_today_button = QPushButton("Xóa lịch sử hôm nay")
        self.delete_selected_date_button = QPushButton("Xóa lịch sử ngày chọn")
        self.delete_all_button = QPushButton("Xóa tất cả lịch sử")

        controls.addWidget(self.section_label)
        controls.addWidget(self.section_combo)
        controls.addWidget(self.filter_checkbox)
        controls.addWidget(self.date_edit)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.export_button)
        controls.addWidget(self.recalculate_status_button)
        controls.addWidget(self.delete_today_button)
        controls.addWidget(self.delete_selected_date_button)
        controls.addWidget(self.delete_all_button)
        controls.addStretch()

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "Mã SV",
                "Họ tên",
                "Lớp",
                "Môn học",
                "Lớp học phần",
                "Ngày",
                "Check-in",
                "Check-out",
                "Trạng thái",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.section_combo.currentIndexChanged.connect(self.load_history)
        self.refresh_button.clicked.connect(self.refresh_page)
        self.export_button.clicked.connect(self.export_csv)
        self.recalculate_status_button.clicked.connect(self.recalculate_statuses)
        self.delete_today_button.clicked.connect(self.delete_today_history)
        self.delete_selected_date_button.clicked.connect(self.delete_selected_date_history)
        self.delete_all_button.clicked.connect(self.delete_all_history)
        self.filter_checkbox.stateChanged.connect(self.load_history)
        self.date_edit.dateChanged.connect(self.load_history)

        layout.addLayout(controls)
        layout.addWidget(self.table)

    def load_sections(self):
        """Load danh sách lớp học phần để lọc lịch sử."""
        current_section_id = self.section_combo.currentData()
        self.section_combo.blockSignals(True)
        self.section_combo.clear()

        selected_index = 0
        for index, (section_id, _subject_id, subject_name, section_name, _start_time, _late_time) in enumerate(
            get_course_sections()
        ):
            self.section_combo.addItem(f"{section_id} - {subject_name} - {section_name}", section_id)
            if section_id == current_section_id:
                selected_index = index

        if self.section_combo.count() > 0:
            self.section_combo.setCurrentIndex(selected_index)

        self.section_combo.blockSignals(False)

    def current_section_id(self):
        return self.section_combo.currentData()

    def current_date_filter(self):
        if not self.filter_checkbox.isChecked():
            return None
        return self.date_edit.date().toString("yyyy-MM-dd")

    def refresh_page(self):
        self.load_sections()
        self.load_history()

    def load_history(self):
        """Hiển thị lịch sử theo lớp học phần đang chọn và ngày lọc nếu có."""
        section_id = self.current_section_id()
        if not section_id:
            rows = []
        else:
            rows = get_attendance_history(section_id=section_id, date_filter=self.current_date_filter())

        self.table.setRowCount(len(rows))
        for row_index, row_data in enumerate(rows):
            for col_index, value in enumerate(row_data):
                self.table.setItem(row_index, col_index, QTableWidgetItem(str(value or "")))

    def refresh_dashboard(self):
        """Refresh dashboard nếu HistoryPage đang nằm trong MainWindow."""
        main_window = self.window()
        if hasattr(main_window, "home_page"):
            main_window.home_page.load_dashboard_data()

    def show_delete_result(self, deleted_count):
        """Thông báo kết quả sau khi xóa dữ liệu attendance."""
        self.load_history()
        self.refresh_dashboard()
        if deleted_count > 0:
            QMessageBox.information(self, "Đã xóa", f"Đã xóa {deleted_count} bản ghi.")
        else:
            QMessageBox.information(self, "Không có dữ liệu", "Không có dữ liệu phù hợp để xóa.")

    def recalculate_statuses(self):
        """Cập nhật lại Đi trễ/Đúng giờ theo late_time hiện tại của lớp học phần."""
        confirm = QMessageBox.question(
            self,
            "Cập nhật trạng thái trễ",
            "Bạn có muốn cập nhật lại trạng thái theo late_time hiện tại không?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        updated_count = recalculate_attendance_statuses()
        self.load_history()
        self.refresh_dashboard()
        QMessageBox.information(self, "Hoàn tất", f"Đã cập nhật {updated_count} bản ghi.")

    def delete_today_history(self):
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            "Bạn có chắc muốn xóa lịch sử điểm danh hôm nay không?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        self.show_delete_result(delete_attendance_by_date(today))

    def delete_selected_date_history(self):
        selected_date = self.date_edit.date().toString("yyyy-MM-dd")
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa lịch sử điểm danh ngày {selected_date} không?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.show_delete_result(delete_attendance_by_date(selected_date))

    def delete_all_history(self):
        confirm = QMessageBox.question(
            self,
            "Cảnh báo xóa toàn bộ",
            "Bạn có chắc muốn xóa TOÀN BỘ lịch sử điểm danh không? Hành động này không thể hoàn tác.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.show_delete_result(delete_all_attendance())

    def export_csv(self):
        section_id = self.current_section_id()
        rows = get_attendance_history(section_id=section_id, date_filter=self.current_date_filter()) if section_id else []
        if not rows:
            QMessageBox.warning(self, "Không có dữ liệu", "Không có lịch sử để xuất.")
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

        df = pd.DataFrame(
            rows,
            columns=[
                "Mã sinh viên",
                "Họ tên",
                "Lớp",
                "Môn học",
                "Lớp học phần",
                "Ngày",
                "Check-in",
                "Check-out",
                "Trạng thái",
            ],
        )
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        QMessageBox.information(self, "Xuất CSV", f"Đã xuất file: {file_path}")
