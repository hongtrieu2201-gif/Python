from datetime import datetime

from modules.database import add_check_in, get_today_attendance, update_check_out


CHECK_IN_DEADLINE = "07:30:00"


class AttendanceService:
    """Xử lý nghiệp vụ check-in/check-out, không tạo nhiều dòng trong cùng ngày."""

    def mark_present(self, student_id):
        """Xử lý một lần quét khuôn mặt của sinh viên."""
        now = datetime.now()
        date_text = now.strftime("%Y-%m-%d")
        time_text = now.strftime("%H:%M:%S")

        attendance = get_today_attendance(student_id, date_text)
        if attendance is None:
            status = "Late" if time_text > CHECK_IN_DEADLINE else "Present"
            inserted = add_check_in(student_id, date_text, time_text, status)
            if inserted:
                return {
                    "action": "check_in",
                    "date": date_text,
                    "check_in_time": time_text,
                    "check_out_time": None,
                    "status": status,
                }

            # Trường hợp hiếm: đã có dòng do insert gần như đồng thời.
            attendance = get_today_attendance(student_id, date_text)

        attendance_id, check_in_time, check_out_time, status = attendance
        if check_out_time is None:
            update_check_out(attendance_id, time_text)
            return {
                "action": "check_out",
                "date": date_text,
                "check_in_time": check_in_time,
                "check_out_time": time_text,
                "status": status,
            }

        return {
            "action": "already_checked_out",
            "date": date_text,
            "check_in_time": check_in_time,
            "check_out_time": check_out_time,
            "status": status,
        }
