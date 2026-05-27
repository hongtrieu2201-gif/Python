from datetime import datetime, time

from modules.database import add_check_in, get_course_section, get_today_attendance, update_check_out


DEFAULT_LATE_TIME = "07:30:00"


def parse_time_value(value, default=DEFAULT_LATE_TIME):
    """Chuyển chuỗi giờ về datetime.time, hỗ trợ 7:30, 07:30, 07:30:00."""
    if isinstance(value, time):
        return value

    text = str(value or "").strip()
    if not text:
        text = default

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue

    # Nếu format bị lỗi, dùng mốc mặc định 07:30:00.
    return datetime.strptime(default, "%H:%M:%S").time()


def calculate_attendance_status(check_in_time, late_time):
    """Tính Present/Late bằng kiểu datetime.time, không so sánh chuỗi."""
    check_in = parse_time_value(check_in_time)
    late = parse_time_value(late_time)
    return "Đi trễ" if check_in > late else "Đúng giờ"


class AttendanceService:
    """Xử lý nghiệp vụ check-in/check-out theo lớp học phần."""

    def mark_present(self, student_id, section_id):
        """Xử lý một lần quét mặt trong một lớp học phần cụ thể."""
        now = datetime.now()
        date_text = now.strftime("%Y-%m-%d")
        time_text = now.strftime("%H:%M:%S")

        section = get_course_section(section_id)
        subject_id = section[1] if section else None
        late_time = section[5] if section and section[5] else DEFAULT_LATE_TIME

        attendance = get_today_attendance(student_id, section_id, date_text)
        if attendance is None:
            status = calculate_attendance_status(time_text, late_time)
            inserted = add_check_in(student_id, subject_id, section_id, date_text, time_text, status)
            if inserted:
                return {
                    "action": "check_in",
                    "date": date_text,
                    "check_in_time": time_text,
                    "check_out_time": None,
                    "status": status,
                    "late_time": late_time,
                }

            attendance = get_today_attendance(student_id, section_id, date_text)
            if attendance is None:
                return {
                    "action": "error",
                    "date": date_text,
                    "check_in_time": None,
                    "check_out_time": None,
                    "status": "Lỗi lưu điểm danh",
                    "late_time": late_time,
                }

        attendance_id, check_in_time, check_out_time, status = attendance
        if check_out_time is None:
            update_check_out(attendance_id, time_text)
            return {
                "action": "check_out",
                "date": date_text,
                "check_in_time": check_in_time,
                "check_out_time": time_text,
                "status": status,
                "late_time": late_time,
            }

        return {
            "action": "already_checked_out",
            "date": date_text,
            "check_in_time": check_in_time,
            "check_out_time": check_out_time,
            "status": status,
            "late_time": late_time,
        }
