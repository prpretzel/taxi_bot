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

class InputMessage(StatesGroup):
    invite_input = State()
    message = State()


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

    async def __call__(self, callback_query: types.CallbackQuery) -> None: 
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        kb_name = 'admin_menu' if chat_id==self._config.ADMIN_ID else 'moder_menu'
        await self.send_message(chat_id, order_id, 'Админское меню', kb_name)
        await self._bot.answer_callback_query(callback_query.id)


class DriversStatus(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None: 
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
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
            text.append(f'{status_mapper[driver_status]} {self.tg_user_link(user_id, first_name)} {phone_number} {driver_car}')
            statuses[driver_status] += 1
        offline, online, busy = statuses[50], statuses[100], statuses[150]
        text = [
            f'🟢Свободных водителей: {online}',
            f'🟡На заказах: {busy}',
            f'🔴Offline: {offline}',
            '----------------'
        ] + text
        text = '\n'.join(text)
        await self.send_message(chat_id, order_id, text, 'hide_message')
        await self._bot.answer_callback_query(callback_query.id)


class InviteBroadcastMessage(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        await self.delete_old_messages(chat_id=chat_id)
        await self.send_message(callback_query.from_user.id, order_id, 'Введите текст сообщения:', 'broadcast_cancel')
        await InputMessage.invite_input.set()
        await self._bot.answer_callback_query(callback_query.id)


class CheckBroadcastMessage(AdminBaseHandler):

    async def __call__(self, message: types.Message, state:FSMContext) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(message)
        await self.discard_reply_markup(chat_id, order_id)
        text = optionals['text']
        await self.set_state(state, 'message', text)
        await InputMessage.next()
        await self.send_message(chat_id, order_id, text, 'broadcast_message')


class BroadcastMessage(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        await self.delete_old_messages(chat_id=chat_id)
        text = await self.get_state(state, 'message')
        target = callback_query.data.split('@')[-1]
        users_id = [user.user_id for user in self._db.get_group(target).all()]
        for user_id in users_id:
            await self.send_message(user_id, order_id, text, 'hide_message')
        await state.finish()
        await self._bot.answer_callback_query(callback_query.id)


class CancelBroadcast(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        await self.delete_old_messages(chat_id=chat_id)
        kb_name = 'admin_menu' if chat_id==self._config.ADMIN_ID else 'moder_menu'
        await self.send_message(chat_id, order_id, 'Админское меню', kb_name)
        await self._bot.answer_callback_query(callback_query.id)
        if await state.get_state():
            await state.finish()


class DeleteOldLogs(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        self._db.delete_old_logs(expire_hours=1)
        