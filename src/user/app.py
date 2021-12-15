import json
from flask_cors import CORS
from flask import Flask, request, g, jsonify, make_response, Response
from functools import reduce

from src.error_code.error_code import ResultSuccess
from .auth import authenticate_token, generate_token
from .user_proxy import UserProxy

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
        result = user_proxy.login()
    return jsonify(result.to_dict())