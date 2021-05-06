from flask import Blueprint, render_template, request, current_app, flash, abort, redirect, url_for
from utils import parse_client_list, send_sms, prepare_send_sms, waiting_follow_notify
from models import db, ClientInfo, Seller, Following, FollowStatusChoices, Tag
from flask_login import login_required, login_user, logout_user, current_user, login_url
from sqlalchemy import or_, desc
from flask_restful import Api, reqparse, Resource, marshal_with, fields
from datetime import datetime
import json
import pymysql
import re


# Auth Blueprint begin
auth_app = Blueprint('auth', import_name='auth', url_prefix='/auth')


@auth_app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        tel = request.form.get('tel')
        user = Seller.query.filter_by(name=name).first()
        if user and user.tel == tel:
            if login_user(user, remember=True):
                next_url = request.args.get('next', url_for('crm.following_list'))
                return redirect(next_url)
        else:
            flash('登录失败', 'auth')

    return render_template('crm-login.html')


@auth_app.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
# Auth Blueprint end


# crm blueprint begin
crm_app = Blueprint('crm', import_name='crm', url_prefix='/crm')


@crm_app.route('/index', methods=['GET'])
@login_required
def index():
    talking_notify_follows = waiting_follow_notify(
        current_user.id,
        FollowStatusChoices.Talking,
        current_app.config['NOTIFY_DAYS']
    )
    got_wechat_notify_follows = waiting_follow_notify(
        current_user.id,
        FollowStatusChoices.Got_wechat,
        current_app.config['NOTIFY_DAYS']
    )
    sent_sample_notify_follows = waiting_follow_notify(
        current_user.id,
        FollowStatusChoices.Sent_sample,
        current_app.config['NOTIFY_DAYS']
    )
    bought_notify_follows = waiting_follow_notify(
        current_user.id,
        FollowStatusChoices.Bought,
        current_app.config['NOTIFY_DAYS']
    )

    return render_template(
        'crm-index.html',
        active=1,
        today=datetime.today().date(),
        username=current_user.name,
        bought_notify=(bought_notify_follows.count(), bought_notify_follows.all()),
        sent_notify=(sent_sample_notify_follows.count(), sent_sample_notify_follows.all()),
        talking_notify=(talking_notify_follows.count(), talking_notify_follows.all()),
        wechat_notify=(got_wechat_notify_follows.count(), got_wechat_notify_follows.all()),
    )


@crm_app.route('/add-following', methods=['GET', 'POST'])
@login_required
def add_following():
    tag_list = [{
        'id': t.id,
        'name': t.name,
    } for t in Tag.query.all()]

    if request.method == 'POST':
        name = request.form.get('name')
        tel = request.form.get('tel')
        company = request.form.get('company')
        status = request.form.get('status')
        fid = request.form.get('id')
        markup = request.form.get('markup', '')
        address = request.form.get('address', '')
        tags = request.form.getlist('tags')
        is_update = request.form.get('is_update', False)

        if name and company:
            if tel and re.match('^\d{11}$', tel):
                tags = Tag.query.filter(Tag.id.in_(tags)).all()
                if is_update and fid:
                    f = Following.query.get_or_404(fid)
                    f.name = name
                    f.tel = tel
                    f.company = company
                    f.status = status
                    f.markup = markup
                    f.address = address
                    f.tags = tags
                    db.session.add(f)
                    flash('更新成功', 'crm')
                else:
                    f = Following(
                        name=name,
                        tel=tel,
                        company=company,
                        status=status,
                        markup=markup,
                        address=address,
                        tags=tags,
                    )
                    f.follower_id = current_user.id
                    db.session.add(f)
                    flash('添加成功', 'crm')
                db.session.commit()
                return redirect(url_for('crm.following_list'))
            else:
                flash('手机号码不正确', 'crm')
        else:
            flash('信息不完整，请检查是否填写完整')
        return redirect(
            url_for(
                'crm.add_following',
                name=name,
                tel=tel,
                company=company,
                status=status,
                address=address,
                markup=markup,
                tags=tag_list,
                is_update=is_update,
            )
        )
    else:
        is_update = request.args.get('is_update', False)
        name = request.args.get('name', '')
        fid = request.args.get('id')
        company = request.args.get('company', '')
        tel = request.args.get('tel', '')
        address = request.args.get('address', '')
        status = request.args.get('status', 1)
        markup = request.args.get('markup', '')
        curr_tags = request.args.getlist('curr_tags')

    return render_template(
        'add-following.html',
        choices=FollowStatusChoices,
        active=2,
        id=fid,
        is_update=is_update,
        name=name,
        company=company,
        address=address,
        tel=tel,
        status=status,
        tags=tag_list,
        curr_tags=[t for t in curr_tags],
        markup=markup,
        username=current_user.name,
    )


@crm_app.route('/following-list', methods=['GET'])
@crm_app.route('/following-list/has-downloaded/<int:download>', methods=['GET'])
@login_required
def following_list(download: int = 2):
    criteria = request.args.get('filter')
    ctx = Following.query.filter_by(follower_id=current_user.id)

    if download == 0:
        ctx = ctx.filter_by(download=False)
    elif download == 1:
        ctx = ctx.filter_by(download=True)

    if criteria:
        ctx = ctx.filter(or_(
            Following.company.like(f'%{criteria}%'),
            Following.name.like(f'%{criteria}%'),
            Following.tel.like(f'%{criteria}%'),
        ))

    ctx = ctx.order_by(desc('created_at'))
    ctx.all()
    return render_template(
        'following-list.html',
        following=ctx.all(),
        count=ctx.count(),
        active=3,
        filter=criteria,
        username=current_user.name,
    )


@crm_app.route('/download', methods=['GET'])
@crm_app.route('/download/has-downloaded/<int:downloaded>', methods=['GET'])
@login_required
def download(downloaded: int = 0):
    from app import excel
    downloaded = downloaded == 1
    qs = Following.query.filter_by(download=downloaded)
    resp = excel.make_response_from_array(
        [(
            v.name,
            v.company,
            v.tel,
            v.address,
            v.status.value,
            v.markup if v.markup else '无备注',
            [t.name for t in v.tags],
        ) for v in qs.all()],
        file_type='csv',
        file_name='客户列表.csv',
    )

    if not downloaded:
        Following.query.filter_by(download=downloaded).update({
            'download': True,
        })
        db.session.commit()

    return resp


@crm_app.route('mock-update', methods=['GET'])
@login_required
def mock_update():
    fid = request.args.get('id')
    if not fid:
        return '', 400
    Following.query.filter_by(id=fid).update({})
    db.session.commit()
    return '', 201


@crm_app.route('/memo', methods=['GET'])
@login_required
def memo():
    return 'memo'
# crm blueprint end


sms_app = Blueprint('sms', import_name='sms', url_prefix='/sms')
api = Api(sms_app)


client_info_fields = {
    'name': fields.String(),
    'tel': fields.String(),
    'company': fields.String(),
    'address': fields.String(),
}

api_token_args = reqparse.RequestParser()
api_token_args.add_argument(
    'secret',
    type=str,
    location=('headers', 'form', 'args'),
    required=True,
    default=None,
)
client_post_args = reqparse.RequestParser()
client_api_arg_props = {
    'type': str,
    'location': ('form', ),
    'required': True,
    'default': None,
}
client_post_args.add_argument(
    'name',
    **client_api_arg_props,
)
client_post_args.add_argument(
    'company',
    **client_api_arg_props,
)
client_post_args.add_argument(
    'tel',
    **client_api_arg_props,
)
client_post_args.add_argument(
    'address',
    **client_api_arg_props,
)


class ClientInfoResource(Resource):
    @marshal_with(client_info_fields)
    def get(self, client_id=None):
        args = api_token_args.parse_args()
        secret = args['secret']
        if secret != 'ggadmin5197':
            abort(401)

        if client_id:
            result = ClientInfo.query.get(client_id)
            if not result:
                abort(404)
        return ClientInfo.query.all()

    @marshal_with(client_info_fields)
    def post(self):
        secret = api_token_args.parse_args().get('secret')
        args = client_post_args.parse_args()

        if secret != 'ggadmin5197':
            abort(403)

        data = ClientInfo(
            name=args['name'],
            company=args['company'],
            tel=args['tel'],
            address=args['address'],
        )

        try:
            db.session.add(data)
            db.session.commit()
        except Exception as e:
            return None

        return data


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

    filters = filter_args.parse_args()
    province = filters['province']
    company = filters['company']
    query = ClientInfo.query

    print(f'args: page={page}, page_size={page_size}, province={province}, company={company}')

    if province:
        query = query.filter(ClientInfo.address.startswith(province))

    if company:
        query = query.filter(ClientInfo.company.like(f'%{company}%'))

    # 检查页码是否超过总页数
    result = query.distinct(ClientInfo.tel)
    record_count = result.count()
    mod = record_count % page_size
    limit = record_count / page_size
    limit = limit if mod == 0 else limit + 1
    # 超过则从第一页开始
    if page > limit:
        page = 1

    if not result:
        abort(404)
    return render_template(
        'client-list.html',
        client_list=result.paginate(page, page_size),
        page=page,
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
