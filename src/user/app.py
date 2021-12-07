import json
from flask_cors import CORS
from flask import Flask, request, g, jsonify, make_response, Response
from functools import reduce
from auth import authenticate_token, generate_token

app = Flask(__name__)
CORS(app)

@app.route('/')
def app_status():
    return 'app is running'

@app.route('/user/login', methods=['POST'])
def login():
    params = get_request_params()
    return jsonify(params)


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
    

