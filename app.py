#! /usr/bin/env python3
from datetime import datetime
from typing import List
from flask import Flask, jsonify, request, make_response, render_template, session, redirect, url_for, flash
from PIL import Image, ImageDraw, ImageFont
from pymongo.cursor import Cursor
import requests
import pyzbar.pyzbar as pyzbar
import qrcode
from celery import Celery
from flask_mail import Mail, Message
from blueprints import sms_app
from utils import SentClient, init_credential
from flask_pymongo import PyMongo
import os


class ReverseProxied:
    """
    # 反向代理处理中间件
    # 重点处理HTTPX_X_FORWARDED_PREFIX,用于写入script_name，使url_for结果正常
    # 其次处理HTTPX_X_FORWARDED_FOR,替换真正的客户ip
    # 本wsgi参数命名根据werkzeug的ProxyFixMiddleware而定
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_FORWARDED_PREFIX', '')
        x_forwarded_for = environ.get('HTTP_X_FORWARDED_FOR', '')
        host = environ.get('HTTP_X_FORWARDED_HOST', '')
        scheme = environ.get('HTTP_X_FORWARDED_PROTO', '')

        if host:
            environ['HTTP_HOST'] = host
            print(f'host: {host}')

        if script_name:
            environ['SCRIPT_NAME'] = script_name
            print(f'script_name: {environ["SCRIPT_NAME"]}')

        if scheme:
            environ['wsgi.url_scheme'] = scheme
            print(f'scheme: {scheme}')

        if x_forwarded_for:
            print(f'x_forwarded_for: {x_forwarded_for}')

        return self.app(environ, start_response)


flask_app = Flask(__name__)
flask_app.wsgi_app = ReverseProxied(flask_app.wsgi_app)
flask_app.config['SECRET_KEY'] = 'somethinguniqueandrememberless'
flask_app.config['CELERY_BROKER_URL'] = 'amqp://ggadmin:GG_20200401@www.rechatun.com:5672/'
flask_app.config['CELERY_BROKER_URL'] = 'amqp://ggadmin:GG_20200401@www.rechatun.com:5672/'
flask_app.config['MONGODB_URI'] = 'mongodb://colaftc:fcp0520@localhost:27017/agent'
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

# a clousure for get tx credential singleton global
get_credential = init_credential(flask_app.config['TX_APPID'], flask_app.config['TX_APPSECRET'])
g_no_check_list = [
    '/login',
    '/mail',
    '/exp/info',
    '/qr/decode',
    '/qr/rebuild',
    '/celery',
    '/sms-callback',
    '/get-sample',
]


@celery.task
def send_sms_task(numbers: List[str], sign: str = '浩轩陈皮', template_id: str = '881535'):
    with flask_app.app_context():
        req = models.SendSmsRequest()
        req.SmsSdkAppid = flask_app.config['SMS_SDKAPPID']
        req.Sign = sign
        req.TemplateID = template_id
        send_sms(numbers, req)


@celery.task
def send_sms_single_task(number: str, sign: str = '浩轩陈皮', template_id: str = '881535'):
    with flask_app.app_context():
        req = models.SendSmsRequest()
        req.SmsSdkAppid = flask_app.config['SMS_SDKAPPID']
        req.Sign = sign
        req.TemplateID = template_id
        send_sms([number], req)


@celery.task
def send_mail_async(content: str, subject: str, to: str, mailer: Mail = mail) -> None:
    msg = Message(subject, sender=flask_app.config['MAIL_DEFAULT_SENDER'], recipients=[to])
    msg.body = content

    with flask_app.app_context():
        mailer.send(msg)


@flask_app.before_request
def before_request(*args, **kwargs):
    request.root_dir = os.path.dirname(__file__)
    if request.path in g_no_check_list:
        return None

    user = session.get('user')
    if user is not None:
        request.user = user
        return None

    request.user = None
    return redirect(url_for('login'))


@flask_app.route('/get-sample', methods=['GET', 'POST'])
def get_sample():
    if request.method == 'POST':
        receiver = request.form['receiver']
        tel = request.form['tel']
        addr = request.form['addr']
        result = mongo.db.sample.insert({
            'receiver': receiver,
            'tel': tel,
            'address': addr,
            'created_at': datetime.now(),
            'status': 0,
        })
        print(result.id)
        return render_template('got-sample.html')

    return render_template('get-sample.html')


@flask_app.route('/sms-callback', methods=['GET', 'POST'])
def sms_callback():
    # json example
    # [{'mobile': '15215221290', 'report_status': 'SUCCESS', 'description': '用户短信接收成功', 'errmsg': 'DELIVRD',
    #   'user_receive_time': '2021-03-22 14:10:53' '2034:03221042101042831562207829460731', 'nationcode': '86'}]

    if request.method == 'GET':
        result: Cursor = mongo.db.sms_result.find()
        return {'data': [{
            'mobile': r['mobile'],
            'status': r['status'],
            'errmsg': r['errmsg'],
            'desc': r['desc'],
            'receive_at': r['receive_at'],
        } for r in result]} if result.count() > 0 else 'None'
    else:
        print('sms-callback')
        json = request.json

        data = [{
            'mobile': j['mobile'],
            'status': j['report_status'],
            'desc': j['description'],
            'errmsg': j['errmsg'],
            'receive_at': j['user_receive_time'],
        } for j in json]

        try:
            mongo.db.sms_result.insert_many(data)
        except Exception as e:
            print(f'sms-callback save not ok : {e}')
        return ''


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
