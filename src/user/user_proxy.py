import os
import time
import json
from math import sin, cos, sqrt, atan2, radians

from flask.json import jsonify
from numpy import sort
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

    # login & register related
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
        return ResultSuccess(result, "已注册,去登录")

    def login(self, tel, password_hash):
        user = self._database.get_user_by_tel(tel=tel)
        if user is None:
            raise UserNotExistError()
        if user.password_hash != password_hash:
            raise PasswordError()
        else:
            token = generate_token(user, user.user_type)
            data = {
                'name':user.name,
                'token':token
            }
            return ResultSuccess(data, "登录成功")

    # parking lot/spot search
    # TODO just a prototype, need fuzzy search support, lot & spot support
    def search_pname(self, p_name, lat=0, lng=0):
        p_list = self._database.get_p_by_name(p_name)
        for it in p_list:
            coord = json.loads(it['coordinate'])
            it['distance'] = self.distance_cal(lat, lng, coord['lat'], coord['lng'])
        p_list = sorted(p_list, key=lambda d: d['distance'])
        return ResultSuccess({'list':p_list}, message="找到{}个结果".format(len(p_list)))

    def distance_cal(self, lat1, lng1, lat2, lng2):
        lat1 = radians(lat1)
        lng1 = radians(lng1)
        lat2 = radians(lat2)
        lng2 = radians(lng2)
        
        dlng = lng2 - lng1
        dlat = lat2 - lat1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlng / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        # distance in km
        return 6373.0 * c


    # "with user_proxy" triggers __enter__ function
    def __enter__(self):
        self.connect()

    def connect(self):
        self._database.connect()

    def __exit__(self, exception_type, exception_value, traceback):
        self.disconnect()

    def disconnect(self):
        self._database.disconnect()