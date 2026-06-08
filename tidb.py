#C:\Users\Dell\Downloads\isrgrootx1.pem

from sqlalchemy import create_engine, text

DATABASE_URL = (
    "mysql+pymysql://3FtQQGViQkjLout.root:yQrM14kdizk6648t@gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com:4000/flask_auth"
)


engine = create_engine(
    DATABASE_URL,
    connect_args={
        "ssl": {
            "ca": r"C:\Users\Dell\Downloads\isrgrootx1.pem"
        }
    }
)

try:
    with engine.connect() as conn:
        
        conn.execute(
            text("""
                INSERT INTO users (username, email, password)
                VALUES (:username, :email, :password)
            """),
            {
                "username": "Malik",
                "email": "newemail@gmail.com",
                "password": "123456"
            }
        )

        conn.commit()

    print("✅ Data inserted successfully")

except Exception as e:
    print("❌ Error:")
    print(e)