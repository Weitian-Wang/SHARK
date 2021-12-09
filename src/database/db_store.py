from datetime import datetime
from sqlalchemy import create_engine, func, distinct
from sqlalchemy.orm import sessionmaker
from .schema import Base, User, ParkingLot, ParkingSpot, Order