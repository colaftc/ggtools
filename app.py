#! /usr/bin/env python3

from flask import Flask, jsonify, request, make_response
from PIL import Image, ImageDraw, ImageFont
import requests
import pyzbar.pyzbar as pyzbar
import qrcode

app = Flask(__name__)


def decode_qrcode(url: str, filename: str = 'temp.jpg') -> str:
    res = requests.get(url)
    with open(filename, 'wb') as f:
        f.write(res.content)
        img = Image.open(filename)
        code = pyzbar.decode(img)
        return code


@app.route('/qr/decode', methods=['POST'])
def qr_decode() :
    url = request.values.get('url', '')
    print(url)
    if url == '':
        return jsonify({'data': None})

    data = decode_qrcode(url)
    return jsonify({
        'data': data[0].data.decode('utf-8')
    })


@app.route('/qr/rebuild', methods=['POST'])
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


# TODO : write transport info query here...

if __name__ == '__main__':
    app.run(port=8000)
