from abc import abstractmethod
from aiogram import Bot
from taxi_bot.database_handler import DataBase
from taxi_bot.load_config import Config
from taxi_bot.logger import Logger
from taxi_bot.buttons import keyboard_generator


class BaseHandler:

    def __init__(
            self, 
            db: DataBase, 
            bot: Bot, 
            config: Config, 
            kbs: dict,
            logger: Logger,
        ):
        self._db = db
        self._bot = bot
        self._config = config
        self._kbs = kbs
        self._logger = logger

    @abstractmethod
    async def __call__(self, *args, **kwargs):
        raise NotImplementedError

    async def set_state(self, state, field, value):
        async with state.proxy() as data:
            data[field] = value

    async def update_state(self, state, field, value):
        try:
            async with state.proxy() as data:
                data[field] = data[field] + value
        except KeyError:
            return 

    async def get_state(self, state, field):
        try:
            async with state.proxy() as data:
                value = data[field]
            return value
        except KeyError:
            return 

    async def create_user(self, message):
        phone_number = self._db.create_user(message)
        if not phone_number:
            user_id = message.from_user.id
            message = await self._bot.send_message(
                chat_id=user_id,
                text="Пожалуйста, оставьте свой номер телефона для связи, нажав кнопку 'Оставить свой контакт'",
                reply_markup=self._kbs['request_contact']
            )
            self._db.create_order_message(-1, user_id, message.message_id)
        return phone_number

    async def show_order(self, order, driver_id, keyboard=True):
        lat, lon = order.location_from.split('|')
        order_id = order.order_id
        title = order.location_to
        address = f"{order.price} рублей"
        keyboard = keyboard_generator(self._config.buttons['driver_accept_refuse'], order_id) if keyboard else None
        message = await self._bot.send_venue(
            chat_id=driver_id,
            latitude=lat,
            longitude=lon,
            title=title,
            address=address,
            reply_markup=keyboard,
        )
        self._db.create_order_message(order_id, driver_id, message.message_id)

    async def show_active_orders(self, driver_id):
        active_orders = self._db.get_orders(100)
        if active_orders:
            message = await self._bot.send_message(
                chat_id=driver_id,
                text=f'Новые заказы:'
            )
            self._db.create_order_message(-1, driver_id, message.message_id)
        for order in active_orders:
            await self.show_order(order, driver_id)

    async def delete_old_messages(self, order_id=None, chat_id=None):
        if order_id:
            orders = self._db.get_order_messages(order_id=order_id)
        if chat_id:
            orders = self._db.get_order_messages(chat_id=chat_id)
        log_ids = list()
        for order in orders:
            log_id, chat_id, message_id = order.log_id, order.chat_id, order.message_id
            try:
                await self._bot.delete_message(chat_id, message_id)
            except:
                pass
            log_ids.append(log_id)
        self._db.delete_order_message(log_ids)

    def time_handler(self, dt1, dt2):
        if dt1 == dt2:
            return
        dt = (dt1 - dt2).seconds
        hours = str(dt//3600).zfill(2)
        minutes = str(dt%3600//60).zfill(2)
        seconds = str(dt%60).zfill(2)
        return f"{hours}:{minutes}:{seconds}"