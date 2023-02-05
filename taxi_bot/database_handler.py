from sqlalchemy import create_engine, Column, String, Integer, DateTime, Identity, BigInteger, JSON, func, Sequence
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import List, Tuple
from taxi_bot.load_config import Config
from aiogram import types


class User(Base):
    __tablename__ = 'users'

    user_id = Column('user_id', BigInteger, primary_key=True)
    username = Column('username', String)
    first_name = Column('first_name', String)
    last_name = Column('last_name', String)
    referral = Column('referral', String)
    phone_number = Column('phone_number', String)
    user_registration_date = Column('user_registration_date', DateTime)
    active = Column('active', Integer, default=1)

    def __init__(
            self, 
            user_id, 
            username, 
            first_name, 
            last_name, 
            referral
        ):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.referral = referral
        self.user_registration_date = datetime.now()
        # self.active = 1


class Driver(Base):
    __tablename__ = 'drivers'

    user_id = Column('user_id', BigInteger, primary_key=True)
    username = Column('username', String)
    first_name = Column('first_name', String)
    phone_number = Column('phone_number', String)
    active = Column('active', Integer)
    driver_registration_date = Column('driver_registration_date', DateTime)
    driver_status = Column('driver_status', Integer)
    driver_car = Column('driver_car', String)
    driver_balance = Column('driver_balance', Integer)
    driver_shift_id = Column('driver_shift_id', Integer)

    def __init__(
            self, 
            user_id, 
            username, 
            first_name, 
            last_name, 
            referral
        ):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.referral = referral
        self.user_registration_date = datetime.now()
        self.active = 1

    
class Order(Base):
    __tablename__ = 'orders'

    order_id = Column('order_id', Integer, Sequence(f'{__tablename__}_order_id_seq'), primary_key=True)
    order_dt = Column('order_dt', DateTime)
    accept_dt = Column('accept_dt', DateTime)
    wait_dt = Column('wait_dt', DateTime)
    pick_dt = Column('pick_dt', DateTime)
    end_dt = Column('end_dt', DateTime)
    passenger_id = Column('passenger_id', BigInteger)
    driver_id = Column('driver_id', BigInteger)
    location_from = Column('location_from', String)
    location_to = Column('location_to', String)
    price = Column('price', Integer)
    order_status = Column('order_status', Integer)

    def __init__(self, passenger_id):
        self.order_dt = datetime.now()
        self.passenger_id = passenger_id
        self.order_status = 70


class Shift(Base):
    __tablename__ = 'shifts'

    shift_id = Column('shift_id', Integer, Sequence(f'{__tablename__}_shift_id_seq'), primary_key=True)
    driver_id = Column('driver_id', BigInteger)
    shift_start = Column('shift_start', DateTime)
    shift_end = Column('shift_end', DateTime)
    total_trips = Column('total_trips', Integer)
    total_income = Column('total_income', Integer)

    def __init__(self, driver_id):
        self.driver_id = driver_id
        self.shift_start = datetime.now()
        self.total_income = 0
        self.total_trips = 0


class Log_Message(Base):
    __tablename__ = 'logs'

    log_id = Column('log_id', Integer, Sequence(f'{__tablename__}_log_id_seq'), primary_key=True)
    date_time = Column('date_time', DateTime)
    level = Column('level', String)
    chat_id = Column('chat_id', BigInteger)
    message_id = Column('message_id', Integer)
    order_id = Column('order_id', Integer)
    source = Column('source', String)
    message = Column('message', String)
    shown = Column('shown', Integer)

    def __init__(self, level, chat_id, message_id, order_id, source, message, shown):
        self.date_time = datetime.now()
        self.level = level
        self.chat_id = chat_id
        self.message_id = message_id
        self.order_id = order_id
        self.source = source
        self.message = message
        self.shown = shown


class DataBase(Config):
    
    def __init__(self, creds_path=None):
        if creds_path is None:
            return
        
        import os
        import json

        with open(creds_path, encoding='UTF-8') as f:
            self.config: dict = json.load(f)
        
        if self.config['GCLOUD_CREDS_PATH']:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.config['GCLOUD_CREDS_PATH']

        def getconn():
            from google.cloud.sql.connector import Connector
            connector = Connector()
            conn = connector.connect(
                self.config['INSTANCE_CONNECTION_NAME'],
                "pg8000",
                user=self.config['DB_USER'],
                password=self.config['DB_PASS'],
                db=self.config['DB_NAME'],
            )
            return conn
        
        self.engine = create_engine(f"postgresql+pg8000://", creator=getconn)
        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self._session = Session()

    def log_message(self, level, chat_id, message_id, order_id, _self, message, shown):
        source = _self.__class__.__name__
        log = Log_Message(level, chat_id, message_id, order_id, source, message, shown)
        self._session.add(log)
        self._session.commit()

    def update_log_status(self, log_ids):
        log_messages: List[Log_Message] = self._session.query(Log_Message).filter(Log_Message.log_id.in_(log_ids)).all()
        for log_message in log_messages:
            log_message.shown = 0
        self._session.commit()

    def delete_old_logs(self, expire_hours=120):
        pass
        # from datetime import timedelta
        # expire_time = datetime.now() - timedelta(hours=expire_hours)
        # (
        #     self._session.query(Log_Message)
        #     .filter(Log_Message.shown==0)
        #     .filter(Log_Message.date_time < expire_time)
        # ).delete()
        # self._session.commit()

    def get_group(self, group=None):
        users = self._session.query(User).filter(User.active==1)
        if group=='Passenger':
            return users.filter(User.driver_status.is_(None))
        elif group=='Driver':
            return users.filter(User.driver_status!=0)
        elif group=='Moder':
            return users.filter(User.user_id.in_(self.config.MODER_IDs))
        else:
            return users

    def update_activity(self, user_id, activity_status):
        user = self._session.query(User).filter(User.user_id==user_id).first()
        user.active = activity_status
        self._session.commit()

    def create_user(self, message: types.Message, referral):
        user_id = message.from_user.id
        user = self._session.query(User).filter(User.user_id==user_id).first()
        if not user:
            username = message.from_user.username
            first_name = message.from_user.first_name
            last_name = message.from_user.last_name
            new_passenger = User(user_id, username, first_name, last_name, referral)
            self._session.add(new_passenger)
        else:
            user.active = 1
        self._session.commit()
        return self.check_user_phone_number(user_id)

    def check_user_phone_number(self, user_id):
        return bool(self.get_user_by_id(user_id).phone_number)

    def update_phone_number(self, user_id, phone_number):
        user = self.get_user_by_id(user_id)
        user.phone_number = phone_number
        self._session.commit()

    def create_driver(self, user_id, first_name, driver_car):
        driver = self.get_user_by_id(user_id)
        driver.driver_registration_date = datetime.now()
        driver.first_name = first_name
        driver.driver_status = 50
        driver.driver_car = driver_car
        driver.driver_balance = 0
        driver.driver_shift_id = 0
        self._session.commit()

    def create_order(self, passenger_id) -> int:
        new_order = Order(passenger_id)
        self._session.add(new_order)
        self._session.commit()
        return new_order.order_id

    def update_order_location_from(self, order_id, location_from) -> Order:
        order = self.get_order_by_id(order_id)
        order.order_status = 80
        order.location_from = location_from
        self._session.commit()
        return order

    def update_order_location_to(self, order_id, location_to) -> Order:
        order = self.get_order_by_id(order_id)
        order.order_status = 90
        order.location_to = location_to
        self._session.commit()
        return order

    def update_order_price(self, order_id, price) -> Order:
        order = self.get_order_by_id(order_id)
        order.order_status = 100
        order.price = price
        self._session.commit()
        return order

    def update_order_driver(self, order_id, driver_id) -> Order:
        order = self.get_order_by_id(order_id)
        if order.driver_id:
            return
        order.order_status = 200
        order.driver_id = driver_id
        order.accept_dt = datetime.now()
        self._session.commit()
        return order

    def update_order_driver_none(self, order_id, driver_id) -> Order:
        order = self.get_order_by_id(order_id)
        if order.driver_id == driver_id:
            order.order_status = 100
            order.driver_id = None
            self._session.commit()
            return order

    def update_wait_dt(self, order_id) -> Order:
        order = self.get_order_by_id(order_id)
        order.order_status = 250
        order.wait_dt = datetime.now()
        self._session.commit()
        return order

    def update_pick_dt(self, order_id) -> Order:
        order = self.get_order_by_id(order_id)
        order.order_status = 300
        order.pick_dt = datetime.now()
        self._session.commit()
        return order

    def update_end_dt(self, order_id) -> Order:
        order = self.get_order_by_id(order_id)
        order.order_status = 400
        order.end_dt = datetime.now()
        self._session.commit()
        return order

    def update_cancel_dt(self, order_id) -> Order:
        order = self.get_order_by_id(order_id)
        order.end_dt = datetime.now()
        self._session.commit()
        return order

    def update_order(self, order_id, new_status) -> Order:
        order = self.get_order_by_id(order_id)
        order.order_status = new_status
        self._session.commit()
        return order

    def get_order_by_id(self, order_id) -> Order:
        order = self._session.query(Order).filter(Order.order_id==order_id).first()
        return order

    def get_orders(self, status) -> List[Order]:
        order = self._session.query(Order).filter(Order.order_status==status).all()
        return order

    def get_user_active_order(self, user_id) -> Order:
        statuses = [100,200,250,300]
        return self._session.query(Order).filter(Order.passenger_id==user_id).filter(Order.order_status.in_(statuses)).first()

    def get_order_messages(self, order_id, chat_id, message_id) -> List[Log_Message]:
        messages = self._session.query(Log_Message).filter(Log_Message.shown==1)
        if order_id:
            messages = messages.filter(Log_Message.order_id==order_id)
        if chat_id:
            messages = messages.filter(Log_Message.chat_id==chat_id)
        if message_id:
            messages = messages.filter(Log_Message.message_id==message_id)
        return messages.all()

    def get_user_by_id(self, user_id) -> User:
        return self.get_group().filter(User.user_id==user_id).first()

    def update_driver_status(self, driver_id, new_status):
        driver = self.get_user_by_id(driver_id)
        driver.driver_status = new_status
        self._session.commit()

    def get_drivers(self, status=None) -> List[User]:
        drivers = self.get_group('Driver').filter(User.active==1)
        if status:
            drivers = drivers.filter(User.driver_status==status)
        return drivers.all()

    def get_drivers_id(self, status=None) -> List[int]:
        drivers = self.get_drivers(status)
        drivers_id = [dr.user_id for dr in drivers]
        return drivers_id

    def get_drivers_active_order(self, driver_id) -> Order:
        order = self._session.query(Order).filter(Order.driver_id==driver_id).filter(Order.order_status.in_([200,250,300])).first()
        return order

    def get_available_drivers_count(self) -> int:
        drivers = self.get_group('Driver').filter(User.active==1).filter(User.driver_status.in_([100,150])).all()
        return len(drivers)

    def get_active_shift_by_driver_id(self, driver_id) -> Shift:
        driver = self.get_user_by_id(driver_id)
        shift_id = driver.driver_shift_id
        shift = self._session.query(Shift).filter(Shift.shift_id==shift_id).first()
        return shift

    def driver_start_shift(self, driver_id) -> None:
        new_shift = Shift(driver_id)
        driver = self.get_user_by_id(driver_id)
        self._session.add(new_shift)
        self._session.commit()
        driver.driver_shift_id = new_shift.shift_id
        self._session.commit()

    def driver_complete_trip(self, driver_id, income) -> None:
        shift = self.get_active_shift_by_driver_id(driver_id)
        driver = self.get_user_by_id(driver_id)
        driver.driver_status = 100
        shift.total_income += income
        shift.total_trips += 1
        self._session.commit()

    def driver_end_shift(self, driver_id) -> Shift:
        shift = self.get_active_shift_by_driver_id(driver_id)
        shift.shift_end = datetime.now()
        self._session.commit()
        return shift
