from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.database import (
    add_course_section,
    add_subject,
    delete_course_section,
    delete_default_course_data,
    delete_subject,
    get_course_sections,
    get_subjects,
)


class SectionPage(QWidget):
    """Trang quản lý môn học và lớp học phần."""

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        subject_form = QFormLayout()
        self.subject_id_input = QLineEdit()
        self.subject_name_input = QLineEdit()
        self.teacher_name_input = QLineEdit()
        self.subject_id_input.setPlaceholderText("VD: AI101")
        self.subject_name_input.setPlaceholderText("VD: Trí tuệ nhân tạo")
        self.teacher_name_input.setPlaceholderText("VD: Nguyễn Văn B")
        subject_form.addRow("Mã môn", self.subject_id_input)
        subject_form.addRow("Tên môn", self.subject_name_input)
        subject_form.addRow("Giảng viên", self.teacher_name_input)

        subject_buttons = QHBoxLayout()
        self.add_subject_button = QPushButton("Thêm môn học")
        self.delete_subject_button = QPushButton("Xóa môn học")
        self.refresh_button = QPushButton("Làm mới")
        subject_buttons.addWidget(self.add_subject_button)
        subject_buttons.addWidget(self.delete_subject_button)
        subject_buttons.addWidget(self.refresh_button)
        subject_buttons.addStretch()

        self.subject_table = QTableWidget(0, 3)
        self.subject_table.setHorizontalHeaderLabels(["Mã môn", "Tên môn", "Giảng viên"])
        self.subject_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.subject_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.subject_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        section_form = QFormLayout()
        self.section_id_input = QLineEdit()
        self.section_name_input = QLineEdit()
        self.start_time_input = QLineEdit()
        self.late_time_input = QLineEdit()
        self.subject_combo = QComboBox()
        self.section_id_input.setPlaceholderText("VD: AI101-01")
        self.section_name_input.setPlaceholderText("VD: Nhóm 01 - Sáng thứ 2")
        self.start_time_input.setPlaceholderText("VD: 07:00:00")
        self.late_time_input.setPlaceholderText("VD: 07:30:00")
        section_form.addRow("Môn học", self.subject_combo)
        section_form.addRow("Mã lớp học phần", self.section_id_input)
        section_form.addRow("Tên lớp học phần", self.section_name_input)
        section_form.addRow("Giờ bắt đầu", self.start_time_input)
        section_form.addRow("Mốc đi trễ", self.late_time_input)

        section_buttons = QHBoxLayout()
        self.add_section_button = QPushButton("Thêm lớp học phần")
        self.delete_section_button = QPushButton("Xóa lớp học phần")
        self.delete_default_button = QPushButton("Xóa dữ liệu mặc định")
        section_buttons.addWidget(self.add_section_button)
        section_buttons.addWidget(self.delete_section_button)
        section_buttons.addWidget(self.delete_default_button)
        section_buttons.addStretch()

        self.section_table = QTableWidget(0, 6)
        self.section_table.setHorizontalHeaderLabels(
            ["Mã lớp HP", "Mã môn", "Tên môn", "Tên lớp HP", "Bắt đầu", "Đi trễ sau"]
        )
        self.section_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.section_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.section_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.add_subject_button.clicked.connect(self.handle_add_subject)
        self.delete_subject_button.clicked.connect(self.handle_delete_subject)
        self.add_section_button.clicked.connect(self.handle_add_section)
        self.delete_section_button.clicked.connect(self.handle_delete_section)
        self.delete_default_button.clicked.connect(self.handle_delete_default_data)
        self.refresh_button.clicked.connect(self.load_data)

        layout.addLayout(subject_form)
        layout.addLayout(subject_buttons)
        layout.addWidget(self.subject_table)
        layout.addLayout(section_form)
        layout.addLayout(section_buttons)
        layout.addWidget(self.section_table)

    def refresh_related_pages(self):
        """Refresh combobox/dashboard nếu trang này đang nằm trong MainWindow."""
        main_window = self.window()
        if hasattr(main_window, "attendance_page"):
            main_window.attendance_page.load_sections()
        if hasattr(main_window, "student_page"):
            main_window.student_page.refresh_student_table()
        if hasattr(main_window, "register_face_page"):
            main_window.register_face_page.refresh_sections_and_students()
        if hasattr(main_window, "home_page"):
            main_window.home_page.load_dashboard_data()

    def load_data(self):
        subjects = get_subjects()
        self.subject_table.setRowCount(len(subjects))
        self.subject_combo.clear()

        for row, subject in enumerate(subjects):
            subject_id, subject_name, teacher_name = subject
            self.subject_combo.addItem(f"{subject_id} - {subject_name}", subject_id)
            for col, value in enumerate(subject):
                self.subject_table.setItem(row, col, QTableWidgetItem(value or ""))

        sections = get_course_sections()
        self.section_table.setRowCount(len(sections))
        for row, section in enumerate(sections):
            for col, value in enumerate(section):
                self.section_table.setItem(row, col, QTableWidgetItem(value or ""))

        self.refresh_related_pages()

    def selected_subject_id(self):
        row = self.subject_table.currentRow()
        if row < 0:
            return None
        item = self.subject_table.item(row, 0)
        return item.text() if item else None

    def selected_section_id(self):
        row = self.section_table.currentRow()
        if row < 0:
            return None
        item = self.section_table.item(row, 0)
        return item.text() if item else None

    def handle_add_subject(self):
        subject_id = self.subject_id_input.text().strip()
        subject_name = self.subject_name_input.text().strip()
        teacher_name = self.teacher_name_input.text().strip()

        if not subject_id or not subject_name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập mã môn và tên môn.")
            return
        if not add_subject(subject_id, subject_name, teacher_name):
            QMessageBox.warning(self, "Trùng mã", "Mã môn học đã tồn tại.")
            return

        self.subject_id_input.clear()
        self.subject_name_input.clear()
        self.teacher_name_input.clear()
        self.load_data()
        QMessageBox.information(self, "Thành công", "Đã thêm môn học.")

    def handle_delete_subject(self):
        subject_id = self.selected_subject_id()
        if not subject_id:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn môn học cần xóa.")
            return

        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa môn học {subject_id}?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        success, message = delete_subject(subject_id)
        if success:
            QMessageBox.information(self, "Đã xóa", message)
            self.load_data()
        else:
            QMessageBox.warning(self, "Không thể xóa", message)

    def handle_add_section(self):
        subject_id = self.subject_combo.currentData()
        section_id = self.section_id_input.text().strip()
        section_name = self.section_name_input.text().strip()
        start_time = self.start_time_input.text().strip() or "07:00:00"
        late_time = self.late_time_input.text().strip() or "07:30:00"

        if not subject_id:
            QMessageBox.warning(self, "Chưa có môn", "Vui lòng thêm/chọn môn học trước.")
            return
        if not section_id or not section_name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập mã và tên lớp học phần.")
            return
        if not add_course_section(section_id, subject_id, section_name, start_time, late_time):
            QMessageBox.warning(self, "Trùng mã", "Mã lớp học phần đã tồn tại.")
            return

        self.section_id_input.clear()
        self.section_name_input.clear()
        self.start_time_input.clear()
        self.late_time_input.clear()
        self.load_data()
        QMessageBox.information(self, "Thành công", "Đã thêm lớp học phần.")

    def handle_delete_section(self):
        section_id = self.selected_section_id()
        if not section_id:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn lớp học phần cần xóa.")
            return

        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa lớp học phần {section_id}?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        success, message = delete_course_section(section_id)
        if success:
            QMessageBox.information(self, "Đã xóa", message)
            self.load_data()
        else:
            QMessageBox.warning(self, "Không thể xóa", message)

    def handle_delete_default_data(self):
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa dữ liệu mặc định",
            "Bạn có chắc muốn xóa DEFAULT và DEFAULT_SECTION nếu chúng tồn tại?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        success, message = delete_default_course_data()
        if success:
            QMessageBox.information(self, "Hoàn tất", message)
            self.load_data()
        else:
            QMessageBox.warning(self, "Không thể xóa", message)
