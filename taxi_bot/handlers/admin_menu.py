from aiogram import types
from taxi_bot.handlers.base_handler import BaseHandler
from taxi_bot.database_handler import DataBase
from aiogram import Bot
from taxi_bot.load_config import Config
from taxi_bot.logger import Logger
from taxi_bot.buttons import keyboard_generator
from aiogram.types import ReplyKeyboardRemove
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import re 


class AdminBaseHandler(BaseHandler):

    def __init__(
            self, 
            db: DataBase, 
            bot: Bot, 
            config: Config, 
            kbs: dict,
            logger: Logger,
        ):
        super().__init__(db, bot, config, kbs, logger)


class AdminMenu(AdminBaseHandler):

    async def __call__(self, message: types.Location) -> None: 
        chat_id = message.from_user.id
        text = 'Админское меню'
        await self.send_message(chat_id, -1, text, 'admin_menu')


class DriversStatus(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None: 
        
        chat_id = callback_query.from_user.id
        text = list()
        statuses = {50:0, 100:0, 150:0}
        status_mapper = {50:'🔴', 100:'🟢', 150:'🟡'}
        drivers = self._db.get_drivers()
        drivers.sort(key=lambda v: v.driver_status, reverse=True)
        for driver in drivers:
            driver_status = driver.driver_status
            first_name = driver.first_name[:10]
            user_id = driver.user_id
            driver_car = driver.driver_car[:15]
            phone_number = driver.phone_number
            text.append(f'{status_mapper[driver_status]} {self.tg_user_link(user_id, first_name)} {driver_car} {phone_number}')
            statuses[driver_status] += 1
        offline, online, busy = statuses[50], statuses[100], statuses[150]
        text = [
            f'Свободных водителей: {online}',
            f'На заказах: {busy}'
        ] + text
        text = '\n'.join(text)
        await self.send_message(chat_id, -1, text)
        await self._bot.answer_callback_query(callback_query.id)
