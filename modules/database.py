import os
import sqlite3
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "attendance.db")
DEFAULT_SUBJECT_ID = "DEFAULT"
DEFAULT_SECTION_ID = "DEFAULT_SECTION"


def get_connection():
    """Tạo kết nối SQLite và bật khóa ngoại."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return column_name in [row[1] for row in cursor.fetchall()]


def init_database():
    """Tạo bảng và migrate schema, không tự tạo dữ liệu môn/lớp học phần."""
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
        migrate_students_table(conn)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id TEXT PRIMARY KEY,
                subject_name TEXT NOT NULL,
                teacher_name TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS course_sections (
                section_id TEXT PRIMARY KEY,
                subject_id TEXT,
                section_name TEXT,
                start_time TEXT,
                late_time TEXT,
                FOREIGN KEY(subject_id) REFERENCES subjects(subject_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS section_students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                UNIQUE(section_id, student_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                subject_id TEXT,
                section_id TEXT,
                attendance_date TEXT,
                date TEXT,
                time TEXT,
                check_in_time TEXT,
                check_out_time TEXT,
                status TEXT,
                created_at TEXT,
                FOREIGN KEY(student_id) REFERENCES students(student_id)
            )
            """
        )

        if not column_exists(cursor, "attendance", "subject_id"):
            cursor.execute("ALTER TABLE attendance ADD COLUMN subject_id TEXT")
        if not column_exists(cursor, "attendance", "attendance_date"):
            cursor.execute("ALTER TABLE attendance ADD COLUMN attendance_date TEXT")
        if not column_exists(cursor, "attendance", "check_in_time"):
            cursor.execute("ALTER TABLE attendance ADD COLUMN check_in_time TEXT")
        if not column_exists(cursor, "attendance", "check_out_time"):
            cursor.execute("ALTER TABLE attendance ADD COLUMN check_out_time TEXT")
        if not column_exists(cursor, "attendance", "section_id"):
            cursor.execute("ALTER TABLE attendance ADD COLUMN section_id TEXT")
        if not column_exists(cursor, "attendance", "created_at"):
            cursor.execute("ALTER TABLE attendance ADD COLUMN created_at TEXT")

        # Đồng bộ dữ liệu cũ: trước đây app dùng cột date/time.
        cursor.execute(
            """
            UPDATE attendance
            SET attendance_date = COALESCE(attendance_date, date)
            WHERE attendance_date IS NULL
            """
        )
        cursor.execute(
            """
            UPDATE attendance
            SET created_at = COALESCE(created_at, datetime('now'))
            WHERE created_at IS NULL
            """
        )
        cursor.execute(
            """
            UPDATE attendance
            SET subject_id = (
                SELECT subject_id
                FROM course_sections
                WHERE course_sections.section_id = attendance.section_id
            )
            WHERE (subject_id IS NULL OR subject_id = '')
              AND section_id IS NOT NULL
              AND section_id <> ''
            """
        )

        # Nếu database cũ đã có lịch sử điểm danh, tự tạo quan hệ
        # sinh viên - lớp học phần từ các bản ghi attendance hiện có.
        cursor.execute(
            """
            INSERT OR IGNORE INTO section_students(section_id, student_id)
            SELECT DISTINCT section_id, student_id
            FROM attendance
            WHERE section_id IS NOT NULL
              AND section_id <> ''
              AND student_id IS NOT NULL
              AND student_id <> ''
            """
        )

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
                WHEN check_in_time > '07:30:00' THEN 'Đi trễ'
                ELSE 'Đúng giờ'
            END
            WHERE check_in_time IS NOT NULL AND (status IS NULL OR status = '')
            """
        )
        cursor.execute("UPDATE attendance SET status = 'Đi trễ' WHERE status = 'Late'")
        cursor.execute("UPDATE attendance SET status = 'Đúng giờ' WHERE status = 'Present'")

        cursor.execute("DROP INDEX IF EXISTS idx_attendance_student_date")
        cursor.execute(
            """
            DELETE FROM attendance
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM attendance
                GROUP BY student_id, section_id, attendance_date
            )
            """
        )
        cursor.execute("DROP INDEX IF EXISTS idx_attendance_student_section_date")
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_student_section_attendance_date
            ON attendance(student_id, section_id, attendance_date)
            """
        )
        conn.commit()


def migrate_students_table(conn):
    """Migrate bảng students sang schema mới có id/contact/created_at."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(students)")
    columns = [row[1] for row in cursor.fetchall()]

    if "id" in columns and "contact" in columns:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS students_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            contact TEXT,
            face_image_path TEXT,
            created_at TEXT
        )
        """
    )

    contact_expr = "contact" if "contact" in columns else "email"
    class_expr = "COALESCE(class_name, '')"
    cursor.execute(
        f"""
        INSERT OR IGNORE INTO students_new(student_id, full_name, class_name, contact, face_image_path, created_at)
        SELECT
            student_id,
            full_name,
            {class_expr},
            {contact_expr},
            NULL,
            datetime('now')
        FROM students
        WHERE student_id IS NOT NULL AND full_name IS NOT NULL
        """
    )
    cursor.execute("DROP TABLE students")
    cursor.execute("ALTER TABLE students_new RENAME TO students")
    conn.execute("PRAGMA foreign_keys = ON")


def add_student(student_id, full_name, class_name, contact):
    """Thêm sinh viên mới, trả về False nếu mã sinh viên bị trùng."""
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO students(student_id, full_name, class_name, contact, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (student_id, full_name, class_name, contact),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def upsert_student(student_id, full_name, class_name, contact):
    """Thêm sinh viên chung nếu chưa có, nếu đã có thì giữ dữ liệu hiện tại."""
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM students WHERE student_id = ?",
                (student_id,),
            )
            if cursor.fetchone():
                return False

            conn.execute(
                """
                INSERT INTO students(student_id, full_name, class_name, contact, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (student_id, full_name, class_name, contact),
            )
            conn.commit()
            return True
    except sqlite3.Error:
        raise


def delete_student(student_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        conn.commit()


def get_students():
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT student_id, full_name, class_name, contact FROM students ORDER BY student_id"
        )
        return cursor.fetchall()


def get_students_by_section(section_id):
    """Lấy danh sách sinh viên thuộc một lớp học phần."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT s.student_id, s.full_name, s.class_name, s.contact
            FROM section_students ss
            JOIN students s ON ss.student_id = s.student_id
            WHERE ss.section_id = ?
            ORDER BY s.student_id
            """,
            (section_id,),
        )
        return cursor.fetchall()


def get_student(student_id):
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT student_id, full_name, class_name, contact FROM students WHERE student_id = ?",
            (student_id,),
        )
        return cursor.fetchone()


def add_student_to_section(section_id, student_id):
    """Gắn sinh viên vào lớp học phần, trả về False nếu đã có trong lớp."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO section_students(section_id, student_id) VALUES (?, ?)",
                (section_id, student_id),
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def remove_student_from_section(section_id, student_id):
    """Chỉ xóa quan hệ sinh viên khỏi lớp học phần, không xóa bảng students."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM section_students WHERE section_id = ? AND student_id = ?",
            (section_id, student_id),
        )
        conn.commit()
        return cursor.rowcount


def is_student_in_section(section_id, student_id):
    """Kiểm tra sinh viên có thuộc lớp học phần đang điểm danh không."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM section_students WHERE section_id = ? AND student_id = ?",
            (section_id, student_id),
        )
        return cursor.fetchone() is not None


def add_subject(subject_id, subject_name, teacher_name):
    """Thêm môn học, trả về False nếu mã môn bị trùng."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO subjects(subject_id, subject_name, teacher_name) VALUES (?, ?, ?)",
                (subject_id, subject_name, teacher_name),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_subjects():
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT subject_id, subject_name, teacher_name FROM subjects ORDER BY subject_id"
        )
        return cursor.fetchall()


def delete_subject(subject_id):
    """Xóa môn học nếu không còn lớp học phần phụ thuộc."""
    with get_connection() as conn:
        section_count = conn.execute(
            "SELECT COUNT(*) FROM course_sections WHERE subject_id = ?",
            (subject_id,),
        ).fetchone()[0]
        if section_count > 0:
            return False, "Không thể xóa môn học vì vẫn còn lớp học phần thuộc môn này."

        cursor = conn.execute("DELETE FROM subjects WHERE subject_id = ?", (subject_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Không tìm thấy môn học cần xóa."
        return True, "Đã xóa môn học."


def add_course_section(section_id, subject_id, section_name, start_time, late_time):
    """Thêm lớp học phần, trả về False nếu mã lớp học phần bị trùng."""
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO course_sections(section_id, subject_id, section_name, start_time, late_time)
                VALUES (?, ?, ?, ?, ?)
                """,
                (section_id, subject_id, section_name, start_time, late_time),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_course_sections():
    """Lấy danh sách lớp học phần kèm tên môn học."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT
                cs.section_id,
                cs.subject_id,
                COALESCE(s.subject_name, ''),
                cs.section_name,
                cs.start_time,
                cs.late_time
            FROM course_sections cs
            LEFT JOIN subjects s ON cs.subject_id = s.subject_id
            ORDER BY cs.section_id
            """
        )
        return cursor.fetchall()


def get_course_section(section_id):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT
                cs.section_id,
                cs.subject_id,
                COALESCE(s.subject_name, ''),
                cs.section_name,
                cs.start_time,
                cs.late_time
            FROM course_sections cs
            LEFT JOIN subjects s ON cs.subject_id = s.subject_id
            WHERE cs.section_id = ?
            """,
            (section_id,),
        )
        return cursor.fetchone()


def delete_course_section(section_id):
    """Xóa lớp học phần nếu chưa được dùng trong lịch sử điểm danh."""
    with get_connection() as conn:
        attendance_count = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE section_id = ?",
            (section_id,),
        ).fetchone()[0]
        if attendance_count > 0:
            return False, "Không thể xóa lớp học phần vì đang được dùng trong lịch sử điểm danh."

        conn.execute("DELETE FROM section_students WHERE section_id = ?", (section_id,))
        cursor = conn.execute("DELETE FROM course_sections WHERE section_id = ?", (section_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "Không tìm thấy lớp học phần cần xóa."
        return True, "Đã xóa lớp học phần."


def delete_default_course_data():
    """Xóa DEFAULT/DEFAULT_SECTION nếu dữ liệu mặc định không còn được dùng."""
    with get_connection() as conn:
        attendance_count = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE section_id = ?",
            (DEFAULT_SECTION_ID,),
        ).fetchone()[0]
        if attendance_count > 0:
            return (
                False,
                "Không thể xóa DEFAULT_SECTION vì đang được dùng trong lịch sử điểm danh.",
            )

        conn.execute("DELETE FROM section_students WHERE section_id = ?", (DEFAULT_SECTION_ID,))
        conn.execute("DELETE FROM course_sections WHERE section_id = ?", (DEFAULT_SECTION_ID,))
        subject_section_count = conn.execute(
            "SELECT COUNT(*) FROM course_sections WHERE subject_id = ?",
            (DEFAULT_SUBJECT_ID,),
        ).fetchone()[0]
        if subject_section_count == 0:
            conn.execute("DELETE FROM subjects WHERE subject_id = ?", (DEFAULT_SUBJECT_ID,))
        conn.commit()
        return True, "Đã xóa dữ liệu mặc định DEFAULT/DEFAULT_SECTION nếu tồn tại."


def get_today_attendance(student_id, section_id, date_text):
    """Lấy bản ghi check-in/check-out theo sinh viên, lớp học phần và ngày."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, check_in_time, check_out_time, status
            FROM attendance
            WHERE student_id = ? AND section_id = ? AND attendance_date = ?
            LIMIT 1
            """,
            (student_id, section_id, date_text),
        )
        return cursor.fetchone()


def add_check_in(student_id, subject_id, section_id, date_text, check_in_time, status):
    """Tạo bản ghi check-in đầu tiên trong ngày của một lớp học phần."""
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO attendance(
                    student_id,
                    subject_id,
                    section_id,
                    attendance_date,
                    date,
                    time,
                    check_in_time,
                    check_out_time,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, datetime('now'))
                """,
                (student_id, subject_id, section_id, date_text, date_text, check_in_time, check_in_time, status),
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError as error:
        print(f"Lỗi insert attendance: {error}")
        return False
    except sqlite3.Error as error:
        print(f"Lỗi database khi điểm danh: {error}")
        raise


def update_check_out(attendance_id, check_out_time):
    """Cập nhật check-out cho bản ghi đã check-in."""
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE attendance SET check_out_time = ? WHERE id = ? AND check_out_time IS NULL",
            (check_out_time, attendance_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_attendance_history(date_filter=None):
    query = """
        SELECT
            a.student_id,
            st.full_name,
            st.class_name,
            COALESCE(sb.subject_name, ''),
            COALESCE(cs.section_name, a.section_id, ''),
            a.date,
            a.check_in_time,
            COALESCE(a.check_out_time, 'Chưa check-out'),
            a.status
        FROM attendance a
        LEFT JOIN students st ON a.student_id = st.student_id
        LEFT JOIN course_sections cs ON a.section_id = cs.section_id
        LEFT JOIN subjects sb ON cs.subject_id = sb.subject_id
    """
    params = ()
    if date_filter:
        query += " WHERE a.date = ?"
        params = (date_filter,)
    query += " ORDER BY a.date DESC, a.check_in_time DESC"

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchall()


def get_attendance_history(section_id=None, date_filter=None):
    """Lấy lịch sử điểm danh, có thể lọc theo lớp học phần và ngày."""
    query = """
        SELECT
            a.student_id,
            st.full_name,
            st.class_name,
            COALESCE(sb.subject_name, sb2.subject_name, ''),
            COALESCE(cs.section_name, a.section_id, ''),
            a.attendance_date,
            a.check_in_time,
            COALESCE(a.check_out_time, 'Chưa check-out'),
            a.status
        FROM attendance a
        LEFT JOIN students st ON a.student_id = st.student_id
        LEFT JOIN course_sections cs ON a.section_id = cs.section_id
        LEFT JOIN subjects sb ON cs.subject_id = sb.subject_id
        LEFT JOIN subjects sb2 ON a.subject_id = sb2.subject_id
    """
    where_clauses = []
    params = []
    if section_id:
        where_clauses.append("a.section_id = ?")
        params.append(section_id)
    if date_filter:
        where_clauses.append("a.attendance_date = ?")
        params.append(date_filter)
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY a.attendance_date DESC, a.check_in_time DESC"

    with get_connection() as conn:
        cursor = conn.execute(query, tuple(params))
        return cursor.fetchall()


def delete_today_attendance():
    """Xóa toàn bộ lịch sử check-in/check-out hôm nay, không đụng dữ liệu khác."""
    today = datetime.now().strftime("%Y-%m-%d")
    return delete_attendance_by_date(today)


def delete_attendance_by_date(date_str):
    """Xóa lịch sử điểm danh theo ngày YYYY-MM-DD và trả về số dòng đã xóa."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM attendance WHERE attendance_date = ?", (date_str,))
        conn.commit()
        return cursor.rowcount


def delete_all_attendance():
    """Xóa toàn bộ lịch sử điểm danh, không xóa sinh viên/ảnh/model."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM attendance")
        conn.commit()
        return cursor.rowcount


def recalculate_attendance_statuses():
    """Cập nhật lại status Late/Present theo late_time hiện tại của từng lớp học phần."""
    from modules.attendance_service import DEFAULT_LATE_TIME, calculate_attendance_status

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                a.id,
                a.check_in_time,
                COALESCE(cs.late_time, ?)
            FROM attendance a
            LEFT JOIN course_sections cs ON a.section_id = cs.section_id
            WHERE a.check_in_time IS NOT NULL
            """,
            (DEFAULT_LATE_TIME,),
        ).fetchall()

        updated_count = 0
        for attendance_id, check_in_time, late_time in rows:
            new_status = calculate_attendance_status(check_in_time, late_time)
            cursor = conn.execute(
                "UPDATE attendance SET status = ? WHERE id = ? AND COALESCE(status, '') <> ?",
                (new_status, attendance_id, new_status),
            )
            updated_count += cursor.rowcount

        conn.commit()
        return updated_count


def get_dashboard_stats(section_id=None):
    """Lấy số liệu dashboard, có thể lọc theo lớp học phần."""
    today = datetime.now().strftime("%Y-%m-%d")
    params = [today]
    section_clause = ""
    if section_id:
        section_clause = " AND section_id = ?"
        params.append(section_id)

    with get_connection() as conn:
        if section_id:
            total_students = conn.execute(
                "SELECT COUNT(*) FROM section_students WHERE section_id = ?",
                (section_id,),
            ).fetchone()[0]
        else:
            total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]

        checked_in_today = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM attendance
            WHERE attendance_date = ? AND check_in_time IS NOT NULL{section_clause}
            """,
            tuple(params),
        ).fetchone()[0]
        late_today = conn.execute(
            f"SELECT COUNT(*) FROM attendance WHERE attendance_date = ? AND status = 'Đi trễ'{section_clause}",
            tuple(params),
        ).fetchone()[0]
        not_checked_out_today = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM attendance
            WHERE attendance_date = ?
              AND check_in_time IS NOT NULL
              AND check_out_time IS NULL{section_clause}
            """,
            tuple(params),
        ).fetchone()[0]

    not_checked_in_today = max(total_students - checked_in_today, 0)
    return {
        "total_students": total_students,
        "checked_in_today": checked_in_today,
        "not_checked_in_today": not_checked_in_today,
        "late_today": late_today,
        "not_checked_out_today": not_checked_out_today,
    }
