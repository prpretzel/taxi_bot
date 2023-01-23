from sqlalchemy import create_engine, Column, String, Integer, DateTime, Identity, BigInteger, JSON
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import List, Tuple
from taxi_bot.load_config import Config
from aiogram import types
config = Config()

from sqlalchemy import select


class User(Base):
    __tablename__ = 'users'

    user_id = Column('user_id', BigInteger, primary_key=True)
    username = Column('username', String)
    first_name = Column('first_name', String)
    last_name = Column('last_name', String)
    phone_number = Column('phone_number', String)
    user_registration_date = Column('user_registration_date', DateTime)
    driver_registration_date = Column('driver_registration_date', DateTime)
    active = Column('active', Integer)
    driver_status = Column('driver_status', Integer)
    driver_car = Column('driver_car', String)
    driver_balance = Column('driver_balance', Integer)
    driver_shift_id = Column('driver_shift_id', Integer)


    def __init__(
            self, 
            user_id, 
            username, 
            first_name, 
            last_name
        ):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.active = 1
        self.user_registration_date = datetime.now()

    
class Order(Base):
    __tablename__ = 'orders'

    order_id = Column('order_id', Integer, Identity(), primary_key=True)
    order_dt = Column('order_dt', DateTime)
    wait_dt = Column('wait_dt', DateTime)
    pick_dt = Column('pick_dt', DateTime)
    end_dt = Column('end_dt', DateTime)
    cancel_dt = Column('cancel_dt', DateTime)
    passenger_id = Column('passenger_id', BigInteger)
    driver_id = Column('driver_id', BigInteger)
    location_from = Column('location_from', String)
    location_to = Column('location_to', String)
    price = Column('price', Integer)
    order_status = Column('order_status', Integer)


    def __init__(self, passenger_id, location_from):
        self.order_dt = datetime.now()
        self.passenger_id = passenger_id
        self.location_from = location_from
        self.order_status = 80


class Shift(Base):
    __tablename__ = 'shifts'

    shift_id = Column('shift_id', Integer, Identity(), primary_key=True)
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

    log_id = Column('log_id', Integer, Identity(), primary_key=True)
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


class DataBase:
    
    def __init__(self):
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.ext.asyncio import AsyncSession
        user = config.DB_USER
        password = config.DB_PASS
        database = config.DB_NAME 
        host = '34.29.38.218'
        port = 5432
        DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

        self._engine = create_async_engine(DATABASE_URL)

        Session = sessionmaker(
            self._engine, 
            autocommit=False, 
            autoflush=False, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        self._session = Session()

# ------------------------------------------------------------------------------------------------------------------ 
# ------------------------------------------------------------------------------------------------------------------

    async def init_tables(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)            

    async def log_message(self, level, chat_id, message_id, order_id, _self, message, shown):
        source = _self.__class__.__name__
        log = Log_Message(level, chat_id, message_id, order_id, source, message, shown)
        self._session.add(log)
        await self._session.commit()

    async def update_log_status(self, log_ids):
        log_messages: List[Log_Message] = await self._session.scalars(select(Log_Message).filter(Log_Message.log_id.in_(log_ids)))
        for log_message in log_messages:
            log_message.shown = 0
        await self._session.commit()

    def get_group(self, group=None):
        statement = select(User).filter(User.active==1)
        if group=='Passenger':
            statement = statement.filter(User.driver_status.is_(None))
        elif group=='Driver':
            statement = statement.filter(User.driver_status!=0)
        return statement

    async def update_activity(self, user_id, activity_status):
        user = await self.get_user_by_id(user_id)
        user.active = activity_status
        await self._session.commit()

    async def create_user(self, message: types.Message):
        user_id = message.from_user.id
        user = await self.get_user_by_id(user_id)
        if not user:
            username = message.from_user.username
            first_name = message.from_user.first_name
            last_name = message.from_user.last_name
            new_passenger = User(user_id, username, first_name, last_name)
            self._session.add(new_passenger)
        else:
            user.active = 1
        await self._session.commit()
        return await self.check_user_phone_number(user_id)

    async def check_user_phone_number(self, user_id):
        user = await self.get_user_by_id(user_id)
        phone_number = bool(user.phone_number)
        return phone_number

    async def update_phone_number(self, user_id, phone_number):
        user = await self.get_user_by_id(user_id)
        user.phone_number = phone_number
        await self._session.commit()

    async def create_driver(self, user_id, first_name, driver_car):
        driver = await self.get_user_by_id(user_id)
        driver.driver_registration_date = datetime.now()
        driver.first_name = first_name
        driver.driver_status = 50
        driver.driver_car = driver_car
        driver.driver_balance = 0
        driver.driver_shift_id = 0
        await self._session.commit()

    async def create_order(self, passenger_id, location_from) -> int:
        new_order = Order(passenger_id, location_from)
        self._session.add(new_order)
        await self._session.commit()
        return new_order.order_id

    async def update_order_location_to(self, order_id, location_to) -> Order:
        order = await self.get_order_by_id(order_id)
        order.order_status = 90
        order.location_to = location_to
        await self._session.commit()
        return order

    async def update_order_price(self, order_id, price) -> Order:
        order = await self.get_order_by_id(order_id)
        order.order_status = 100
        order.price = price
        await self._session.commit()
        return order

    async def update_order_driver(self, order_id, driver_id) -> Order:
        order = await self.get_order_by_id(order_id)
        driver_id = order.driver_id
        if driver_id:
            return
        order.order_status = 200
        order.driver_id = driver_id
        await self._session.commit()
        return order

    async def update_wait_dt(self, order_id) -> Order:
        order = await self.get_order_by_id(order_id)
        order.order_status = 250
        order.wait_dt = datetime.now()
        await self._session.commit()
        return order

    async def update_pick_dt(self, order_id) -> Order:
        order = await self.get_order_by_id(order_id)
        order.order_status = 300
        order.pick_dt = datetime.now()
        await self._session.commit()
        return order

    async def update_end_dt(self, order_id) -> Order:
        order = await self.get_order_by_id(order_id)
        order.order_status = 400
        order.end_dt = datetime.now()
        await self._session.commit()
        return order

    async def update_cancel_dt(self, order_id) -> Order:
        order = await self.get_order_by_id(order_id)
        order.cancel_dt = datetime.now()
        await self._session.commit()
        return order

    async def update_order(self, order_id, new_status) -> Order:
        order = await self.get_order_by_id(order_id)
        order.order_status = new_status
        await self._session.commit()
        return order

    async def get_order_by_id(self, order_id) -> Order:
        order = await self._session.scalar(select(Order).filter(Order.order_id==order_id))
        return order

    async def get_orders(self, status) -> List[Order]:
        orders = await self._session.scalars(select(Order).filter(Order.order_status==status))
        return orders

    async def get_user_active_order(self, user_id) -> Order:
        statuses = [100,200,250,300]
        orders = await self._session.scalar(select(Order).filter(Order.passenger_id==user_id).filter(Order.order_status.in_(statuses)))
        return orders

    async def get_order_messages(self, order_id, chat_id, message_id) -> List[Log_Message]:
        statement = select(Log_Message).filter(Log_Message.shown==1)
        if order_id:
            statement = statement.filter(Log_Message.order_id==order_id)
        if chat_id:
            statement = statement.filter(Log_Message.chat_id==chat_id)
        if message_id:
            statement = statement.filter(Log_Message.message_id==message_id)
        return await self._session.scalars(statement)

    async def get_user_by_id(self, user_id) -> User:
        user = await self._session.scalar(select(User).filter(User.user_id==user_id))
        return user

    async def update_driver_status(self, driver_id, new_status):
        driver = await self.get_user_by_id(driver_id)
        driver.driver_status = new_status
        await self._session.commit()

    async def get_drivers(self, status=None) -> List[User]:
        statement = self.get_group('Driver')
        if status:
            statement = statement.filter(User.driver_status==status)
        return await self._session.scalars(statement)

    async def get_drivers_id(self, status=None) -> List[int]:
        drivers = await self.get_drivers(status)
        drivers_id = [dr.user_id for dr in drivers]
        return drivers_id

    async def get_drivers_active_order(self, driver_id) -> Order:
        order = await self._session.scalar(select(Order).filter(Order.driver_id==driver_id).filter(Order.order_status.in_([200,250,300])))
        return order

    async def get_available_drivers_count(self) -> int:
        drivers_count = await self._session.execute('COUNT * FROM drivers WHERE active=1 AND driver_status IN (100, 150)')
        print(drivers_count)
        return drivers_count + 3

    async def get_active_shift_by_driver_id(self, driver_id) -> Shift:
        driver = await self.get_user_by_id(driver_id)
        shift_id = driver.driver_shift_id
        shift = await self._session.scalar(select(Shift).filter(Shift.shift_id==shift_id))
        return shift

    async def driver_start_shift(self, driver_id) -> None:
        new_shift = Shift(driver_id)
        driver = await self.get_user_by_id(driver_id)
        self._session.add(new_shift)
        await self._session.commit()
        driver.driver_shift_id = new_shift.shift_id
        await self._session.commit()

    async def driver_complete_trip(self, driver_id, income) -> None:
        shift = await self.get_active_shift_by_driver_id(driver_id)
        driver = await self.get_user_by_id(driver_id)
        driver.driver_status = 100
        shift.total_income += income
        shift.total_trips += 1
        await self._session.commit()

    async def driver_end_shift(self, driver_id) -> Shift:
        shift = await self.get_active_shift_by_driver_id(driver_id)
        shift.shift_end = datetime.now()
        await self._session.commit()
        return shift
