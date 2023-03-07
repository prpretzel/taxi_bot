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
        chat_id, message_id, order_id, optionals = await self.message_data(callback_query)
        await self.edit_message(chat_id, message_id, order_id, 'Админское меню', 'admin_menu')


class ModerMenu(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None: 
        chat_id, message_id, order_id, optionals = await self.message_data(callback_query)
        await self.edit_message(chat_id, message_id, order_id, 'Меню модератора', 'moder_menu')


class DriversStatus(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None: 
        chat_id, message_id, order_id, optionals = await self.message_data(callback_query)
        text = list()
        statuses = {50:0, 100:0, 150:0, 30:0}
        status_mapper = {50:'🔴', 100:'🟢', 150:'🟡', 30:'❌'}
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
        await self.edit_message(chat_id, message_id, order_id, text, 'moder_menu')


class InviteBroadcastMessage(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        chat_id, message_id, order_id, optionals = await self.message_data(callback_query)
        await self.send_message(chat_id, order_id, 'Введите текст сообщения:', 'broadcast_cancel', delete_old=True)
        await InputMessage.invite_input.set()


class CheckBroadcastMessage(AdminBaseHandler):

    async def __call__(self, message: types.Message, state:FSMContext) -> None:
        chat_id, message_id, order_id, optionals = await self.message_data(message)
        await self.discard_reply_markup(chat_id, order_id)
        text = optionals['text']
        await self.set_state(state, 'message', text)
        await InputMessage.next()
        await self.send_message(chat_id, order_id, text, 'broadcast_message')


class BroadcastMessage(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        chat_id, message_id, order_id, optionals = await self.message_data(callback_query)
        text = await self.get_state(state, 'message')
        await self.edit_message(chat_id, message_id, order_id, text)
        target = callback_query.data.split('@')[-1]
        users_id = [user.user_id for user in self._db.get_group(target).all()]
        for user_id in users_id:
            await self.send_message(user_id, order_id, text, 'hide_message')
        await state.finish()


class CancelBroadcast(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        chat_id, message_id, order_id, optionals = await self.message_data(callback_query)
        await self.send_message(chat_id, order_id, 'Админское меню', 'admin_menu', delete_old=True)
        if await state.get_state():
            await state.finish()


class OrderDetails(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None: 
        chat_id, message_id, order_id, optionals = await self.message_data(callback_query)
        order = self._db.get_order_by_id(order_id)
        await self.show_admin_order(order, callback_query=callback_query)


class DeleteOldLogs(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        chat_id, message_id, order_id, optionals = await self.message_data(callback_query)
        self._db.delete_old_logs(expire_hours=1)


class UserInfo(AdminBaseHandler):

    async def __call__(self, message: types.Message, state:FSMContext) -> None: 
        chat_id, message_id, order_id, optionals = await self.message_data(message)
        try:
            user_id = int(optionals['text'].lower().replace('user', ''))
            await self.show_admin_user(user_id)
        except Exception as err:
            self.log_error(chat_id, message_id, order_id, self, f"{err} {optionals['text']}")


class BanDriver(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        chat_id, message_id, driver_id, optionals = await self.message_data(callback_query)
        driver = self._db.get_user_by_id(driver_id)
        driver_status = driver.driver_status
        if driver_status == 150:
            await self.send_message(self._config.ADMIN_ID, None, 'Водитель на заказе')
            return
        self._db.driver_end_shift(driver_id)
        self._db.update_driver_status(driver_id, 30)
        await self.send_message(self._config.ADMIN_ID, None, 'Водитель забанен')


class BanUser(AdminBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None:
        chat_id, message_id, user_id, optionals = await self.message_data(callback_query)
        pass


class OrderInfo(AdminBaseHandler):

    async def __call__(self, message: types.Message, state:FSMContext) -> None: 
        chat_id, message_id, order_id, optionals = await self.message_data(message)
        try:
            order_id = int(optionals['text'].lower().replace('order', ''))
            order = self._db.get_order_by_id(order_id)
            await self.show_admin_order(order)
        except Exception as err:
            self.log_error(chat_id, message_id, order_id, self, f"{err} {optionals['text']}")
            