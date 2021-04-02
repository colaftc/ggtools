from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import ChoiceType
from flask_login import UserMixin
from enum import Enum
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


class Seller(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True)
    tel = db.Column(db.String(50), unique=True)
    status = db.Column(db.Boolean(), default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now())

    def __str__(self):
        return f'{self.name} | {self.tel if self.tel else "无记录"}'


class FollowStatusChoices(Enum):
    Talking ='初步交流'
    Got_wechat = '已加微信'
    Sent_sample = '已发样板'
    Bought = '已成交'


class Following(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name = db.Column(db.String(100))
    tel = db.Column(db.String(20))
    status = db.Column(ChoiceType(FollowStatusChoices))
    created_at = db.Column(db.DateTime, default=datetime.datetime.now())
