import os

import cv2


class FaceDetector:
    """Detect khuôn mặt bằng Haar Cascade của OpenCV."""

    def __init__(self):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            raise RuntimeError("Không tải được Haar Cascade nhận diện khuôn mặt.")

    def preprocess_gray(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.equalizeHist(gray)

    def detect_faces(self, frame):
        gray = self.preprocess_gray(frame)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(80, 80),
        )

        # Nếu lần detect đầu chưa thấy mặt, thử tham số dễ hơn.
        if len(faces) == 0:
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(50, 50),
            )
        return gray, faces

    def get_largest_face(self, frame):
        gray, faces = self.detect_faces(frame)
        if len(faces) == 0:
            return None, gray, faces
        largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
        x, y, w, h = largest_face
        face_roi = gray[y : y + h, x : x + w]
        return face_roi, gray, faces


def save_face_image(face_roi, student_id, dataset_dir):
    """Lưu ảnh khuôn mặt vào dataset/students/{student_id}/face_n.jpg."""
    student_dir = os.path.join(dataset_dir, student_id)
    os.makedirs(student_dir, exist_ok=True)

    existing_files = [
        name
        for name in os.listdir(student_dir)
        if name.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    file_name = f"face_{len(existing_files) + 1}.jpg"
    file_path = os.path.join(student_dir, file_name)
    cv2.imwrite(file_path, face_roi)
    return file_path
