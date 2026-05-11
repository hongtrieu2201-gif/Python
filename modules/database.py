import os
import sqlite3
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "attendance.db")


def get_connection():
    """Tạo kết nối SQLite và bật khóa ngoại."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """Tạo các bảng cần thiết nếu chưa tồn tại."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                class_name TEXT,
                email TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                date TEXT,
                time TEXT,
                status TEXT,
                FOREIGN KEY(student_id) REFERENCES students(student_id)
            )
            """
        )

        # Nếu từng có dữ liệu trùng trước đó, giữ lại dòng đầu tiên trong ngày.
        cursor.execute(
            """
            DELETE FROM attendance
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM attendance
                GROUP BY student_id, date
            )
            """
        )

        # Chặn trùng ở tầng database: mỗi sinh viên chỉ có 1 dòng trong 1 ngày.
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_student_date
            ON attendance(student_id, date)
            """
        )
        conn.commit()


def add_student(student_id, full_name, class_name, email):
    """Thêm sinh viên mới, trả về False nếu mã sinh viên bị trùng."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO students(student_id, full_name, class_name, email) VALUES (?, ?, ?, ?)",
                (student_id, full_name, class_name, email),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def delete_student(student_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        conn.commit()


def get_students():
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT student_id, full_name, class_name, email FROM students ORDER BY student_id"
        )
        return cursor.fetchall()


def get_student(student_id):
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT student_id, full_name, class_name, email FROM students WHERE student_id = ?",
            (student_id,),
        )
        return cursor.fetchone()


def get_attendance_time(student_id, date_text):
    """Lấy giờ điểm danh cũ của sinh viên trong một ngày, nếu đã có."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT time
            FROM attendance
            WHERE student_id = ? AND date = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (student_id, date_text),
        )
        row = cursor.fetchone()
        return row[0] if row else None


def add_attendance(student_id, date_text, time_text, status="Present"):
    """Lưu điểm danh nếu sinh viên chưa được điểm danh trong ngày."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO attendance(student_id, date, time, status) VALUES (?, ?, ?, ?)",
                (student_id, date_text, time_text, status),
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def get_attendance_history(date_filter=None):
    query = """
        SELECT a.student_id, s.full_name, s.class_name, a.date, a.time, a.status
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.student_id
    """
    params = ()
    if date_filter:
        query += " WHERE a.date = ?"
        params = (date_filter,)
    query += " ORDER BY a.date DESC, a.time DESC"

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchall()


def get_dashboard_stats():
    """Lấy các số liệu tổng quan để hiển thị trên trang chủ."""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        attended_today = conn.execute(
            "SELECT COUNT(DISTINCT student_id) FROM attendance WHERE date = ?",
            (today,),
        ).fetchone()[0]

    not_attended_today = max(total_students - attended_today, 0)
    return {
        "total_students": total_students,
        "attended_today": attended_today,
        "not_attended_today": not_attended_today,
    }
