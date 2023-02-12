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

class OrderForm(StatesGroup):
    order_id = State()
    location_from = State()
    location_to = State()
    price = State()
    previous_message = State()


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
        

class NewOrder(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state:FSMContext) -> None: 
        if not await self.create_user(callback_query):
            await self.answer_callback_query(callback_query)
            return
        await OrderForm.order_id.set()
        passenger_id, message_id, order_id, optionals = self.message_data(callback_query)
        active_order = self._db.get_user_active_order(passenger_id)
        if active_order:
            order_id = active_order.order_id
            await self.show_order(active_order, passenger_id)
            text = f"Мы все еще ищем Вам машину...\nВодителей на линии: {self._db.get_available_drivers_count()}"
            await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
        else:
            order_id = self._db.create_order(passenger_id)
            await self.send_message(passenger_id, order_id, "Отправьте сообщение с местом, откуда Вас нужно забрать", 'passenger_send_location', delete_old=True)
            message = await self.send_message(passenger_id, order_id, "Или нажмите кнопку '🧭Отправить геопозицию'", 'passenger_cancel')
            await self.set_state(state, 'order_id', order_id)
            await self.set_state(state, 'previous_message', message)
        await self.answer_callback_query(callback_query)
        

class NewOrderFrom(OrderBaseHandler):

    async def __call__(self, message: types.Location, state:FSMContext) -> None: 
        order_id = await self.get_state(state, 'order_id')
        passenger_id, message_id, order_id, optionals = self.message_data(message, order_id)
        previous_message = await self.get_state(state, 'previous_message')
        await self.remove_inline_markup(previous_message, order_id)
        location_from = optionals['location'] if 'location' in optionals else optionals['text']
        if len(location_from) > 120:
            text = "Краткость - сестра таланта 😉"
            message = await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
            return
        self._db.update_order_location_from(order_id, location_from)
        await self.set_state(state, 'location_from', location_from)
        await self.discard_reply_markup(passenger_id, order_id)
        text = "Куда Вы хотите ехать?"
        message = await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
        await self.set_state(state, 'previous_message', message)
        await OrderForm.next()


class NewOrderToText(OrderBaseHandler):

    async def __call__(self, message: types.Message, state=FSMContext) -> None:
        order_id = await self.get_state(state, 'order_id')
        passenger_id, message_id, order_id, optionals = self.message_data(message, order_id)
        previous_message = await self.get_state(state, 'previous_message')
        await self.remove_inline_markup(previous_message, order_id)
        location_to = optionals['location'] if 'location' in optionals else optionals['text']
        if len(location_to) > 120:
            text = "Краткость - сестра таланта 😉"
            message = await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
            return
        self._db.update_order_location_to(order_id, location_to)
        text = "Укажите Вашу цену:"
        message = await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
        await self.set_state(state, 'previous_message', message)
        await OrderForm.next()


class NewOrderPrice(OrderBaseHandler):

    async def __call__(self, message: types.Message, state=FSMContext) -> None:
        order_id = await self.get_state(state, 'order_id')
        passenger_id, message_id, order_id, optionals = self.message_data(message, order_id)
        previous_message = await self.get_state(state, 'previous_message')
        await self.remove_inline_markup(previous_message, order_id)
        price = optionals['text']
        if re.match('^\d{1,10}$', price):
            self._db.update_order_price(order_id, price)
            await state.finish()
            order = self._db.get_order_by_id(order_id)
            await self.show_order(order=order, chat_id=passenger_id, delete_old=True)
            for chat_id in self._db.get_drivers_id(100):
                await self.show_order(order=order, chat_id=chat_id, kb_name='driver_accept_refuse')
            await self.show_admin_order(order)
            text = f"Идет поиск машины...\nВодителей на линии: {self._db.get_available_drivers_count()}"
            message = await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
        else:
            text = "Введите стоимость поездки в рублях (например 250)"
            message = await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
        await self.set_state(state, 'previous_message', message)


class DriverAccept(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        if not await self.create_user(callback_query):
            return
        driver_id, message_id, order_id, optionals = self.message_data(callback_query)
        if not self._db.update_order_driver(order_id, driver_id):
            await self.send_message(driver_id, order_id, 'Заказ был принят другим водителем')
            return
        driver = self._db.get_user_by_id(driver_id)
        driver_name = driver.first_name
        driver_car = driver.driver_car
        driver_phone_number = driver.phone_number
        order = self._db.get_order_by_id(order_id)
        passenger_id = order.passenger_id
        passenger_phone_number = self._db.get_user_by_id(passenger_id).phone_number
        self._db.update_driver_status(driver_id, 150)
        await self.show_order(order, passenger_id, delete_old=True)
        await self.show_order(order, driver_id)
        text = f"Ваш заказ #{order_id}\nТелефон для связи с пассажиром {passenger_phone_number}\nЧат с пассажиром: {self.tg_user_link(passenger_id, 'Открыть чат')}"
        await self.send_message(driver_id, order_id, text, 'driver_cancel_wait')
        text = f"Машина найдена. Ваш водитель, {driver_name}, приедет на {driver_car}\nТелефон для связи с водителем {driver_phone_number}"
        await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
        await self.answer_callback_query(callback_query)


class DriverHide(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id, message_id, order_id, optionals = self.message_data(callback_query)
        await self.delete_old_messages(message_id=message_id, force=True)
        await self.answer_callback_query(callback_query)


class DriverReturn(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id, message_id, order_id, optionals = self.message_data(callback_query)
        order = self._db.update_order_driver_none(order_id, driver_id)
        passenger_id = order.passenger_id
        self._db.update_order_status(order_id, 100)
        self._db.update_driver_status(driver_id, 100)
        await self.show_order(order=order, chat_id=passenger_id, delete_old=True)
        text = f"Мы продолжаем искать Вам машину"
        await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
        for chat_id in self._db.get_drivers_id(100):
            await self.show_order(order=order, chat_id=chat_id, kb_name='driver_accept_refuse')
        await self.answer_callback_query(callback_query)


class DriverWait(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id, message_id, order_id, optionals = self.message_data(callback_query)
        order = self._db.update_wait_dt(order_id)
        await self.send_message(order.passenger_id, order_id, text=f"Водитель ожидает\nВремя бесплатного ожидания 10 минут")
        await self.edit_message(driver_id, message_id, order_id, kb_name='driver_cancel_pick')
        await self.answer_callback_query(callback_query)


class DriverPick(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id, message_id, order_id, optionals = self.message_data(callback_query)
        order = self._db.update_pick_dt(order_id)
        await self.send_message(order.passenger_id, order_id, text=f"Начало поездки")
        await self.edit_message(driver_id, message_id, order_id, kb_name='driver_complete')
        await self.answer_callback_query(callback_query)


class DriverComplete(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id, message_id, order_id, optionals = self.message_data(callback_query)
        order = self._db.get_order_by_id(order_id)
        passenger_id = order.passenger_id
        self._db.update_end_dt(order_id)
        self._db.driver_complete_trip(driver_id, order.price)
        dt1 = order.order_dt
        dt2 = order.wait_dt
        dt3 = order.pick_dt
        dt4 = order.end_dt
        end_trip_text = [
            f"Поездка завершена",
            f"Время ожидания такси: {self.time_handler(dt2, dt1)}",
            f"Время ожидания пассажира: {self.time_handler(dt3, dt2)}",
            f"Поездка заняла: {self.time_handler(dt4, dt3)}",
            f"Стоимость поездки: {order.price} рублей",
        ]
        end_trip_text = "\n".join(end_trip_text)
        passenger_text = [
            end_trip_text,
            f"Расскажите о нас своим друзьям и получите возможность выиграть денежный приз!\nПодробности тут ➡️ /referral",
            f"Вы можете оставить отзыв о нашем такси в {self._config.BOT_SUPPORT}"
        ]
        passenger_text = "\n\n".join(passenger_text)
        await self.send_message(chat_id=passenger_id, order_id=order_id, text=passenger_text, kb_name='passenger_call_taxi', delete_old=True)
        await self.send_message(chat_id=driver_id, order_id=order_id, text=end_trip_text)
        await self.show_active_orders(driver_id)
        await self.answer_callback_query(callback_query)


class DriverCancel(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id, message_id, order_id, optionals = self.message_data(callback_query)
        order = self._db.update_cancel_dt(order_id)
        self._db.update_order_status(order_id, order.order_status+7)
        passenger_id = order.passenger_id
        self._db.update_driver_status(driver_id, 100)
        await self.send_message(chat_id=passenger_id, order_id=order_id, text=f"Водитель отменил поездку", kb_name='passenger_call_taxi', delete_old=True)
        await self.send_message(chat_id=driver_id, order_id=order_id, text=f"Вы отменили поездку")
        await self.show_active_orders(driver_id)
        await self.answer_callback_query(callback_query)
        

class PassengerCancel(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        passenger_id, message_id, order_id, optionals = self.message_data(callback_query)
        order = self._db.update_cancel_dt(order_id)
        self._db.update_order_status(order_id, order.order_status+3)
        driver_id = order.driver_id
        await self.send_message(chat_id=passenger_id, order_id=order_id, text=f"Вы отменили поездку", kb_name='passenger_call_taxi', delete_old=True)
        if driver_id:
            await self.send_message(chat_id=driver_id, order_id=order_id, text=f"Пользователь отменил поездку")
            self._db.update_driver_status(driver_id, 100)
            await self.show_active_orders(driver_id)
        if await state.get_state():
            await state.finish()
        await self.answer_callback_query(callback_query)
        