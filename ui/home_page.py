import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from modules.database import get_course_sections, get_dashboard_stats
from modules.face_trainer import DATASET_DIR, LABEL_MAP_PATH, MODEL_PATH


class StatCard(QFrame):
    """Card thống kê trên dashboard."""

    def __init__(self, title, value, note, color):
        super().__init__()
        self.setObjectName("dashboardCard")
        self.setMinimumHeight(148)
        self.setStyleSheet(
            """
            QFrame#dashboardCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            """
        )

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        accent_bar = QFrame()
        accent_bar.setFixedWidth(7)
        accent_bar.setStyleSheet(
            f"""
            QFrame {{
                background-color: {color};
                border: none;
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
            }}
            """
        )

        content = QWidget()
        content.setObjectName("cardContent")
        content.setStyleSheet("QWidget#cardContent { background: transparent; border: none; }")

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 16, 18, 16)
        content_layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")

        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("cardValue")

        self.note_label = QLabel(note)
        self.note_label.setObjectName("cardNote")
        self.note_label.setWordWrap(True)

        content_layout.addWidget(self.title_label)
        content_layout.addWidget(self.value_label)
        content_layout.addWidget(self.note_label)
        content_layout.addStretch()

        root_layout.addWidget(accent_bar)
        root_layout.addWidget(content, 1)

    def set_value(self, value, note=None):
        self.value_label.setText(str(value))
        if note is not None:
            self.note_label.setText(note)


class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_dashboard_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Face Attendance Desktop")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Dashboard tổng quan theo lớp học phần đang chọn.")
        subtitle.setObjectName("mutedText")
        subtitle.setWordWrap(True)

        filter_row = QHBoxLayout()
        section_label = QLabel("Lớp học phần")
        section_label.setObjectName("mutedText")
        self.section_combo = QComboBox()
        self.section_combo.currentIndexChanged.connect(self.load_dashboard_data)
        filter_row.addWidget(section_label)
        filter_row.addWidget(self.section_combo, 1)

        self.card_total_students = StatCard("Tổng số sinh viên", "0", "Sinh viên đã lưu trong SQLite", "#2f6fed")
        self.card_checked_in_today = StatCard("Đã check-in hôm nay", "0", "Theo lớp học phần đang chọn", "#10b981")
        self.card_late_today = StatCard("Đi trễ hôm nay", "0", "Dựa trên late_time của lớp học phần", "#f59e0b")
        self.card_not_checked_out_today = StatCard("Chưa check-out", "0", "Đã check-in nhưng chưa check-out", "#ef4444")
        self.card_face_images = StatCard("Tổng ảnh khuôn mặt", "0", "Ảnh trong dataset/students", "#8b5cf6")
        self.card_model_status = StatCard("Trạng thái model", "Chưa train", "Kiểm tra models/face_model.yml", "#0ea5e9")

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.addWidget(self.card_total_students, 0, 0)
        grid.addWidget(self.card_checked_in_today, 0, 1)
        grid.addWidget(self.card_late_today, 0, 2)
        grid.addWidget(self.card_not_checked_out_today, 1, 0)
        grid.addWidget(self.card_face_images, 1, 1)
        grid.addWidget(self.card_model_status, 1, 2)

        info = QLabel("Dữ liệu dashboard được lấy từ SQLite, dataset và model theo lớp học phần đang chọn.")
        info.setObjectName("infoBox")
        info.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(filter_row)
        layout.addLayout(grid)
        layout.addWidget(info)
        layout.addStretch()

    def load_sections(self):
        """Load danh sách lớp học phần cho bộ lọc dashboard."""
        current_section_id = self.section_combo.currentData()
        self.section_combo.blockSignals(True)
        self.section_combo.clear()
        for section_id, _subject_id, subject_name, section_name, _start_time, late_time in get_course_sections():
            text = f"{section_id} - {subject_name} - {section_name} | Trễ sau {late_time or '07:30:00'}"
            self.section_combo.addItem(text, section_id)

        if current_section_id:
            index = self.section_combo.findData(current_section_id)
            if index >= 0:
                self.section_combo.setCurrentIndex(index)
        self.section_combo.blockSignals(False)

    def count_face_images(self):
        """Đếm toàn bộ ảnh khuôn mặt trong dataset/students."""
        if not os.path.isdir(DATASET_DIR):
            return 0

        image_count = 0
        for _root, _dirs, files in os.walk(DATASET_DIR):
            for file_name in files:
                if file_name.lower().endswith((".jpg", ".jpeg", ".png")):
                    image_count += 1
        return image_count

    def is_model_trained(self):
        """Kiểm tra model đã train hay chưa dựa trên file model và label map."""
        if not os.path.exists(MODEL_PATH) or os.path.getsize(MODEL_PATH) <= 1:
            return False
        if not os.path.exists(LABEL_MAP_PATH):
            return False

        try:
            with open(LABEL_MAP_PATH, "r", encoding="utf-8") as file:
                label_map = json.load(file)
            return bool(label_map)
        except (OSError, json.JSONDecodeError):
            return False

    def load_dashboard_data(self, *_args):
        """Load dữ liệu mới nhất khi mở app hoặc quay lại trang chủ."""
        self.load_sections()
        stats = get_dashboard_stats(self.section_combo.currentData())
        face_image_count = self.count_face_images()
        model_trained = self.is_model_trained()

        self.card_total_students.set_value(stats["total_students"])
        self.card_checked_in_today.set_value(stats["checked_in_today"])
        self.card_late_today.set_value(stats["late_today"])
        self.card_not_checked_out_today.set_value(stats["not_checked_out_today"])
        self.card_face_images.set_value(face_image_count)

        if model_trained:
            self.card_model_status.set_value("Đã train", "Model sẵn sàng dùng để điểm danh")
        else:
            self.card_model_status.set_value("Chưa train", "Hãy đăng ký ảnh khuôn mặt và train model")
