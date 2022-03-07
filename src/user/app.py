import json
from flask_cors import CORS
from flask import Flask, request, g, jsonify, make_response, Response
from functools import reduce

from pytest import param
from src.error_code import ErrorCode, SystemInternalError
from src.error_code.error_code import ResultSuccess
from .auth import authenticate_token, generate_token
from .user_proxy import UserProxy
from .constant import UserType

app = Flask(__name__)
CORS(app)

def get_request_params():
    params = dict()
    if request.get_json():
        params['json'] = request.get_json() or {}
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

# TODO remove auth test from front end
@app.route('/user/auth_test', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL])
def auth_check(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = ResultSuccess()
    return jsonify(result.to_dict())

@app.route('/user/search_pname', methods=['GET'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.MODERATOR, UserType.ADMIN, UserType.SUPER_ADMIN])
def search_pname(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.search_pname(params['p_name'], float(params['lat']), float(params['lng']))
        return jsonify(result.to_dict())

@app.route('/user/get_appointments', methods=['GET'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.MODERATOR, UserType.ADMIN, UserType.SUPER_ADMIN])
def get_appointments_by_id_and_type(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        # use date passed in params 
        result = user_proxy.get_appointments_by_id_type(params['id'], int(params['type']), params['date'] if params['date'] and len(params['date']) else None)
        return jsonify(result.to_dict())

@app.route('/user/check_period_validity', methods=['POST'])
@authenticate_token([UserType.INDIVIDUAL, UserType.PROPERTY, UserType.MODERATOR, UserType.ADMIN, UserType.SUPER_ADMIN])
def check_period_validity(auth):
    params = get_request_params()
    user_proxy = get_user_proxy()
    with user_proxy:
        result = user_proxy.check_period(params['id'], int(params['type']), params['start_time'], params['end_time'])
        return jsonify(result.to_dict())
