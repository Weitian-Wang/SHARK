import os
import time

from flask.json import jsonify
from sqlalchemy.sql.expression import true
from sqlalchemy.sql.functions import user
from src.database import DBStore
from src.error_code import *
from src.user.auth import generate_token

# for threading and logic handling
class UserProxy():
    def __init__(self):
        self._database = DBStore()
        self._expire_time = '7200'

    def tel_check(self, tel):
        user =  self._database.get_user_by_tel(tel=tel)
        if user is None:
            return ResultSuccess({'exist':False})
        return ResultSuccess({'exist':True})

    def register(self, tel, name, password_hash, user_type=1):
        # check all user input shits
        if self.tel_check(tel)._data['exist'] == True:
            raise UserExistError
        user = self._database.create_user(tel=tel, name=name, password_hash=password_hash, user_type=user_type)
        result = {'tel':user.tel}
        return ResultSuccess(result, "Register successful, go login.")

    def login(self, tel, password_hash):
        user = self._database.get_user_by_tel(tel=tel)
        if user is None:
            raise UserNotExistError()
        if user.password_hash != password_hash:
            raise PasswordError()
        else:
            token = generate_token(user)
            data = {
                'name':user.name,
                'token':token
            }
            return ResultSuccess(data, "Login successful.")

    # "with user_proxy" triggers __enter__
    def __enter__(self):
        self.connect()

    def connect(self):
        self._database.connect()

    def __exit__(self, exception_type, exception_value, traceback):
        self.disconnect()

    def disconnect(self):
        self._database.disconnect()