import os
from datetime import datetime

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from modules.attendance_service import AttendanceService
from modules.database import get_course_sections
from modules.face_recognizer import FaceRecognizer


SCAN_COOLDOWN_SECONDS = 8
MODEL_MISSING_MESSAGE = "Chưa có model. Vui lòng huấn luyện model trước."


def get_unicode_font(font_size):
    """Tìm font Windows hỗ trợ tiếng Việt, nếu không có thì dùng font mặc định."""
    font_paths = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_unicode_text(frame, text, position, font_size, color):
    """Vẽ text Unicode tiếng Việt lên frame OpenCV bằng Pillow."""
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_frame)
    draw = ImageDraw.Draw(pil_image)
    font = get_unicode_font(font_size)

    b, g, r = color
    draw.text(position, text, font=font, fill=(r, g, b))
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)


class AttendancePage(QWidget):
    def __init__(self):
        super().__init__()
        self.cap = None
        self.recognizer = FaceRecognizer()
        self.attendance_service = AttendanceService()
        self.last_scan_times = {}
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.section_combo = QComboBox()
        self.section_combo.setPlaceholderText("Chọn lớp học phần")

        self.video_label = QLabel("Webcam điểm danh")
        self.video_label.setObjectName("cameraBox")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(720, 420)

        buttons = QHBoxLayout()
        self.start_button = QPushButton("Bắt đầu điểm danh")
        self.stop_button = QPushButton("Dừng điểm danh")
        self.reload_button = QPushButton("Tải lại model")
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.reload_button)
        buttons.addStretch()

        self.status_label = QLabel("Sẵn sàng.")
        self.status_label.setObjectName("infoBox")

        self.start_button.clicked.connect(self.start_attendance)
        self.stop_button.clicked.connect(self.release_camera)
        self.reload_button.clicked.connect(self.reload_model)

        layout.addWidget(self.section_combo)
        layout.addWidget(self.video_label)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        self.load_sections()

    def load_sections(self):
        """Load danh sách lớp học phần để người dùng chọn trước khi điểm danh."""
        current_section_id = self.section_combo.currentData()
        self.section_combo.clear()
        for section_id, _subject_id, subject_name, section_name, _start_time, late_time in get_course_sections():
            text = f"{section_id} - {subject_name} - {section_name} | Trễ sau {late_time or '07:30:00'}"
            self.section_combo.addItem(text, section_id)

        if current_section_id:
            index = self.section_combo.findData(current_section_id)
            if index >= 0:
                self.section_combo.setCurrentIndex(index)

    def reload_model(self, silent=False):
        """Tải model; silent=True dùng khi tự load lúc chuyển trang."""
        if self.recognizer.load_model():
            if not silent:
                QMessageBox.information(self, "Model", "Đã tải lại model.")
            return True

        self.status_label.setText(MODEL_MISSING_MESSAGE)
        if not silent:
            QMessageBox.warning(self, "Model", MODEL_MISSING_MESSAGE)
        return False

    def start_attendance(self):
        self.load_sections()
        if not self.section_combo.currentData():
            QMessageBox.warning(self, "Chưa chọn lớp học phần", "Vui lòng chọn lớp học phần trước khi điểm danh.")
            return

        self.reload_model(silent=True)
        if not self.recognizer.is_ready():
            self.status_label.setText(MODEL_MISSING_MESSAGE)
            return

        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Lỗi webcam", "Không mở được webcam.")
            self.cap = None
            return

        self.timer.start(30)
        self.status_label.setText("Đang nhận diện...")

    def can_process_student(self, student_id):
        """Tránh xử lý liên tục nhiều frame cho cùng một lần quét mặt."""
        now = datetime.now()
        last_time = self.last_scan_times.get(student_id)
        if last_time and (now - last_time).total_seconds() < SCAN_COOLDOWN_SECONDS:
            return False
        self.last_scan_times[student_id] = now
        return True

    def update_frame(self):
        if self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        _gray, main_face, result = self.recognizer.recognize_main_face(frame)
        if not self.recognizer.is_ready():
            self.status_label.setText(MODEL_MISSING_MESSAGE)
            self.show_frame(frame)
            return

        if main_face is None:
            self.status_label.setText("Chưa thấy khuôn mặt hợp lệ")
            self.show_frame(frame)
            return

        x, y, w, h = main_face
        confidence = result["confidence"] if result else 999.0
        student = result["student"] if result else None

        if student:
            student_id, full_name, class_name, _email = student
            text = f"{full_name} ({confidence:.1f})"
            color = (0, 180, 80)
            frame_status = (
                f"Đã nhận diện: {student_id} - {full_name} - {class_name or ''} "
                f"| confidence={confidence:.1f}"
            )

            if self.can_process_student(student_id):
                section_id = self.section_combo.currentData()
                if not section_id:
                    frame_status = "Vui lòng chọn lớp học phần trước khi điểm danh."
                else:
                    attendance_result = self.attendance_service.mark_present(student_id, section_id)
                    action = attendance_result["action"]
                    if action == "check_in":
                        frame_status = (
                            f"Check-in thành công: {full_name} lúc "
                            f"{attendance_result['check_in_time']} ({attendance_result['status']})"
                        )
                    elif action == "check_out":
                        frame_status = (
                            f"Check-out thành công: {full_name} lúc "
                            f"{attendance_result['check_out_time']}"
                        )
                    else:
                        frame_status = (
                            f"{full_name} đã check-out hôm nay lúc "
                            f"{attendance_result['check_out_time']}"
                        )
        else:
            text = f"Unknown ({confidence:.1f})"
            color = (40, 40, 220)
            message = result.get("message") if result else "Unknown"
            frame_status = f"{message or 'Unknown'} | confidence={confidence:.1f}"

        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        frame = draw_unicode_text(
            frame,
            text,
            (x, max(30, y - 10)),
            22,
            color,
        )

        self.status_label.setText(frame_status)
        self.show_frame(frame)

    def show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image).scaled(
            self.video_label.width(),
            self.video_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        self.video_label.setPixmap(pixmap)

    def release_camera(self):
        self.timer.stop()
        self.last_scan_times.clear()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.video_label.clear()
        self.video_label.setText("Webcam điểm danh")
        self.status_label.setText("Đã dừng điểm danh.")
