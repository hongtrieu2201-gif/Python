import os
import sqlite3

import pandas as pd
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
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
    add_student_to_section,
    get_course_sections,
    get_students_by_section,
    remove_student_from_section,
    upsert_student,
)


class StudentPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db_path = "database/attendance.db"
        self.setup_ui()
        self.load_sections()
        self.load_students()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        section_layout = QHBoxLayout()
        self.section_combo = QComboBox()
        self.section_combo.setPlaceholderText("Chọn lớp học phần")
        section_layout.addWidget(self.section_combo)

        form_layout = QFormLayout()
        self.student_id_input = QLineEdit()
        self.full_name_input = QLineEdit()
        self.class_name_input = QLineEdit()
        self.contact_input = QLineEdit()

        self.student_id_input.setPlaceholderText("VD: SV001")
        self.full_name_input.setPlaceholderText("VD: Nguyen Van A")
        self.class_name_input.setPlaceholderText("VD: CNTT K48")
        self.contact_input.setPlaceholderText("Email hoặc số điện thoại")

        form_layout.addRow("Mã sinh viên", self.student_id_input)
        form_layout.addRow("Họ tên", self.full_name_input)
        form_layout.addRow("Lớp", self.class_name_input)
        form_layout.addRow("Email/SĐT", self.contact_input)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Thêm sinh viên")
        self.refresh_button = QPushButton("Làm mới")
        self.delete_button = QPushButton("Xóa sinh viên")
        self.import_button = QPushButton("Nhập Excel/CSV")
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.import_button)
        button_layout.addStretch()

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Mã SV", "Họ tên", "Lớp", "Email/SĐT"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.section_combo.currentIndexChanged.connect(self.load_students)
        self.add_button.clicked.connect(self.handle_add_student)
        self.refresh_button.clicked.connect(self.refresh_student_table)
        self.delete_button.clicked.connect(self.handle_delete_student)
        self.import_button.clicked.connect(self.import_students_from_file)

        layout.addLayout(section_layout)
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.table)

    def load_sections(self):
        """Load combobox lớp học phần."""
        current_section_id = self.section_combo.currentData()
        self.section_combo.blockSignals(True)
        self.section_combo.clear()
        for section_id, _subject_id, subject_name, section_name, _start_time, _late_time in get_course_sections():
            self.section_combo.addItem(f"{section_id} - {subject_name} - {section_name}", section_id)

        if current_section_id:
            index = self.section_combo.findData(current_section_id)
            if index >= 0:
                self.section_combo.setCurrentIndex(index)
        self.section_combo.blockSignals(False)

    def selected_section_id(self):
        return self.section_combo.currentData()

    def require_section(self):
        """Bắt buộc chọn lớp học phần trước khi thao tác danh sách sinh viên."""
        if not self.selected_section_id():
            QMessageBox.warning(self, "Chưa chọn lớp học phần", "Vui lòng chọn lớp học phần trước.")
            return False
        return True

    def handle_add_student(self):
        if not self.require_section():
            return

        section_id = self.selected_section_id()
        student_id = self.student_id_input.text().strip()
        full_name = self.full_name_input.text().strip()
        class_name = self.class_name_input.text().strip()
        contact = self.contact_input.text().strip()

        if not student_id or not full_name or not class_name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập mã sinh viên, họ tên và lớp.")
            return

        # Thêm vào students nếu chưa tồn tại, sau đó gắn vào lớp học phần.
        upsert_student(student_id, full_name, class_name, contact)
        added_to_section = add_student_to_section(section_id, student_id)
        if not added_to_section:
            QMessageBox.warning(self, "Đã có trong lớp", "Sinh viên đã thuộc lớp học phần đang chọn.")
            return

        QMessageBox.information(self, "Thành công", "Đã thêm sinh viên vào lớp học phần.")
        self.student_id_input.clear()
        self.full_name_input.clear()
        self.class_name_input.clear()
        self.contact_input.clear()
        self.load_students()

    def handle_delete_student(self):
        if not self.require_section():
            return

        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn sinh viên cần xóa khỏi lớp học phần.")
            return

        section_id = self.selected_section_id()
        student_id = self.table.item(row, 0).text()
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa sinh viên {student_id} khỏi lớp học phần đang chọn?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            remove_student_from_section(section_id, student_id)
            self.load_students()

    def import_students_from_file(self):
        """Import danh sách sinh viên vào lớp học phần đang chọn."""
        if not self.require_section():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file Excel/CSV",
            os.getcwd(),
            "Student Files (*.xlsx *.xls *.csv)",
        )
        if not file_path:
            return

        try:
            df = self.read_student_file(file_path)
            df, skipped_missing, duplicated_in_file = self.validate_student_dataframe(df)
            inserted_count, duplicated_in_section = self.insert_students_bulk(df)
            duplicate_count = duplicated_in_file + duplicated_in_section
            self.refresh_student_table()

            QMessageBox.information(
                self,
                "Import hoàn tất",
                (
                    "Import hoàn tất\n"
                    f"Thêm vào lớp học phần thành công: {inserted_count} sinh viên\n"
                    f"Bị trùng mã sinh viên trong lớp học phần: {duplicate_count} dòng\n"
                    f"Bị bỏ qua do thiếu dữ liệu: {skipped_missing} dòng"
                ),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Lỗi import", str(error))
        except ImportError as error:
            QMessageBox.critical(self, "Thiếu thư viện đọc Excel", str(error))
        except sqlite3.Error as error:
            QMessageBox.critical(self, "Lỗi database", f"Lỗi database: {error}")
        except Exception as error:
            QMessageBox.critical(self, "Lỗi import", f"Không import được file: {error}")

    def read_student_file(self, file_path):
        """Đọc file CSV/XLS/XLSX bằng pandas."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            df = pd.read_csv(file_path, dtype=str)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path, dtype=str)
        else:
            raise ValueError("File sai định dạng. Vui lòng chọn .xlsx, .xls hoặc .csv.")

        if df.empty:
            raise ValueError("File rỗng, không có dữ liệu để import.")
        return df

    def validate_student_dataframe(self, df):
        """Kiểm tra cột bắt buộc, bỏ dòng thiếu dữ liệu và bỏ trùng trong file."""
        required_columns = ["student_id", "full_name", "class_name"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"File thiếu cột bắt buộc: {', '.join(missing_columns)}")

        if "contact" not in df.columns:
            df["contact"] = ""

        df = df[["student_id", "full_name", "class_name", "contact"]].copy()
        df = df.fillna("")
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()

        missing_mask = (
            (df["student_id"] == "")
            | (df["full_name"] == "")
            | (df["class_name"] == "")
        )
        skipped_missing = int(missing_mask.sum())
        df = df[~missing_mask].copy()

        duplicated_in_file = int(df.duplicated(subset=["student_id"], keep="first").sum())
        df = df.drop_duplicates(subset=["student_id"], keep="first")
        return df, skipped_missing, duplicated_in_file

    def insert_students_bulk(self, df):
        """Thêm sinh viên chung nếu cần và gắn vào lớp học phần đang chọn."""
        section_id = self.selected_section_id()
        inserted_count = 0
        duplicated_in_section = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for _index, row in df.iterrows():
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO students(student_id, full_name, class_name, contact, created_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                    """,
                    (row["student_id"], row["full_name"], row["class_name"], row["contact"]),
                )

                try:
                    cursor.execute(
                        "INSERT INTO section_students(section_id, student_id) VALUES (?, ?)",
                        (section_id, row["student_id"]),
                    )
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    duplicated_in_section += 1

            conn.commit()

        return inserted_count, duplicated_in_section

    def refresh_student_table(self):
        """Refresh combobox lớp học phần và bảng sinh viên."""
        self.load_sections()
        self.load_students()

    def load_students(self):
        section_id = self.selected_section_id()
        students = get_students_by_section(section_id) if section_id else []
        self.table.setRowCount(len(students))
        for row, student in enumerate(students):
            for col, value in enumerate(student):
                self.table.setItem(row, col, QTableWidgetItem(value or ""))
