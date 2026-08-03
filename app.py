
from flask import Flask, render_template, request, redirect, session, flash, send_from_directory ,url_for
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
            
            session["user_id"] = user._mapping["id"]
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

    username = session.get("user")
    user_id = session.get("user_id")

    # If old session doesn't have user_id,
    # recover it from the logged-in email.
    if not user_id and session.get("email"):

        try:

            with engine.connect() as conn:

                user = conn.execute(
                    text("""
                        SELECT id
                        FROM users
                        WHERE email = :email
                    """),
                    {
                        "email": session["email"]
                    }
                ).fetchone()

                if user:
                    user_id = user._mapping["id"]
                    session["user_id"] = user_id

        except Exception as e:

            print("USER ID RECOVERY ERROR:", repr(e))


    # Default values
    total_courses = 0
    total_notes = 0
    total_lectures = 0

    purchased_courses_count = 0
    completed_courses = 0

    learning_progress = 0
    watched_lectures = 0

    certificates = 0
    study_hours = 0

    featured_courses = []
    recent_notes = []

    last_course = None


    try:

        with engine.connect() as conn:

            # ==========================================
            # TOTAL COURSES
            # ==========================================

            total_courses = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM courses
                """)
            ).scalar() or 0


            # ==========================================
            # TOTAL NOTES
            # ==========================================

            total_notes = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM notes
                """)
            ).scalar() or 0


            # ==========================================
            # TOTAL LECTURES
            # ==========================================

            total_lectures = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM lectures
                """)
            ).scalar() or 0


            # ==========================================
            # FEATURED COURSES
            # ==========================================

            featured_courses = conn.execute(
                text("""
                    SELECT
                        c.id,
                        c.title,
                        c.description,
                        c.thumbnail,
                        c.price,
                        c.is_free,
                        c.category_id,

                        cat.name AS category_name,

                        (
                            SELECT COUNT(*)
                            FROM lectures l
                            WHERE l.course_id = c.id
                        ) AS lecture_count

                    FROM courses c

                    LEFT JOIN categories cat
                        ON c.category_id = cat.id

                    ORDER BY c.id DESC

                    LIMIT 8
                """)
            ).fetchall()


            # ==========================================
            # RECENT NOTES
            # ==========================================

            recent_notes = conn.execute(
                text("""
                    SELECT
                        id,
                        title,
                        subject,
                        content
                    FROM notes
                    ORDER BY id DESC
                    LIMIT 5
                """)
            ).fetchall()


            # ==========================================
            # USER PURCHASED COURSES
            # ==========================================

            if user_id:

                purchased_courses_count = conn.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM purchased_courses
                        WHERE user_id = :user_id
                    """),
                    {
                        "user_id": user_id
                    }
                ).scalar() or 0


                # ======================================
                # LAST PURCHASED COURSE
                # ======================================

                last_course = conn.execute(
                    text("""
                        SELECT
                            c.id,
                            c.title,
                            c.description,
                            c.thumbnail,
                            c.price,
                            c.is_free,

                            (
                                SELECT COUNT(*)
                                FROM lectures l
                                WHERE l.course_id = c.id
                            ) AS lecture_count

                        FROM purchased_courses pc

                        INNER JOIN courses c
                            ON c.id = pc.course_id

                        WHERE pc.user_id = :user_id

                        ORDER BY pc.id DESC

                        LIMIT 1
                    """),
                    {
                        "user_id": user_id
                    }
                ).fetchone()


    except Exception as e:

        print("=" * 60)
        print("DASHBOARD DB ERROR:", repr(e))
        print("=" * 60)


    return render_template(
        "dashboard.html",

        username=username,

        # Statistics
        total_courses=total_courses,
        total_notes=total_notes,
        total_lectures=total_lectures,

        # User
        purchased_courses_count=purchased_courses_count,

        # Progress
        completed_courses=completed_courses,
        watched_lectures=watched_lectures,
        learning_progress=learning_progress,

        # Achievements
        certificates=certificates,
        study_hours=study_hours,

        # Dashboard content
        featured_courses=featured_courses,
        recent_notes=recent_notes,
        last_course=last_course
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

@app.route("/admin/payments")
@admin_required
def admin_payments():

    with engine.connect() as conn:

        payments = conn.execute(text("""

        SELECT
        payment_requests.*,
        users.username,
        courses.title

        FROM payment_requests

        JOIN users
        ON payment_requests.user_id=users.id

        JOIN courses
        ON payment_requests.course_id=courses.id

        WHERE payment_requests.status='Pending'

        ORDER BY payment_requests.id DESC

        """)).fetchall()

    return render_template(
        "admin_payments.html",
        payments=payments
    )

@app.route("/my-payments")
def my_payments():

    if "user" not in session:
        return redirect("/login")

    with engine.connect() as conn:

        payments = conn.execute(
            text("""
                SELECT
                payment_requests.*,
                courses.title

                FROM payment_requests

                JOIN courses
                ON payment_requests.course_id = courses.id

                WHERE payment_requests.user_id=:user

                ORDER BY payment_requests.id DESC
            """),
            {
                "user": session["user_id"]
            }
        ).fetchall()

    return render_template(
        "my_payments.html",
        payments=payments
    )

@app.route("/add_course", methods=["GET", "POST"])
@admin_required
def add_course():

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        price = request.form["price"]
        category_id = request.form["category_id"]

        is_free = 1 if request.form.get("is_free") else 0

        thumbnail = None

        image = request.files.get("thumbnail")

        if image and image.filename:

            filename = secure_filename(image.filename)

            folder = "static/uploads/course_thumbnails"

            os.makedirs(folder, exist_ok=True)

            image.save(os.path.join(folder, filename))

            thumbnail = filename

        with engine.connect() as conn:

            conn.execute(
                text("""
                    INSERT INTO courses
                    (
                        title,
                        description,
                        thumbnail,
                        price,
                        is_free,
                        category_id
                    )
                    VALUES
                    (
                        :title,
                        :description,
                        :thumbnail,
                        :price,
                        :is_free,
                        :category_id
                    )
                """),
                {
                    "title": title,
                    "description": description,
                    "thumbnail": thumbnail,
                    "price": price,
                    "is_free": is_free,
                    "category_id": category_id
                }
            )

            conn.commit()

        flash("Course Added Successfully!", "success")

        return redirect("/manage_courses")
    with engine.connect() as conn:

        categories = conn.execute(
            text("""
                SELECT *
                FROM categories
                ORDER BY name
            """)
        ).fetchall()

    return render_template(
        "add_course.html",
        categories=categories
    )

@app.route("/course/<int:id>")
def course(id):

    if "user" not in session:
        return redirect("/login")


    with engine.connect() as conn:

        # Get Course
        course = conn.execute(
            text("""
                SELECT *
                FROM courses
                WHERE id=:id
            """),
            {
                "id": id
            }
        ).fetchone()


        if not course:
            return "Course not found",404


        # Get Lectures
        lectures = conn.execute(
            text("""
                SELECT *
                FROM lectures
                WHERE course_id=:id
                ORDER BY id
            """),
            {
                "id": id
            }
        ).fetchall()


        # Get Category
        category = conn.execute(
            text("""
                SELECT *
                FROM categories
                WHERE id=:category_id
            """),
            {
                "category_id": course.category_id
            }
        ).fetchone()



        # Check Course Purchase
        purchased = False


        if "user_id" in session:

            purchase = conn.execute(
                text("""
                    SELECT id
                    FROM purchased_courses
                    WHERE user_id=:user
                    AND course_id=:course
                """),
                {
                    "user": session["user_id"],
                    "course": id
                }
            ).fetchone()


            if purchase:
                purchased = True



    return render_template(
        "course_detail.html",
        course=course,
        lectures=lectures,
        category=category,
        purchased=purchased
    )

@app.route("/manage_courses")
@admin_required
def manage_courses():

    with engine.connect() as conn:

        courses = conn.execute(
            text("""
                SELECT *
                FROM courses
                ORDER BY id DESC
            """)
        ).fetchall()

    return render_template(
        "manage_courses.html",
        courses=courses
    )

@app.route("/delete_course/<int:id>", methods=["POST"])
@admin_required
def delete_course(id):

    with engine.connect() as conn:

        conn.execute(
            text("""
                DELETE FROM courses
                WHERE id=:id
            """),
            {
                "id": id
            }
        )

        conn.commit()

    flash(
        "Course deleted successfully!",
        "success"
    )

    return redirect("/manage_courses")

@app.route("/edit_course/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_course(id):

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        price = request.form["price"]

        is_free = 1 if request.form.get("is_free") else 0

        with engine.connect() as conn:

            conn.execute(
                text("""
                    UPDATE courses

                    SET
                        title=:title,
                        description=:description,
                        price=:price,
                        is_free=:is_free

                    WHERE id=:id
                """),
                {
                    "title": title,
                    "description": description,
                    "price": price,
                    "is_free": is_free,
                    "id": id
                }
            )

            conn.commit()

        flash(
            "Course updated successfully!",
            "success"
        )

        return redirect("/manage_courses")


    with engine.connect() as conn:

        course = conn.execute(
            text("""
                SELECT *
                FROM courses
                WHERE id=:id
            """),
            {
                "id": id
            }
        ).fetchone()


    if not course:

        return "Course not found",404


    return render_template(
        "edit_course.html",
        course=course
    )

@app.route("/courses/<slug>")
def category_courses(slug):

    with engine.connect() as conn:

        category = conn.execute(
            text("""
                SELECT *
                FROM categories
                WHERE slug=:slug
            """),
            {"slug": slug}
        ).fetchone()

        if not category:
            return "Category not found",404

        courses = conn.execute(
            text("""
                SELECT *
                FROM courses
                WHERE category_id=:category_id
                ORDER BY id ASC
            """),
            {"category_id": category.id}
        ).fetchall()

    return render_template(
        "courses.html",
        category=category,
        courses=courses
    )

@app.route("/watch/<int:id>")
def watch(id):

    if "user" not in session:
        return redirect("/login")

    with engine.connect() as conn:

        # Get Lecture
        lecture = conn.execute(
            text("""
                SELECT *
                FROM lectures
                WHERE id=:id
            """),
            {"id": id}
        ).fetchone()

        if not lecture:
            return "Lecture Not Found",404

        # Get Course
        course = conn.execute(
            text("""
                SELECT *
                FROM courses
                WHERE id=:course
            """),
            {"course": lecture.course_id}
        ).fetchone()

        if not course:
            return "Course Not Found",404

        # FREE COURSE
        # FREE COURSE OR FREE LECTURE
        if course.is_free == 1 or lecture.is_free == 1:

            return render_template(
                "watch.html",
                lecture=lecture,
                course=course
            )
        # Check Purchase
        purchase = conn.execute(
            text("""
                SELECT id
                FROM purchased_courses
                WHERE
                    user_id=:user
                AND
                    course_id=:course
            """),
            {
                "user": session["user_id"],
                "course": course.id
            }
        ).fetchone()

    if not purchase:

        flash(
            "Purchase this course first.",
            "warning"
        )

        return redirect(url_for(
    "buy_course",
    id=course.id
))

    return render_template(
        "watch.html",
        lecture=lecture,
        course=course
    )

@app.route("/add_lecture", methods=["GET", "POST"])
@admin_required
def add_lecture():

    with engine.connect() as conn:

        with engine.connect() as conn:



            categories = conn.execute(
                text("""
                    SELECT *
                    FROM categories
                    ORDER BY name
                """)
            ).fetchall()

            courses = conn.execute(
                text("""
                    SELECT
                        id,
                        title
                    FROM courses
                    ORDER BY title
                """)
            ).fetchall()
            
    if request.method == "POST":

        title = request.form["title"]
        description = request.form.get("description")
        course_id = request.form["course_id"]

        video_type = request.form["video_type"]

        is_free = 1 if request.form.get("is_free") else 0
        is_locked = 1 if request.form.get("is_locked") else 0

        
        duration = request.form.get("duration")

        youtube_url = None
        video_file = None
        thumbnail = None

        # --------------------------
        # YouTube Video
        # --------------------------

        if video_type == "youtube":

            youtube_url = request.form.get("youtube_url")

            if youtube_url:

                if "watch?v=" in youtube_url:

                    video_id = youtube_url.split("watch?v=")[1].split("&")[0]

                    youtube_url = (
                        "https://www.youtube.com/embed/" + video_id
                    )

                elif "youtu.be/" in youtube_url:

                    video_id = youtube_url.split("youtu.be/")[1].split("?")[0]

                    youtube_url = (
                        "https://www.youtube.com/embed/" + video_id
                    )

        # --------------------------
        # Upload MP4
        # --------------------------

        else:
            video = request.files.get("video_file")

            if video and video.filename:

                filename = secure_filename(video.filename)

                video_folder = "static/uploads/videos"

                os.makedirs(video_folder, exist_ok=True)

                video.save(
                    os.path.join(
                        video_folder,
                        filename
                    )
                )

                video_file = filename
        # --------------------------
        # Thumbnail
        # --------------------------

        thumb = request.files.get("thumbnail")

        if thumb and thumb.filename:

            thumb_name = secure_filename(thumb.filename)

            thumb_folder = "static/uploads/lecture_thumbnails"

            os.makedirs(thumb_folder, exist_ok=True)

            thumb.save(
                os.path.join(
                    thumb_folder,
                    thumb_name
                )
            )

            thumbnail = thumb_name

        # --------------------------
        # Insert
        # --------------------------

        with engine.connect() as conn:

            conn.execute(
                text("""
                    INSERT INTO lectures
                    (
                        title,
                        description,
                        youtube_url,
                        video_type,
                        video_file,
                        thumbnail,
                       
                        course_id,
                        is_free,
                        is_locked,
                       
                        duration
                    )

                    VALUES
                    (
                        :title,
                        :description,
                        :youtube_url,
                        :video_type,
                        :video_file,
                        :thumbnail,
                       
                        :course_id,
                        :is_free,
                        :is_locked,
                       
                        :duration
                    )
                """),
                {
                    "title": title,
                    "description": description,
                    "youtube_url": youtube_url,
                    "video_type": video_type,
                    "video_file": video_file,
                    "thumbnail": thumbnail,
                   
                    "course_id": course_id,
                    "is_free": is_free,
                    "is_locked": is_locked,
                    
                    "duration": duration
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
        categories=categories,
        courses=courses
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
                    lectures.description,
                    lectures.youtube_url,
                    lectures.video_type,
                    lectures.video_file,
                    lectures.thumbnail,
                    lectures.duration,
                    lectures.price,
                    lectures.is_free,
                    lectures.is_locked,
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
        course_id = request.form["course_id"]

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
                        category_id = :category_id,
                        course_id = :course_id

                    WHERE id = :id
                """),
                {
                    "title": title,
                    "youtube_url": youtube_url,
                    "category_id": category_id,
                    "course_id": course_id,
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
        courses = conn.execute(
    text("""
        SELECT
            id,
            title
        FROM courses
        ORDER BY title
    """)
).fetchall()

    if not lecture:
        return "Lecture not found", 404


    return render_template(
        "edit_lecture.html",
        lecture=lecture,
        categories=categories,
        courses=courses
    )


@app.route("/lectures")
def lectures():

    if "user" not in session:
        return redirect("/login")

    with engine.connect() as conn:

        courses = conn.execute(
            text("""
                SELECT
    c.*,
    cat.name AS category_name,
    cat.slug AS category_slug,

    (
        SELECT COUNT(*)
        FROM lectures l
        WHERE l.course_id = c.id
    ) AS lecture_count

FROM courses c

LEFT JOIN categories cat
ON c.category_id = cat.id

ORDER BY c.id DESC;
""")
        ).fetchall()

    return render_template(
        "lectures.html",
        courses=courses
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
        SELECT
            id,
            title,
            description,
            youtube_url,
            video_type,
            video_file,
            thumbnail,
            duration,
            price,
            is_free,
            is_locked,
            category_id

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

@app.route("/buy/<int:id>")
def buy_course(id):

    if "user" not in session:
        return redirect("/login")

    with engine.connect() as conn:

        course=conn.execute(
            text("""
            SELECT *
            FROM courses
            WHERE id=:id
            """),
            {"id":id}
        ).fetchone()

    if not course:
        return "Course Not Found",404

    return render_template(
        "payment.html",
        course=course
    )

@app.route("/upload_payment",methods=["POST"])
def upload_payment():

    if "user" not in session:
        return redirect("/login")

    course_id=request.form["course_id"]
    amount=request.form["amount"]

    image=request.files["payment_image"]

    filename=secure_filename(image.filename)

    os.makedirs(
        "static/uploads/payments",
        exist_ok=True
    )

    image.save(
        os.path.join(
            "static/uploads/payments",
            filename
        )
    )

    with engine.connect() as conn:

        existing = conn.execute(
            text("""
                SELECT id
                FROM payment_requests
                WHERE user_id=:user
                AND course_id=:course
                AND status='Pending'
            """),
            {
                "user": session["user_id"],
                "course": course_id
            }
        ).fetchone()

        if existing:

            flash(
                "You have already submitted payment for this course. Please wait for admin approval.",
                "error"
            )

            return redirect(
    url_for("buy_course", id=course_id)
)

        # Agar pending payment nahi hai tabhi insert hoga

        conn.execute(
            text("""
                INSERT INTO payment_requests
                (
                    user_id,
                    course_id,
                    amount,
                    screenshot,
                    status
                )
                VALUES
                (
                    :user,
                    :course,
                    :amount,
                    :image,
                    'Pending'
                )
            """),
            {
                "user": session["user_id"],
                "course": course_id,
                "amount": amount,
                "image": filename
            }
        )

        conn.commit()    
    flash(
        "Payment submitted successfully. Wait for admin approval.",
        "success"
    )

    return redirect(
    url_for("buy_course", id=course_id)
)

@app.route("/manage_payments")
@admin_required
def manage_payments():

    with engine.connect() as conn:

        payments = conn.execute(
            text("""
                SELECT
                    pr.*,
                    users.username,
                    courses.title AS course_name

                FROM payment_requests pr

                JOIN users
                    ON pr.user_id = users.id

                JOIN courses
                    ON pr.course_id = courses.id

                ORDER BY pr.created_at DESC
            """)
        ).fetchall()

    return render_template(
        "admin_payments.html",
        payments=payments
    )

@app.route("/approve_payment/<int:id>")
@admin_required
def approve_payment(id):

    with engine.connect() as conn:

        # Get payment details
        payment = conn.execute(
            text("""
                SELECT *
                FROM payment_requests
                WHERE id=:id
            """),
            {
                "id": id
            }
        ).fetchone()


        if not payment:
            return "Payment Not Found", 404


        # Update payment status
        conn.execute(
            text("""
                UPDATE payment_requests
                SET status='Approved'
                WHERE id=:id
            """),
            {
                "id": id
            }
        )


        # Check if course already purchased
        existing = conn.execute(
            text("""
                SELECT id
                FROM purchased_courses
                WHERE user_id=:user
                AND course_id=:course
            """),
            {
                "user": payment.user_id,
                "course": payment.course_id
            }
        ).fetchone()


        # Insert only if not already purchased
        if not existing:

            conn.execute(
                text("""
                    INSERT INTO purchased_courses
                    (
                        user_id,
                        course_id,
                        amount
                    )

                    VALUES
                    (
                        :user,
                        :course,
                        :amount
                    )
                """),
                {
                    "user": payment.user_id,
                    "course": payment.course_id,
                    "amount": payment.amount
                }
            )


        conn.commit()


    flash(
        "Course Unlocked Successfully!",
        "success"
    )

    return redirect("/manage_payments")

@app.route("/reject_payment/<int:id>")
@admin_required
def reject_payment(id):

    with engine.connect() as conn:

        conn.execute(
            text("""
                UPDATE payment_requests

                SET status='Rejected'

                WHERE id=:id
            """),
            {"id": id}
        )

        conn.commit()

    flash(
        "Payment Rejected!",
        "warning"
    )

    return redirect("/manage_payments")

if __name__ == "__main__":
    app.run(debug=True)