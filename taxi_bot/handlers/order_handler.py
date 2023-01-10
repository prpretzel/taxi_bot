from aiogram import types
from taxi_bot.handlers.base_handler import BaseHandler
from taxi_bot.database_handler import DataBase
from aiogram import Bot
from taxi_bot.load_config import Config
from taxi_bot.logger import Logger
from taxi_bot.buttons import keyboard_generator

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

class OrderForm(StatesGroup):
    order_id = State()
    location_from = State()
    location_to = State()
    price = State()


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
        passenger_id = message.from_user.id
        active_order = self._db.get_user_active_order(passenger_id)
        if active_order:
            order_id = active_order.order_id
            self._db.create_order_message(order_id, passenger_id, message.message_id)
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
        await self.set_state(state, 'order_id', order_id)
        await OrderForm.location_from.set()
        message = await self._bot.send_message(
            chat_id=passenger_id,
            text="Куда вы хотите ехать?",
            reply_markup=keyboard_generator(self._config.buttons['passenger_cancel'], order_id),
        )
        self._db.create_order_message(order_id, passenger_id, message.message_id)


class NewOrderTo(OrderBaseHandler):

    async def __call__(self, message: types.Message, state=FSMContext) -> None:
        passenger_id = message.from_user.id
        order_id = await self.get_state(state, 'order_id')
        location_to = message.text
        self._db.create_order_message(order_id, passenger_id, message.message_id)
        self._db.update_order_location_to(order_id, location_to)
        await OrderForm.next()
        message = await self._bot.send_message(
            chat_id=passenger_id,
            text="Укажите Вашу цену:",
            reply_markup=keyboard_generator(self._config.buttons['passenger_cancel'], order_id),
        )
        self._db.create_order_message(order_id, passenger_id, message.message_id)


class NewOrderPrice(OrderBaseHandler):

    async def __call__(self, message: types.Message, state=FSMContext) -> None:
        passenger_id = message.from_user.id
        order_id = await self.get_state(state, 'order_id')
        self._db.create_order_message(order_id, passenger_id, message.message_id)
        price = message.text
        self._db.update_order_price(order_id, price)
        await state.finish()
        message = await self._bot.send_message(
            chat_id=passenger_id,
            text="Идет поиск машины...",
            reply_markup=keyboard_generator(self._config.buttons['passenger_cancel'], order_id),
        )
        self._db.create_order_message(order_id, passenger_id, message.message_id)
        order = self._db.get_order_by_id(order_id)
        for dr in self._db.get_drivers_id(100):
            await self.show_order(order=order, driver_id=dr)


class DriverAccept(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = callback_query.data.split('@')[-1]
        driver_id = callback_query.from_user.id
        self._db.update_driver_status(driver_id, 150)
        await self.delete_old_messages(order_id)
        order = self._db.get_order_by_id(order_id)
        await self.show_order(order, driver_id, keyboard=False)
        passenger_phone_number = self._db.get_passenger_by_id(order.passenger_id).phone_number
        message = await callback_query.message.answer(
            text=f'Ваш заказ #{order_id}\nТелефон для связи с пассажиром {passenger_phone_number}',
            reply_markup=keyboard_generator(self._config.buttons['driver_cancel_wait_pick'], order_id),
        )
        self._db.create_order_message(order_id, driver_id, message.message_id)
        new_status = 200
        driver_info = self._db.get_driver_by_id(driver_id)
        driver_name = driver_info.first_name
        driver_car = driver_info.driver_car
        driver_phone_number = driver_info.phone_number
        passenger_id, _ = self._db.update_order(order_id, new_status, driver_id)
        message = await self._bot.send_message(
            chat_id=passenger_id,
            text=f"Машина найдена. Ваш водитель, {driver_name}, приедет на {driver_car}\nТелефон для связи с водителем {driver_phone_number}",
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
        print(order_id)
        self._db.update_wait_dt(order_id)
        new_status = 250
        driver_id = callback_query.from_user.id
        passenger_id, _ = self._db.update_order(order_id, new_status, driver_id)
        message = await self._bot.send_message(chat_id=passenger_id, text=f"Водитель ожидает")
        self._db.create_order_message(order_id, passenger_id, message.message_id)
        await self._bot.answer_callback_query(callback_query.id)


class DriverPick(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = callback_query.data.split('@')[-1]
        self._db.update_pick_dt(order_id)
        new_status = 300
        driver_id = callback_query.from_user.id
        self._db.update_order(order_id, new_status, driver_id)
        message = await callback_query.message.edit_reply_markup(keyboard_generator(self._config.buttons['driver_complete'], order_id))
        self._db.create_order_message(order_id, driver_id, message.message_id)
        await self._bot.answer_callback_query(callback_query.id)


class DriverComplete(OrderBaseHandler):

    def time_handler(self, dt1, dt2):
        if dt1 != dt2:
            dt = (dt1 - dt2).seconds
            hours = str(dt//3600).zfill(2)
            minutes = str(dt//60).zfill(2)
            seconds = str(dt%60).zfill(2)
            return f"{hours}:{minutes}:{seconds}"
        return
        

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = callback_query.data.split('@')[-1]
        self._db.update_end_dt(order_id)
        order = self._db.get_order_by_id(order_id)
        dt1 = order.order_dt
        dt2 = order.wait_dt if order.wait_dt else order.pick_dt
        dt3 = order.pick_dt
        dt4 = order.end_dt
        driver_arrival = "Время ожидания такси: ", self.time_handler(dt2, dt1)
        driver_wait = "Время ожидания пассажира: ", self.time_handler(dt3, dt2)
        travel_time = "Поездка заняла: ", self.time_handler(dt4, dt3)
        add_text = [f"{text} {delta}" for text, delta in [driver_arrival, driver_wait, travel_time] if delta]
        add_text = "\n"+"\n".join(add_text)
        new_status = 400
        driver_id = callback_query.from_user.id
        self._db.update_driver_status(driver_id, 100)
        passenger_id, _ = self._db.update_order(order_id, new_status, driver_id)
        await self.delete_old_messages(order_id)
        await self._bot.send_message(chat_id=passenger_id, text=f"Поездка завершена (пассажир){add_text}")
        await self._bot.send_message(chat_id=driver_id, text=f"Поездка завершена (водитель){add_text}")
        await self.show_active_orders(driver_id)
        await self._bot.answer_callback_query(callback_query.id)


class DriverCancel(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        order_id = callback_query.data.split('@')[-1]
        await self.delete_old_messages(order_id)
        new_status = 150
        passenger_id, driver_id = self._db.update_order(order_id, new_status)
        self._db.update_driver_status(driver_id, 100)
        self._db.update_cancel_dt(order_id)
        await self._bot.send_message(chat_id=passenger_id, text=f"Водитель отменил поездку")
        await self._bot.send_message(chat_id=driver_id, text=f"Вы отменили поездку")
        await self.show_active_orders(driver_id)
        await self._bot.answer_callback_query(callback_query.id)


class PassengerCancel(OrderBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        order_id = callback_query.data.split('@')[-1]
        await self.delete_old_messages(order_id=order_id)
        new_status = 50
        passenger_id, driver_id = self._db.update_order(order_id, new_status)
        self._db.update_cancel_dt(order_id)
        await self._bot.send_message(chat_id=passenger_id, text=f"Вы отменили поездку")
        if driver_id:
            await self._bot.send_message(chat_id=driver_id, text=f"Пользователь отменил поездку")
            self._db.update_driver_status(driver_id, 100)
        await self.show_active_orders(driver_id)
        current_state = await state.get_state()
        await self._bot.answer_callback_query(callback_query.id)
        if current_state is None:
            return
        await state.finish()
        