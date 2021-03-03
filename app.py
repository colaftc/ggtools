#! /usr/bin/env python3

from flask import Flask, jsonify, request, make_response, render_template, session, redirect, url_for, flash
from PIL import Image, ImageDraw, ImageFont
import requests
import pyzbar.pyzbar as pyzbar
import qrcode
from celery import Celery
from flask_mail import Mail, Message
import os


flask_app = Flask(__name__)
flask_app.config['SECRET_KEY'] = 'somethinguniqueandrememberless'
flask_app.config['CELERY_BROKER_URL'] = 'amqp://ggadmin:GG_20200401@www.rechatun.com:5672/'
flask_app.config['CELERY_BROKER_URL'] = 'amqp://ggadmin:GG_20200401@www.rechatun.com:5672/'
flask_app.config['result_backend'] = 'redis://www.rechatun.com:6899/0'
flask_app.config['accept_content'] = ['pickle', 'json']
flask_app.config['result_serializer'] = 'pickle'

celery = Celery(flask_app.name, broker=flask_app.config['CELERY_BROKER_URL'])
celery.conf.update(flask_app.config)

# Flask-Mail configuration
flask_app.config['MAIL_SERVER'] = 'smtp.126.com'
flask_app.config['MAIL_PORT'] = 25
flask_app.config['MAIL_USE_TLS'] = True
flask_app.config['MAIL_USERNAME'] = 'colaftc'
flask_app.config['MAIL_PASSWORD'] = 'QKRIUAMMLHGGYEGB'
flask_app.config['MAIL_DEFAULT_SENDER'] = 'colaftc@126.com'

mail = Mail(flask_app)

@celery.task
def test_task():
    with open('./testing.dat', 'w+', encoding='utf-8') as f:
        f.write(flask_app.config['SECRET_KEY'])


@celery.task
def send_mail_async(content: str, subject: str, to: str, mailer: Mail = mail) -> None:
    msg = Message(subject, sender=flask_app.config['MAIL_DEFAULT_SENDER'], recipients=[to])
    msg.body = content

    with flask_app.app_context():
        mailer.send(msg)


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


@flask_app.route('/celery', methods=['GET', 'POST'])
def tests():
    task = test_task.apply_async(countdown=20)
    return 'ok'


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


# TODO : write transport info query here...

if __name__ == '__main__':
    flask_app.run(port=8000)
