from flask import Blueprint, render_template, request


sms_app = Blueprint('sms', import_name='sms', url_prefix='/sms')


@sms_app.route('/test', methods=['GET', 'POST'])
def test_send():
    from app import prepare_send_sms, send_sms
    number = request.form.get('number', '+8613925114811')
    req = prepare_send_sms()
    return send_sms([number], req)


@sms_app.route('/add-template', methods=['GET', 'POST'])
def add_template():
    return 'Add Template View'


@sms_app.route('/send', methods=['GET', 'POST'])
def send():
    return render_template('sms_send.html')


@sms_app.route('/send-single', methods=['GET', 'POST'])
def send_single():
    return 'Send Single'


@sms_app.route('/index', methods=['GET'])
def index():
    return render_template('sms_index.html')
