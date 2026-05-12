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


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def init_database():
    """Tạo bảng và migrate attendance sang mô hình check-in/check-out."""
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

        if not column_exists(cursor, "attendance", "check_in_time"):
            cursor.execute("ALTER TABLE attendance ADD COLUMN check_in_time TEXT")
        if not column_exists(cursor, "attendance", "check_out_time"):
            cursor.execute("ALTER TABLE attendance ADD COLUMN check_out_time TEXT")

        # Dữ liệu cũ dùng cột time, chuyển sang check_in_time để không mất lịch sử.
        cursor.execute(
            """
            UPDATE attendance
            SET check_in_time = COALESCE(check_in_time, time)
            WHERE check_in_time IS NULL
            """
        )
        cursor.execute(
            """
            UPDATE attendance
            SET status = CASE
                WHEN check_in_time > '07:30:00' THEN 'Late'
                ELSE 'Present'
            END
            WHERE check_in_time IS NOT NULL
            """
        )

        # Nếu từng có dữ liệu trùng, giữ lại dòng đầu tiên của mỗi sinh viên trong ngày.
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


def get_today_attendance(student_id, date_text):
    """Lấy bản ghi check-in/check-out trong ngày của một sinh viên."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, check_in_time, check_out_time, status
            FROM attendance
            WHERE student_id = ? AND date = ?
            LIMIT 1
            """,
            (student_id, date_text),
        )
        return cursor.fetchone()


def add_check_in(student_id, date_text, check_in_time, status):
    """Tạo bản ghi check-in đầu tiên trong ngày."""
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO attendance(student_id, date, time, check_in_time, check_out_time, status)
                VALUES (?, ?, ?, ?, NULL, ?)
                """,
                (student_id, date_text, check_in_time, check_in_time, status),
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def update_check_out(attendance_id, check_out_time):
    """Cập nhật check-out cho bản ghi đã check-in."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE attendance SET check_out_time = ? WHERE id = ? AND check_out_time IS NULL",
            (check_out_time, attendance_id),
        )
        conn.commit()
        return conn.total_changes > 0


def get_attendance_history(date_filter=None):
    query = """
        SELECT
            a.student_id,
            s.full_name,
            s.class_name,
            a.date,
            a.check_in_time,
            COALESCE(a.check_out_time, 'Chưa check-out'),
            a.status
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.student_id
    """
    params = ()
    if date_filter:
        query += " WHERE a.date = ?"
        params = (date_filter,)
    query += " ORDER BY a.date DESC, a.check_in_time DESC"

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchall()


def delete_today_attendance():
    """Xóa toàn bộ lịch sử check-in/check-out hôm nay, không đụng dữ liệu khác."""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM attendance WHERE date = ?", (today,))
        conn.commit()
        return cursor.rowcount


def get_dashboard_stats():
    """Lấy số liệu tổng quan cho dashboard."""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        checked_in_today = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE date = ? AND check_in_time IS NOT NULL",
            (today,),
        ).fetchone()[0]
        late_today = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Late'",
            (today,),
        ).fetchone()[0]
        not_checked_out_today = conn.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE date = ?
              AND check_in_time IS NOT NULL
              AND check_out_time IS NULL
            """,
            (today,),
        ).fetchone()[0]

    not_checked_in_today = max(total_students - checked_in_today, 0)
    return {
        "total_students": total_students,
        "checked_in_today": checked_in_today,
        "not_checked_in_today": not_checked_in_today,
        "late_today": late_today,
        "not_checked_out_today": not_checked_out_today,
    }
