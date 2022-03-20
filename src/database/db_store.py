import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.functions import current_time
from src.error_code.error_code import *
from src.user.constant import OrderStatus, PaymentStatus, SpotType
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
        spot = self._session.query(ParkingSpot).filter(ParkingSpot.ps_id == ps_id).one()
        return spot


    # 110 kilometers per lat, 111.32 kilometers per lng, approximate to same km/degree
    # ±0.018 degree = ±2km
    def get_personal_spots_in_proximity(self, lat, lng, range = 0.018):
        # -90 to 90 for latitude, -180 to 180 for longitude
        # ignore overflow and underflow
        spot_list = []
        spots = self._session.query(ParkingSpot).filter(ParkingSpot.spot_type == SpotType.INDIVIDUAL, ParkingSpot.latitude<=(lat+range), ParkingSpot.latitude>=(lat-range), ParkingSpot.longitude<=(lng+range), ParkingSpot.longitude>=(lng-range)).all()
        for spot in spots:
            spot_list.append({'id': spot.ps_id, 'type': SpotType.INDIVIDUAL, 'name':spot.name, 'price_per_min': spot.price_per_min, 'latitude':spot.latitude, 'longitude':spot.longitude})
        return spot_list

    def get_all_property_lots_in_proximity(self, lat, lng, range = 0.018):
        lot_list = []
        lots = self._session.query(ParkingLot).filter(ParkingLot.latitude<=lat+range, ParkingLot.latitude>=(lat-range), ParkingLot.longitude<=(lng+range), ParkingLot.longitude>=(lng-range)).all()
        for lot in lots:
            lot_list.append({'id': lot.pl_id, 'type': SpotType.PROPERTY, 'name':lot.name, 'price_per_min': lot.price_per_min, 'latitude':lot.latitude, 'longitude':lot.longitude})
        return lot_list

    # supports parking lots and spots
    def get_p_by_name(self, p_name):
        # for searching parking spots
        spot_sql = "SELECT ps_id AS p_id, name, spot_type AS type, price_per_min, latitude, longitude FROM parking_spot WHERE name LIKE '%{}%' AND spot_type=1".format(p_name)
        rst = self._session.execute(spot_sql)
        # turn CursorResult object (query result) into list of dictionary
        p_dict_list = [dict(item) for item in rst]
        # for searching parking lots
        lot_sql = "SELECT pl_id AS p_id, name, 2 AS type, price_per_min, latitude, longitude FROM parking_lot WHERE name LIKE '%{}%'".format(p_name)
        rst = self._session.execute(lot_sql)
        # merge spots & lots results
        p_dict_list.extend([dict(item) for item in rst])
        return p_dict_list

    def get_appointments_by_id(self, id):
        rst = self._session.query(ParkingSpot).filter(ParkingSpot.ps_id == id).first()
        return rst.appointments

    def get_subspots_by_pl_id(self, pl_id):
        spots = self._session.query(ParkingSpot).filter(ParkingSpot.pl_id == pl_id).all()
        return spots

    def spot_update_flag_lock(self, ps_id):
        # refresh sql buffer
        self._session.commit()
        # query with exclusive row level lock
        spot = self._session.query(ParkingSpot).filter(ParkingSpot.ps_id == ps_id).with_for_update().one()
        if spot.flag == 1:
            # release lock
            self._session.commit()
            raise WaitingSync()
        else:
            spot.flag = 1
            self._session.commit()

    def spot_update_flag_unlock(self, ps_id):
        self._session.commit()
        spot = self._session.query(ParkingSpot).filter(ParkingSpot.ps_id == ps_id).with_for_update().one()
        spot.flag = 0
        self._session.commit()


    def order_update_flag_lock(self, order_id):
        # refresh sql buffer
        self._session.commit()
        # query with exclusive row level lock
        order = self._session.query(Order).filter(Order.order_id == order_id).with_for_update().one()
        if order.flag == 1:
            # release lock
            self._session.commit()
            raise WaitingSync()
        else:
            order.flag = 1
            self._session.commit()

    def order_update_flag_unlock(self, order_id):
        self._session.commit()
        order = self._session.query(Order).filter(Order.order_id == order_id).with_for_update().one()
        order.flag = 0
        self._session.commit()

    def get_order_by_id(self, order_id):
        return self._session.query(Order).filter(Order.order_id == order_id).first()

    # acceptable updates: PLACED->USING_SPOT, PLACED->CANCELED, PLACED->DENIED, USING_SPOT->COMPLETED
    def update_order_status(self, order_id, new_status):
        if new_status not in [OrderStatus.PLACED, OrderStatus.USING_SPOT, OrderStatus.CANCELED, OrderStatus.DENIED, OrderStatus.ABNORMAL, OrderStatus.COMPLETED]:
            raise ParamError()
        self.order_update_flag_lock(order_id)
        order = self.get_order_by_id(order_id)
        if (order.order_status == OrderStatus.PLACED and new_status not in [OrderStatus.USING_SPOT, OrderStatus.CANCELED, OrderStatus.DENIED]) or (order.order_status == OrderStatus.USING_SPOT and new_status != OrderStatus.COMPLETED):
            self.order_update_flag_unlock(order_id)
            raise ParamError()
        self._session.query(Order).filter(Order.order_id == order_id).update({"order_status": new_status})
        self.order_update_flag_unlock(order_id)
        self._session.commit()

    def place_order(self, order_id, user_tel, ps_id, start_time, end_time):
        current_time = datetime.utcnow()
        order = Order(
            order_id = order_id,
            ps_id = ps_id,
            custom_tel = user_tel,
            order_status = OrderStatus.PLACED,
            payment_status = PaymentStatus.UNPAID,
            # utc as creat time
            utc_create_time = current_time,
            # local time as start/end_time, corresponds with appointments
            assigned_start_time = start_time,
            assigned_end_time = end_time
        )
        self._session.add(order)
        return order

    def update_appointments(self, ps_id, new_appointments):
        self.commit()
        self._session.query(ParkingSpot).filter(ParkingSpot.ps_id == ps_id).update({"appointments": new_appointments})
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
            self._session.commit()
        except Exception as ex:
            raise ex

    def rollback(self):
        try:
            self._session.rollback()
        except Exception as ex:
            raise ex