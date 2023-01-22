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

    async def __call__(self, message: types.Message) -> None: 
        chat_id = message.from_user.id
        self.log_message(chat_id, message.message_id, -1, self, '/admin')
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
            text.append(f'{status_mapper[driver_status]} {self.tg_user_link(user_id, first_name)} {phone_number} {driver_car}')
            statuses[driver_status] += 1
        offline, online, busy = statuses[50], statuses[100], statuses[150]
        text = [
            f'🟢Свободных водителей: {online}',
            f'🟡На заказах: {busy}',
            '----------------'
        ] + text
        text = '\n'.join(text)
        await self.send_message(chat_id, -1, text)
        await self._bot.answer_callback_query(callback_query.id)


class InviteBroadcastMessage(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        await self.send_message(callback_query.from_user.id, -1, 'Введите текст сообщения:', 'broadcast_cancel')
        await InputMessage.invite_input.set()
        await self._bot.answer_callback_query(callback_query.id)


class CheckBroadcastMessage(AdminBaseHandler):

    async def __call__(self, message: types.Message, state:FSMContext) -> None:
        text = message.text
        self.log_message(message.from_user.id, message.message_id, -1, self, text)
        await self.set_state(state, 'message', text)
        await InputMessage.next()
        await self.send_message(message.from_user.id, -1, text, 'broadcast_message')


class BroadcastMessage(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        text = await self.get_state(state, 'message')
        target = callback_query.data.split('@')[-1]
        if target == 'Moders':
            users_id = self._config.MODER_IDs
        else:
            users_id = [user.user_id for user in self._db.get_group(target[-1]).all()]
        await self.delete_old_messages(message_id=callback_query.message.message_id)
        for user_id in users_id:
            await self.send_message(user_id, -1, text, 'hide_message')
        await state.finish()
        await self._bot.answer_callback_query(callback_query.id)


class CancelBroadcast(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        chat_id = callback_query.from_user.id
        await self.send_message(chat_id, -1, '/admin')
        await self.delete_old_messages(chat_id=chat_id)
        await self._bot.answer_callback_query(callback_query.id)
        current_state = await state.get_state()
        if current_state is None:
            return
        await state.finish()
