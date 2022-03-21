from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, Float, false
from sqlalchemy.dialects.mysql import JSON
import uuid
from sqlalchemy.sql.elements import True_
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.schema import Constraint, ForeignKey

from sqlalchemy.sql.sqltypes import Integer
from tables import Col

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
    name = Column(String(255), nullable=False)
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
    # } need a parse function?? 
    # TODO generate subordinate parking spots
    spot_id_range = Column(JSON, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    price_per_min = Column(Float, nullable=False)

class ParkingSpot(Base):
    __tablename__ = 'parking_spot'
    ps_id = Column(String(36), primary_key=True, nullable=False, default=get_str_uuid())
    # real life id, e.g. A0069 if property owned
    # or spot name if individual owned
    name = Column(String(255), nullable=False)
    # INDIVIDUAL = 1, PROPERTY = 2
    spot_type = Column(Integer, nullable=False)
    # spot_type = 1, individual owned spot
    owner_tel = Column(String(11), ForeignKey('user.tel'), nullable=True)
    # spot_type = 2, property management owned spot
    pl_id = Column(String(36), ForeignKey('parking_lot.pl_id'), nullable=True)
    price_per_min = Column(Float, nullable=False)
    # NOT_AVAILABLE = 0, AVAILABLE = 1, RESERVED = 2, USING = 3
    status = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    # appointments = {'2022-02-25':[['00:00','12:00'], ['20:30','21:00']], '2022-05-04':[['06:00','12:00'], ['22:30','23:00']]}
    appointments = Column(JSON, nullable=False, default={})
    # flag for row level mutually exclusive update
    flag = Column(Integer, nullable=False, default=0)

class Order(Base):
    __tablename__ = 'order'
    order_id = Column(String(36), primary_key=True, nullable=False, default=get_str_uuid)
    custom_tel = Column(String(11), ForeignKey('user.tel'), nullable=False)
    ps_id = Column(String(36), nullable=False)
    # DENIED = 0, PLACED = 1, USING_SPOT = 2, CANCELED = 4, ABNORMAL = 5, LEFT_UNPAID = 10, COMPLETED_PAID = 11
    order_status = Column(Integer, nullable=False)
    utc_create_time = Column(DateTime, nullable=False, default=get_datetime)
    utc_complete_time = Column(DateTime, nullable=True)

    assigned_start_time = Column(DateTime, nullable=False)
    assigned_end_time = Column(DateTime, nullable=False)

    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)

    flag = Column(Integer, nullable=False, default=0)