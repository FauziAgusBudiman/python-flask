from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)


# ==========================================
# KONFIGURASI DATABASE
# ==========================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "employee_db"
}


# ==========================================
# KONEKSI DATABASE
# ==========================================

def get_db():

    conn = mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"]
    )

    return conn


# ==========================================
# HALAMAN UTAMA
# SEARCH + FILTER
# ==========================================

@app.route("/")
def index():

    search = request.args.get("search", "")
    departemen = request.args.get("departemen", "")

    conn = get_db()

    cursor = conn.cursor(dictionary=True)

    # Query dasar
    query = """
        SELECT *
        FROM karyawan
        WHERE 1=1
    """

    params = []

    # Search
    if search:

        query += """
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

    # Filter departemen
    if departemen:

        query += """
            AND departemen = %s
        """

        params.append(departemen)

    # Urutkan data
    query += """
        ORDER BY id DESC
    """

    cursor.execute(query, params)

    karyawan = cursor.fetchall()


    # ==========================================
    # AMBIL DAFTAR DEPARTEMEN
    # ==========================================

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
        departemen=departemen
    )


# ==========================================
# TAMBAH KARYAWAN
# ==========================================

@app.route("/tambah", methods=["GET", "POST"])
def tambah():

    if request.method == "POST":

        nama = request.form["nama"]
        email = request.form["email"]
        jabatan = request.form["jabatan"]
        departemen = request.form["departemen"]


        conn = get_db()

        cursor = conn.cursor()


        query = """
            INSERT INTO karyawan
            (nama, email, jabatan, departemen)
            VALUES (%s, %s, %s, %s)
        """


        cursor.execute(
            query,
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


        return redirect(url_for("index"))


    return render_template("tambah.html")


# ==========================================
# EDIT KARYAWAN
# ==========================================

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    conn = get_db()

    cursor = conn.cursor(dictionary=True)


    # Ambil data berdasarkan ID
    cursor.execute(
        """
        SELECT *
        FROM karyawan
        WHERE id = %s
        """,
        (id,)
    )


    data = cursor.fetchone()


    # Jika data tidak ditemukan
    if data is None:

        cursor.close()
        conn.close()

        return "Data karyawan tidak ditemukan", 404


    # Jika form disubmit
    if request.method == "POST":

        nama = request.form["nama"]
        email = request.form["email"]
        jabatan = request.form["jabatan"]
        departemen = request.form["departemen"]


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


        return redirect(url_for("index"))


    cursor.close()
    conn.close()


    return render_template(
        "edit.html",
        data=data
    )


# ==========================================
# HAPUS KARYAWAN
# ==========================================

@app.route("/hapus/<int:id>")
def hapus(id):

    conn = get_db()

    cursor = conn.cursor()


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


    return redirect(url_for("index"))


# ==========================================
# JALANKAN SERVER
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )