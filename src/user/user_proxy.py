import os
import time
import json
from math import sin, cos, sqrt, atan2, radians
from datetime import datetime, timedelta

from flask.json import jsonify
from numpy import sort
from sqlalchemy.sql.expression import true
from sqlalchemy.sql.functions import user
from src.database import DBStore
from src.error_code import *
from src.user.auth import generate_token
from src.user.constant import SpotType

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
            raise UserExistError()
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


    # TODO fuzzy search
    def search_pname(self, p_name, lat=0, lng=0):
        p_list = self._database.get_p_by_name(p_name)
        for it in p_list:
            coord = json.loads(it['coordinate'])
            it['distance'] = self.distance_cal(lat, lng, coord['lat'], coord['lng'])
        p_list = sorted(p_list, key=lambda d: d['distance'])
        return ResultSuccess({'list':p_list}, message="找到{}个结果".format(len(p_list)))


    def get_appointments_by_id_type(self, id, type, date=str(datetime.today().date())):
        if type == SpotType.INDIVIDUAL:
            appointments = self._database.get_appointments_by_id(id=id)
            data = {'appointment_list': appointments.get(date, [])}
            return ResultSuccess(data)
            
        elif type == SpotType.PROPERTY:
            spots = self._database.get_subspots_by_pl_id(id)
            # TODO support parking lots
            return ResultSuccess()
        else:
            raise ParamError()


    def check_period(self, id, type, start_time, end_time):
        if type == SpotType.INDIVIDUAL:
            return self.check_period_of_spot(id, start_time, end_time)
        elif type == SpotType.PROPERTY:
            return self.check_period_of_lot(id, start_time, end_time)
        else:
            raise ParamError()

    def check_period_of_spot(self, ps_id, start_time, end_time):
        # parse and check time
        st = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        et = datetime.strptime(end_time, '%Y-%m-%d %H:%M')
        if st>=et:
            raise ParamError()
        # get appointments of the spot
        appointments = self._database.get_appointments_by_id(ps_id)
        
        # period spans single day
        if st.date() == et.date():
            date_str = str(st.date())
            appointments = appointments.get(date_str)
            # no appointments in the date
            if not appointments:
                return ResultSuccess(message="该时段可预约")
            else:
                for appointment in appointments:
                    # appointment start time inbetween period OR appointment end time inbetween period. POSSIBLE IMPROVEMENT
                    if (datetime.strptime(f'{date_str} {appointment[0]}', '%Y-%m-%d %H:%M')>st and datetime.strptime(f'{date_str} {appointment[0]}', '%Y-%m-%d %H:%M')<et) or (datetime.strptime(f'{date_str} {appointment[1]}', '%Y-%m-%d %H:%M')>st and datetime.strptime(f'{date_str} {appointment[1]}', '%Y-%m-%d %H:%M')<et):
                        raise InvalidPeriod()
                return ResultSuccess(message="该时段可预约")
        
        # period spans multiple days, any appointments in between will fail requested period
        it = st.date()+timedelta(days=1)
        while it < et.date():
            if appointments.get(str(it)) != None:
                raise InvalidPeriod()
            it = it+timedelta(days=1)
        
        # check start date
        start_date_appointments = appointments.get(str(st.date()), [])
        end_date_appointments = appointments.get(str(et.date()), [])
        end_of_start_date = datetime.strptime(f'{str(st.date() + timedelta(days=1))} 00:00', '%Y-%m-%d %H:%M')
        start_of_end_date = datetime.strptime(f'{str(et.date())} 00:00', '%Y-%m-%d %H:%M')
        for appointment in start_date_appointments:
            if (datetime.strptime(f'{str(st.date())} {appointment[0]}', '%Y-%m-%d %H:%M')>st and datetime.strptime(f'{str(st.date())} {appointment[0]}', '%Y-%m-%d %H:%M')<end_of_start_date) or (datetime.strptime(f'{str(st.date())} {appointment[1]}', '%Y-%m-%d %H:%M')>st and datetime.strptime(f'{str(st.date())} {appointment[1]}', '%Y-%m-%d %H:%M')<end_of_start_date):
                raise InvalidPeriod()
        for appointment in end_date_appointments:
            if (datetime.strptime(f'{str(et.date())} {appointment[0]}', '%Y-%m-%d %H:%M')>start_of_end_date and datetime.strptime(f'{str(et.date())} {appointment[0]}', '%Y-%m-%d %H:%M')<et) or (datetime.strptime(f'{str(et.date())} {appointment[1]}', '%Y-%m-%d %H:%M')>start_of_end_date and datetime.strptime(f'{str(et.date())} {appointment[1]}', '%Y-%m-%d %H:%M')<et):
                raise InvalidPeriod()
        return ResultSuccess(message="该时段可预约")

    def check_period_of_lot(self, pl_id, start_time, end_time):
        spots = self._database.get_subspots_by_pl_id(pl_id=pl_id)
        print('breakpoint')

    # utility functions
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