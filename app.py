from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import math
from functools import wraps

app = Flask(__name__)

# Secret key untuk session dan flash message
app.secret_key = "employee-app-secret-key"


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "employee_db"
}


def get_db():
    conn = mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"]
    )

    return conn


# =========================================================
# LOGIN REQUIRED DECORATOR
# =========================================================

def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Silakan login terlebih dahulu.",
                "error"
            )

            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # Jika sudah login, langsung ke dashboard
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Validasi input
        if not username or not password:

            flash(
                "Username dan password wajib diisi.",
                "error"
            )

            return render_template("login.html")

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Cari user
        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE username = %s
            AND password = %s
            """,
            (username, password)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:

            # Simpan informasi user ke session
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            flash(
                "Login berhasil. Selamat datang!",
                "success"
            )

            return redirect(url_for("index"))

        else:

            flash(
                "Username atau password salah.",
                "error"
            )

            return render_template("login.html")

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "Anda telah berhasil logout.",
        "success"
    )

    return redirect(url_for("login"))


# =========================================================
# DASHBOARD + SEARCH + FILTER + PAGINATION
# =========================================================

@app.route("/")
@login_required
def index():

    search = request.args.get("search", "").strip()
    departemen = request.args.get("departemen", "").strip()

    # Pagination
    page = request.args.get("page", 1, type=int)

    if page < 1:
        page = 1

    per_page = 5

    offset = (page - 1) * per_page

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # =====================================================
    # TOTAL KARYAWAN
    # =====================================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM karyawan
    """)

    total_karyawan = cursor.fetchone()["total"]

    # =====================================================
    # STATISTIK DEPARTEMEN
    # =====================================================

    cursor.execute("""
        SELECT departemen, COUNT(*) AS total
        FROM karyawan
        GROUP BY departemen
        ORDER BY departemen ASC
    """)

    department_stats = cursor.fetchall()

    # =====================================================
    # SEARCH + FILTER
    # =====================================================

    base_query = """
        FROM karyawan
        WHERE 1=1
    """

    params = []

    if search:

        base_query += """
            AND (
                nama LIKE %s
                OR email LIKE %s
                OR jabatan LIKE %s
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value
        ])

    if departemen:

        base_query += """
            AND departemen = %s
        """

        params.append(departemen)

    # =====================================================
    # TOTAL DATA
    # =====================================================

    cursor.execute(
        "SELECT COUNT(*) AS total " + base_query,
        params
    )

    total_data = cursor.fetchone()["total"]

    total_pages = math.ceil(
        total_data / per_page
    )

    # Jika halaman melebihi halaman terakhir
    if total_pages > 0 and page > total_pages:

        page = total_pages

        offset = (page - 1) * per_page

    # =====================================================
    # AMBIL DATA KARYAWAN
    # =====================================================

    data_query = """
        SELECT *
    """ + base_query + """
        ORDER BY id DESC
        LIMIT %s OFFSET %s
    """

    data_params = params + [
        per_page,
        offset
    ]

    cursor.execute(
        data_query,
        data_params
    )

    karyawan = cursor.fetchall()

    # =====================================================
    # DAFTAR DEPARTEMEN
    # =====================================================

    cursor.execute("""
        SELECT DISTINCT departemen
        FROM karyawan
        ORDER BY departemen ASC
    """)

    departemen_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "index.html",

        karyawan=karyawan,
        departemen_list=departemen_list,

        search=search,
        departemen=departemen,

        total_karyawan=total_karyawan,
        department_stats=department_stats,

        page=page,
        per_page=per_page,
        total_data=total_data,
        total_pages=total_pages,

        username=session.get("username")
    )


# =========================================================
# TAMBAH KARYAWAN
# =========================================================

@app.route("/tambah", methods=["GET", "POST"])
@login_required
def tambah():

    if request.method == "POST":

        nama = request.form.get(
            "nama",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        jabatan = request.form.get(
            "jabatan",
            ""
        ).strip()

        departemen = request.form.get(
            "departemen",
            ""
        ).strip()

        # =================================================
        # VALIDASI
        # =================================================

        if not nama or not email or not jabatan or not departemen:

            flash(
                "Semua field wajib diisi.",
                "error"
            )

            return render_template(
                "tambah.html",

                nama=nama,
                email=email,
                jabatan=jabatan,
                departemen=departemen
            )

        # Validasi email sederhana
        if "@" not in email or "." not in email:

            flash(
                "Format email tidak valid.",
                "error"
            )

            return render_template(
                "tambah.html",

                nama=nama,
                email=email,
                jabatan=jabatan,
                departemen=departemen
            )

        conn = get_db()
        cursor = conn.cursor()

        # =================================================
        # CEK EMAIL
        # =================================================

        cursor.execute(
            """
            SELECT id
            FROM karyawan
            WHERE email = %s
            """,
            (email,)
        )

        existing_email = cursor.fetchone()

        if existing_email:

            cursor.close()
            conn.close()

            flash(
                "Email tersebut sudah digunakan.",
                "error"
            )

            return render_template(
                "tambah.html",

                nama=nama,
                email=email,
                jabatan=jabatan,
                departemen=departemen
            )

        # =================================================
        # INSERT
        # =================================================

        cursor.execute(
            """
            INSERT INTO karyawan
            (
                nama,
                email,
                jabatan,
                departemen
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                nama,
                email,
                jabatan,
                departemen
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        flash(
            "Data karyawan berhasil ditambahkan.",
            "success"
        )

        return redirect(
            url_for("index")
        )

    return render_template(
        "tambah.html"
    )


# =========================================================
# EDIT KARYAWAN
# =========================================================

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):

    conn = get_db()
    cursor = conn.cursor(
        dictionary=True
    )

    # Ambil data
    cursor.execute(
        """
        SELECT *
        FROM karyawan
        WHERE id = %s
        """,
        (id,)
    )

    data = cursor.fetchone()

    if data is None:

        cursor.close()
        conn.close()

        flash(
            "Data karyawan tidak ditemukan.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    # =====================================================
    # UPDATE
    # =====================================================

    if request.method == "POST":

        nama = request.form.get(
            "nama",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        jabatan = request.form.get(
            "jabatan",
            ""
        ).strip()

        departemen = request.form.get(
            "departemen",
            ""
        ).strip()

        # Validasi field
        if not nama or not email or not jabatan or not departemen:

            cursor.close()
            conn.close()

            flash(
                "Semua field wajib diisi.",
                "error"
            )

            return render_template(
                "edit.html",

                data={
                    "id": id,
                    "nama": nama,
                    "email": email,
                    "jabatan": jabatan,
                    "departemen": departemen
                }
            )

        # Validasi email
        if "@" not in email or "." not in email:

            cursor.close()
            conn.close()

            flash(
                "Format email tidak valid.",
                "error"
            )

            return render_template(
                "edit.html",

                data={
                    "id": id,
                    "nama": nama,
                    "email": email,
                    "jabatan": jabatan,
                    "departemen": departemen
                }
            )

        # Cek email
        cursor.execute(
            """
            SELECT id
            FROM karyawan
            WHERE email = %s
            AND id != %s
            """,
            (email, id)
        )

        existing_email = cursor.fetchone()

        if existing_email:

            cursor.close()
            conn.close()

            flash(
                "Email tersebut sudah digunakan oleh karyawan lain.",
                "error"
            )

            return render_template(
                "edit.html",

                data={
                    "id": id,
                    "nama": nama,
                    "email": email,
                    "jabatan": jabatan,
                    "departemen": departemen
                }
            )

        # Update
        cursor.execute(
            """
            UPDATE karyawan
            SET
                nama = %s,
                email = %s,
                jabatan = %s,
                departemen = %s
            WHERE id = %s
            """,
            (
                nama,
                email,
                jabatan,
                departemen,
                id
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        flash(
            "Data karyawan berhasil diperbarui.",
            "success"
        )

        return redirect(
            url_for("index")
        )

    cursor.close()
    conn.close()

    return render_template(
        "edit.html",
        data=data
    )


# =========================================================
# HAPUS
# =========================================================

@app.route("/hapus/<int:id>")
@login_required
def hapus(id):

    conn = get_db()
    cursor = conn.cursor()

    # Cek data
    cursor.execute(
        """
        SELECT id
        FROM karyawan
        WHERE id = %s
        """,
        (id,)
    )

    data = cursor.fetchone()

    if data is None:

        cursor.close()
        conn.close()

        flash(
            "Data karyawan tidak ditemukan.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    # Delete
    cursor.execute(
        """
        DELETE FROM karyawan
        WHERE id = %s
        """,
        (id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    flash(
        "Data karyawan berhasil dihapus.",
        "success"
    )

    return redirect(
        url_for("index")
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )