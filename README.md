# Face Attendance Desktop

## Giới thiệu đề tài

Face Attendance Desktop là phần mềm desktop nhận diện khuôn mặt để điểm danh sinh viên bằng Python. Ứng dụng dùng giao diện PyQt6, mở webcam trực tiếp trong cửa sổ phần mềm và lưu dữ liệu bằng SQLite.

Project này được xây dựng lại theo hướng desktop app, không dùng Streamlit, Flask, Django hoặc web server.

## Công nghệ sử dụng

- Python 3
- PyQt6
- OpenCV và OpenCV LBPH Face Recognizer
- NumPy
- Pandas
- Pillow
- SQLite

## Chức năng chính

- Trang chủ giới thiệu quy trình sử dụng.
- Quản lý sinh viên: thêm, xem danh sách, xóa sinh viên, kiểm tra trùng mã sinh viên.
- Đăng ký khuôn mặt: mở webcam, detect mặt bằng Haar Cascade, lưu nhiều ảnh cho mỗi sinh viên.
- Huấn luyện model: train LBPH từ ảnh trong `dataset/students`.
- Điểm danh webcam: nhận diện realtime, vẽ khung khuôn mặt, tự lưu điểm danh.
- Lịch sử điểm danh: xem bảng lịch sử, lọc theo ngày, xuất CSV.

## Cấu trúc thư mục

```text
face_attendance_desktop/
|-- main.py
|-- requirements.txt
|-- README.md
|
|-- database/
|   `-- attendance.db
|
|-- dataset/
|   `-- students/
|
|-- models/
|   |-- face_model.yml
|   `-- label_map.json
|
|-- modules/
|   |-- database.py
|   |-- face_detector.py
|   |-- face_trainer.py
|   |-- face_recognizer.py
|   `-- attendance_service.py
|
`-- ui/
    |-- main_window.py
    |-- home_page.py
    |-- student_page.py
    |-- register_face_page.py
    |-- train_page.py
    |-- attendance_page.py
    `-- history_page.py
```

## Cài thư viện

Mở Terminal trong thư mục `face_attendance_desktop`, sau đó chạy:

```bash
pip install -r requirements.txt
```

## Chạy chương trình

```bash
python main.py
```

## Hướng dẫn sử dụng

1. Vào trang **Quản lý sinh viên** để thêm mã sinh viên, họ tên, lớp và email hoặc số điện thoại.
2. Vào trang **Đăng ký khuôn mặt**, chọn sinh viên, mở webcam và chụp nhiều ảnh khuôn mặt.
3. Vào trang **Huấn luyện model**, bấm **Train model** để tạo `models/face_model.yml`.
4. Vào trang **Điểm danh webcam**, bấm **Bắt đầu điểm danh** để nhận diện và lưu lịch sử.
5. Vào trang **Lịch sử điểm danh** để xem, lọc theo ngày hoặc xuất CSV.

## Lưu ý khi webcam không nhận mặt

- Ngồi gần camera.
- Bật đủ sáng.
- Nhìn thẳng vào camera.
- Tránh kính phản sáng.
- Chụp nhiều ảnh cho mỗi sinh viên, nên có nhiều góc mặt và biểu cảm nhẹ khác nhau.

## Ghi chú

- File `database/attendance.db` được tạo tự động khi chạy app lần đầu.
- File `models/face_model.yml` ban đầu là placeholder và sẽ được ghi lại sau khi train model.
- Cần cài đúng `opencv-contrib-python` vì LBPH nằm trong module `cv2.face`.
