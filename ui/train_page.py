from PyQt6.QtWidgets import QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from modules.face_trainer import train_model


class TrainPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        self.title = QLabel("Huấn luyện model LBPH")
        self.title.setObjectName("pageTitle")
        self.description = QLabel("Train model từ toàn bộ ảnh trong dataset/students.")
        self.description.setObjectName("mutedText")
        self.train_button = QPushButton("Train model")
        self.result_label = QLabel("Chưa train model trong phiên chạy này.")
        self.result_label.setObjectName("infoBox")

        self.train_button.clicked.connect(self.handle_train)

        layout.addWidget(self.title)
        layout.addWidget(self.description)
        layout.addWidget(self.train_button)
        layout.addWidget(self.result_label)
        layout.addStretch()

    def handle_train(self):
        success, message, image_count = train_model()
        if success:
            self.result_label.setText(f"{message} Số ảnh đã train: {image_count}")
            QMessageBox.information(self, "Train model", self.result_label.text())
        else:
            self.result_label.setText(message)
            QMessageBox.warning(self, "Train model", message)
