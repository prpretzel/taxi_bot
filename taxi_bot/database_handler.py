from sqlalchemy import create_engine, ForeignKey, Column, String, Integer, DateTime, Boolean, Identity, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import List, Tuple
from taxi_bot.load_config import Config
Base = declarative_base()
config = Config()


class User(Base):
    __tablename__ = 'users'

    user_id = Column('user_id', Integer, primary_key=True)
    username = Column('username', String)
    first_name = Column('first_name', String)
    last_name = Column('last_name', String)
    phone_number = Column('phone_number', String)
    registration_date = Column('registration_date', String)
    active = Column('active', Integer)
    driver_status = Column('driver_status', Integer)
    driver_car = Column('driver_car', Integer)


    def __init__(
            self, 
            user_id, 
            username, 
            first_name, 
            last_name, 
            phone_number, 
            user_registration_date, 
            driver_registration_date=None, 
            driver_status=None, 
            driver_car=None
        ):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.phone_number = phone_number
        self.active = True
        self.user_registration_date = user_registration_date
        self.driver_registration_date = driver_registration_date
        self.driver_status = driver_status
        self.driver_car = driver_car

    
class Order(Base):
    __tablename__ = 'orders'

    order_id = Column('order_id', Integer, Identity(), primary_key=True)
    order_dt = Column('order_dt', String)
    passenger_id = Column('passenger_id', Integer)
    driver_id = Column('driver_id', Integer)
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

    def get_group(self, group=None):
        if group=='Passenger':
            return self._session.query(User).filter(User.driver_status==0)
        elif group=='Driver':
            return self._session.query(User).filter(User.driver_status!=0)
        else:
            return self._session.query(User)

    def update_activity(self, user_id, activity_status):
        user: User = self.get_group().filter(User.user_id==user_id).first()
        user.active = activity_status
        self._session.commit()

    def create_user(self, user_id, username, first_name, last_name, phone_number):
        user: User = self._session.query(User).filter(User.user_id==user_id).first()
        if not user:
            registration_date = datetime.now()
            new_passenger = User(user_id, username, first_name, last_name, phone_number, registration_date)
            self._session.add(new_passenger)
        else:
            user.active = 1
        self._session.commit()

    def create_driver(self, user_id, first_name, driver_car):
        user: User = self._session.query(User).filter(User.user_id==user_id).first()
        user.driver_registration_date = datetime.now()
        user.first_name = first_name
        user.driver_status = 50
        user.driver_car = driver_car
        self._session.commit()

    def update_phone_number(self, user_id, phone_number):
        user: User = self._session.query(User).filter(User.user_id==user_id).first()
        user.phone_number = phone_number
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

    def get_orders(self, status) -> List[Order]:
        order = self._session.query(Order).filter(Order.order_status==status).all()
        return order

    def get_user_active_order(self, user_id):
        return self._session.query(Order).filter(Order.passenger_id==user_id).filter(Order.order_status==100).first()

    def create_order_message(self, order_id, user_id, message_id):
        new_message_order = SentMessage(order_id, user_id, message_id)
        self._session.add(new_message_order)
        self._session.commit()

    def get_order_messages(self, order_id=None, chat_id=None):
        if order_id:
            messages: List[SentMessage] = self._session.query(SentMessage).filter(SentMessage.order_id==order_id).all()
        if chat_id:
            messages: List[SentMessage] = self._session.query(SentMessage).filter(SentMessage.chat_id==chat_id).all()
        messages = [(m.chat_id, m.message_id) for m in messages]
        return messages

    def update_order(self, order_id, new_status, driver_id=None):
        order: Order = self._session.query(Order).filter(Order.order_id==order_id).first()
        order.order_status = new_status
        if driver_id: order.driver_id = driver_id
        self._session.commit()
        return order.passenger_id, order.driver_id

    def get_passenger_by_id(self, passenger_id):
        passenger: User = self.get_group().filter(User.user_id==passenger_id).first()
        return passenger

    def get_driver_by_id(self, driver_id):
        driver: User = self.get_group('Driver').filter(User.user_id==driver_id).first()
        return driver

    def update_driver_status(self, driver_id, new_status):
        driver = self.get_group('Driver').filter(User.user_id==driver_id).first()
        driver.driver_status = new_status
        self._session.commit()

    def get_drivers_id(self, status=None):
        drivers = self.get_group('Driver')
        if status:
            drivers = drivers.filter(User.driver_status==status)
        drivers = [dr.user_id for dr in drivers.all()]
        return drivers
