import json
from flask_cors import CORS
from flask import Flask, request, g, jsonify, make_response, Response
from functools import reduce
from datetime import datetime, timedelta
from src.error_code import ErrorCode, SystemInternalError
from src.error_code.error_code import ResultSuccess
from .auth import authenticate_token, generate_token
from .user_proxy import UserProxy
from .constant import OrderStatus, UserType
from src.user import auth

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

def get_request_params():
    params = dict()
    # if request.get_json():
        # params['json'] = request.get_json() or {}
    if request.data:
        params['json'] = json.loads(request.data, strict=False)
    if request.files.to_dict():
        params['files'] = request.files.to_dict() or {}
    if request.form.to_dict():
        params['data'] = request.form.to_dict()
    if request.args:
        params['params'] = {k: v for k, v in request.args.items()}
    combined_params = reduce(lambda d1, d2: dict(d1, **d2),
                                     list(params.values()), {})
    return combined_params

def get_user_proxy():
    # Allow multiple threads to each have their own instance of user_proxy
    if not hasattr(g, 'user_proxy'):
        g.user_proxy = UserProxy()
    return g.user_proxy

@app.errorhandler(ErrorCode)
def exception_handle(ex):
    return jsonify(ex.to_dict())

@app.errorhandler(500)
def handle_internal_exception(ex):
    err = SystemInternalError()
    return jsonify(err.to_dict()), 200

@app.route('/')
def app_status():
    return 'SHARK app is running'

@app.route('/user/tel_check', methods=['POST'])
def tel_check():
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.tel_check(tel=params['tel'])
    return jsonify(result.to_dict())

@app.route('/user/register', methods=['POST'])
def register():
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.register(**params)
    return jsonify(result.to_dict())

@app.route('/user/login', methods=['POST'])
def login():
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.login(tel=params['tel'], password_hash=params['password_hash'])    
    return jsonify(result.to_dict())

@app.route('/user/switch_role', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def switch_role_to_property(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.switch_role(auth['user_tel'], int(params['target_role']))    
    return jsonify(result.to_dict())

# operation of admin, change user's role
@app.route('/user/switch_role', methods=['POST'])
@authenticate_token([UserType.ADMIN])
def switch_role(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.switch_role(auth, params['user_tel'], int(params['target_user_type']))    
    return jsonify(result.to_dict())

@app.route('/user/search_pname', methods=['GET'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def search_pname(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.search_pname(params['p_name'], float(params['lat']), float(params['lng']))
        return jsonify(result.to_dict())

@app.route('/user/get_p_near_coord', methods=['GET'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def get_p_near_coord(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.get_p_near_coord(float(params['lat']), float(params['lng']))
        return jsonify(result.to_dict())

@app.route('/user/get_appointments', methods=['GET'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def get_appointments_by_id_and_type(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        # use date passed in params 
        result = user_proxy.get_appointments_by_id_type(params['id'], int(params['type']), params['date'] if params['date'] and len(params['date']) else None)
        return jsonify(result.to_dict())

@app.route('/user/check_period_validity', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def check_period_validity(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.check_period(params['id'], int(params['type']), params['start_time'], params['end_time'])
        return jsonify(result.to_dict())

@app.route('/user/reserve', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def reserve_spot(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        order = user_proxy.reserve_spot(auth['user_tel'], params['ps_id'], params['start_time'], params['end_time'])
        result = ResultSuccess(message="预约成功")
        return jsonify(result.to_dict())

@app.route('/user/cancel_order', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL])
def cancel_order(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.cancel_order(auth['user_tel'], params['order_id'])
        return jsonify(result.to_dict())

@app.route('/user/get_orders', methods=['GET'])
@authenticate_token([UserType.INDIVIDUAL, UserType.ADMIN])
def get_orders(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.get_orders(auth['user_tel'])
        return jsonify(result.to_dict())

@app.route('/user/enter_spot', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL, UserType.ADMIN])
def enter_spot(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.enter_spot(auth['user_tel'], params['order_id'])
        return jsonify(result.to_dict())

@app.route('/user/leave_spot', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL, UserType.ADMIN])
def leave_spot(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.leave_spot(auth['user_tel'], params['order_id'])
        return jsonify(result.to_dict())

@app.route('/user/pay_order', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL, UserType.ADMIN])
def pay_order(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.pay_order(auth['user_tel'], params['order_id'])
        return jsonify(result.to_dict())

@app.route('/individual/add_spot', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def add_spot(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.add_spot(user_tel = auth['user_tel'], name = params['name'], id = params['id'], rate = float(params['rate']), lat = float(params['lat']), lng = float(params['lng']))
        return jsonify(result.to_dict())

@app.route('/individual/get_spot_list', methods=['GET'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def get_spot_list(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.get_spot_list(auth['user_tel'])
        return jsonify(result.to_dict())

@app.route('/individual/get_spot_info_of_date', methods=['GET'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def get_spot_info_of_date(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.get_spot_info_of_date(auth['user_tel'], params['ps_id'], params['date'])
        return jsonify(result.to_dict())

# no frontend ui support
@app.route('/individual/delete_spot', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def delete_spot(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.delete_spot(auth['user_tel'], params['ps_id'], params['date'])
        return jsonify(result.to_dict())

@app.route('/individual/deny_order', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def deny_order(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.deny_order(auth['user_tel'], params['order_id'])
        return jsonify(result.to_dict())

@app.route('/individual/change_spot_status', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def change_spot_status(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.change_spot_status(auth['user_tel'], params['ps_id'], int(params['new_status']))
        return jsonify(result.to_dict())

@app.route('/individual/change_spot_rate', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def change_spot_rate(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.change_spot_rate(auth['user_tel'], params['ps_id'], float(params['new_rate']))
        return jsonify(result.to_dict())

@app.route('/property/load_lot_management_page', methods=['GET'])
@authenticate_token([UserType.PROPERTY, UserType.ADMIN])
def get_lot_info(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.deny_order(auth['user_tel'], params['order_id'])
        return jsonify(result.to_dict())

@app.route('/user/get_account_info', methods=['GET'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.ADMIN])
def get_account_info(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.get_account_info(auth['user_tel'])
        return jsonify(result.to_dict())
