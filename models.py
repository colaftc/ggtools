from flask_sqlalchemy import SQLAlchemy
import datetime


db = SQLAlchemy()


class ClientInfo(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name = db.Column(db.String(100))
    company = db.Column(db.String(255))
    address = db.Column(db.String(255))
    tel = db.Column(db.String(50), unique=True)
    industry = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.datetime.now())

    def __str__(self):
        return f'{self.company}: {self.tel}'
