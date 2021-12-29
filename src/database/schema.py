from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, Float
from sqlalchemy.dialects.mysql import JSON
import uuid
from sqlalchemy.sql.elements import True_
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.schema import Constraint, ForeignKey

from sqlalchemy.sql.sqltypes import Integer

Base = declarative_base()

def get_str_uuid():
    return str(uuid.uuid4())

def get_datetime():
    # NOT local time
    return datetime.utcnow()

class User(Base):
    __tablename__ = 'user'
    # tel is the unique identifier of user
    tel = Column(String(11), primary_key=True, nullable=False)
    name = Column(String(12), nullable=False)
    # md5 result 128 bit 
    password_hash = Column(String(32), nullable=False)
    # INDIVIDUAL = 1, PROPERTY = 2, ADMIN = 3, MODERATOR = 4, SUPER_ADMIN = 5
    # authority: INDIVIDUAL create themselves, ADMIN creates PROPERTY, SUPER_ADMIN creates ALL
    # user_type switch not supported
    user_type = Column(Integer, nullable=False)
    create_date = Column(DateTime, nullable=False, default=get_datetime)
    credits = Column(Float, nullable=False, default=5)

class ParkingLot(Base):
    __tablename__ = 'parking_lot'
    # uuid4 string length 36
    pl_id = Column(String(36), primary_key=True, nullable=False, default=get_str_uuid)
    pl_name = Column(String(255), nullable=False)
    manager_tel = Column(String(11), ForeignKey('user.tel'), nullable=False)
    # e.g.
    # {
    #   'A':{
    #       'start':1,
    #       'end':420 
    #   },
    #   'B':{
    #       'start':1,
    #       'end':69 
    #   },
    #   etc.
    # }
    spot_id_range = Column(JSON, nullable=False)
    no_spots = Column(Integer, nullable=False)
    # {
    #   lat: 40.689247,
    #   lng: -74.044502
    # }
    coordinate = Column(JSON, nullable=False)
    # {
    #   1:{lat: 40.689247, lng: -74.044502},
    #   2:{lat: 40.689247, lng: -74.044502},
    #   3:{lat: 40.689247, lng: -74.044502},
    #   etc
    # }
    #  used to draw outline of the parking lot on map
    vertex = Column(JSON, nullable=True)

class ParkingSpot(Base):
    __tablename__ = 'parking_spot'
    ps_id = Column(String(36), primary_key=True, nullable=False, default=get_str_uuid())
    # real life id, e.g. A0069
    id = Column(String(255), nullable=False)
    # INDIVIDUAL = 1, PROPERTY = 2, MIXED = 3
    spot_type = Column(Integer, nullable=False)
    # spot_type = 1, individual owned spot
    owner_tel = Column(String(11), ForeignKey('user.tel'), nullable=True)
    # spot_type = 2, property management owned spot
    pl_id = Column(String(36), ForeignKey('parking_lot.pl_id'), nullable=True)
    
    price_per_min = Column(Float, nullable=False)
    # AVAILABLE = 1, RESERVED = 2, USING = 3, NOT_AVAILABLE = 4
    status = Column(Integer, nullable=False)
    available_start_time = Column(DateTime, nullable=True)
    available_end_time  = Column

class Order(Base):
    __tablename__ = 'order'
    order_id = Column(String(36), primary_key=True, nullable=False, default=get_str_uuid)
    custom_tel = Column(String(11), ForeignKey('user.tel'), nullable=False)
    ps_id = Column(String(36), nullable=False)
    # PLACED = 1, USING_SPOT = 2, COMPLETED = 3, ABNORMAL = 4
    order_status = Column(Integer, nullable=False)
    # UNPAIED = 0, PAID = 1
    payment_status = Column(Integer, nullable=False, default=False)
    create_date = Column(DateTime, nullable=False, default=get_datetime)
    complete_date = Column(DateTime, nullable=True)

    assigned_start_date = Column(DateTime, nullable=False)
    assigned_leave_date = Column(DateTime, nullable=False)

    actual_start_date = Column(DateTime, nullable=True)
    actual_leave_date = Column(DateTime, nullable=True)

