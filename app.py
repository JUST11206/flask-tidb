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
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_USERNAME"),
     MAIL_TIMEOUT=20
)

mail = Mail(app)
print("MAIL_USERNAME =", repr(os.getenv("MAIL_USERNAME")))
print("MAIL_PASSWORD EXISTS =", bool(os.getenv("MAIL_PASSWORD")))

DATABASE_URL = "mysql+pymysql://3FtQQGViQkjLout.root:yQrM14kdizk6648t@gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com:4000/flask_auth"

engine = create_engine(
    DATABASE_URL,
    pool_recycle=3600
)

UPLOAD_FOLDER = "static/profile_images"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

@app.route("/lectures")
def lectures():
    return render_template("lectures.html")

@app.route("/pdf")
def pdfs():
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



if __name__ == "__main__":
    app.run(debug=True)