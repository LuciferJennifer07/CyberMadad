from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import sqlite3
import os

# ✅ Flask app FIRST
app = Flask(__name__)
app.secret_key = "nyaysetu_secret"

# ✅ Then bcrypt
bcrypt = Bcrypt(app)

# ✅ Then upload folder
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DB_NAME = "database.db"



# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            mobile TEXT,
            aadhaar_last4 TEXT,
            photo TEXT,
            role TEXT
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            fraud_type TEXT,
            description TEXT,
            evidence TEXT,
            status TEXT DEFAULT 'Pending'
        )
        """
    )

        # ADD allow_contact column if not exists
    try:
        c.execute("ALTER TABLE cases ADD COLUMN allow_contact INTEGER DEFAULT 0")
    except:
        pass


    conn.commit()
    conn.close()


init_db()
try:
    c.execute("ALTER TABLE cases ADD COLUMN allow_contact INTEGER DEFAULT 0")
except:
    pass

# ---------- PUBLIC PAGES ----------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/team")
def team():
    return render_template("team.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user[3], password):
            session["user_id"] = user[0]
            session["role"] = user[7]
            return redirect(url_for("dashboard"))

        return "Invalid credentials"

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        mobile = request.form["mobile"]
        aadhaar = request.form["aadhaar"]
        role = request.form["role"]

        password = bcrypt.generate_password_hash(
            request.form["password"]
        ).decode("utf-8")

        photo = request.files["photo"]
        photo_name = secure_filename(photo.filename)
        photo.save(os.path.join(UPLOAD_FOLDER, photo_name))

        conn = get_db()
        c = conn.cursor()

        try:
            c.execute(
                """
                INSERT INTO users
                (name, email, password, mobile, aadhaar_last4, photo, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (name, email, password, mobile, aadhaar, photo_name, role),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Email already exists"

        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)



@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("dashboard.html", role=session["role"])


@app.route("/submit", methods=["GET", "POST"])
def submit_case():
    if "user_id" not in session or session["role"] != "victim":
        return "Access denied"

    if request.method == "POST":
        fraud = request.form["fraud"]
        description = request.form["description"]

        # 👇 CRITICAL LINE
        allow_contact = 1 if request.form.get("allow_contact") else 0

        file = request.files["evidence"]
        fname = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, fname))

        conn = get_db()
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO cases
            (user_id, fraud_type, description, evidence, allow_contact)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session["user_id"], fraud, description, fname, allow_contact),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("submit_case.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        # Future me yahan email / DB save add kar sakte ho
        return "Thank you! We will get back to you soon."

    return render_template("contact.html")


@app.route("/investigator")
def investigator():
    if session.get("role") != "investigator":
        return "Access denied"

    conn = get_db()
    c = conn.cursor()

    c.execute(
        """
        SELECT
            cases.id,
            users.name,
            users.email,
            users.mobile,
            cases.fraud_type,
            cases.description,
            cases.status,
            cases.evidence,
            cases.allow_contact
        FROM cases
        JOIN users ON cases.user_id = users.id
        ORDER BY cases.id DESC
        """
    )

    cases = c.fetchall()

    # 👇 force allow_contact to int (IMPORTANT)
    cases = [list(row) for row in cases]
    for case in cases:
        case[8] = int(case[8])

    conn.close()

    return render_template("investigator.html", cases=cases)





@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


