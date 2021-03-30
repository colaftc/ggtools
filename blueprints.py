from flask import Blueprint, render_template, request, current_app, flash, abort
from utils import parse_client_list, send_sms, prepare_send_sms
from models import db, ClientInfo
from sqlalchemy.exc import IntegrityError
from flask_restful import Api, reqparse, Resource, marshal_with, fields
import json
import pymysql


sms_app = Blueprint('sms', import_name='sms', url_prefix='/sms')
api = Api(sms_app)


client_info_fields = {
    'name': fields.String(),
    'tel': fields.String(),
    'company': fields.String(),
    'industry': fields.String(),
    'address': fields.String(),
}


class ClientInfoResource(Resource):
    @marshal_with(client_info_fields)
    def get(self, client_id=None):
        if client_id:
            result = ClientInfo.query.get(client_id)
            if not result:
                abort(404)
        return ClientInfo.query.all()


api.add_resource(ClientInfoResource, '/api/client-info', '/api/client-info/<int:client_id>')
paginate_args = reqparse.RequestParser()
paginate_args.add_argument(
    'page',
    type=int,
    location=['args'],
    required=False,
    default=1,
)
filter_args = reqparse.RequestParser()
filter_args.add_argument(
    'province',
    type=str,
    location=['form', 'args'],
    required=False,
    default=None,
)
filter_args.add_argument(
    'company',
    type=str,
    location=['form', 'args'],
    required=False,
    default=None,
)


@sms_app.route('/client-info', methods=['GET', "POST"])
def client_info(area: str = None):
    args = paginate_args.parse_args()
    page = args['page']
    page_size = int(request.cookies.get('page_size', 200))

    record_count = ClientInfo.query.count()
    if record_count < page_size * page:
        page = 1

    filters = filter_args.parse_args()
    province = filters['province']
    company = filters['company']
    query = ClientInfo.query

    print(f'args: page={page}, page_size={page_size}, province={province}, company={company}')

    if province:
        query = query.filter(ClientInfo.address.startswith(province))

    if company:
        query = query.filter(ClientInfo.company.like(f'%{company}%'))

    result = query.distinct(ClientInfo.tel)

    if not result:
        abort(404)
    return render_template(
        'client-list.html',
        client_list=result.paginate(page, page_size),
        page=page,
        area=area,
        page_size=page_size,
        count=record_count,
        filters=[province, company],
    )


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
        # data = [ClientInfo(**c._asdict()) for c in parse_client_list(request, client_list, add_86prefix=False)]
        # try:
        #     db.session.bulk_save_objects(data)
        #     db.session.commit()
        # except IntegrityError as e:
        #     print(e)
        [db.engine.execute(
            f'insert ignore into client_info(name, tel, address , company, industry) values("{c.name}", "{c.tel}", "{pymysql.escape_string(c.address)}", "{c.company}", "{c.industry}")',
        ) for c in parse_client_list(request, client_list, add_86prefix=False)]
        flash('录入成功')
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
