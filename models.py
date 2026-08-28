from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()



class Notification(db.Model):

    __tablename__ = "notifications"


    id = db.Column(
        db.Integer,
        primary_key=True
    )


    title = db.Column(
        db.String(255),
        nullable=False
    )


    message = db.Column(
        db.Text
    )


    type = db.Column(
        db.String(20)
    )


    reference_id = db.Column(
        db.Integer
    )


    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )



class NotificationRead(db.Model):

    __tablename__ = "notification_reads"


    id = db.Column(
        db.Integer,
        primary_key=True
    )


    user_id = db.Column(
        db.Integer,
        nullable=False
    )


    notification_id = db.Column(
        db.Integer,
        nullable=False
    )


    read_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )