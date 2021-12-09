import os
import time
from src.database import DBStore

# for threading and logic handling
class UserProxy():
    def __init__(self):
        self._database = DBStore()
        self._expire_time = '7200'

    def tel_check(self, tel):
        if self._database.serch_user_by_tel(tel=tel):
            raise UserExistError()
