from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file
)

import mysql.connector
import math
import os

from functools import wraps
from werkzeug.utils import secure_filename

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


app = Flask(__name__)

app.secret_key = "employee-app-secret-key"


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
# KONFIGURASI UPLOAD FOTO
# ==========================================

UPLOAD_FOLDER = os.path.join("static", "uploads")

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==========================================
# DATABASE
# ==========================================

def get_db():
    return mysql.connector.connect(**DB_CONFIG)


# ==========================================
# CEK EXTENSION FILE
# ==========================================

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ==========================================
# LOGIN REQUIRED
# ==========================================

def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Silakan login terlebih dahulu.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        return f(*args, **kwargs)

    return decorated_function


# ==========================================
# ADMIN REQUIRED
# ==========================================

def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Silakan login terlebih dahulu.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        if session.get("role") != "admin":

            flash(
                "Akses hanya tersedia untuk admin.",
                "error"
            )

            return redirect(
                url_for("index")
            )

        return f(*args, **kwargs)

    return decorated_function


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:

        return redirect(
            url_for("index")
        )

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        if not username or not password:

            flash(
                "Username dan password wajib diisi.",
                "error"
            )

            return render_template(
                "login.html"
            )

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, username, role
            FROM users
            WHERE username = %s
            AND password = %s
            """,
            (username, password)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user:

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            flash(
                "Login berhasil.",
                "success"
            )

            return redirect(
                url_for("index")
            )

        else:

            flash(
                "Username atau password salah.",
                "error"
            )

    return render_template(
        "login.html"
    )


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
@login_required
def logout():

    session.clear()

    flash(
        "Anda telah logout.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ==========================================
# DASHBOARD + DATA KARYAWAN
# ==========================================

@app.route("/")
@login_required
def index():

    search = request.args.get(
        "search",
        ""
    ).strip()

    departemen = request.args.get(
        "departemen",
        ""
    ).strip()

    page = request.args.get(
        "page",
        1,
        type=int
    )

    per_page = 5

    offset = (
        page - 1
    ) * per_page

    db = get_db()
    cursor = db.cursor(
        dictionary=True
    )

    # ======================================
    # DASHBOARD
    # ======================================

    cursor.execute(
        "SELECT COUNT(*) AS total FROM karyawan"
    )

    total_karyawan = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT departemen, COUNT(*) AS jumlah
        FROM karyawan
        GROUP BY departemen
        ORDER BY departemen
        """
    )

    department_data = cursor.fetchall()

    # ======================================
    # FILTER
    # ======================================

    conditions = []
    params = []

    if search:

        conditions.append(
            """
            (
                nama LIKE %s
                OR email LIKE %s
                OR jabatan LIKE %s
            )
            """
        )

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value
        ])

    if departemen:

        conditions.append(
            "departemen = %s"
        )

        params.append(
            departemen
        )

    where_clause = ""

    if conditions:

        where_clause = (
            " WHERE "
            + " AND ".join(conditions)
        )

    # ======================================
    # TOTAL DATA
    # ======================================

    count_query = (
        "SELECT COUNT(*) AS total "
        "FROM karyawan "
        + where_clause
    )

    cursor.execute(
        count_query,
        params
    )

    total_data = cursor.fetchone()["total"]

    total_pages = max(
        1,
        math.ceil(
            total_data / per_page
        )
    )

    if page > total_pages:

        page = total_pages

        offset = (
            page - 1
        ) * per_page

    # ======================================
    # DATA KARYAWAN
    # ======================================

    query = (
        "SELECT * FROM karyawan "
        + where_clause
        + " ORDER BY id DESC LIMIT %s OFFSET %s"
    )

    cursor.execute(
        query,
        params + [
            per_page,
            offset
        ]
    )

    data = cursor.fetchall()

    # ======================================
    # DEPARTEMEN
    # ======================================

    cursor.execute(
        """
        SELECT DISTINCT departemen
        FROM karyawan
        ORDER BY departemen
        """
    )

    departemen_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "index.html",
        data=data,
        total_karyawan=total_karyawan,
        department_data=department_data,
        departemen_list=departemen_list,
        search=search,
        departemen=departemen,
        page=page,
        total_pages=total_pages
    )


# ==========================================
# TAMBAH KARYAWAN
# ADMIN ONLY
# ==========================================

@app.route("/tambah", methods=["GET", "POST"])
@admin_required
def tambah():

    if request.method == "POST":

        nama = request.form["nama"].strip()
        email = request.form["email"].strip()
        jabatan = request.form["jabatan"].strip()
        departemen = request.form["departemen"].strip()

        # ==================================
        # VALIDASI
        # ==================================

        if not nama or not email or not jabatan or not departemen:

            flash(
                "Semua field wajib diisi.",
                "error"
            )

            return render_template(
                "tambah.html",
                data=request.form
            )

        # ==================================
        # VALIDASI EMAIL
        # ==================================

        if "@" not in email:

            flash(
                "Format email tidak valid.",
                "error"
            )

            return render_template(
                "tambah.html",
                data=request.form
            )

        # ==================================
        # FOTO
        # ==================================

        foto = request.files.get("foto")

        filename = None

        if foto and foto.filename:

            if not allowed_file(foto.filename):

                flash(
                    "Format foto harus JPG, JPEG, PNG, atau GIF.",
                    "error"
                )

                return render_template(
                    "tambah.html",
                    data=request.form
                )

            filename = secure_filename(
                foto.filename
            )

            # Hindari nama file sama
            base, extension = os.path.splitext(
                filename
            )

            counter = 1

            original_filename = filename

            while os.path.exists(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            ):

                filename = (
                    f"{base}_{counter}"
                    f"{extension}"
                )

                counter += 1

            foto.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

        # ==================================
        # INSERT
        # ==================================

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO karyawan
            (
                nama,
                email,
                jabatan,
                departemen,
                foto
            )
            VALUES
            (%s, %s, %s, %s, %s)
            """,
            (
                nama,
                email,
                jabatan,
                departemen,
                filename
            )
        )

        db.commit()

        cursor.close()
        db.close()

        flash(
            "Data karyawan berhasil ditambahkan.",
            "success"
        )

        return redirect(
            url_for("index")
        )

    return render_template(
        "tambah.html",
        data={}
    )


# ==========================================
# EDIT KARYAWAN
# ADMIN ONLY
# ==========================================

@app.route(
    "/edit/<int:id>",
    methods=["GET", "POST"]
)
@admin_required
def edit(id):

    db = get_db()
    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT *
        FROM karyawan
        WHERE id = %s
        """,
        (id,)
    )

    data = cursor.fetchone()

    if not data:

        cursor.close()
        db.close()

        flash(
            "Data karyawan tidak ditemukan.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    if request.method == "POST":

        nama = request.form["nama"].strip()
        email = request.form["email"].strip()
        jabatan = request.form["jabatan"].strip()
        departemen = request.form["departemen"].strip()

        # ==================================
        # VALIDASI
        # ==================================

        if not nama or not email or not jabatan or not departemen:

            flash(
                "Semua field wajib diisi.",
                "error"
            )

            data.update(
                request.form.to_dict()
            )

            cursor.close()
            db.close()

            return render_template(
                "edit.html",
                data=data
            )

        if "@" not in email:

            flash(
                "Format email tidak valid.",
                "error"
            )

            data.update(
                request.form.to_dict()
            )

            cursor.close()
            db.close()

            return render_template(
                "edit.html",
                data=data
            )

        # ==================================
        # FOTO BARU
        # ==================================

        foto = request.files.get("foto")

        filename = data["foto"]

        if foto and foto.filename:

            if not allowed_file(
                foto.filename
            ):

                flash(
                    "Format foto harus JPG, JPEG, PNG, atau GIF.",
                    "error"
                )

                data.update(
                    request.form.to_dict()
                )

                cursor.close()
                db.close()

                return render_template(
                    "edit.html",
                    data=data
                )

            # Hapus foto lama
            if data["foto"]:

                old_path = os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    data["foto"]
                )

                if os.path.exists(
                    old_path
                ):

                    os.remove(
                        old_path
                    )

            filename = secure_filename(
                foto.filename
            )

            base, extension = os.path.splitext(
                filename
            )

            counter = 1

            while os.path.exists(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            ):

                filename = (
                    f"{base}_{counter}"
                    f"{extension}"
                )

                counter += 1

            foto.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

        # ==================================
        # UPDATE
        # ==================================

        cursor.execute(
            """
            UPDATE karyawan
            SET
                nama = %s,
                email = %s,
                jabatan = %s,
                departemen = %s,
                foto = %s
            WHERE id = %s
            """,
            (
                nama,
                email,
                jabatan,
                departemen,
                filename,
                id
            )
        )

        db.commit()

        cursor.close()
        db.close()

        flash(
            "Data karyawan berhasil diperbarui.",
            "success"
        )

        return redirect(
            url_for("index")
        )

    cursor.close()
    db.close()

    return render_template(
        "edit.html",
        data=data
    )


# ==========================================
# HAPUS KARYAWAN
# ADMIN ONLY
# ==========================================

@app.route("/hapus/<int:id>")
@admin_required
def hapus(id):

    db = get_db()
    cursor = db.cursor(
        dictionary=True
    )

    # Ambil foto
    cursor.execute(
        """
        SELECT foto
        FROM karyawan
        WHERE id = %s
        """,
        (id,)
    )

    data = cursor.fetchone()

    # Hapus foto
    if data and data["foto"]:

        foto_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            data["foto"]
        )

        if os.path.exists(
            foto_path
        ):

            os.remove(
                foto_path
            )

    # Hapus data
    cursor.execute(
        """
        DELETE FROM karyawan
        WHERE id = %s
        """,
        (id,)
    )

    db.commit()

    cursor.close()
    db.close()

    flash(
        "Data karyawan berhasil dihapus.",
        "success"
    )

    return redirect(
        url_for("index")
    )


# ==========================================
# EXPORT EXCEL
# ADMIN ONLY
# ==========================================

@app.route("/export/excel")
@admin_required
def export_excel():

    db = get_db()
    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT
            id,
            nama,
            email,
            jabatan,
            departemen
        FROM karyawan
        ORDER BY id ASC
        """
    )

    data = cursor.fetchall()

    cursor.close()
    db.close()

    # ======================================
    # BUAT EXCEL
    # ======================================

    workbook = Workbook()

    worksheet = workbook.active

    worksheet.title = "Data Karyawan"

    headers = [
        "ID",
        "Nama",
        "Email",
        "Jabatan",
        "Departemen"
    ]

    worksheet.append(headers)

    for row in data:

        worksheet.append([
            row["id"],
            row["nama"],
            row["email"],
            row["jabatan"],
            row["departemen"]
        ])

    # Lebar kolom
    worksheet.column_dimensions["A"].width = 10
    worksheet.column_dimensions["B"].width = 30
    worksheet.column_dimensions["C"].width = 30
    worksheet.column_dimensions["D"].width = 25
    worksheet.column_dimensions["E"].width = 20

    filepath = os.path.join(
        "static",
        "export_karyawan.xlsx"
    )

    workbook.save(
        filepath
    )

    return send_file(
        filepath,
        as_attachment=True,
        download_name="data_karyawan.xlsx"
    )


# ==========================================
# EXPORT PDF
# ADMIN ONLY
# ==========================================

@app.route("/export/pdf")
@admin_required
def export_pdf():

    db = get_db()
    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT
            id,
            nama,
            email,
            jabatan,
            departemen
        FROM karyawan
        ORDER BY id ASC
        """
    )

    data = cursor.fetchall()

    cursor.close()
    db.close()

    filepath = os.path.join(
        "static",
        "export_karyawan.pdf"
    )

    # ======================================
    # BUAT PDF
    # ======================================

    document = SimpleDocTemplate(
        filepath,
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    elements = []

    title = Paragraph(
        "Data Karyawan",
        styles["Title"]
    )

    elements.append(title)

    elements.append(
        Spacer(1, 20)
    )

    table_data = [
        [
            "ID",
            "Nama",
            "Email",
            "Jabatan",
            "Departemen"
        ]
    ]

    for row in data:

        table_data.append([
            str(row["id"]),
            row["nama"],
            row["email"],
            row["jabatan"],
            row["departemen"]
        ])

    table = Table(
        table_data,
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.grey
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                1,
                colors.black
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "ALIGN",
                (0, 0),
                (0, -1),
                "CENTER"
            ),
        ])
    )

    elements.append(table)

    document.build(
        elements
    )

    return send_file(
        filepath,
        as_attachment=True,
        download_name="data_karyawan.pdf"
    )


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True
    )