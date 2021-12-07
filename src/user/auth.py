from datetime import datetime, timedelta

APP_SECRET = "SHARK"

def generate_token(user, user_type, expire_hours=2):
    payload = {
        'user_id': user.id,
        'user_type': user_type,
        'exp': datetime.utcnow() + timedelta(hours=expire_hours)
    }

def authenticate_token():
    pass
