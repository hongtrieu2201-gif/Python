import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from modules.attendance_service import AttendanceService
from modules.face_recognizer import FaceRecognizer


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
    """Vẽ text Unicode tiếng Việt lên frame OpenCV bằng Pillow.

    frame dùng định dạng BGR của OpenCV, còn Pillow dùng RGB nên cần chuyển đổi qua lại.
    color truyền theo định dạng BGR để dùng thống nhất với cv2.rectangle.
    """
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
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

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

        layout.addWidget(self.video_label)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)

    def reload_model(self, silent=False):
        if self.recognizer.load_model():
            if not silent:
                QMessageBox.information(self, "Model", "Đã tải lại model.")
            return True

        if not silent:
            QMessageBox.warning(self, "Model", "Chưa train model hoặc thiếu file model.")
        return False

    def start_attendance(self):
        self.reload_model(silent=True)
        if not self.recognizer.is_ready():
            self.status_label.setText("Chưa train model.")
            return

        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Lỗi webcam", "Không mở được webcam.")
            self.cap = None
            return

        self.timer.start(30)
        self.status_label.setText("Đang nhận diện...")

    def update_frame(self):
        if self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        _gray, _faces, results = self.recognizer.recognize_frame(frame)
        if not self.recognizer.is_ready():
            self.status_label.setText("Chưa train model.")
            self.show_frame(frame)
            return

        if not results:
            self.status_label.setText("Đang nhận diện: chưa thấy khuôn mặt.")
            self.show_frame(frame)
            return

        # Mỗi frame có khuôn mặt đều cập nhật status mới, tránh giữ lại text cũ.
        frame_status = "Đã thấy khuôn mặt: Unknown."
        for result in results:
            x, y, w, h = result["rect"]
            confidence = result["confidence"]
            student = result["student"]

            if student:
                student_id, full_name, class_name, _email = student
                text = f"{full_name} ({student_id}) - {class_name or ''}"
                color = (0, 180, 80)
                frame_status = f"Đã nhận diện: {student_id} - {full_name} - {class_name or ''}."

                # Service tự kiểm tra database để không tạo bản ghi trùng trong ngày.
                attendance_result = self.attendance_service.mark_present(student_id)
                if attendance_result["inserted"]:
                    frame_status = f"Điểm danh thành công: {full_name} lúc {attendance_result['time']}"
                else:
                    frame_status = f"{full_name} đã điểm danh hôm nay lúc {attendance_result['old_time']}"
            else:
                text = f"Unknown ({confidence:.1f})"
                color = (40, 40, 220)
                frame_status = "Đã thấy khuôn mặt: Unknown."

            # Giữ OpenCV để vẽ khung, dùng Pillow để vẽ chữ Unicode.
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
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.video_label.clear()
        self.video_label.setText("Webcam điểm danh")
        self.status_label.setText("Đã dừng điểm danh.")
