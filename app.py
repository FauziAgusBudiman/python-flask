from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import math

app = Flask(__name__)

# Secret key digunakan untuk flash message
app.secret_key = "employee-app-secret-key"

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
# HALAMAN UTAMA + DASHBOARD + SEARCH + FILTER + PAGINATION
# =========================================================

@app.route("/")
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
    # DASHBOARD
    # =====================================================

    # Total seluruh karyawan
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM karyawan
    """)

    total_karyawan = cursor.fetchone()["total"]

    # Total karyawan per departemen
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
    # TOTAL DATA UNTUK PAGINATION
    # =====================================================

    cursor.execute(
        "SELECT COUNT(*) AS total " + base_query,
        params
    )

    total_data = cursor.fetchone()["total"]

    total_pages = math.ceil(total_data / per_page)

    # Jika page lebih besar dari halaman terakhir
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

    data_params = params + [per_page, offset]

    cursor.execute(data_query, data_params)

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

        # Dashboard
        total_karyawan=total_karyawan,
        department_stats=department_stats,

        # Pagination
        page=page,
        per_page=per_page,
        total_data=total_data,
        total_pages=total_pages
    )


# =========================================================
# TAMBAH KARYAWAN
# =========================================================

@app.route("/tambah", methods=["GET", "POST"])
def tambah():

    if request.method == "POST":

        nama = request.form.get("nama", "").strip()
        email = request.form.get("email", "").strip()
        jabatan = request.form.get("jabatan", "").strip()
        departemen = request.form.get("departemen", "").strip()

        # =========================
        # VALIDASI
        # =========================

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

        # Cek email sudah digunakan atau belum
        cursor.execute("""
            SELECT id
            FROM karyawan
            WHERE email = %s
        """, (email,))

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

        # =========================
        # INSERT DATA
        # =========================

        cursor.execute("""
            INSERT INTO karyawan
            (nama, email, jabatan, departemen)
            VALUES (%s, %s, %s, %s)
        """, (
            nama,
            email,
            jabatan,
            departemen
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash(
            "Data karyawan berhasil ditambahkan.",
            "success"
        )

        return redirect(url_for("index"))

    return render_template("tambah.html")


# =========================================================
# EDIT KARYAWAN
# =========================================================

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Ambil data berdasarkan ID
    cursor.execute("""
        SELECT *
        FROM karyawan
        WHERE id = %s
    """, (id,))

    data = cursor.fetchone()

    if data is None:

        cursor.close()
        conn.close()

        flash(
            "Data karyawan tidak ditemukan.",
            "error"
        )

        return redirect(url_for("index"))

    # =====================================================
    # UPDATE DATA
    # =====================================================

    if request.method == "POST":

        nama = request.form.get("nama", "").strip()
        email = request.form.get("email", "").strip()
        jabatan = request.form.get("jabatan", "").strip()
        departemen = request.form.get("departemen", "").strip()

        # Validasi field kosong
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

        # Cek apakah email digunakan karyawan lain
        cursor.execute("""
            SELECT id
            FROM karyawan
            WHERE email = %s
            AND id != %s
        """, (email, id))

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

        # Update database
        cursor.execute("""
            UPDATE karyawan
            SET
                nama = %s,
                email = %s,
                jabatan = %s,
                departemen = %s
            WHERE id = %s
        """, (
            nama,
            email,
            jabatan,
            departemen,
            id
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash(
            "Data karyawan berhasil diperbarui.",
            "success"
        )

        return redirect(url_for("index"))

    cursor.close()
    conn.close()

    return render_template(
        "edit.html",
        data=data
    )


# =========================================================
# HAPUS KARYAWAN
# =========================================================

@app.route("/hapus/<int:id>")
def hapus(id):

    conn = get_db()
    cursor = conn.cursor()

    # Cek apakah data ada
    cursor.execute("""
        SELECT id
        FROM karyawan
        WHERE id = %s
    """, (id,))

    data = cursor.fetchone()

    if data is None:

        cursor.close()
        conn.close()

        flash(
            "Data karyawan tidak ditemukan.",
            "error"
        )

        return redirect(url_for("index"))

    # Hapus data
    cursor.execute("""
        DELETE FROM karyawan
        WHERE id = %s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    flash(
        "Data karyawan berhasil dihapus.",
        "success"
    )

    return redirect(url_for("index"))


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )