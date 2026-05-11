from PyQt6.QtWidgets import (
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

from modules.database import add_student, delete_student, get_students


class StudentPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_students()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form_layout = QFormLayout()
        self.student_id_input = QLineEdit()
        self.full_name_input = QLineEdit()
        self.class_name_input = QLineEdit()
        self.email_input = QLineEdit()

        self.student_id_input.setPlaceholderText("VD: SV001")
        self.full_name_input.setPlaceholderText("VD: Nguyen Van A")
        self.class_name_input.setPlaceholderText("VD: CNTT K48")
        self.email_input.setPlaceholderText("Email hoặc số điện thoại")

        form_layout.addRow("Mã sinh viên", self.student_id_input)
        form_layout.addRow("Họ tên", self.full_name_input)
        form_layout.addRow("Lớp", self.class_name_input)
        form_layout.addRow("Email/SĐT", self.email_input)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Thêm sinh viên")
        self.refresh_button = QPushButton("Làm mới")
        self.delete_button = QPushButton("Xóa sinh viên")
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Mã SV", "Họ tên", "Lớp", "Email/SĐT"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.add_button.clicked.connect(self.handle_add_student)
        self.refresh_button.clicked.connect(self.load_students)
        self.delete_button.clicked.connect(self.handle_delete_student)

        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.table)

    def handle_add_student(self):
        student_id = self.student_id_input.text().strip()
        full_name = self.full_name_input.text().strip()
        class_name = self.class_name_input.text().strip()
        email = self.email_input.text().strip()

        if not student_id or not full_name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập mã sinh viên và họ tên.")
            return

        if not add_student(student_id, full_name, class_name, email):
            QMessageBox.warning(self, "Trùng mã", "Mã sinh viên đã tồn tại.")
            return

        QMessageBox.information(self, "Thành công", "Đã thêm sinh viên.")
        self.student_id_input.clear()
        self.full_name_input.clear()
        self.class_name_input.clear()
        self.email_input.clear()
        self.load_students()

    def handle_delete_student(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn sinh viên cần xóa.")
            return

        student_id = self.table.item(row, 0).text()
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa sinh viên {student_id}?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            delete_student(student_id)
            self.load_students()

    def load_students(self):
        students = get_students()
        self.table.setRowCount(len(students))
        for row, student in enumerate(students):
            for col, value in enumerate(student):
                self.table.setItem(row, col, QTableWidgetItem(value or ""))
