from aiogram import types
from taxi_bot.handlers.base_handler import BaseHandler
from taxi_bot.database_handler import DataBase
from aiogram import Bot
from taxi_bot.load_config import Config
from taxi_bot.logger import Logger
from taxi_bot.buttons import keyboard_generator


class DriverBaseHandler(BaseHandler):

    def __init__(
            self, 
            db: DataBase, 
            bot: Bot, 
            config: Config, 
            kbs: dict,
            logger: Logger,
        ):
        super().__init__(db, bot, config, kbs, logger)


class DriverMenu(DriverBaseHandler):

    async def __call__(self, message: types.Message) -> None:
        driver_id = message.from_user.id
        if driver_id in self._db.get_drivers_id():
            await self._bot.send_message(
                chat_id=driver_id,
                text='Меню водителя',
                reply_markup=self._kbs['driver_menu']
            )
        else:
            await self._bot.send_message(
                chat_id=driver_id,
                text='Для начала работы в такси напишите администратору'
            )


class DriverStatus(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id = callback_query.from_user.id
        driver_info = self._db.get_driver_by_id(driver_id)
        status = driver_info.driver_status
        if status==150:
            await self._bot.send_message(
                chat_id=driver_id,
                text='Завершите или отмените свой заказ',
            )
            await self._bot.answer_callback_query(callback_query.id)
            return

        data = callback_query.data
        if data == 'driver_start_work':
            new_status = 100 
            text = 'Вы начали свой рабочий день'
        elif data == 'driver_end_work':
            new_status = 50
            text = 'Вы закончили свой рабочий день'
        await self._bot.send_message(
            chat_id=driver_id,
            text=text,
        )
        self._db.update_driver_status(driver_id, new_status)
        await self._bot.answer_callback_query(callback_query.id)