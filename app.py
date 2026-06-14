#pip install sqlalchemy pymysql cryptography
from flask import Flask , render_template,request,redirect,session ,flash
from sqlalchemy import create_engine, text
from datetime import timedelta
import os
from werkzeug.utils import secure_filename
from email_validator import validate_email, EmailNotValidError
from flask import flash
from flask_mail import Mail, Message
import random



app = Flask(__name__)
app.secret_key = "secret@123"
app.permanent_session_lifetime = timedelta(days=7)

# app.config.update(
#     MAIL_SERVER='smtp.gmail.com',
#     MAIL_PORT=587,
#     MAIL_USE_TLS=True,
#     MAIL_USE_SSL=False,
#     MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
#     MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
#     MAIL_DEFAULT_SENDER=os.environ.get("MAIL_USERNAME")
# )
# mail = Mail(app)

#Work on local proper

# app.config.update(
#     MAIL_SERVER='smtp.gmail.com',
#     MAIL_PORT=587,
#     MAIL_USE_TLS=True,
#     MAIL_USE_SSL=False ,
#     MAIL_USERNAME="u5976421@gmail.com",
#     MAIL_PASSWORD="tgde nrwr wqxc cqeg",
#     MAIL_DEFAULT_SENDER="u5976421@gmail.com"
#     )
# mail = Mail(app)
# #new 

app.config.update(
    MAIL_SERVER='smtp.sendgrid.net',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_USERNAME='apikey',
    MAIL_PASSWORD=os.getenv("SENDGRID_API_KEY"),
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_USERNAME")
)

mail = Mail(app)

print("MAIL_USERNAME =", os.getenv("MAIL_USERNAME"))
print("SENDGRID_API_KEY EXISTS =", bool(os.getenv("SENDGRID_API_KEY")))

DATABASE_URL = "mysql+pymysql://3FtQQGViQkjLout.root:yQrM14kdizk6648t@gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com:4000/flask_auth"

engine = create_engine(
    DATABASE_URL,
    pool_recycle=3600
)

UPLOAD_FOLDER = "static/profile_images"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/mail-test")
def mail_test():
    try:

        print("MAIL_USERNAME =", repr(app.config.get("MAIL_USERNAME")))
        print("MAIL_DEFAULT_SENDER =", repr(app.config.get("MAIL_DEFAULT_SENDER")))

        msg = Message(
            subject="Render Test",
            sender=app.config.get("MAIL_USERNAME"),
            recipients=["saifmalik7217@gmail.com"]
        )

        msg.body = "Testing Render SMTP"

        mail.send(msg)

        return "SUCCESS"

    except Exception as e:
        print("MAIL TEST ERROR:", repr(e))
        return f"ERROR: {repr(e)}"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():

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
            session["user"] = user.username
            session["email"] = user.email
            return redirect("/dashboard")
        flash("You enter Wrong Password! or Email", "error")
        return redirect("/login")

    return render_template("login.html")

#signup 


# @app.route("/signup", methods=["GET", "POST"])
# def signup():

#     if request.method == "POST":

#         username = request.form["username"]
#         email = request.form["email"]

#         password = request.form["password"]

#         with engine.connect() as conn:

#             conn.execute(
#                 text("""
#                 INSERT INTO users(username,email,password)
#                 VALUES(:username,:email,:password)
#                 """),
#                 {
#                     "username": username,
#                     "email": email,
#                     "password": password
#                 }
#             )

#             conn.commit()

#          # User ko automatically login kara do
#         session.permanent = True
#         session["user"] = username
#         session["email"] = email

#         # Direct dashboard par bhejo
#         return redirect("/dashboard")

#     return render_template("signup.html")

#This is 10 june 2026 

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        try:
            username = request.form["username"]
            email = request.form["email"]
            password = request.form["password"]

            # EMAIL VALIDATION
            try:
                valid = validate_email(email)
                email = valid.email

            except EmailNotValidError:
                flash("Please enter a valid email address!", "error")
                return redirect("/signup")

            # CHECK IF EMAIL ALREADY EXISTS
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

            # OTP GENERATION
            otp = random.randint(100000, 999999)

            session["otp"] = str(otp)
            session["username"] = username
            session["email"] = email
            session["password"] = password

            # SEND EMAIL
            try:

                msg = Message(
                    subject="OTP Verification",
                    sender=app.config.get("MAIL_USERNAME"),
                    recipients=[email]
                )

                msg.body = f"""
Hello {username},

Your OTP for StudyHub account verification is:

{otp}

This OTP is valid for a short time.

Thanks,
StudyHub Team
"""
                
                print("STARTING EMAIL SEND")
                mail.send(msg)

                print("EMAIL SENT SUCCESSFULLY")

            except Exception as e:

                print("=" * 50)
                print("SMTP ERROR:", repr(e))
                print("=" * 50)

                flash("OTP email failed!", "error")
                return redirect("/signup")

            # SUCCESS
            return redirect("/verify-otp")

        except Exception as e:

            print("=" * 50)
            print("SIGNUP ERROR:", repr(e))
            print("=" * 50)

            flash("Something went wrong!", "error")
            return redirect("/signup")

    return render_template("signup.html")



    #         try:
    #             msg = Message(
    #                 "OTP Verification",
    #                 sender=app.config.get('MAIL_USERNAME'),
    #                 recipients=[email]
    #             )

    #             msg.body = f"Your OTP is: {otp}"
    #             mail.send(msg)

    #         except Exception as e:
    #             print("EMAIL ERROR:", e)
    #             flash("OTP email failed. Try again!", "error")
    #             return redirect("/signup")

    #         return redirect("/verify-otp")

    #     except Exception as e:
    #         print("SIGNUP ERROR:", e)
    #         flash("Something went wrong!", "error")
    #         return redirect("/signup")

    # return render_template("signup.html")


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":

        try:
            user_otp = request.form["otp"]

            # ---------------- OTP CHECK ----------------
            if user_otp == session.get("otp"):

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

                except Exception as e:
                    print("DB INSERT ERROR:", e)
                    flash("Database error while creating account!", "error")
                    return redirect("/signup")

                session["user"] = session["username"]

                flash("Account created successfully!", "success")
                return redirect("/dashboard")

            flash("Invalid OTP!", "error")

        except Exception as e:
            print("OTP VERIFY ERROR:", e)
            flash("Something went wrong!", "error")
            return redirect("/signup")

    return render_template("verify-otp.html")
# @app.route("/verify-otp", methods=["GET", "POST"])
# def verify_otp():

#     if request.method == "POST":

#         user_otp = request.form["otp"]

#         if user_otp == session.get("otp"):

#             with engine.connect() as conn:

#                 conn.execute(
#                     text("""
#                     INSERT INTO users(username,email,password)
#                     VALUES(:username,:email,:password)
#                     """),
#                     {
#                         "username": session["username"],
#                         "email": session["email"],
#                         "password": session["password"]
#                     }
#                 )

#                 conn.commit()

#             session["user"] = session["username"]

#             flash("Account created successfully!", "success")

#             return redirect("/dashboard")

#         flash("Invalid OTP!", "error")

#     return render_template("verify-otp.html")


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
# Dashboard
@app.route("/dashboard")
def dash():

    if "user" not in session:
        return redirect("/login")

    return render_template(
        "dashboard.html",
        username=session["user"]
    )


# Logout
@app.route("/logout")
def logout():

    session.clear()
    return redirect("/login")

#sidebar section
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/notes")
def note():
    return render_template("notes.html")

# @app.route("/lectures")
# def lectures():
#     return render_template("lectures.html")


@app.route("/pdf")
def pdf():
    return render_template("pdf.html")

@app.route("/notes/<subject>")
def subject(subject):
    return render_template("subject.html", subject=subject)


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
def add_lecture():

    if request.method == "POST":

        title = request.form["title"]
        youtube_url = request.form["youtube_url"]

        with engine.connect() as conn:

            conn.execute(
                text("""
                INSERT INTO lectures
                (title, youtube_url)
                VALUES
                (:title, :youtube_url)
                """),
                {
                    "title": title,
                    "youtube_url": youtube_url
                }
            )

            conn.commit()

        return redirect("/admin")

    return render_template("add_lecture.html")

@app.route("/lectures")
def lect():

    with engine.connect() as conn:
        lectures = conn.execute(
            text("SELECT * FROM lectures")
        ).fetchall()

    print(lectures)   # <-- add this

    return render_template(
        "lectures.html",
        lectures=lectures
    )

PDF_FOLDER = "static/pdfs"
app.config["PDF_FOLDER"] = PDF_FOLDER

os.makedirs(PDF_FOLDER, exist_ok=True)

@app.route("/add_pdf", methods=["GET", "POST"])
def add_pdf():

    if request.method == "POST":

        title = request.form["title"]
        pdf = request.files["pdf"]

        filename = secure_filename(pdf.filename)

        path = os.path.join(app.config["PDF_FOLDER"], filename)
        pdf.save(path)

        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO pdfs (title, pdf_file) VALUES (:title, :pdf_file)"),
                {"title": title, "pdf_file": filename}
            )
            conn.commit()

        return redirect("/pdfs")   # 👈 MUST BE THIS

    return render_template("add_pdf.html")

@app.route("/pdfs")
def pdfs():

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM pdfs"))
        pdf_list = result.fetchall()

    print(pdf_list)   # 👈 ADD THIS LINE (IMPORTANT DEBUG)

    return render_template("pdf.html", pdfs=pdf_list)





if __name__ == "__main__":
    app.run(debug=True)