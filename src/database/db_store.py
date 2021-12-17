import os
from datetime import datetime
from sqlalchemy import create_engine, func, distinct
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