import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.functions import current_time
from src.error_code.error_code import *
from .schema import Base, User, ParkingLot, ParkingSpot, Order

class DBStore():
    def __init__(self):
        #TODO make this configurable 
        host = os.environ.get('MYSQL_HOST', 'localhost')
        port = os.environ.get('MYSQL_PORT', '3306')
        user = os.environ.get('MYSQL_USER', 'root')
        password = os.environ.get('MYSQL_PASSWD', 'Wwt123456')
        database = os.environ.get('MYSQL_DB', 'SHARK')

        connection_url = f'mysql://{user}:{password}@{host}:{port}/{database}?charset=utf8'

        self._engine = create_engine(connection_url)
        self._sessionmaker = sessionmaker(bind=self._engine)
        self._session = None
        # create all tables in schema, if not exist
        Base.metadata.create_all(bind=self._engine)

    def create_user(self, tel, name, password_hash, user_type):
        current_time = datetime.utcnow()
        user = User(
            tel = tel,
            name = name,
            password_hash = password_hash,
            user_type = user_type,
            create_date = current_time
        )
        self._session.add(user)
        return user

    def get_user_by_tel(self, tel):
        user = self._session.query(User).filter(User.tel == tel).first()
        return user
    
    def change_user_role(self, user_tel, target_role):
        self._session.query(User).filter(User.tel == user_tel).update({"user_type": target_role})
        try:
            self.commit()
        except:
            self.rollback()

    def get_spot_by_id(self, ps_id):
        spot = self._session.query(ParkingSpot).filter(ParkingSpot.ps_id == ps_id).first()
        return spot

    def get_spot_by_id_LOCK_ROW(self, ps_id):
        # IMPORTANT update sqlalchemy buffer, re-fetch data from database
        self.commit()
        # with_for_update locks the row with corresponding ps_id, releases lock upon session commit
        rst = self._session.query(ParkingSpot).filter(ParkingSpot.ps_id == ps_id).with_for_update().one()
        return rst

    # supports parking lots and spots
    def get_p_by_name(self, p_name):
        # for searching parking spots
        spot_sql = "SELECT ps_id AS p_id, name, spot_type AS type, price_per_min, coordinate FROM parking_spot WHERE name LIKE '%{}%' AND spot_type=1".format(p_name)
        rst = self._session.execute(spot_sql)
        # turn CursorResult object (query result) into list of dictionary
        p_dict_list = [dict(item) for item in rst]
        # for searching parking lots
        lot_sql = "SELECT pl_id AS p_id, name, 2 AS type, price_per_min, coordinate FROM parking_lot WHERE name LIKE '%{}%'".format(p_name)
        rst = self._session.execute(lot_sql)
        # merge spots & lots results
        p_dict_list.extend([dict(item) for item in rst])
        return p_dict_list

    def get_appointments_by_id(self, id):
        rst = self._session.query(ParkingSpot).filter(ParkingSpot.ps_id == id).first()
        return rst.appointments
    
    def reserve_spot(self, ps_id, start_time, end_time):
        # parse and check time
        st = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        et = datetime.strptime(end_time, '%Y-%m-%d %H:%M')
        if st>=et:
            raise ParamError()

        # get appointments of the spot, lock row when fetch ParkingSpot
         # IMPORTANT update sqlalchemy buffer, re-fetch data from database
        self.commit()
        # with_for_update locks the row with corresponding ps_id, releases lock upon session commit
        spot = self._session.query(ParkingSpot).filter(ParkingSpot.ps_id == ps_id).with_for_update().one()
        appointments = spot.appointments

        # CASE 1, period spans single day
        if st.date() == et.date():
            date_str = str(st.date())
            appointments_of_that_date = appointments.get(date_str, [])
            try:
                if appointments_of_that_date == []:
                    appointments[start_time.split(' ')[0]] = [[start_time.split(' ')[1], end_time.split(' ')[1]]]
                    spot.appointments = appointments
                    # release row lock of the spot
                    self.commit()
                    return ResultSuccess(message="预约成功")
                else:
                    insert_location = self.check_and_insert_period_in_specific_date(ps_id, appointments_of_that_date=appointments_of_that_date, period_start_time=st, period_end_time=et)
                    appointments[start_time.split(' ')[0]].insert(insert_location, [start_time.split(' ')[1], end_time.split(' ')[1]])
                    spot.appointments = appointments
                    self.commit()
                    return ResultSuccess(message="预约成功")
            except InvalidPeriod:
                return InvalidPeriod()

        # CASE 2, period spans multiple days, any appointments in between will render period unavailable
        # 2.1 check days inbetween
        it = st.date()+timedelta(days=1)
        while it < et.date():
            if appointments.get(str(it)) != None:
                raise InvalidPeriod()
            it = it+timedelta(days=1)
        # 2.2 check both start_date and end_date of the period for availability
        start_date_appointments = appointments.get(str(st.date()), [])
        end_date_appointments = appointments.get(str(et.date()), [])
        end_of_start_date = datetime.strptime(f'{str(st.date() + timedelta(days=1))} 00:00', '%Y-%m-%d %H:%M')
        start_of_end_date = datetime.strptime(f'{str(et.date())} 00:00', '%Y-%m-%d %H:%M')
        try:
            insert_location_s = self.check_and_insert_period_in_specific_date(ps_id, appointments_of_that_date=start_date_appointments, period_start_time=st, period_end_time=end_of_start_date)
        except InvalidPeriod:
            InvalidPeriod()
        try:
            insert_location_e = self.check_and_insert_period_in_specific_date(ps_id, appointments_of_that_date=end_date_appointments, period_start_time=start_of_end_date, period_end_time=et)
        except InvalidPeriod:
            InvalidPeriod()
        # after confirm valid
        # 2.3 insert in dates in between
        it = st.date()+timedelta(days=1)
        while it < et.date():
            if appointments.get(str(it), []) == []:
                appointments[str(it)] = [['00:00', '23:59']]
            else:
                raise InvalidPeriod()
            it = it+timedelta(days=1)
        # 2.4 insert in start date
        if start_date_appointments == []:
            appointments[start_time.split(' ')[0]] = [[start_time.split(' ')[1], '23:59']]
        else:
            appointments[start_time.split(' ')[0]].insert(insert_location_s, [start_time.split(' ')[1], '23:59'])
        # 2.5 insert in end date
        if end_date_appointments == []:
            appointments[start_time.split(' ')[0]] = [['00:00', end_time.split(' ')[1]]]
        else:
            appointments[start_time.split(' ')[0]].insert(insert_location_e, ['00:00', end_time.split(' ')[1]])
        # 2.6 update spot and commit, release the lock
        spot.appointments = appointments
        self.commit()
        # TODO insert record into Order table
        return ResultSuccess(message="预约成功")

    def get_subspots_by_pl_id(self, pl_id):
        spots = self._session.query(ParkingSpot).filter(ParkingSpot.pl_id == pl_id).all()
        return spots

    def insert_appointment(self, ps_id, new_appointment):
        spot = self._session.query(ParkingSpot).filter(ParkingSpot.ps_id==ps_id).one()
        spot.appointments = new_appointment
        self.commit()

    def withdraw_appointment(self, ps_id, start_time, end_time):
        pass

    def __enter__(self):
        self.connect()

    def connect(self):
        self._session = self._sessionmaker()

    def __exit__(self, exception_type, exception_value, traceback):
        self.disconnect()

    def disconnect(self):
        if self._session is not None:
            self._session.commit()
            self._session.close()
            self._session = None

    def commit(self):
        try:
            print("!!!COMMIT INVOKED!!!")
            self._session.commit()
        except Exception as ex:
            raise ex

    def rollback(self):
        try:
            self._session.rollback()
        except Exception as ex:
            raise ex