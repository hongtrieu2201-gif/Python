from datetime import datetime

from modules.database import add_attendance, get_attendance_time


class AttendanceService:
    """Xử lý nghiệp vụ điểm danh, tránh lưu trùng trong cùng một ngày."""

    def mark_present(self, student_id):
        """Điểm danh sinh viên và trả về giờ cũ nếu hôm nay đã điểm danh."""
        now = datetime.now()
        date_text = now.strftime("%Y-%m-%d")
        time_text = now.strftime("%H:%M:%S")

        old_time = get_attendance_time(student_id, date_text)
        if old_time:
            return {
                "inserted": False,
                "date": date_text,
                "time": old_time,
                "old_time": old_time,
            }

        inserted = add_attendance(student_id, date_text, time_text, "Present")
        if inserted:
            return {
                "inserted": True,
                "date": date_text,
                "time": time_text,
                "old_time": None,
            }

        # Trường hợp hiếm: database đã có dòng do lần insert gần như đồng thời.
        old_time = get_attendance_time(student_id, date_text)
        return {
            "inserted": False,
            "date": date_text,
            "time": old_time or time_text,
            "old_time": old_time or time_text,
        }
