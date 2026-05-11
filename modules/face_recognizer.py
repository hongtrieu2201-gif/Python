import json
import os

import cv2

from modules.database import get_student
from modules.face_detector import FaceDetector
from modules.face_trainer import LABEL_MAP_PATH, MODEL_PATH


class FaceRecognizer:
    """Nhận diện sinh viên bằng model LBPH đã train."""

    def __init__(self, confidence_threshold=70):
        self.confidence_threshold = confidence_threshold
        self.detector = FaceDetector()
        self.recognizer = None
        self.label_map = {}
        self.load_model()

    def load_model(self):
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

    def recognize_frame(self, frame):
        gray, faces = self.detector.detect_faces(frame)
        results = []

        if not self.is_ready():
            return gray, faces, results

        for x, y, w, h in faces:
            face_roi = gray[y : y + h, x : x + w]
            label, confidence = self.recognizer.predict(face_roi)

            student_id = None
            student = None
            status = "Unknown"
            if confidence <= self.confidence_threshold:
                student_id = self.label_map.get(str(label))
                student = get_student(student_id) if student_id else None
                if student:
                    status = "Recognized"

            results.append(
                {
                    "rect": (x, y, w, h),
                    "student_id": student_id,
                    "student": student,
                    "confidence": confidence,
                    "status": status,
                }
            )

        return gray, faces, results
