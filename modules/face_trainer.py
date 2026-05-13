import json
import os

import cv2
import numpy as np
from PIL import Image


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset", "students")
MODELS_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "face_model.yml")
LABEL_MAP_PATH = os.path.join(MODELS_DIR, "label_map.json")
FACE_SIZE = (200, 200)


def preprocess_face_image(gray_face):
    """Chuẩn hóa ảnh mặt cho LBPH: grayscale, equalizeHist, resize 200x200."""
    if len(gray_face.shape) == 3:
        gray_face = cv2.cvtColor(gray_face, cv2.COLOR_BGR2GRAY)
    gray_face = cv2.equalizeHist(gray_face)
    gray_face = cv2.resize(gray_face, FACE_SIZE)
    return gray_face.astype(np.uint8)


def train_model():
    """Train LBPH từ toàn bộ ảnh trong dataset/students."""
    os.makedirs(DATASET_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    face_images = []
    labels = []
    label_map = {}
    current_label = 0

    for student_id in sorted(os.listdir(DATASET_DIR)):
        student_dir = os.path.join(DATASET_DIR, student_id)
        if not os.path.isdir(student_dir):
            continue

        student_images = []
        for file_name in os.listdir(student_dir):
            if not file_name.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            image_path = os.path.join(student_dir, file_name)
            image = Image.open(image_path).convert("L")
            image_np = np.array(image, dtype=np.uint8)
            student_images.append(preprocess_face_image(image_np))

        if not student_images:
            continue

        label_map[str(current_label)] = student_id
        face_images.extend(student_images)
        labels.extend([current_label] * len(student_images))
        current_label += 1

    if not face_images:
        return False, "Chưa có ảnh khuôn mặt để train model.", 0

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(face_images, np.array(labels))
    recognizer.write(MODEL_PATH)

    with open(LABEL_MAP_PATH, "w", encoding="utf-8") as file:
        json.dump(label_map, file, ensure_ascii=False, indent=4)

    return True, "Train model thành công.", len(face_images)
