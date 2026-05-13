import json
import os

import cv2

from modules.database import get_student
from modules.face_detector import FaceDetector
from modules.face_trainer import LABEL_MAP_PATH, MODEL_PATH, preprocess_face_image


class FaceRecognizer:
    """Nhận diện sinh viên bằng model LBPH đã train."""

    def __init__(self, confidence_threshold=80):
        self.confidence_threshold = confidence_threshold
        self.detector = FaceDetector()
        self.recognizer = None
        self.label_map = {}
        self.load_model()

    def load_model(self):
        """Load lại cả face_model.yml và label_map.json."""
        if not os.path.exists(MODEL_PATH) or not os.path.exists(LABEL_MAP_PATH):
            self.recognizer = None
            self.label_map = {}
            return False

        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.recognizer.read(MODEL_PATH)
            with open(LABEL_MAP_PATH, "r", encoding="utf-8") as file:
                self.label_map = json.load(file)
            return True
        except (cv2.error, json.JSONDecodeError, OSError):
            self.recognizer = None
            self.label_map = {}
            return False

    def is_ready(self):
        return self.recognizer is not None and bool(self.label_map)

    def build_result(self, rect, label, confidence):
        """Tạo kết quả nhận diện, kiểm tra threshold và label_map rõ ràng."""
        label_key = str(label)
        student_id = None
        student = None
        status = "Unknown"
        message = ""

        # Với LBPH: confidence càng thấp càng tốt.
        if confidence <= self.confidence_threshold:
            student_id = self.label_map.get(label_key)
            if not student_id:
                message = "Label không tồn tại trong label_map"
            else:
                student = get_student(student_id)
                if student:
                    status = "Recognized"
                else:
                    message = "Không tìm thấy sinh viên trong database"
        else:
            message = "Confidence vượt ngưỡng nhận diện"

        return {
            "rect": rect,
            "label": label,
            "student_id": student_id,
            "student": student,
            "confidence": confidence,
            "threshold": self.confidence_threshold,
            "status": status,
            "message": message,
        }

    def recognize_main_face(self, frame):
        """Detect và predict duy nhất khuôn mặt chính trong frame."""
        gray, main_face = self.detector.detect_main_face(frame)
        if main_face is None or not self.is_ready():
            return gray, main_face, None

        x, y, w, h = main_face
        face_roi = gray[y : y + h, x : x + w]
        face_roi = preprocess_face_image(face_roi)
        label, confidence = self.recognizer.predict(face_roi)
        return gray, main_face, self.build_result(main_face, label, confidence)

    def recognize_frame(self, frame):
        gray, faces = self.detector.detect_faces(frame)
        results = []

        if not self.is_ready():
            return gray, faces, results

        for x, y, w, h in faces:
            face_roi = gray[y : y + h, x : x + w]
            face_roi = preprocess_face_image(face_roi)
            label, confidence = self.recognizer.predict(face_roi)
            results.append(self.build_result((x, y, w, h), label, confidence))

        return gray, faces, results
