#! /usr/bin/env python3
from typing import List, Any
from flask import Flask, jsonify, request, make_response, render_template, session, redirect, url_for, flash
from PIL import Image, ImageDraw, ImageFont
from collections import namedtuple
import requests
import pyzbar.pyzbar as pyzbar
import qrcode
from celery import Celery
from flask_mail import Mail, Message
from blueprints import sms_app
from flask_pymongo import PyMongo
# tencent cloud sdk
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.sms.v20190711 import sms_client, models
import os


class ReverseProxied:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        print(f'Proxied script-name : {environ.get("HTTP_X_SCRIPT_NAME", "")}')
        print(f'Proxied x-forwarded-for : {environ.get("HTTP_X_FORWARDED_FOR", "")}')
        return self.app(environ, start_response)


flask_app = Flask(__name__)
flask_app.wsgi_app = ReverseProxied(flask_app.wsgi_app)
flask_app.config['SECRET_KEY'] = 'somethinguniqueandrememberless'
flask_app.config['CELERY_BROKER_URL'] = 'amqp://ggadmin:GG_20200401@www.rechatun.com:5672/'
flask_app.config['CELERY_BROKER_URL'] = 'amqp://ggadmin:GG_20200401@www.rechatun.com:5672/'
flask_app.config['MONGODB_URI'] = 'mongodb://localhost/sms'
flask_app.config['result_backend'] = 'redis://www.rechatun.com:6899/0'
flask_app.config['accept_content'] = ['pickle', 'json']
flask_app.config['result_serializer'] = 'pickle'


celery = Celery(flask_app.name, broker=flask_app.config['CELERY_BROKER_URL'])
celery.conf.update(flask_app.config)
mongo = PyMongo(flask_app, uri=flask_app.config['MONGODB_URI'])

# sms settings
flask_app.config['TX_APPID'] = 'AKID6PSFl0LRt4zYy8MYpKZXEepjMifNobCP'
flask_app.config['TX_APPSECRET'] = '6bcMs64ylHWVMxITOcgV7crqY0LSJgx4'
flask_app.config['SMS_SDKAPPID'] = '1400491233'

# Flask-Mail configuration
flask_app.config['MAIL_SERVER'] = 'smtp.126.com'
flask_app.config['MAIL_PORT'] = 25
flask_app.config['MAIL_USE_TLS'] = True
flask_app.config['MAIL_USERNAME'] = 'colaftc'
flask_app.config['MAIL_PASSWORD'] = 'QKRIUAMMLHGGYEGB'
flask_app.config['MAIL_DEFAULT_SENDER'] = 'colaftc@126.com'

flask_app.register_blueprint(sms_app)

mail = Mail(flask_app)
g_no_check_list = [
    '/login',
    '/mail',
    '/exp/info',
    '/qr/decode',
    '/qr/rebuild',
    '/celery',
]


SentClient = namedtuple('SentClient', ['client_name', 'client_number'])


def init_tx_credential():
    return credential.Credential(secretId=flask_app.config['TX_APPID'], secretKey=flask_app.config['TX_APPSECRET'])


def save_sent_sms(sent_list: List[SentClient], err=None):
    if err is not None:
        print('发送出错不作记录')
        return

    with flask_app.app_context():
        mongo.db.sms.insert_many([{
            'client_name': v['client_name'],
            'client_number': v['client_number'],
        } for v in sent_list])


@celery.task
def send_sms_task(numbers: List[SentClient], sign: str = '浩轩陈皮', template_id='881535'):
    req = prepare_send_sms(template_id, sign)
    send_sms(numbers, req)


def prepare_send_sms(template_id='881535', sign: str = '浩轩陈皮') -> models.SendSmsRequest:
    req = models.SendSmsRequest()
    req.SmsSdkAppid = flask_app.config['SMS_SDKAPPID']
    req.Sign = sign
    req.TemplateID = template_id
    return req


def parse_client_list():
    # TODO: make this complete
    pass


def send_sms(numbers: List[SentClient], req: models.SendSmsRequest, after_send_func=None):
    client = sms_client.SmsClient(init_tx_credential(), 'ap-guangzhou')
    req.PhoneNumberSet = numbers
    error = None
    try:
        resp = client.SendSms(req)
        return resp.to_json_string()
    except TencentCloudSDKException as err:
        error = err
        print(err)
    finally:
        if after_send_func is not None:
            after_send_func(numbers=numbers, err=error)


@celery.task
def send_mail_async(content: str, subject: str, to: str, mailer: Mail = mail) -> None:
    msg = Message(subject, sender=flask_app.config['MAIL_DEFAULT_SENDER'], recipients=[to])
    msg.body = content

    with flask_app.app_context():
        mailer.send(msg)


@flask_app.before_request
def before_request(*args, **kwargs):
    if request.path in g_no_check_list:
        return None

    user = session.get('user')
    if user is not None:
        request.user = user
        return None

    request.user = None
    return redirect('/login')


@flask_app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', form=request.form)
    else:
        username = request.form.get('username')
        pwd = request.form.get('password')
        if username == 'ggadmin' and pwd == 'GG_20200401':
            resp = make_response('<html></html>', 301)
            session['user'] = {
                'username': 'ggadmin',
                'role': 'admin',
            }
            resp.headers['content-type'] = 'text/plain'
            resp.headers['location'] = url_for('sms.index')
            flash('登录成功')
            return resp
        else:
            return render_template('login.html')


@flask_app.route('/logout', methods=['GET'])
def logout():
    session.pop('user')
    request.user = None
    return redirect(url_for('login'))


@flask_app.route('/mail', methods=['GET', 'POST'])
def mail():
    if request.method == 'GET':
        return render_template('mail.html', email=session.get('email', ''))

    email = request.form['email']
    session['email'] = email

    # send the email
    email_data = {
        'subject': 'Hello from Flask',
        'to': email,
        'body': 'This is a test email sent from a background Celery task.'
    }
    if request.form['submit'] == 'Send':
        # send right away
        send_mail_async.apply_async(args=[email_data['body'], email_data['subject'], email_data['to']])
        flash('Sending email to {0}'.format(email))
    else:
        # send in one minute
        send_mail_async.apply_async(args=[email_data['body'], email_data['subject'], email_data['to']], countdown=60)
        flash('An email will be sent to {0} in one minute'.format(email))

    return redirect(url_for('mail'))


def decode_qrcode(url: str, filename: str = 'temp.jpg') -> str:
    res = requests.get(url)
    with open(filename, 'wb') as f:
        f.write(res.content)
        img = Image.open(filename)
        code = pyzbar.decode(img)
        return code


@flask_app.route('/qr/decode', methods=['POST'])
def qr_decode():
    url = request.values.get('url', '')
    print(url)
    if url == '':
        return jsonify({'data': None})

    data = decode_qrcode(url)
    return jsonify({
        'data': data[0].data.decode('utf-8')
    })


@flask_app.route('/qr/rebuild', methods=['POST'])
def qr_rebuild():
    try:
        url = request.values['url']
        text = request.values['text']
    except:
        return jsonify({
            'errMsg': 'invalid params',
        }), 403

    filename = 'temp_code.jpg'
    data = decode_qrcode(url)
    qr = qrcode.QRCode(8, qrcode.constants.ERROR_CORRECT_Q)
    qr.add_data(data[0].data.decode('utf-8'))
    qr.make()
    img = qr.make_image()
    draw = ImageDraw.Draw(img)
    draw.text((img.size[0] / 2 - 40, img.size[1] - 40),
              text,
              font=ImageFont.truetype(font='hei.ttf', size=28)
              )
    img.save(filename)

    with open(filename, 'rb') as f:
        resp = make_response(f.read())
        resp.headers['Content-type'] = 'image/jpeg'
        return resp


@flask_app.route('/exp/info', methods=['POST'])
def exp_info():
    exp_type = request.values.get('type', 'auto')
    exp_code = request.values.get('number', '')
    secret = request.values.get('secret', '')

    if secret != 'ggadmin5197':
        return jsonify({
            'errMsg': 'forbiden'
        }), 403

    exp_api_url = 'https://api.jisuapi.com/express/query'
    exp_appkey = '78dfa54445483038'
    res = requests.post(exp_api_url, data={
        'type': exp_type,
        'number': exp_code,
        'appkey': exp_appkey,
    })
    if res.status_code == 200:
        result = res.json()
    else:
        return jsonify({
            'errMsg': 'result not found',
        }), 404

    print(result)
    return jsonify(result)


if __name__ == '__main__':
    flask_app.run(port=8000)
