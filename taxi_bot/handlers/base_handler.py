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

    async def show_order(self, order, driver_id):
        lat, lon = order.location_from.split('|')
        order_id = order.order_id
        message = await self._bot.send_location(
            chat_id=driver_id,
            latitude=lat,
            longitude=lon,
            reply_markup=keyboard_generator(self._config.buttons['driver_accept_refuse'], order_id),
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

    async def delete_old_messages(self, order_id=None, driver_id=None):
        if order_id:
            orders = self._db.get_order_messages(order_id=order_id)
        if driver_id:
            orders = self._db.get_order_messages(chat_id=chat_id)
        for chat_id, message_id in orders:
            try:
                await self._bot.delete_message(chat_id, message_id)
            except:
                pass