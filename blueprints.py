from flask import Blueprint, render_template, request, current_app
from utils import parse_client_list, send_sms, prepare_send_sms
import json


sms_app = Blueprint('sms', import_name='sms', url_prefix='/sms')


@sms_app.route('/test', methods=['GET', 'POST'])
def test_send():
    number = request.form.get('number', '+8613925114811')
    req = prepare_send_sms()
    return send_sms([number], req)


@sms_app.route('/add-template', methods=['GET', 'POST'])
def add_template():
    return 'Add Template View'


@sms_app.route('/client-list', methods=['GET', 'POST'])
def upload_client_list():
    if request.method == 'POST':
        client_list = request.files.get('list')
        if client_list is None:
            return 'None', 403
        # TODO: do save client-list here
        data = parse_client_list(request, client_list, add_86prefix=False)
        for d in data:
            print(d)
        return 'got it'
    else:
        return render_template('upload-client-list.html')


@sms_app.route('/parse', methods=['GET', 'POST'])
def parse_to_csv():
    with_name = request.form.get('with-name', False)

    # TODO: complete this method, convert to csv file for download

    if with_name:
        pass
    else:
        pass
    return 'Not Implement'


@sms_app.route('/send', methods=['GET', 'POST'])
def send():
    if request.method == 'GET':
        return render_template('sms_send.html')

    try:
        template_id = request.form.get('template_id')
        sign = request.form.get('sign')
        if template_id and sign:
            req = prepare_send_sms(sdk_id=current_app.config['SMS_SDKAPPID'], template_id=template_id, sign=sign)
        else:
            req = prepare_send_sms(sdk_id=current_app.config['SMS_SDKAPPID'])
        data = parse_client_list(request, request.files['list'])

        from app import get_credential
        resp = json.loads(send_sms([v.client_number for v in data], req=req, cred=get_credential()))
        return render_template('sms_finished.html', resp=resp)
    except Exception as ex:
        print(ex)
        return render_template('sms_send.html')


@sms_app.route('/send-single', methods=['GET', 'POST'])
def send_single():
    if request.method == 'GET':
        return render_template('sms_send_single.html')

    try:
        number = '+86' + request.form['number']
        template_id = request.form.get('template_id')
        sign = request.form.get('sign')

        from app import get_credential

        if template_id and sign:
            req = prepare_send_sms(sdk_id=current_app.config['SMS_SDKAPPID'], template_id=template_id, sign=sign)
        else:
            req = prepare_send_sms(sdk_id=current_app.config['SMS_SDKAPPID'])

        resp = json.loads(send_sms([number], req=req, cred=get_credential()))
        return render_template('sms_finished.html', resp=resp)
    except Exception as ex:
        print(ex)
        return render_template('sms_send_single.html')


@sms_app.route('/index', methods=['GET'])
def index():
    return render_template('sms_index.html')
