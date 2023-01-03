from aiogram import types
from taxi_bot.handlers.base_handler import BaseHandler
from taxi_bot.database_handler import DataBase
from aiogram import Bot
from taxi_bot.load_config import Config
from taxi_bot.logger import Logger
from taxi_bot.buttons import keyboard_generator

class OrderBaseHandler(BaseHandler):

    def __init__(
            self, 
            db: DataBase, 
            bot: Bot, 
            config: Config, 
            kbs: dict,
            logger: Logger,
        ):
        super().__init__(db, bot, config, kbs, logger)

    async def delete_old_messages(self, order_id):
        for chat_id, message_id in self._db.get_order_messages(order_id):
            try:
                await self._bot.delete_message(chat_id, message_id)
            except:
                pass


class NewOrder(OrderBaseHandler):

    async def __call__(self, message: types.Location) -> None:
        passenger_id = message.from_user.id
        active_order = self._db.get_order_user_active_order(passenger_id)
        if active_order:
            order_id = active_order.order_id
            message = await self._bot.send_message(
                chat_id=passenger_id,
                text="Мы все еще ищем Вам машину...",
                reply_markup=keyboard_generator(self._config.buttons['passenger_cancel'], order_id),
            )
            self._db.create_order_message(order_id, passenger_id, message.message_id)
            return
        lat = str(message.location.latitude)
        lon = str(message.location.longitude)
        location_from = lat + "|" + lon
        order_id = self._db.create_order(passenger_id, location_from)
        self._db.create_order_message(order_id, passenger_id, message.message_id)
        for dr in self._db.get_drivers_id(100):
            message = await self._bot.send_location(
                chat_id=dr,
                latitude=lat,
                longitude=lon,
                reply_markup=keyboard_generator(self._config.buttons['driver_accept_refuse'], order_id),
            )
            self._db.create_order_message(order_id, dr, message.message_id)
        message = await self._bot.send_message(
            chat_id=passenger_id,
            text="Идет поиск машины...",
            reply_markup=keyboard_generator(self._config.buttons['passenger_cancel'], order_id),
        )
        self._db.create_order_message(order_id, passenger_id, message.message_id)


class DriverAccept(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = callback_query.data.split('@')[-1]
        driver_id = callback_query.from_user.id
        self._db.update_driver_status(driver_id, 150)
        for chat_id, message_id in self._db.get_order_messages(order_id):
            try:
                if chat_id != callback_query.from_user.id:
                    await self._bot.delete_message(chat_id, message_id)
            except:
                self._db.create_order_message(order_id, driver_id, callback_query.message.message_id)

        order_info = self._db.get_order_by_id(order_id)
        passenger_phone_number = self._db.get_passenger_by_id(order_info.passenger_id).phone_number
        message = await callback_query.message.answer(
            text=f'Ваш заказ #{order_id}\nТелефон для связи с пассажиром {passenger_phone_number}',
            reply_markup=keyboard_generator(self._config.buttons['driver_cancel_wait_pick'], order_id),
        )
        self._db.create_order_message(order_id, driver_id, message.message_id)
        new_status = 200
        driver_info = self._db.get_driver_by_id(driver_id)
        driver_car = driver_info.driver_car
        driver_phone_number = driver_info.phone_number
        passenger_id, _ = self._db.update_order(order_id, new_status, driver_id)
        message = await self._bot.send_message(
            chat_id=passenger_id,
            text=f"Машина найдена. Ваш водитель приедет на {driver_car}\nТелефон для связи с водителем {driver_phone_number}",
            reply_markup=keyboard_generator(self._config.buttons['passenger_cancel'], order_id),
        )
        self._db.create_order_message(order_id, passenger_id, message.message_id)
        await self._bot.answer_callback_query(callback_query.id)


class DriverRefuse(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        await self._bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)
        await self._bot.answer_callback_query(callback_query.id)


class DriverWait(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = callback_query.data.split('@')[-1]
        new_status = 250
        driver_id = callback_query.from_user.id
        passenger_id, _ = self._db.update_order(order_id, new_status, driver_id)
        message = await self._bot.send_message(chat_id=passenger_id, text=f"Водитель ожидает")
        self._db.create_order_message(order_id, passenger_id, message.message_id)
        await self._bot.answer_callback_query(callback_query.id)


class DriverPick(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = callback_query.data.split('@')[-1]
        new_status = 300
        driver_id = callback_query.from_user.id
        self._db.update_order(order_id, new_status, driver_id)
        message = await callback_query.message.edit_reply_markup(keyboard_generator(self._config.buttons['driver_complete'], order_id))
        self._db.create_order_message(order_id, driver_id, message.message_id)
        await self._bot.answer_callback_query(callback_query.id)


class DriverComplete(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = callback_query.data.split('@')[-1]
        new_status = 400
        driver_id = callback_query.from_user.id
        self._db.update_driver_status(driver_id, 100)
        passenger_id, _ = self._db.update_order(order_id, new_status, driver_id)
        await self.delete_old_messages(order_id)
        message = await self._bot.send_message(chat_id=passenger_id, text=f"Поездка завершена (пассажир)")
        self._db.create_order_message(order_id, passenger_id, message.message_id)
        message = await self._bot.send_message(chat_id=driver_id, text=f"Поездка завершена (водитель)")
        self._db.create_order_message(order_id, driver_id, message.message_id)
        await self._bot.answer_callback_query(callback_query.id)


class DriverCancel(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = callback_query.data.split('@')[-1]
        await self.delete_old_messages(order_id)
        new_status = 150
        passenger_id, driver_id = self._db.update_order(order_id, new_status)
        self._db.update_driver_status(driver_id, 100)
        await self._bot.send_message(chat_id=passenger_id, text=f"Водитель отменил поездку")
        await self._bot.send_message(chat_id=driver_id, text=f"Вы отменили поездку")
        await self._bot.answer_callback_query(callback_query.id)


class PassengerCancel(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = callback_query.data.split('@')[-1]
        await self.delete_old_messages(order_id)
        new_status = 50
        passenger_id, driver_id = self._db.update_order(order_id, new_status)
        await self._bot.send_message(chat_id=passenger_id, text=f"Вы отменили поездку")
        if driver_id:
            await self._bot.send_message(chat_id=driver_id, text=f"Пользователь отменил поездку")
            self._db.update_driver_status(driver_id, 100)
        await self._bot.answer_callback_query(callback_query.id)
