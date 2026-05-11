import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from modules.database import get_dashboard_stats
from modules.face_trainer import DATASET_DIR, LABEL_MAP_PATH, MODEL_PATH


class StatCard(QFrame):
    """Card thống kê nhỏ trên dashboard."""

    def __init__(self, title, value, note, color):
        super().__init__()
        self.setObjectName("dashboardCard")
        self.setStyleSheet(
            f"""
            QFrame#dashboardCard {{
                background: white;
                border: 1px solid #e3e8f2;
                border-left: 6px solid {color};
                border-radius: 12px;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")

        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("cardValue")

        self.note_label = QLabel(note)
        self.note_label.setObjectName("cardNote")
        self.note_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.note_label)
        layout.addStretch()

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

        subtitle = QLabel("Dashboard tổng quan hệ thống điểm danh khuôn mặt sinh viên.")
        subtitle.setObjectName("mutedText")
        subtitle.setWordWrap(True)

        self.card_total_students = StatCard(
            "Tổng số sinh viên",
            "0",
            "Sinh viên đã lưu trong SQLite",
            "#2f6fed",
        )
        self.card_attended_today = StatCard(
            "Đã điểm danh hôm nay",
            "0",
            "Số sinh viên có bản ghi trong ngày",
            "#10b981",
        )
        self.card_not_attended_today = StatCard(
            "Chưa điểm danh hôm nay",
            "0",
            "Tính theo tổng sinh viên trừ số đã điểm danh",
            "#f59e0b",
        )
        self.card_face_images = StatCard(
            "Tổng ảnh khuôn mặt",
            "0",
            "Ảnh trong dataset/students",
            "#8b5cf6",
        )
        self.card_model_status = StatCard(
            "Trạng thái model",
            "Chưa train",
            "Kiểm tra models/face_model.yml và label_map.json",
            "#ef4444",
        )

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.addWidget(self.card_total_students, 0, 0)
        grid.addWidget(self.card_attended_today, 0, 1)
        grid.addWidget(self.card_not_attended_today, 0, 2)
        grid.addWidget(self.card_face_images, 1, 0)
        grid.addWidget(self.card_model_status, 1, 1, 1, 2)

        info = QLabel("Dữ liệu dashboard được lấy tự động từ SQLite, thư mục dataset và file model.")
        info.setObjectName("infoBox")
        info.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(grid)
        layout.addWidget(info)
        layout.addStretch()

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

    def load_dashboard_data(self):
        """Load dữ liệu mới nhất khi mở app hoặc quay lại trang chủ."""
        stats = get_dashboard_stats()
        face_image_count = self.count_face_images()
        model_trained = self.is_model_trained()

        self.card_total_students.set_value(stats["total_students"])
        self.card_attended_today.set_value(stats["attended_today"])
        self.card_not_attended_today.set_value(stats["not_attended_today"])
        self.card_face_images.set_value(face_image_count)

        if model_trained:
            self.card_model_status.set_value("Đã train", "Model sẵn sàng dùng để điểm danh")
        else:
            self.card_model_status.set_value("Chưa train", "Hãy đăng ký ảnh khuôn mặt và train model")
