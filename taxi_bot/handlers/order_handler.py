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


class NewOrderFrom(OrderBaseHandler):

    async def __call__(self, message: types.Location, state:FSMContext) -> None: 
        if not await self.create_user(message):
            return
        passenger_id = message.from_user.id
        await self.delete_old_messages(chat_id=passenger_id)
        active_order = self._db.get_user_active_order(passenger_id)
        if active_order:
            order_id = active_order.order_id
            await self.delete_old_messages(order_id=order_id)
            await self.show_order(active_order, passenger_id, keyboard=False)
            text = f"Мы все еще ищем Вам машину...\nВодителей на линии: {self._db.get_available_drivers_count()}"
            await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
            self.log_message(passenger_id, message.message_id, order_id, self, f'active_order')
            return
        
        location_from = f'{message.location.latitude}|{message.location.longitude}'
        order_id = self._db.create_order(passenger_id, location_from)
        self.log_message(passenger_id, message.message_id, order_id, self, f'location_from: {location_from}')
        message = await self._bot.send_message(passenger_id, "msg_text", reply_markup=ReplyKeyboardRemove())
        await message.delete()
        text = "Куда вы хотите ехать?"
        message = await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
        await self.set_state(state, 'order_id', order_id)
        await self.set_state(state, 'previous_message', message)
        await OrderForm.location_from.set()


class NewOrderTo(OrderBaseHandler):

    async def __call__(self, message: types.Message, state=FSMContext) -> None:
        passenger_id = message.from_user.id
        order_id = await self.get_state(state, 'order_id')
        previous_message = await self.get_state(state, 'previous_message')
        await self.remove_reply_markup(previous_message, order_id)
        location_to = message.text
        self.log_message(passenger_id, message.message_id, order_id, self, f'location_to: {location_to}')
        self._db.update_order_location_to(order_id, location_to)
        await OrderForm.next()
        text = "Укажите Вашу цену:"
        message = await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
        await self.set_state(state, 'previous_message', message)


class NewOrderPrice(OrderBaseHandler):

    async def __call__(self, message: types.Message, state=FSMContext) -> None:
        passenger_id = message.from_user.id
        order_id = await self.get_state(state, 'order_id')
        previous_message = await self.get_state(state, 'previous_message')
        await self.remove_reply_markup(previous_message, order_id)
        price = message.text
        if re.match('^\d+$', price):
            self.log_message(passenger_id, message.message_id, order_id, self, f'price: {price}')
            self._db.update_order_price(order_id, price)
            await state.finish()
            await self.delete_old_messages(chat_id=passenger_id)
            order = self._db.get_order_by_id(order_id)
            await self.show_order(order=order, chat_id=passenger_id, keyboard=False)
            for chat_id in self._db.get_drivers_id(100):
                await self.show_order(order=order, chat_id=chat_id)
            text = f"Идет поиск машины...\nВодителей на линии: {self._db.get_available_drivers_count()}"
            message = await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
        else:
            self.log_message(passenger_id, message.message_id, order_id, self, f'price_input_error: {price}')
            text="Введите стоимость поездки в рублях (например 250)"
            message = await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
        await self.set_state(state, 'previous_message', message)


class DriverAccept(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        if not await self.create_user(callback_query):
            return
        driver_id = callback_query.from_user.id
        driver = self._db.get_user_by_id(driver_id)
        driver_name = driver.first_name
        driver_car = driver.driver_car
        driver_phone_number = driver.phone_number
        order_id = int(callback_query.data.split('@')[-1])
        await self.remove_reply_markup(callback_query, order_id)
        order = self._db.get_order_by_id(order_id)
        passenger_id = order.passenger_id
        passenger_phone_number = self._db.get_user_by_id(passenger_id).phone_number
        self._db.update_driver_status(driver_id, 150)
        self._db.update_order_driver(order_id, driver_id)
        await self.delete_old_messages(order_id=order_id)
        await self.show_order(order, passenger_id, keyboard=False)
        await self.show_order(order, driver_id, keyboard=False)
        text = f'Ваш заказ #{order_id}\nТелефон для связи с пассажиром {passenger_phone_number}'
        message = await callback_query.message.answer(
            text=text,
            reply_markup=keyboard_generator(self._config.buttons['driver_cancel_wait'], order_id),
        )
        self.log_message(driver_id, message.message_id, order_id, self, text)
        text = f"Машина найдена. Ваш водитель, {driver_name}, приедет на {driver_car}\nТелефон для связи с водителем {driver_phone_number}"
        await self.send_message(passenger_id, order_id, text, 'passenger_cancel')
        await self._bot.answer_callback_query(callback_query.id)


class DriverRefuse(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = int(callback_query.data.split('@')[-1])
        chat_id = callback_query.from_user.id
        await self.delete_old_messages(chat_id=chat_id, order_id=order_id)
        self.log_info(callback_query.from_user.id, callback_query.message.message_id, order_id, self, 'hide_order')
        await self._bot.answer_callback_query(callback_query.id)


class DriverWait(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = int(callback_query.data.split('@')[-1])
        order = self._db.update_wait_dt(order_id)
        await self.edit_reply_markup(callback_query, 'driver_cancel_pick', order_id)
        await self.send_message(order.passenger_id, order_id, text=f"Водитель ожидает")
        await self._bot.answer_callback_query(callback_query.id)


class DriverPick(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = int(callback_query.data.split('@')[-1])
        self._db.update_pick_dt(order_id)
        await self.edit_reply_markup(callback_query, 'driver_complete', order_id)
        await self._bot.answer_callback_query(callback_query.id)


class DriverComplete(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = int(callback_query.data.split('@')[-1])
        order = self._db.get_order_by_id(order_id)
        self._db.update_end_dt(order_id)
        dt1 = order.order_dt
        dt2 = order.wait_dt
        dt3 = order.pick_dt
        dt4 = order.end_dt
        driver_arrival = "Время ожидания такси: ", self.time_handler(dt2, dt1)
        driver_wait = "Время ожидания пассажира: ", self.time_handler(dt3, dt2)
        travel_time = "Поездка заняла: ", self.time_handler(dt4, dt3)
        add_text = [f"{text} {delta}" for text, delta in [driver_arrival, driver_wait, travel_time] if delta]
        add_text = "\n"+"\n".join(add_text)
        driver_id = callback_query.from_user.id
        self._db.driver_complete_trip(driver_id, order.price)
        self._db.update_end_dt(order_id)
        await self.delete_old_messages(order_id)
        await self.send_message(chat_id=order.passenger_id, order_id=order_id, text=f"Поездка завершена (пассажир){add_text}", kb_name='passenger_call_taxi')
        await self.send_message(chat_id=driver_id, order_id=order_id, text=f"Поездка завершена (водитель){add_text}")
        await self.show_active_orders(driver_id)
        await self._bot.answer_callback_query(callback_query.id)


class DriverCancel(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = int(callback_query.data.split('@')[-1])
        order = self._db.update_order(order_id, 150)
        await self.delete_old_messages(order_id)
        passenger_id, driver_id = order.passenger_id, order.driver_id
        self._db.update_driver_status(driver_id, 100)
        self._db.update_cancel_dt(order_id)
        await self.send_message(chat_id=passenger_id, order_id=order_id, text=f"Водитель отменил поездку", kb_name='passenger_call_taxi')
        await self.send_message(chat_id=driver_id, order_id=order_id, text=f"Вы отменили поездку")
        await self.show_active_orders(driver_id)
        await self._bot.answer_callback_query(callback_query.id)


class PassengerCancel(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        order_id = int(callback_query.data.split('@')[-1])
        await self.delete_old_messages(order_id=order_id)
        order = self._db.update_order(order_id, 50)
        passenger_id, driver_id = order.passenger_id, order.driver_id
        self._db.update_cancel_dt(order_id)
        await self.send_message(chat_id=passenger_id, order_id=order_id, text=f"Вы отменили поездку", kb_name='passenger_call_taxi')
        if driver_id:
            await self.send_message(chat_id=driver_id, order_id=order_id, text=f"Пользователь отменил поездку")
            self._db.update_driver_status(driver_id, 100)
            await self.show_active_orders(driver_id)
        current_state = await state.get_state()
        await self._bot.answer_callback_query(callback_query.id)
        if current_state is None:
            return
        await state.finish()
        