from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
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


TagsMap = db.Table(
    'tags_map',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')),
    db.Column('following_id', db.Integer, db.ForeignKey('following.id')),
)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50))
    followings = db.relationship('Following', secondary=TagsMap)

    def __str__(self):
        return self.name


class FollowStatusChoices(Enum):
    Talking ='初步交流'
    Got_wechat = '已加微信'
    Sent_sample = '已发样板'
    Bought = '成交客户'
    Giveup = '放弃跟进'


class Following(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name = db.Column(db.String(100))
    company = db.Column(db.String(100))
    address = db.Column(db.String(255))
    tel = db.Column(db.String(20))
    follower_id = db.Column(db.Integer(), db.ForeignKey('seller.id'))
    follower = db.relationship('Seller', backref=db.backref('follows'), lazy='dynamic', uselist=True)
    tags = db.relationship('Tag', secondary=TagsMap)
    status = db.Column(ChoiceType(FollowStatusChoices))
    markup = db.Column(db.String(200))
    download = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment='更新时间')
