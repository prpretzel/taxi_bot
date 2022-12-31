from sqlalchemy import create_engine, ForeignKey, Column, String, Integer, DateTime, Boolean, Identity, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import List, Tuple
from taxi_bot.load_config import Config
Base = declarative_base()
config = Config()


class Passenger(Base):
    __tablename__ = 'passengers'

    user_id = Column('user_id', Integer, primary_key=True)
    username = Column('username', String)
    first_name = Column('first_name', String)
    last_name = Column('last_name', String)
    phone_number = Column('phone_number', String)
    registration_date = Column('registration_date', String)


    def __init__(self, user_id, username, first_name, last_name, phone_number, registration_date):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.phone_number = phone_number
        self.registration_date = registration_date


class Driver(Base):
    __tablename__ = 'drivers'

    user_id = Column('user_id', Integer, primary_key=True)
    username = Column('username', String)
    first_name = Column('first_name', String)
    last_name = Column('last_name', String)
    phone_number = Column('phone_number', String)
    registration_date = Column('registration_date', String)
    driver_status = Column('driver_status', Integer)
    driver_car = Column('driver_car', Integer)


    def __init__(self, user_id, username, first_name, last_name, phone_number, registration_date, driver_status, driver_car):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.phone_number = phone_number
        self.registration_date = registration_date
        self.driver_car = driver_car
        self.driver_status = driver_status

    
class Order(Base):
    __tablename__ = 'orders'

    order_id = Column('order_id', Integer, Identity(), primary_key=True)
    order_dt = Column('order_dt', String)
    passenger_id = Column('passenger_id', Integer, ForeignKey('passengers.user_id'))
    driver_id = Column('driver_id', Integer, ForeignKey('drivers.user_id'))
    location_from = Column('location_from', String)
    order_status = Column('order_status', String)


    def __init__(self, order_dt, passenger_id, driver_id, location_from, order_status):
        self.order_dt = order_dt
        self.passenger_id = passenger_id
        self.driver_id = driver_id
        self.location_from = location_from
        self.order_status = order_status


class SentMessage(Base):
    __tablename__ = 'SentMessage'

    log_id = Column('log_id', Integer, Identity(), primary_key=True)
    order_id = Column('order_id', Integer)
    chat_id = Column('chat_id', Integer)
    message_id = Column('message_id', Integer)


    def __init__(self, order_id, dr, message_id):
        self.order_id = order_id
        self.chat_id = dr
        self.message_id = message_id


class DataBase:
    
    def __init__(self):
        engine = create_engine(f"sqlite:///{config.database_path}")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        self._session = Session()

    def create_passenger(self, user_id, username, first_name, last_name, phone_number):
        exists = self._session.query(Passenger).filter(Passenger.user_id==user_id).first()
        if not exists:
            registration_date = datetime.now()
            new_passenger = Passenger(user_id, username, first_name, last_name, phone_number, registration_date)
            self._session.add(new_passenger)
            self._session.commit()

    def create_driver(self, user_id, username, first_name, last_name, phone_number, car):
        exists = self._session.query(Driver).filter(Driver.user_id==user_id).first()
        if not exists:
            registration_date = datetime.now()
            status = 100
            new_driver = Driver(user_id, username, first_name, last_name, phone_number, registration_date, status, car)
            self._session.add(new_driver)
            self._session.commit()

    def update_phone_number(self, user_id, phone_number):
        passenger: Passenger = self._session.query(Passenger).filter(Passenger.user_id==user_id).first()
        driver: Driver = self._session.query(Driver).filter(Driver.user_id==user_id).first()
        if driver: driver.phone_number = phone_number
        if passenger: passenger.phone_number = phone_number
        self._session.commit()

    def create_order(self, passenger_id, location_from):
        driver_id = None
        order_dt = datetime.now()
        status = 100
        new_order = Order(order_dt, passenger_id, driver_id, location_from, status)
        self._session.add(new_order)
        self._session.commit()
        return new_order.order_id

    def get_order_by_id(self, order_id):
        order = self._session.query(Order).filter(Order.order_id==order_id).filter(Order.order_status==100).first()
        return order

    def get_order_user_active_order(self, user_id):
        return self._session.query(Order).filter(Order.passenger_id==user_id).filter(Order.order_status==100).first()

    def create_order_message(self, order_id, dr, message_id):
        new_message_order = SentMessage(order_id, dr, message_id)
        self._session.add(new_message_order)
        self._session.commit()

    def get_order_messages(self, order_id):
        messages: List[SentMessage] = self._session.query(SentMessage).filter(SentMessage.order_id==order_id).all()
        messages = [(m.chat_id, m.message_id) for m in messages]
        return messages

    def update_order(self, order_id, new_status, driver_id=None):
        order: Order = self._session.query(Order).filter(Order.order_id==order_id).first()
        order.order_status = new_status
        if driver_id: order.driver_id = driver_id
        self._session.commit()
        return order.passenger_id, order.driver_id

    def get_passenger_by_id(self, passenger_id):
        passenger = self._session.query(Passenger).filter(Passenger.user_id==passenger_id).first()
        return passenger

    def get_driver_by_id(self, driver_id):
        driver = self._session.query(Driver).filter(Driver.user_id==driver_id).first()
        return driver

    def get_available_drivers_id(self):
        drivers: List[Driver] = self._session.query(Driver).filter(Driver.driver_status==100).all()
        drivers = [dr.user_id for dr in drivers]
        return drivers
