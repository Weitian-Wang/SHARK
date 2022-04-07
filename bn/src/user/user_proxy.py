import uuid
from math import sin, cos, sqrt, atan2, radians
from datetime import datetime, timedelta

from src.database import DBStore
from src.error_code import *
from src.user.auth import generate_token
from src.user.constant import OrderStatus, SpotStatus, SpotType, UserType

# for threading and logic handling
class UserProxy():
    def __init__(self):
        self._database = DBStore()
        self._expire_time = '7200'

    # account related
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
                'token':token,
                'user_type': user.user_type
            }
            return ResultSuccess(data, "登录成功")


    def switch_role(self, user_tel, target_role):
        user = self._database.get_user_by_tel(tel=user_tel)
        if not user or target_role not in [UserType.INDIVIDUAL, UserType.PROPERTY]:
            raise ParamError()
        else:
            self._database.change_user_role(user_tel, target_role)
            return ResultSuccess(message="修改用户角色成功")
            
    # parking space search
    # TODO fuzzy search
    def search_pname(self, p_name, lat=0, lng=0):
        p_list = self._database.get_p_by_name(p_name)
        for it in p_list:
            it['distance'] = self.distance_cal(lat, lng, it.get('latitude'), it.get('longitude'))
        p_list = sorted(p_list, key=lambda d: d['distance'])
        return ResultSuccess({'list':p_list}, message="找到{}个结果".format(len(p_list)))

    def get_p_near_coord(self, lat, lng, no_results = 7, range = 0.018):
        # spot list
        list = self._database.get_personal_spots_in_proximity(lat, lng, range)
        # lot list
        lot_list = self._database.get_all_property_lots_in_proximity(lat, lng, range)
        list.extend(lot_list)
        for it in list:
            it['distance'] = self.distance_cal(lat, lng, it.get('latitude'), it.get('longitude'))
        list = sorted(list, key=lambda d: d['distance'])
        return ResultSuccess(data = {'list':list[0:no_results]}, message='找到附近{}个结果'.format(len(list[0:no_results])) if len(list[0:no_results])!= 0 else '附近没有车位或停车场')

    # get appointments and display at time scheduler
    def get_appointments_by_id_type(self, id, type, date=str(datetime.today().date())):
        if type == SpotType.INDIVIDUAL:
            appointments = self._database.get_appointments_by_id(id=id)
            data = {'appointment_list': appointments.get(date, [])}
            return ResultSuccess(data)
            
        elif type == SpotType.PROPERTY:
            spots = self._database.get_subspots_by_pl_id(id)
            appointment_list = [["00:00","23:59"]]
            for spot in spots:
                appointment = self._database.get_appointments_by_id(spot.ps_id)
                appointment = appointment.get(date, [])
                appointment_list = self.find_overlap_appointments(appointment_list, appointment)
            # no spot, one spot, multiple spot, all covered
            return ResultSuccess({'appointment_list': appointment_list})
        else:
            raise ParamError()

    # appointments1 = [["12:00","17:00"], ["18:00","19:00"]]
    # appointments2 = [["11:00","12:30"], ["13:00","14:00"], ["16:00","17:00"], ["17:30","20:00"]]
    def find_overlap_appointments(self, appointments1, appointments2):
        rst = []
        i1 = 0
        i2 = 0
        # two sorted list, complexity O(l1+l2)
        while i1 < len(appointments1) and i2 < len(appointments2):
            ap1 = appointments1[i1]
            ap2 = appointments2[i2]
            if datetime.strptime(ap2[0], "%H:%M")>=datetime.strptime(ap1[1], "%H:%M"):
                i1 += 1
            elif datetime.strptime(ap1[0], "%H:%M")>=datetime.strptime(ap2[1], "%H:%M"):
                i2 += 1
            else:
                period_start = ap1[0] if datetime.strptime(ap1[0], "%H:%M")>=datetime.strptime(ap2[0], "%H:%M") else ap2[0]
                if datetime.strptime(ap1[1], "%H:%M")<=datetime.strptime(ap2[1], "%H:%M"):
                    period_end = ap1[1]
                    i1 += 1
                else:
                    period_end = ap2[1]
                    i2 += 1
                rst.append([period_start, period_end])
        return rst


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
            appointments = appointments.get(date_str, [])
            return self.check_period_in_specific_date(ps_id, appointments_of_that_date=appointments, period_start_time=st, period_end_time=et)
        
        # period spans multiple days, any appointments in between will render period unavailable
        it = st.date()+timedelta(days=1)
        while it < et.date():
            if appointments.get(str(it)) != None:
                raise InvalidPeriod()
            it = it+timedelta(days=1)
        
        start_date_appointments = appointments.get(str(st.date()), [])
        end_date_appointments = appointments.get(str(et.date()), [])
        end_of_start_date = datetime.strptime(f'{str(st.date() + timedelta(days=1))} 00:00', '%Y-%m-%d %H:%M')
        start_of_end_date = datetime.strptime(f'{str(et.date())} 00:00', '%Y-%m-%d %H:%M')
        # check both start_date and end_date of the period for availability
        self.check_period_in_specific_date(ps_id, appointments_of_that_date=start_date_appointments, period_start_time=st, period_end_time=end_of_start_date)
        self.check_period_in_specific_date(ps_id, appointments_of_that_date=end_date_appointments, period_start_time=start_of_end_date, period_end_time=et)
        return ResultSuccess(data={'avail_ps_id':ps_id}, message="该时段可预约")

    def check_period_of_lot(self, pl_id, start_time, end_time):
        spots = self._database.get_subspots_by_pl_id(pl_id=pl_id)
        rst = None
        for spot in spots:
            try:
                rst = self.check_period_of_spot(spot.ps_id, start_time, end_time)
                # exit at first available sub spot
                if isinstance(rst, ResultSuccess):
                    # return id of the first available sub spot
                    return rst
            except InvalidPeriod:
                pass
        raise InvalidPeriod()

    def check_period_in_specific_date(self, ps_id, appointments_of_that_date, period_start_time, period_end_time):
        date_str = str(period_start_time.date())
        for appointment in appointments_of_that_date:
            # improvement: eliminate number of appointments to judge, as appointments list is sorted
            # appointment end time earlier than period start time
            if datetime.strptime(f'{date_str} {appointment[1]}', '%Y-%m-%d %H:%M')<=period_start_time:
                continue
            # appointment start time later than period end time, skip subsequent appointments
            elif datetime.strptime(f'{date_str} {appointment[0]}', '%Y-%m-%d %H:%M')>=period_end_time:
                break
            # all other cases
            else:
                raise InvalidPeriod()
        return ResultSuccess(data={'avail_ps_id':ps_id}, message="该时段可预约")

    def check_and_insert_period_in_specific_date(self, appointments_of_that_date, period_start_time, period_end_time):
        insert_location = 0
        date_str = str(period_start_time.date())
        for appointment in appointments_of_that_date:
            # improvement: eliminate number of appointments to judge, as appointments list is sorted
            # appointment end time earlier than period start time
            if datetime.strptime(f'{date_str} {appointment[1]}', '%Y-%m-%d %H:%M')<=period_start_time:
                insert_location += 1
                continue
            # appointment start time later than period end time, skip subsequent appointments
            elif datetime.strptime(f'{date_str} {appointment[0]}', '%Y-%m-%d %H:%M')>=period_end_time:
                break
            # appointment start time inbetween period OR appointment end time inbetween period
            else:
                raise InvalidPeriod()
        return insert_location

    def reserve_spot(self, user_tel, ps_id, start_time, end_time):
        # !!!+8 China Standard Time!!!
        if datetime.strptime(start_time, '%Y-%m-%d %H:%M') <= datetime.utcnow() + timedelta(hours=8):
            raise ParamError()
        # ENTER check flag and lock
        self._database.spot_update_flag_lock(ps_id)

        # CRITICAL SECTION
        # parse and check time
        st = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        et = datetime.strptime(end_time, '%Y-%m-%d %H:%M')
        if st>=et:
            self._database.spot_update_flag_unlock(ps_id)
            raise ParamError()

        # make sure fetched data is up-to-date
        spot = self._database.get_spot_by_id(ps_id)
        if spot.status == SpotStatus.NOT_AVAILABLE:
            self._database.spot_update_flag_unlock(ps_id)
            raise Unavailable()

        appointments = spot.appointments
        # CASE 1, period spans single day
        if st.date() == et.date():
            date_str = str(st.date())
            appointments_of_that_date = appointments.get(date_str, [])
            if appointments_of_that_date == []:
                appointments[start_time.split(' ')[0]] = [[start_time.split(' ')[1], end_time.split(' ')[1]]]
                self._database.update_appointments(ps_id, new_appointments = appointments)
            else:
                try:
                    insert_location = self.check_and_insert_period_in_specific_date(appointments_of_that_date=appointments_of_that_date, period_start_time=st, period_end_time=et)
                except InvalidPeriod:
                    self._database.spot_update_flag_unlock(ps_id)
                    raise InvalidPeriod()
                appointments[start_time.split(' ')[0]].insert(insert_location, [start_time.split(' ')[1], end_time.split(' ')[1]])
                self._database.update_appointments(ps_id, new_appointments = appointments)

        # CASE 2, period spans multiple days, any appointments in between will render period unavailable
        else:
            # 2.1 check days inbetween
            it = st.date()+timedelta(days=1)
            while it < et.date():
                if appointments.get(str(it)) != None:
                    self._database.spot_update_flag_unlock(ps_id)
                    raise InvalidPeriod()
                it = it+timedelta(days=1)
            # 2.2 check both start_date and end_date of the period for availability
            start_date_appointments = appointments.get(str(st.date()), [])
            end_date_appointments = appointments.get(str(et.date()), [])
            end_of_start_date = datetime.strptime(f'{str(st.date() + timedelta(days=1))} 00:00', '%Y-%m-%d %H:%M')
            start_of_end_date = datetime.strptime(f'{str(et.date())} 00:00', '%Y-%m-%d %H:%M')
            try:
                insert_location_s = self.check_and_insert_period_in_specific_date(appointments_of_that_date=start_date_appointments, period_start_time=st, period_end_time=end_of_start_date)
            except InvalidPeriod:
                self._database.spot_update_flag_unlock(ps_id)
                raise InvalidPeriod()
            try:
                insert_location_e = self.check_and_insert_period_in_specific_date(appointments_of_that_date=end_date_appointments, period_start_time=start_of_end_date, period_end_time=et)
            except InvalidPeriod:
                self._database.spot_update_flag_unlock(ps_id)
                raise InvalidPeriod()
            # after confirm valid
            # 2.3 insert in dates in between
            it = st.date()+timedelta(days=1)
            while it < et.date():
                if appointments.get(str(it), []) == []:
                    appointments[str(it)] = [['00:00', '23:59']]
                else:
                    self._database.spot_update_flag_unlock(ps_id)
                    raise InvalidPeriod()
                it = it+timedelta(days=1)
            # 2.4 insert in start date
            if start_date_appointments == []:
                appointments[start_time.split(' ')[0]] = [[start_time.split(' ')[1], '23:59']]
            else:
                appointments[start_time.split(' ')[0]].insert(insert_location_s, [start_time.split(' ')[1], '23:59'])
            # 2.5 insert in end date
            if end_date_appointments == []:
                appointments[end_time.split(' ')[0]] = [['00:00', end_time.split(' ')[1]]]
            else:
                appointments[end_time.split(' ')[0]].insert(insert_location_e, ['00:00', end_time.split(' ')[1]])
            # 2.6 update spot and commit
            self._database.update_appointments(ps_id, appointments)
        
        order_id = str(uuid.uuid4())
        order = self._database.place_order(order_id, user_tel, ps_id, datetime.strptime(start_time, '%Y-%m-%d %H:%M'), datetime.strptime(end_time, '%Y-%m-%d %H:%M'), spot.price_per_min)
        self._database.spot_update_flag_unlock(ps_id)
        return order
    
    def cancel_order(self, user_tel, order_id):
        order = self._database.get_order_by_id(order_id)
        if not order:
            raise ParamError()
        if order.custom_tel != user_tel:
            raise UnauthorizedOperation()
        # use dictionary as switch clause
        if datetime.utcnow()+timedelta(hours=8) >= order.assigned_start_time:
            # self._database.update_order_status(order_id, OrderStatus.ABNORMAL)
            raise GeneralError(message='已经超过开始时间')

        # PLACED = 1, USING_SPOT = 2, DENIED = 3, CANCELED = 4, ABNORMAL = 5, LEFT_UNPAID = 10, COMPLETED = 11
        reason = {1:'预定成功', 2:'已经开始使用,无法取消', 3:'订单已经被拒绝', 4:'已经取消', 5:'订单异常,无法取消', 10:'无法取消待支付订单', 11:'订单已完成无法取消'}
        if order.order_status != 1:
            raise GeneralError(message=reason[order.order_status])
        # update appointment of order's parking spot
        # entering critical section, check flag and lock
        self._database.spot_update_flag_lock(ps_id=order.ps_id)
        spot = self._database.get_spot_by_id(ps_id=order.ps_id)
        appointments = spot.appointments
        start_time = order.assigned_start_time
        end_time = order.assigned_end_time
        if start_time.date() == end_time.date():
            date_str = str(start_time.date())
            try:
                appointments[date_str].remove([datetime.strftime(start_time, '%H:%M'), datetime.strftime(end_time, '%H:%M')])
            except:
                pass

        else: 
            it = start_time.date() + timedelta(days = 1)
            while it < end_time.date():
                appointments.pop(str(it))
                it += timedelta(days = 1)
            try:
                appointments[str(start_time.date())].remove([datetime.strftime(start_time, '%H:%M'),"23:59"])
            except:
                pass
            try:
                appointments[str(end_time.date())].remove(['00:00', datetime.strftime(end_time, '%H:%M')])
            except:
                pass
        self._database.update_appointments(ps_id=order.ps_id, new_appointments=appointments)
        # release lock
        self._database.spot_update_flag_unlock(ps_id = order.ps_id)
        self._database.update_order_status(order_id, OrderStatus.CANCELED)
        return ResultSuccess(message="订单取消成功")

    def deny_order(self, custom_tel, order_id):
        order = self._database.get_order_by_id(order_id)
        if not order or order.custom_tel != custom_tel:
            raise ParamError()
        # use dictionary as switch clause
        # PLACED = 1, USING_SPOT = 2, DENIED = 3, CANCELED = 4, ABNORMAL = 5, LEFT_UNPAID = 10, COMPLETED = 11
        reason = {1:'预定成功', 2:'已经开始使用,无法拒绝', 3:'订单已经被拒绝', 4:'已经拒绝', 5:'订单异常,无法拒绝', 10:'无法拒绝待支付订单', 11:'订单已完成无法拒绝'}
        if order.order_status != 1:
            raise GeneralError(message=reason[order.order_status])
        # update appointment of order's parking spot
        # entering critical section, check flag and lock
        self._database.spot_update_flag_lock(ps_id = order.ps_id)
        spot = self._database.get_spot_by_id(ps_id=order.ps_id)
        appointments = spot.appointments
        start_time = order.assigned_start_time
        end_time = order.assigned_end_time
        if start_time.date() == end_time.date():
            date_str = str(start_time.date())
            appointments[date_str].remove([datetime.strftime(start_time, '%H:%M'), datetime.strftime(end_time, '%H:%M')])
        else: 
            it = start_time.date() + timedelta(days = 1)
            while it < end_time.date():
                appointments.pop(str(it))
                it += timedelta(days = 1)
            try:
                appointments[str(start_time.date())].remove([datetime.strftime(start_time, '%H:%M'),"23:59"])
            except:
                pass
            try:
                appointments[str(end_time.date())].remove(['00:00', datetime.strftime(end_time, '%H:%M')])
            except:
                pass
        self._database.update_appointments(ps_id=order.ps_id, new_appointments=appointments)
        # release lock
        self._database.spot_update_flag_unlock(ps_id = order.ps_id)
        self._database.update_order_status(order_id, OrderStatus.DENIED)
        return ResultSuccess(message="成功拒绝订单")

    def enter_spot(self, user_tel, order_id):
        order = self._database.get_order_by_id(order_id)
        if datetime.utcnow()+timedelta(hours=8) >= order.assigned_end_time:
            self._database.update_order_status(order_id, OrderStatus.ABNORMAL)
            raise GeneralError(message='已错过预约时段')
        if datetime.utcnow()+timedelta(hours=8) < order.assigned_start_time:
            raise EnterTooEarly()
            
        if not order:
            raise ParamError()
        if order.custom_tel != user_tel:
            raise UnauthorizedOperation()

        self._database.update_order_status(order_id, OrderStatus.USING_SPOT)
        self._database.update_order_actual_start_time(order_id)

        return ResultSuccess(message="开始使用车位")

    def leave_spot(self, user_tel, order_id):
        spot = self._database.get_order_by_id(order_id)
        if not spot:
            raise ParamError()
        if spot.custom_tel != user_tel:
            raise UnauthorizedOperation()

        self._database.update_order_status(order_id, OrderStatus.LEFT_UNPAID)
        self._database.update_order_actual_end_time(order_id)
        
        return ResultSuccess(message="离场成功")
    
    def pay_order(self, user_tel, order_id):
        spot = self._database.get_order_by_id(order_id)
        if not spot:
            raise ParamError()
        if spot.custom_tel != user_tel:
            raise UnauthorizedOperation()

        self._database.update_order_status(order_id, OrderStatus.COMPLETED)
        self._database.update_order_complete_time(order_id)
        
        return ResultSuccess(message="支付成功")

    def update_order_status_as_using(self, order_id):
        self._database.update_order_status(order_id, OrderStatus.USING_SPOT)

    def get_orders(self, user_tel):
        data =  self._database.get_user_orders(user_tel)
        data = sorted(data, key=lambda d: (d['status'],d['start_time']))
        return ResultSuccess(data={'order_list':data})


    # account related functions
    def get_account_info(self, user_tel):
        user = self._database.get_user_by_tel(user_tel)
        if not user:
            raise ParamError()
        user_data_dict = {'name':user.name, 'user_tel':user.tel, 'create_date':user.create_date, 'type':user.user_type}
        return ResultSuccess(data={'user':user_data_dict})

    
    # spot management related functions
    def add_spot(self, user_tel, name, id, rate, lat, lng):
        self._database.add_spot(owner_tel = user_tel, name = f'{name} {id}', price_per_min = rate, latitude = lat, longitude = lng)
        return ResultSuccess(message='成功新增车位')

    def get_spot_list(self, user_tel):
        spots = self._database.get_spot_list_by_owner_tel(user_tel)
        spot_list = []
        total_no_of_orders = 0
        for spot in spots:
            order_of_spot = self._database.get_order_list_of_spot(spot.ps_id)
            total_no_of_orders += len(order_of_spot)

            spot_list.append({
                "ps_id": spot.ps_id,
                "name": spot.name,
                # CST = UTC + 8h
                "use_rate": self.get_usage_of_appointments(spot.appointments.get(datetime.strftime(datetime.utcnow()+timedelta(hours=8), "%Y-%m-%d") ,[])),
                "total_no_orders": len(order_of_spot),
                "using_spot": [order.order_id for order in order_of_spot if order.order_status==OrderStatus.USING_SPOT],
                "placed":[order.order_id for order in order_of_spot if order.order_status==OrderStatus.PLACED]
            })
        return ResultSuccess(data={'spot_list':spot_list, 'total_no_of_orders':total_no_of_orders})

    def get_spot_info_of_date(self, user_tel, ps_id, date):
        spot = self._database.get_spot_by_id(ps_id)
        if spot.owner_tel != user_tel:
            raise UnauthorizedOperation()
        spot_info = {}
        if not date:
            order_of_spot = self._database.get_order_list_of_spot(spot.ps_id)
            spot_info = {
                "name": spot.name,
                "use_rate": "N/A",
                "total_no_orders": len(order_of_spot),
                "using_spot": [{'custom_tel':order.custom_tel, 'order_id': order.order_id, 'start_time': order.assigned_start_time, 'end_time': order.assigned_end_time} for order in order_of_spot if order.order_status==OrderStatus.USING_SPOT],
                "placed":[{'custom_tel':order.custom_tel, 'order_id': order.order_id, 'start_time': order.assigned_start_time, 'end_time': order.assigned_end_time} for order in order_of_spot if order.order_status==OrderStatus.PLACED],
                "price_per_min": spot.price_per_min,
                "left_unpaid":[{'custom_tel':order.custom_tel, 'order_id': order.order_id, 'start_time': order.assigned_start_time, 'end_time': order.assigned_end_time, 'price_per_min': order.price_per_min} for order in order_of_spot if order.order_status==OrderStatus.LEFT_UNPAID],
                "completed":[{'custom_tel':order.custom_tel, 'order_id': order.order_id, 'start_time': order.assigned_start_time, 'end_time': order.assigned_end_time, 'price_per_min': order.price_per_min} for order in order_of_spot if order.order_status==OrderStatus.COMPLETED],
                "others":[{'custom_tel':order.custom_tel, 'order_id': order.order_id, 'start_time': order.assigned_start_time, 'end_time': order.assigned_end_time, 'order_status':order.order_status} for order in order_of_spot if order.order_status==OrderStatus.CANCELED or order.order_status==OrderStatus.DENIED or order.order_status==OrderStatus.ABNORMAL],
                "status": spot.status
            }
        else:
            # filter orders with assigned start date as 
            order_of_spot_on_date = self._database.get_order_list_of_spot_on_date(spot.ps_id, date)
            spot_info = {
                "name": spot.name,
                "use_rate": self.get_usage_of_appointments(spot.appointments.get(date,[])),
                "total_no_orders": len(order_of_spot_on_date),
                "using_spot": [{'custom_tel':order.custom_tel, 'order_id': order.order_id, 'start_time': order.assigned_start_time, 'end_time': order.assigned_end_time} for order in order_of_spot_on_date if order.order_status==OrderStatus.USING_SPOT],
                "placed":[{'custom_tel':order.custom_tel, 'order_id': order.order_id, 'start_time': order.assigned_start_time, 'end_time': order.assigned_end_time} for order in order_of_spot_on_date if order.order_status==OrderStatus.PLACED],
                "price_per_min": spot.price_per_min,
                "left_unpaid":[{'custom_tel':order.custom_tel, 'order_id': order.order_id, 'start_time': order.assigned_start_time, 'end_time': order.assigned_end_time, 'price_per_min': order.price_per_min} for order in order_of_spot_on_date if order.order_status==OrderStatus.LEFT_UNPAID],
                "completed":[{'custom_tel':order.custom_tel, 'order_id': order.order_id, 'start_time': order.assigned_start_time, 'end_time': order.assigned_end_time, 'price_per_min': order.price_per_min} for order in order_of_spot_on_date if order.order_status==OrderStatus.COMPLETED],
                "others":[{'custom_tel':order.custom_tel, 'order_id': order.order_id, 'start_time': order.assigned_start_time, 'end_time': order.assigned_end_time, 'order_status':order.order_status} for order in order_of_spot_on_date if order.order_status==OrderStatus.CANCELED or order.order_status==OrderStatus.DENIED or order.order_status==OrderStatus.ABNORMAL],
                "status": spot.status
            }
        return ResultSuccess(data={'spot_info':spot_info})
    
    def change_spot_status(self, user_tel, ps_id, new_status):
        spot = self._database.get_spot_by_id(ps_id)
        if not spot or new_status not in [SpotStatus.AVAILABLE, SpotStatus.NOT_AVAILABLE]:
            raise ParamError()
        if spot.owner_tel != user_tel:
            raise UnauthorizedOperation()
        self._database.update_spot_status(ps_id, new_status)
        return ResultSuccess(message="停止接受新订单" if new_status==SpotStatus.NOT_AVAILABLE else "已启用车位")
        
    def change_spot_rate(self, user_tel, ps_id, new_rate):
        spot = self._database.get_spot_by_id(ps_id)
        if not spot:
            raise ParamError()
        if spot.owner_tel != user_tel:
            raise UnauthorizedOperation()
        self._database.update_spot_rate(ps_id, new_rate)
        return ResultSuccess(message="价格已更新")
    # utility functions
    def get_usage_of_appointments(self, appointments):
        occupied_time = timedelta(seconds=0)
        for appointment in appointments:
            occupied_time += datetime.strptime(appointment[1],"%H:%M") - datetime.strptime(appointment[0],"%H:%M")
        return round(occupied_time/timedelta(days=1)*100)
        
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