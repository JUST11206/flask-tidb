#pip install sqlalchemy pymysql cryptography
from flask import Flask , render_template,request,redirect,session
from sqlalchemy import create_engine, text
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "secret@123"
app.permanent_session_lifetime = timedelta(days=7)

DATABASE_URL = "mysql+pymysql://3FtQQGViQkjLout.root:yQrM14kdizk6648t@gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com:4000/flask_auth"

engine = create_engine(
    DATABASE_URL,
    pool_recycle=3600
)

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
            return redirect("/dashboard")

        return "Invalid Login"

    return render_template("login.html")

#signup 

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        with engine.connect() as conn:

            conn.execute(
                text("""
                INSERT INTO users(username,email,password)
                VALUES(:username,:email,:password)
                """),
                {
                    "username": username,
                    "email": email,
                    "password": password
                }
            )

            conn.commit()

        return redirect("/login")

    return render_template("signup.html")


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

@app.route("/profile")
def profile():
    return render_template("profile.html",
        username="Malik",
        email="malik@gmail.com")

@app.route("/notes/<subject>")
def subject(subject):
    return render_template("subject.html", subject=subject)

if __name__ == "__main__":
    app.run(debug=True)