import os
import time

from flask.json import jsonify
from sqlalchemy.sql.functions import user
from src.database import DBStore
from src.error_code import *

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
        # check all shits
        result = self._database.create_user(tel=tel, name=name, password_hash=password_hash, user_type=user_type)
        return ResultSuccess(result)
        

    def login(self):
        pass

    # "with user_proxy" triggers __enter__
    def __enter__(self):
        self.connect()

    def connect(self):
        self._database.connect()

    def __exit__(self, exception_type, exception_value, traceback):
        self.disconnect()

    def disconnect(self):
        self._database.disconnect()