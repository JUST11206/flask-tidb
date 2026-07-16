#pip install sqlalchemy pymysql cryptography
from flask import Flask, render_template, request, redirect, session, flash, send_from_directory
from sqlalchemy import create_engine, text
from datetime import timedelta
import os
from werkzeug.utils import secure_filename
from email_validator import validate_email, EmailNotValidError
from flask import flash
import random
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from functools import wraps



def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("admin"):
            return redirect("/admin_login")

        return f(*args, **kwargs)

    return decorated_function

app = Flask(__name__)
app.secret_key = "secret@123"
app.permanent_session_lifetime = timedelta(days=30)

@app.after_request
def add_header(response):

    auth_routes = [
        "/",
        "/login",
        "/signup",
        "/verify-otp",
        "/logout",
        "/admin",
        "/admin_login",
        "/admin_logout"
    ]

    if request.path in auth_routes:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response

app.config["PDF_FOLDER"] = os.path.join(
    app.root_path,
    "static",
    "pdfs"
)

os.makedirs(
    app.config["PDF_FOLDER"],
    exist_ok=True
)

print("SENDER_EMAIL =", os.getenv("SENDER_EMAIL"))
print("SENDGRID_API_KEY EXISTS =", bool(os.getenv("SENDGRID_API_KEY")))

DATABASE_URL = "mysql+pymysql://3FtQQGViQkjLout.root:yQrM14kdizk6648t@gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com:4000/flask_auth"

engine = create_engine(
    DATABASE_URL,
    pool_recycle=3600
)

UPLOAD_FOLDER = "static/profile_images"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def send_otp_email(email, username, otp):

    message = Mail(
        from_email=os.getenv("SENDER_EMAIL"),
        to_emails=email,
        subject="StudyHub OTP Verification",
        html_content=f"""
        <h2>Hello {username}</h2>

        <p>Your OTP is:</p>

        <h1>{otp}</h1>

        <p>This OTP is valid for a short time.</p>

        <p>StudyHub Team</p>
        """
    )

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)

        print("EMAIL SENT SUCCESSFULLY")
        return True

    except Exception as e:
        print("SENDGRID ERROR:", e)
        return False

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":

        entered_otp = request.form["otp"]

        if entered_otp == session.get("otp"):

            try:
                with engine.connect() as conn:

                    conn.execute(
                        text("""
                        INSERT INTO users(username,email,password)
                        VALUES(:username,:email,:password)
                        """),
                        {
                            "username": session["username"],
                            "email": session["email"],
                            "password": session["password"]
                        }
                    )

                    conn.commit()

                # Auto login after verification
                session.permanent = True
                
                session["user"] = session["username"]
                session["email"] = session["email"]

                # Remove OTP from session
                session.pop("otp", None)

                flash("Account created successfully!", "success")

                return redirect("/dashboard")

            except Exception as e:

                print("VERIFY OTP ERROR:", repr(e))
                flash("Database error!", "error")

                return redirect("/signup")

        else:

            flash("Invalid OTP!", "error")

            return redirect("/verify-otp")

    return render_template("verify-otp.html")

@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")

    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    # Already logged in
    if "user" in session:
        return redirect("/dashboard")

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        with engine.connect() as conn:

            user = conn.execute(
                text("""
                SELECT * FROM users
                WHERE email=:email
                AND password=:password
                """),
                {
                    "email": email,
                    "password": password
                }
            ).fetchone()

        if user:

            session.permanent = True

            session["user"] = user.username
            session["email"] = user.email

            return redirect("/dashboard")

        flash(
            "You entered wrong password or email!",
            "error"
        )

        return redirect("/login")

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    with engine.connect() as conn:

        popular_notes = conn.execute(
            text("""
                SELECT *
                FROM notes
                ORDER BY views DESC
                LIMIT 3
            """)
        ).fetchall()

        recent_notes = conn.execute(
            text("""
                SELECT *
                FROM notes
                ORDER BY created_at DESC
                LIMIT 3
            """)
        ).fetchall()

    return render_template(
        "dashboard.html",
        username=session["user"],
        popular_notes=popular_notes,
        recent_notes=recent_notes
    )
#This is 10 june 2026 

@app.route("/signup", methods=["GET", "POST"])
def signup():
    # If user is already logged in, don't allow signup page
    if "user" in session:
        return redirect("/dashboard")

    if request.method == "POST":

        try:
            username = request.form["username"]
            email = request.form["email"]
            password = request.form["password"]

            try:
                valid = validate_email(email)
                email = valid.email

            except EmailNotValidError:
                flash("Please enter a valid email address!", "error")
                return redirect("/signup")

            try:
                with engine.connect() as conn:

                    existing_user = conn.execute(
                        text("""
                        SELECT email
                        FROM users
                        WHERE email=:email
                        """),
                        {"email": email}
                    ).fetchone()

                    if existing_user:
                        flash("Email already registered!", "error")
                        return redirect("/signup")

            except Exception as e:
                print("DB CHECK ERROR:", repr(e))
                flash("Database error!", "error")
                return redirect("/signup")

            otp = random.randint(100000, 999999)

            session["otp"] = str(otp)
            session["username"] = username
            session["email"] = email
            session["password"] = password

            if not send_otp_email(email, username, otp):
                flash("OTP email failed!", "error")
                return redirect("/signup")

            return redirect("/verify-otp")

        except Exception as e:

            print("=" * 50)
            print("SIGNUP ERROR:", repr(e))
            print("=" * 50)

            flash("Something went wrong!", "error")
            return redirect("/signup")

    return render_template("signup.html")


#this is a search bar 
@app.route("/search")
def search():

    query = request.args.get("q", "").lower()

    data = [
        {"title":"Python Notes", "url":"/notes/python", "type":"📚 Notes"},
        {"title":"Python PDF", "url":"/pdf", "type":"📄 PDF"},
        {"title":"Python Full Course", "url":"/lectures", "type":"🎥 Lecture"},

        {"title":"Web Development Notes", "url":"/notes/web", "type":"📚 Notes"},
        {"title":"Web Development Lecture", "url":"/lectures", "type":"🎥 Lecture"},
        {"title":"Web Development PDF", "url":"/pdf", "type":"📄 PDF"},

        {"title":"DBMS Notes", "url":"/notes/sql", "type":"📚 Notes"},
        {"title":"DBMS Lecture", "url":"/lectures", "type":"🎥 Lecture"},

        {"title":"PHP Notes", "url":"/notes/php", "type":"📚 Notes"},

        {"title":"DSA Notes", "url":"/notes/dsa", "type":"📚 Notes"},

        {"title":"C Language Course", "url":"/lectures", "type":"🎥 Lecture"},
        {"title":"Java Tutorial", "url":"/lectures", "type":"🎥 Lecture"},
        {"title":"C++", "url":"/lectures", "type":"🎥 Lecture"}
    ]

    results = []

    for item in data:
        words = query.split()

        if any(word in item["title"].lower() for word in words):
            results.append(item)

    return render_template(
        "search_result.html",
        query=query,
        results=results
    )


# Logout
@app.route("/logout")
def logout():

    session.clear()
    return redirect("/login")

#sidebar section
@app.route("/notes")
def note():

    if "user" not in session:
        return redirect("/login")

    query = request.args.get("q", "").strip()
    subject = request.args.get("subject", "").strip()

    with engine.connect() as conn:

        sql = """
            SELECT *
            FROM notes
            WHERE 1=1
        """

        params = {}

        if query:
            sql += """
                AND (
                    title LIKE :query
                    OR subject LIKE :query
                    OR content LIKE :query
                )
            """
            params["query"] = f"%{query}%"

        if subject:
            sql += " AND subject = :subject"
            params["subject"] = subject

        sql += " ORDER BY id DESC"

        notes = conn.execute(
            text(sql),
            params
        ).fetchall()

        subjects = conn.execute(
            text("""
                SELECT DISTINCT subject
                FROM notes
                ORDER BY subject
            """)
        ).fetchall()

    return render_template(
        "notes.html",
        notes=notes,
        subjects=subjects,
        query=query,
        selected_subject=subject
    )

@app.route("/notes/<int:note_id>")
def view_note(note_id):

    if "user" not in session:
        return redirect("/login")

    with engine.connect() as conn:

        note = conn.execute(
            text("""
                SELECT *
                FROM notes
                WHERE id = :id
            """),
            {"id": note_id}
        ).fetchone()

        if not note:
            return "Note not found", 404

        conn.execute(
            text("""
                UPDATE notes
                SET views = views + 1
                WHERE id = :id
            """),
            {"id": note_id}
        )

        conn.commit()

    return render_template(
        "view_note.html",
        note=note
    )


@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        image = request.files.get("profile_image")

        if image and image.filename:

            filename = secure_filename(image.filename)

            image.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

            session["profile_image"] = filename

        return redirect("/profile")

    return render_template(
        "profile.html",
        username=session["user"],
        email=session.get("email"),
        profile_image=session.get("profile_image")
    )

@app.route("/admin")
def admin():

    if not session.get("admin"):
        return redirect("/admin_login")

    return render_template("admin.html")



@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "studyhub123":
            session["admin"] = True

            return redirect("/admin")

        else:
            return "Wrong Username or Password"

    return render_template("admin_login.html")

@app.route("/admin_logout")
def admin_logout():

    session.pop("admin", None)

    return redirect("/")

@app.route("/add_lecture", methods=["GET", "POST"])
@admin_required
def add_lecture():

    with engine.connect() as conn:

        categories = conn.execute(
            text("""
                SELECT *
                FROM categories
                ORDER BY id ASC
            """)
        ).fetchall()


    if request.method == "POST":

        title = request.form["title"]
        youtube_url = request.form["youtube_url"]
        category_id = request.form["category_id"]


        # ================= YOUTUBE URL CONVERT =================

        if "watch?v=" in youtube_url:

            video_id = (
                youtube_url
                .split("watch?v=")[1]
                .split("&")[0]
            )

            youtube_url = (
                "https://www.youtube.com/embed/"
                + video_id
            )


        elif "youtu.be/" in youtube_url:

            video_id = (
                youtube_url
                .split("youtu.be/")[1]
                .split("?")[0]
            )

            youtube_url = (
                "https://www.youtube.com/embed/"
                + video_id
            )


        # ================= INSERT LECTURE =================

        with engine.connect() as conn:

            conn.execute(
                text("""
                    INSERT INTO lectures
                    (
                        title,
                        youtube_url,
                        category_id
                    )

                    VALUES
                    (
                        :title,
                        :youtube_url,
                        :category_id
                    )
                """),
                {
                    "title": title,
                    "youtube_url": youtube_url,
                    "category_id": category_id
                }
            )

            conn.commit()


        flash(
            "Lecture added successfully!",
            "success"
        )

        return redirect("/manage_lectures")


    return render_template(
        "add_lecture.html",
        categories=categories
    )

@app.route("/manage_lectures")
@admin_required
def manage_lectures():

    with engine.connect() as conn:

        lectures = conn.execute(
            text("""
                SELECT
                    lectures.id,
                    lectures.title,
                    lectures.youtube_url,
                    lectures.category_id,
                    categories.name AS category_name,
                    categories.icon AS category_icon

                FROM lectures

                LEFT JOIN categories
                ON lectures.category_id = categories.id

                ORDER BY lectures.id DESC
            """)
        ).fetchall()

    return render_template(
        "manage_lectures.html",
        lectures=lectures
    )


@app.route("/delete_lecture/<int:id>", methods=["POST"])
@admin_required
def delete_lecture(id):

    with engine.connect() as conn:

        conn.execute(
            text("""
            DELETE FROM lectures
            WHERE id = :id
            """),
            {"id": id}
        )

        conn.commit()

    flash("Lecture deleted successfully!", "success")

    return redirect("/manage_lectures")

@app.route("/edit_lecture/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_lecture(id):

    if request.method == "POST":

        title = request.form["title"]
        youtube_url = request.form["youtube_url"]
        category_id = request.form["category_id"]

        # YouTube normal URL → embed URL
        if "watch?v=" in youtube_url:

            video_id = youtube_url.split("watch?v=")[1].split("&")[0]

            youtube_url = (
                "https://www.youtube.com/embed/"
                + video_id
            )

        elif "youtu.be/" in youtube_url:

            video_id = youtube_url.split("youtu.be/")[1].split("?")[0]

            youtube_url = (
                "https://www.youtube.com/embed/"
                + video_id
            )

        with engine.connect() as conn:

            conn.execute(
                text("""
                    UPDATE lectures

                    SET title = :title,
                        youtube_url = :youtube_url,
                        category_id = :category_id

                    WHERE id = :id
                """),
                {
                    "title": title,
                    "youtube_url": youtube_url,
                    "category_id": category_id,
                    "id": id
                }
            )

            conn.commit()

        flash(
            "Lecture updated successfully!",
            "success"
        )

        return redirect("/manage_lectures")


    with engine.connect() as conn:

        lecture = conn.execute(
            text("""
                SELECT *
                FROM lectures
                WHERE id = :id
            """),
            {
                "id": id
            }
        ).fetchone()


        categories = conn.execute(
            text("""
                SELECT *
                FROM categories
                ORDER BY id ASC
            """)
        ).fetchall()


    if not lecture:
        return "Lecture not found", 404


    return render_template(
        "edit_lecture.html",
        lecture=lecture,
        categories=categories
    )

@app.route("/lectures")
def lect():

    with engine.connect() as conn:

        categories = conn.execute(
            text("""
                SELECT
                    categories.*,
                    COUNT(lectures.id) AS lecture_count

                FROM categories

                LEFT JOIN lectures
                ON categories.id = lectures.category_id

                GROUP BY
                    categories.id,
                    categories.name,
                    categories.slug,
                    categories.icon,
                    categories.description

                ORDER BY categories.id ASC
            """)
        ).fetchall()

    return render_template(
        "lectures.html",
        categories=categories
    )
@app.route("/lectures/<slug>")
def category_lectures(slug):

    with engine.connect() as conn:

        category = conn.execute(
            text("""
                SELECT *
                FROM categories
                WHERE slug = :slug
            """),
            {
                "slug": slug
            }
        ).fetchone()


        if not category:
            return "Category not found", 404


        lectures = conn.execute(
            text("""
                SELECT *
                FROM lectures
                WHERE category_id = :category_id
                ORDER BY id ASC
            """),
            {
                "category_id": category.id
            }
        ).fetchall()


    return render_template(
        "category_lectures.html",
        lectures=lectures,
        category=category
    )

@app.route("/manage_pdfs")
@admin_required
def manage_pdfs():

    with engine.connect() as conn:

        pdf_list = conn.execute(
            text("""
                SELECT *
                FROM pdfs
                ORDER BY id DESC
            """)
        ).fetchall()

    return render_template(
        "manage_pdfs.html",
        pdfs=pdf_list
    )

@app.route("/add_pdf", methods=["GET", "POST"])
@admin_required
def add_pdf():

    if request.method == "POST":

        title = request.form["title"]
        pdf = request.files["pdf"]

        if not pdf or pdf.filename == "":
            flash("Please select a PDF file!", "danger")
            return redirect("/add_pdf")

        filename = secure_filename(pdf.filename)

        file_path = os.path.join(
            app.config["PDF_FOLDER"],
            filename
        )

        pdf.save(file_path)

        with engine.connect() as conn:

            conn.execute(
                text("""
                    INSERT INTO pdfs
                    (title, pdf_file)
                    VALUES
                    (:title, :pdf_file)
                """),
                {
                    "title": title,
                    "pdf_file": filename
                }
            )

            conn.commit()

        flash("PDF added successfully!", "success")

        return redirect("/pdfs")

    return render_template("add_pdf.html")

@app.route("/delete_pdf/<int:id>", methods=["POST"])
@admin_required
def delete_pdf(id):

    with engine.connect() as conn:

        pdf = conn.execute(
            text("""
                SELECT *
                FROM pdfs
                WHERE id = :id
            """),
            {"id": id}
        ).fetchone()

        if not pdf:
            flash("PDF not found!", "danger")
            return redirect("/pdfs")

        file_path = os.path.join(
            app.config["PDF_FOLDER"],
            pdf.pdf_file
        )

        if os.path.exists(file_path):
            os.remove(file_path)

        conn.execute(
            text("""
                DELETE FROM pdfs
                WHERE id = :id
            """),
            {"id": id}
        )

        conn.commit()

    flash("PDF deleted successfully!", "success")

    return redirect("/pdfs")

@app.route("/pdfs")
def pdfs():

    with engine.connect() as conn:

        result = conn.execute(
            text("SELECT * FROM pdfs")
        )

        pdf_list = result.fetchall()

    return render_template(
        "pdf.html",
        pdfs=pdf_list
    )

@app.route("/add_note", methods=["GET", "POST"])
@admin_required
def add_note():

    if request.method == "POST":

        title = request.form["title"]
        subject = request.form["subject"]
        content = request.form["content"]

        with engine.connect() as conn:
            conn.execute(
                text("""
                INSERT INTO notes (title, subject, content)
                VALUES (:title, :subject, :content)
                """),
                {
                    "title": title,
                    "subject": subject,
                    "content": content
                }
            )

            conn.commit()

        flash("Note added successfully!", "success")

        return redirect("/manage_notes")

    return render_template("add_note.html")

@app.route("/manage_notes")
@admin_required
def manage_notes():

    with engine.connect() as conn:

        notes = conn.execute(
            text("""
            SELECT * FROM notes
            ORDER BY id DESC
            """)
        ).fetchall()

    return render_template(
        "manage_notes.html",
        notes=notes
    )

@app.route("/edit_note/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_note(id):

    if request.method == "POST":

        title = request.form["title"]
        subject = request.form["subject"]
        content = request.form["content"]

        with engine.connect() as conn:

            conn.execute(
                text("""
                UPDATE notes
                SET title = :title,
                    subject = :subject,
                    content = :content
                WHERE id = :id
                """),
                {
                    "title": title,
                    "subject": subject,
                    "content": content,
                    "id": id
                }
            )

            conn.commit()

        flash("Note updated successfully!", "success")

        return redirect("/manage_notes")

    with engine.connect() as conn:

        note = conn.execute(
            text("""
            SELECT * FROM notes
            WHERE id = :id
            """),
            {"id": id}
        ).fetchone()

    if not note:
        return "Note not found", 404

    return render_template(
        "edit_note.html",
        note=note
    )

@app.route("/delete_note/<int:id>", methods=["POST"])
@admin_required
def delete_note(id):

    with engine.connect() as conn:

        conn.execute(
            text("""
            DELETE FROM notes
            WHERE id = :id
            """),
            {"id": id}
        )

        conn.commit()

    flash("Note deleted successfully!", "success")

    return redirect("/manage_notes")


@app.route("/save_note/<int:note_id>")
def save_note(note_id):

    if "user" not in session:
        return redirect("/login")

    email = session.get("email")

    with engine.connect() as conn:

        existing = conn.execute(
            text("""
                SELECT id
                FROM saved_notes
                WHERE user_email = :email
                AND note_id = :note_id
            """),
            {
                "email": email,
                "note_id": note_id
            }
        ).fetchone()

        if not existing:

            conn.execute(
                text("""
                    INSERT INTO saved_notes
                    (user_email, note_id)
                    VALUES (:email, :note_id)
                """),
                {
                    "email": email,
                    "note_id": note_id
                }
            )

            conn.commit()

    return redirect(f"/notes/{note_id}")


@app.route("/saved_notes")
def saved_notes():

    if "user" not in session:
        return redirect("/login")

    email = session.get("email")

    with engine.connect() as conn:

        notes = conn.execute(
            text("""
                SELECT notes.*
                FROM saved_notes
                JOIN notes
                ON saved_notes.note_id = notes.id
                WHERE saved_notes.user_email = :email
                ORDER BY saved_notes.created_at DESC
            """),
            {"email": email}
        ).fetchall()

    return render_template(
        "saved_notes.html",
        notes=notes
    )

@app.route("/unsave_note/<int:note_id>")
def unsave_note(note_id):

    if "user" not in session:
        return redirect("/login")

    email = session.get("email")

    with engine.connect() as conn:

        conn.execute(
            text("""
                DELETE FROM saved_notes
                WHERE user_email = :email
                AND note_id = :note_id
            """),
            {
                "email": email,
                "note_id": note_id
            }
        )

        conn.commit()

    return redirect("/saved_notes")

@app.route("/service-worker.js")
def service_worker():

    return send_from_directory(
        "static",
        "service-worker.js",
        mimetype="application/javascript"
    )

#Download pdfs in app
@app.route("/downloads")
def downloads():

    if "user" not in session:
        return redirect("/login")

    return render_template(
        "downloads.html",
        username=session["user"]
    )

if __name__ == "__main__":
    app.run(debug=True)