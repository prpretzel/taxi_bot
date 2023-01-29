from abc import abstractmethod
from aiogram import Bot
from aiogram import types
from taxi_bot.database_handler import DataBase
from taxi_bot.load_config import Config
from taxi_bot.logger import Logger
from taxi_bot.buttons import keyboard_generator
from aiogram.types import ReplyKeyboardRemove


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

    async def set_state(self, state, field, value):
        async with state.proxy() as data:
            data[field] = value

    async def update_state(self, state, field, value):
        try:
            async with state.proxy() as data:
                data[field] = data[field] + value
        except KeyError:
            return 

    async def get_state(self, state, field):
        try:
            async with state.proxy() as data:
                value = data[field]
            return value
        except KeyError:
            return 

    async def create_user(self, message):
        phone_number = self._db.create_user(message)
        chat_id = message.from_user.id
        if not phone_number:
            text = "Пожалуйста, оставьте свой номер телефона для связи, нажав кнопку '📞Оставить свой контакт', чтобы водители могли позвонить Вам для уточнения информации по вашему заказу."
            await self.send_message(chat_id, None, text, 'request_contact')
        return phone_number

    async def show_order(self, order, chat_id, kb_name=None):
        import re
        order_id = order.order_id
        title = order.location_to
        address = f"{order.price} рублей"
        geo = re.match(r'\d{1,3}\.\d+|\d{1,3}\.\d+', order.location_from)
        if geo:
            lat, lon = order.location_from.split('|') 
            await self.send_venue(
                chat_id=chat_id,
                lat=lat, 
                lon=lon, 
                destination=title,
                price=address,
                order_id=order_id,
                kb_name=kb_name
            )
        else:
            text = [
                f"Откуда: {order.location_from}",
                f"Куда: {title}",
                f"Стоимость: {address}",
            ]
            text = '\n'.join(text)
            await self.send_message(chat_id, order_id, text, kb_name)

    async def show_active_orders(self, driver_id):
        active_orders = self._db.get_orders(100)
        # text = 'Новые заказы:' if active_orders else 'Новых заказов нет'
        # await self.send_message(driver_id, None, text)
        for order in active_orders:
            await self.show_order(order, driver_id, 'driver_accept_refuse')

    async def delete_old_messages(self, order_id=None, chat_id=None, message_id=None):
        orders = self._db.get_order_messages(order_id=order_id, chat_id=chat_id, message_id=message_id)
        for order in orders:
            chat_id, message_id, order_id = order.chat_id, order.message_id, order.order_id
            try:
                await self._bot.delete_message(chat_id, message_id)
            except Exception as err:
                self.log_error(chat_id, message_id, order_id, self, err)
        self._db.update_log_status(log_ids=[order.log_id for order in orders])

    def time_handler(self, dt1, dt2):
        if dt1 == dt2:
            return
        dt = (dt1 - dt2).seconds
        hours = str(dt//3600).zfill(2)
        minutes = str(dt%3600//60).zfill(2)
        seconds = str(dt%60).zfill(2)
        return f"{hours}:{minutes}:{seconds}"
    
    async def send_message(self, chat_id, order_id, text, kb_name=None):
        kb = keyboard_generator(self._config.buttons[kb_name], order_id) if kb_name else None
        try:
            message = await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=kb,
                parse_mode='html'
            )
            self.log_message(chat_id, message.message_id, order_id, self, text)
            return message
        except Exception as err:
            self.log_error(chat_id, None, order_id, self, err)

    async def edit_reply_markup(self, callback_query: types.CallbackQuery, kb_name, order_id):
        chat_id = callback_query.from_user.id
        try:
            message = await callback_query.message.edit_reply_markup(keyboard_generator(self._config.buttons[kb_name], order_id))
            self.log_info(chat_id, message.message_id, order_id, self, f'edit_kb: {kb_name}')
        except Exception as err:
            self.log_error(chat_id, None, order_id, self, err)

    async def remove_reply_markup(self, query, order_id):
        chat_id = query.from_user.id
        if isinstance(query, types.Message):
            message = await query.delete_reply_markup()
        elif isinstance(query, types.CallbackQuery):
            message = await query.message.delete_reply_markup()
        self.log_info(chat_id, message.message_id, order_id, self, 'remove_kb')
    
    async def discard_reply_markup(self, chat_id, order_id):
        try:
            message = await self._bot.send_message(chat_id, "msg_text", reply_markup=ReplyKeyboardRemove())
        except Exception as err:
            self.log_error(chat_id, None, order_id, self, err)
        await message.delete()

    def message_data(self, input_, order_id=None):
        chat_id = input_.from_user.id
        optionals = dict()
        if isinstance(input_, types.CallbackQuery):
            message_id = input_.message.message_id
            try:
                order_id = int(input_.data.split('@')[-1])
            except:
                pass
            optionals['data'] = input_.data
            optionals['text'] = input_.message.text
            self.log_info(chat_id, message_id, order_id, self, optionals['data'])
        elif isinstance(input_, types.Message):
            message_id = input_.message_id
            if 'text' in input_:
                optionals['text'] = input_.text
                self.log_message(chat_id, message_id, order_id, self, optionals['text'])
            elif 'location' in input_:
                optionals['location'] = f"{input_.location.latitude}|{input_.location.longitude}"
                self.log_message(chat_id, message_id, order_id, self, optionals['location'])
            elif 'contact' in input_:
                optionals['phone_number'] = f'+{input_.contact.phone_number}'
                self.log_message(chat_id, message_id, order_id, self, optionals['phone_number'])
            else:
                self.log_message(chat_id, message_id, order_id, self, input_.content_type)
        else:
            self.log_message(chat_id, message_id, order_id, self, input_.content_type)

        return chat_id, message_id, order_id, optionals

    async def send_venue(self, chat_id, lat, lon, destination, price, order_id, kb_name=None):
        kb = keyboard_generator(self._config.buttons[kb_name], order_id) if kb_name else None
        try:
            message = await self._bot.send_venue(
                chat_id=chat_id,
                latitude=lat,
                longitude=lon,
                title=destination,
                address=price,
                reply_markup=kb,
            )
            self.log_message(chat_id, message.message_id, order_id, self, f'lat: {lat}; lon: {lon} dest: {destination}; price: {price}')
        except Exception as err:
            self.log_error(chat_id, None, order_id, self, err)
    
    def log_info(self, chat_id, message_id, order_id, _self, message):
        self._db.log_message('INFO', chat_id, message_id, order_id, _self, message, 0)
    
    def log_message(self, chat_id, message_id, order_id, _self, message):
        self._db.log_message('MESSAGE', chat_id, message_id, order_id, _self, message, 1)
    
    def log_error(self, chat_id, message_id, order_id, _self, message):
        self._db.log_message('ERROR', chat_id, message_id, order_id, _self, message, 0)

    def tg_user_link(self, chat_id, first_name):
        return f'<a href="tg://user?id={chat_id}">{first_name}</a>'
    
    async def answer_callback_query(self, callback_query):
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        try:
            await self._bot.answer_callback_query(callback_query.id)
        except Exception as err:
            self.log_error(chat_id, message_id, order_id, self, err)