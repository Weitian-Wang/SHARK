import os
import time
from src.database import DBStore
from src.error_code import *

# for threading and logic handling
class UserProxy():
    def __init__(self):
        self._database = DBStore()
        self._expire_time = '7200'

    def tel_check(self, tel):
        if self._database.get_user_by_tel(tel=tel):
            raise UserNotExistError
        
    # "with user_proxy" triggers __enter__
    def __enter__(self):
        self.connect()

    def connect(self):
        self._database.connect()

    def __exit__(self, exception_type, exception_value, traceback):
        self.disconnect()

    def disconnect(self):
        self._database.disconnect()