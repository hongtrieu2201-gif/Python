import os

import cv2
from PyQt6.QtCore import QSize, QTimer, Qt
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from modules.database import get_course_sections, get_students_by_section
from modules.face_detector import FaceDetector, save_face_image


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset", "students")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")


class RegisterFacePage(QWidget):
    def __init__(self):
        super().__init__()
        self.cap = None
        self.current_frame = None
        self.detector = FaceDetector()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.setup_ui()
        self.refresh_sections_and_students()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        section_row = QHBoxLayout()
        section_label = QLabel("Lớp học phần")
        self.section_combo = QComboBox()
        self.section_combo.setPlaceholderText("Chọn lớp học phần")
        section_row.addWidget(section_label)
        section_row.addWidget(self.section_combo, 1)

        student_row = QHBoxLayout()
        student_label = QLabel("Sinh viên")
        self.student_combo = QComboBox()
        self.upload_button = QPushButton("Tải ảnh từ máy")
        student_row.addWidget(student_label)
        student_row.addWidget(self.student_combo, 1)
        student_row.addWidget(self.upload_button)

        self.video_label = QLabel("Webcam đăng ký khuôn mặt")
        self.video_label.setObjectName("cameraBox")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(720, 360)

        camera_buttons = QHBoxLayout()
        self.open_button = QPushButton("Mở webcam")
        self.capture_button = QPushButton("Chụp ảnh khuôn mặt")
        self.close_button = QPushButton("Tắt webcam")
        self.refresh_students_button = QPushButton("Làm mới sinh viên")
        camera_buttons.addWidget(self.open_button)
        camera_buttons.addWidget(self.capture_button)
        camera_buttons.addWidget(self.close_button)
        camera_buttons.addWidget(self.refresh_students_button)
        camera_buttons.addStretch()

        self.status_label = QLabel("Chọn sinh viên và mở webcam để đăng ký khuôn mặt.")
        self.status_label.setObjectName("mutedText")

        gallery_header = QHBoxLayout()
        self.gallery_title = QLabel("Ảnh khuôn mặt đã lưu")
        self.gallery_title.setObjectName("mutedText")
        self.refresh_images_button = QPushButton("Làm mới ảnh")
        self.delete_image_button = QPushButton("Xóa ảnh đang chọn")
        gallery_header.addWidget(self.gallery_title)
        gallery_header.addStretch()
        gallery_header.addWidget(self.refresh_images_button)
        gallery_header.addWidget(self.delete_image_button)

        self.empty_images_label = QLabel("Chưa có ảnh khuôn mặt")
        self.empty_images_label.setObjectName("mutedText")
        self.empty_images_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.image_list.setIconSize(QSize(120, 120))
        self.image_list.setGridSize(QSize(150, 165))
        self.image_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.image_list.setMovement(QListWidget.Movement.Static)
        self.image_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.image_list.setMinimumHeight(190)

        self.section_combo.currentIndexChanged.connect(self.load_students)
        self.student_combo.currentIndexChanged.connect(self.load_face_images)
        self.upload_button.clicked.connect(self.upload_face_image)
        self.open_button.clicked.connect(self.open_camera)
        self.capture_button.clicked.connect(self.capture_face)
        self.close_button.clicked.connect(self.release_camera)
        self.refresh_students_button.clicked.connect(self.refresh_sections_and_students)
        self.refresh_images_button.clicked.connect(self.load_face_images)
        self.delete_image_button.clicked.connect(self.delete_selected_image)

        layout.addLayout(section_row)
        layout.addLayout(student_row)
        layout.addWidget(self.video_label)
        layout.addLayout(camera_buttons)
        layout.addWidget(self.status_label)
        layout.addLayout(gallery_header)
        layout.addWidget(self.empty_images_label)
        layout.addWidget(self.image_list)

    def refresh_sections_and_students(self):
        """Làm mới lớp học phần và danh sách sinh viên theo lớp đang chọn."""
        self.load_sections()
        self.load_students()

    def load_sections(self):
        """Load danh sách lớp học phần từ database."""
        current_section_id = self.section_combo.currentData()
        self.section_combo.blockSignals(True)
        self.section_combo.clear()

        selected_index = 0
        for index, (section_id, _subject_id, subject_name, section_name, _start_time, _late_time) in enumerate(
            get_course_sections()
        ):
            display_text = f"{section_id} - {subject_name} - {section_name}"
            self.section_combo.addItem(display_text, section_id)
            if section_id == current_section_id:
                selected_index = index

        if self.section_combo.count() > 0:
            self.section_combo.setCurrentIndex(selected_index)

        self.section_combo.blockSignals(False)

    def load_students(self):
        """Chỉ hiển thị sinh viên thuộc lớp học phần đang chọn."""
        section_id = self.section_combo.currentData()
        current_student_id = self.student_combo.currentData()
        self.student_combo.blockSignals(True)
        self.student_combo.clear()

        selected_index = 0
        if section_id:
            for index, (student_id, full_name, class_name, _contact) in enumerate(get_students_by_section(section_id)):
                self.student_combo.addItem(f"{student_id} - {full_name} - {class_name or ''}", student_id)
                if student_id == current_student_id:
                    selected_index = index

        if self.student_combo.count() > 0:
            self.student_combo.setCurrentIndex(selected_index)

        self.student_combo.blockSignals(False)
        self.load_face_images()

    def get_selected_student_dir(self):
        student_id = self.student_combo.currentData()
        if not student_id:
            return None
        return os.path.join(DATASET_DIR, student_id)

    def get_face_image_paths(self):
        """Lấy danh sách ảnh đã lưu của sinh viên đang chọn."""
        student_dir = self.get_selected_student_dir()
        if not student_dir or not os.path.isdir(student_dir):
            return []

        image_paths = []
        for file_name in sorted(os.listdir(student_dir)):
            if file_name.lower().endswith(IMAGE_EXTENSIONS):
                image_paths.append(os.path.join(student_dir, file_name))
        return image_paths

    def load_face_images(self):
        """Hiển thị ảnh khuôn mặt dạng thumbnail 120x120 và cập nhật số lượng ảnh."""
        self.image_list.clear()
        image_paths = self.get_face_image_paths()
        self.gallery_title.setText(f"Ảnh khuôn mặt đã lưu ({len(image_paths)} ảnh)")

        if not image_paths:
            self.empty_images_label.setText("Chưa có ảnh khuôn mặt")
            self.empty_images_label.show()
            return

        self.empty_images_label.hide()
        for image_path in image_paths:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                continue

            thumbnail = pixmap.scaled(
                120,
                120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            item = QListWidgetItem(QIcon(thumbnail), os.path.basename(image_path))
            item.setData(Qt.ItemDataRole.UserRole, image_path)
            item.setToolTip(image_path)
            self.image_list.addItem(item)

    def delete_selected_image(self):
        """Xóa ảnh đang chọn trong danh sách thumbnail."""
        item = self.image_list.currentItem()
        if item is None:
            QMessageBox.warning(self, "Chưa chọn ảnh", "Vui lòng chọn ảnh khuôn mặt cần xóa.")
            return

        image_path = item.data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa ảnh {os.path.basename(image_path)}?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            os.remove(image_path)
            self.status_label.setText(f"Đã xóa ảnh: {image_path}")
            self.load_face_images()
        except OSError as error:
            QMessageBox.critical(self, "Lỗi xóa ảnh", f"Không xóa được ảnh: {error}")

    def get_next_upload_path(self, student_id):
        """Tạo đường dẫn upload_1.jpg, upload_2.jpg... không trùng file cũ."""
        student_dir = os.path.join(DATASET_DIR, student_id)
        os.makedirs(student_dir, exist_ok=True)

        index = 1
        while True:
            file_path = os.path.join(student_dir, f"upload_{index}.jpg")
            if not os.path.exists(file_path):
                return file_path
            index += 1

    def detect_face_from_uploaded_image(self, image):
        """Detect mặt trong ảnh upload bằng Haar Cascade theo tham số yêu cầu."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self.detector.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(100, 100),
        )
        if len(faces) == 0:
            return None, faces

        # Nếu có nhiều mặt, chọn mặt lớn nhất để lưu.
        x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
        face_roi = gray[y : y + h, x : x + w]
        return face_roi, faces

    def upload_face_image(self):
        """Chọn ảnh từ máy tính, cắt khuôn mặt và lưu vào dataset của sinh viên."""
        student_id = self.student_combo.currentData()
        if not student_id:
            QMessageBox.warning(self, "Chưa chọn sinh viên", "Vui lòng chọn sinh viên trước khi tải ảnh.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh khuôn mặt",
            os.getcwd(),
            "Image Files (*.jpg *.jpeg *.png)",
        )
        if not file_path:
            return

        image = cv2.imread(file_path)
        if image is None:
            QMessageBox.warning(self, "Lỗi đọc ảnh", "Không đọc được file ảnh đã chọn.")
            return

        face_roi, _faces = self.detect_face_from_uploaded_image(image)
        if face_roi is None:
            QMessageBox.warning(
                self,
                "Không phát hiện khuôn mặt",
                "Không phát hiện được khuôn mặt trong ảnh đã chọn.",
            )
            return

        save_path = self.get_next_upload_path(student_id)
        cv2.imwrite(save_path, face_roi)
        self.status_label.setText(f"Đã tải ảnh: {save_path}")
        self.load_face_images()
        QMessageBox.information(self, "Thành công", "Tải ảnh khuôn mặt thành công.")

    def open_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Lỗi webcam", "Không mở được webcam.")
            self.cap = None
            return
        self.timer.start(30)
        self.status_label.setText("Webcam đang mở.")

    def update_frame(self):
        if self.cap is None:
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        self.current_frame = frame
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

    def capture_face(self):
        student_id = self.student_combo.currentData()
        if not student_id:
            QMessageBox.warning(self, "Chưa có sinh viên", "Vui lòng thêm và chọn sinh viên.")
            return
        if self.current_frame is None:
            QMessageBox.warning(self, "Chưa có ảnh", "Vui lòng mở webcam trước.")
            return

        face_roi, _gray, faces = self.detector.get_largest_face(self.current_frame)
        if face_roi is None:
            self.status_label.setText("Không nhận được khuôn mặt. Hãy ngồi gần camera và nhìn thẳng.")
            QMessageBox.warning(self, "Không thấy mặt", "Không phát hiện khuôn mặt, vui lòng thử lại.")
            return

        file_path = save_face_image(face_roi, student_id, DATASET_DIR)
        self.status_label.setText(f"Đã lưu ảnh: {file_path} | Số mặt phát hiện: {len(faces)}")
        self.load_face_images()
        QMessageBox.information(self, "Thành công", "Đã chụp và lưu ảnh khuôn mặt.")

    def release_camera(self):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.current_frame = None
        self.video_label.clear()
        self.video_label.setText("Webcam đăng ký khuôn mặt")
        self.status_label.setText("Đã tắt webcam.")
