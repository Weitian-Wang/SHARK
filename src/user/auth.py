from datetime import datetime, timedelta
import jwt
from src.error_code import *
from functools import wraps

APP_SECRET = "SHARK"

def generate_token(user, user_type, expire_hours=2):
    payload = {
        'user_id': user.id,
        'user_type': user_type,
        'exp': datetime.utcnow() + timedelta(hours=expire_hours)
    }
    token = jwt.encode(payload, APP_SECRET, algorithm='HS256')
    return token.decode('utf-8')

def decode(token):
    try:
        payload = jwt.decode(token, APP_SECRET, algotithms=['HS256'])
        return payload
    except jwt.exceptions.ExpiredSignatureError:
        raise TokenExpiredError()
    except Exception:
        raise TokenError()

def authenticate_token(user_types=[]):
    from flask import request,g

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            #check request msg
            body = request.get_data()
            if len(body) != request.content_length and request.content_length is not None:
                raise ()

            auth_header = request.headers.get('authorization', None)
            token = extract_token_from_header(auth_header)
            auth = decode(token)
            if auth.get('user_type') not in user_types:
                raise TokenError()
            g.auth = auth
            return f(auth, *args, **kwargs)
        return wrapped
    return decorator


def extract_token_from_header(header):
    if header is None:
        raise TokenError()

    parts = header.split(' ')

    if len(parts) != 2:
        raise TokenError()

    if parts[0] != 'Bearer':
        raise TokenError()

    token = parts[1]
    return token