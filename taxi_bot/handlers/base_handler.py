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

    async def create_user(self, message, referral=None, phone_number_requaried=True):
        phone_number = self._db.create_user(message, referral)
        chat_id = message.from_user.id
        if phone_number_requaried and not phone_number:
            await self.send_message(chat_id, None, self._config.messages['phone_number_request'], 'request_contact')
        return phone_number

    async def show_order(self, order, chat_id, kb_name=None, delete_old=False):
        import re
        order_id = order.order_id
        destination = order.location_to
        price = f"{order.price} рублей"
        geo = re.match(r'\d{1,3}\.\d+|\d{1,3}\.\d+', order.location_from)
        if geo:
            lat, lon = order.location_from.split('|') 
            await self.send_venue(
                chat_id=chat_id,
                lat=lat, 
                lon=lon, 
                destination=destination,
                price=price,
                order_id=order_id,
                kb_name=kb_name,
                delete_old=delete_old,
            )
        else:
            text = [
                f"Откуда: {order.location_from}",
                f"Куда: {destination}",
                f"Стоимость: {price}",
            ]
            text = '\n'.join(text)
            await self.send_message(
                chat_id=chat_id, 
                order_id=order_id, 
                text=text, 
                kb_name=kb_name, 
                delete_old=delete_old, 
            )

    async def show_active_orders(self, driver_id):
        active_orders = self._db.get_orders_by_status(100)
        for order in active_orders:
            await self.show_order(order, driver_id, 'driver_accept_refuse')

    async def delete_old_messages(self, order_id=None, chat_id=None, message_id=None, force=False):
        orders = self._db.get_log_messages(order_id=order_id, chat_id=chat_id, message_id=message_id)
        log_ids = list()
        for order in orders:
            chat_id, message_id, order_id = order.chat_id, order.message_id, order.order_id
            if (order.shown==2) and (not force):
                continue
            try:
                await self._bot.delete_message(chat_id, message_id)
            except Exception as err:
                self.log_error(chat_id, message_id, order_id, self, err)
            log_ids.append(order.log_id)
        self._db.update_log_status(log_ids=log_ids)

    def time_handler(self, dt1, dt2):
        if dt1 == dt2:
            return
        if not dt1 or not dt2:
            return ''
        dt = (dt1 - dt2).seconds
        hours = str(dt//3600).zfill(2)
        minutes = str(dt%3600//60).zfill(2)
        seconds = str(dt%60).zfill(2)
        return f"{hours}:{minutes}:{seconds}"
    
    async def send_message(self, chat_id, order_id, text, kb_name=None, kb_suffix=None, delete_old=False, shown=1):
        kb_suffix = kb_suffix if kb_suffix else order_id
        kb = keyboard_generator(self._config.buttons[kb_name], kb_suffix) if kb_name else None
        try:
            message = await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=kb,
                parse_mode='html'
            )
            if delete_old:
                await self.delete_old_messages(chat_id=chat_id)
                if order_id:
                    await self.delete_old_messages(order_id=order_id)
            self.log_message(chat_id, message.message_id, order_id, self, text, shown=shown)
            return message
        except Exception as err:
            self.log_error(chat_id, None, order_id, self, err)
            
    async def show_admin_order(self, order, callback_query=None):
        from datetime import datetime
        def time_handler_2(dt):
            return (dt, dt.strftime('%H:%M:%S')) if dt else (None, '')
            
        order_id = order.order_id
        passenger = self._db.get_user_by_id(order.passenger_id)
        driver = self._db.get_user_by_id(order.driver_id)
        driver_contact = f"{self.tg_user_link(order.driver_id, driver.first_name)} {driver.phone_number}" if driver else 'Водитель не назначен'
        order_date = order.order_dt.date()
        order_dt, order_dt_str = time_handler_2(order.order_dt)
        accept_dt, accept_dt_str = time_handler_2(order.accept_dt)
        wait_dt, wait_dt_str = time_handler_2(order.wait_dt)
        pick_dt, pick_dt_str = time_handler_2(order.pick_dt)
        end_dt, end_dt_str = time_handler_2(order.end_dt)
        now, now_str = time_handler_2(datetime.now())
        text = [
            f"#{order_id}",
            f"Дата заказа: {order_date}",
            f"Create:  {order_dt_str}",
            f"Accept: {accept_dt_str} ({self.time_handler(accept_dt, order_dt)})",
            f"Wait:     {wait_dt_str} ({self.time_handler(wait_dt, accept_dt)})",
            f"Pick:     {pick_dt_str} ({self.time_handler(pick_dt, wait_dt)})",
            f"End:      {end_dt_str} ({self.time_handler(end_dt, pick_dt)})",
            f"{self.tg_user_link(order.passenger_id, 'Пассажир')} {passenger.phone_number}",
            driver_contact,
            f"Откуда: {order.location_from}",
            f"Куда: {order.location_to}",
            f"Цена: {order.price}",
            f"Статус: ({order.order_status}) {self.map_status(order.order_status)}",
            f"Время обновления: {now_str}",
        ]
        text = '\n'.join(text)
        if not callback_query:
            await self.send_message(self._config.ADMIN_ID, order_id, text, 'order_details', shown=2)
        else:
            chat_id, message_id, order_id, optionals = await self.message_data(callback_query)
            await self.edit_message(chat_id, message_id, order_id, text, 'order_details')
            await self.answer_callback_query(callback_query)
            
    async def show_admin_user(self, user_id):
        from datetime import datetime
        def str_date_from_dt(dt):
            return dt.strftime('%Y-%m-%d')
        
        user = self._db.get_user_by_id(user_id)
        if user:
            user_info = [
                f'ID: {user_id}',
                self.tg_user_link(user_id, user.first_name),
                f'Phone number: {user.phone_number}',
                f'Registration date: {str_date_from_dt(user.user_registration_date)}',
                f'Active: {user.active}',
            ]
            if user.referral:
                user_info.append(f"Referral: {self.tg_user_link(user.referral, 'referral link')}")
            if user.driver_status:
                user_info += [
                    f'Driver registration: {str_date_from_dt(user.driver_registration_date)}',
                    f'Driver status: {user.driver_status}',
                    f'Driver car: {user.driver_car}',
                    f'Driver balance: {user.driver_balance}',
                    f'Driver shift_id: {user.driver_shift_id}',
                ]
            user_info = '\n'.join(user_info)
            await self.send_message(self._config.ADMIN_ID, None, user_info, kb_name='admin_user_actions', kb_suffix=user_id)
            
    async def edit_message(self, chat_id, message_id, order_id, text=None, kb_name=None):
        kb = keyboard_generator(self._config.buttons[kb_name], order_id) if kb_name else None
        if text:
            try:
                message = await self._bot.edit_message_text(
                    chat_id=chat_id, 
                    message_id=message_id, 
                    text=text, 
                    reply_markup=kb, 
                    parse_mode='html'
                )
                self.log_info(chat_id, message.message_id, order_id, self, f'{text}|{kb_name}')
            except Exception as err:
                self.log_error(chat_id, None, order_id, self, err)
        else:
            try:
                message = await self._bot.edit_message_reply_markup(
                    chat_id=chat_id, 
                    message_id=message_id, 
                    reply_markup=kb, 
                )
                self.log_info(chat_id, message.message_id, order_id, self, f'{kb_name}')
            except Exception as err:
                self.log_error(chat_id, None, order_id, self, err)

    async def edit_reply_markup(self, callback_query: types.CallbackQuery, kb_name, order_id):
        chat_id = callback_query.from_user.id
        try:
            message = await callback_query.message.edit_reply_markup(keyboard_generator(self._config.buttons[kb_name], order_id))
            self.log_info(chat_id, message.message_id, order_id, self, f'edit_kb: {kb_name}')
        except Exception as err:
            self.log_error(chat_id, None, order_id, self, err)

    async def send_venue(self, chat_id, lat, lon, destination, price, order_id, kb_name=None, delete_old=False):
        kb = keyboard_generator(self._config.buttons[kb_name], order_id) if kb_name else None
        destination = f"Куда: {destination}"
        try:
            message = await self._bot.send_venue(
                chat_id=chat_id,
                latitude=lat,
                longitude=lon,
                title=destination,
                address=price,
                reply_markup=kb,
            )
            if delete_old:
                await self.delete_old_messages(chat_id=chat_id)
                if order_id:
                    await self.delete_old_messages(order_id=order_id)
            text = f'lat: {lat}; lon: {lon} dest: {destination}; price: {price}'
            self.log_message(chat_id, message.message_id, order_id, self, text)
        except Exception as err:
            self.log_error(chat_id, None, order_id, self, err)

    async def remove_inline_markup(self, query, order_id):
        chat_id, message_id, order_id, optionals = await self.message_data(query)
        try:
            if isinstance(query, types.Message):
                message = await query.delete_reply_markup()
            elif isinstance(query, types.CallbackQuery):
                message = await query.message.delete_reply_markup()
            self.log_info(chat_id, message.message_id, order_id, self, 'remove_kb')
        except Exception as err:
            self.log_error(chat_id, message_id, order_id, self, err)
    
    async def discard_reply_markup(self, chat_id, order_id):
        try:
            message = await self._bot.send_message(chat_id, "msg_text", reply_markup=ReplyKeyboardRemove())
        except Exception as err:
            self.log_error(chat_id, None, order_id, self, err)
        await message.delete()

    async def message_data(self, input_, order_id=None):
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
            await self.answer_callback_query(input_)
        elif isinstance(input_, types.Message):
            message_id = input_.message_id
            if 'text' in input_:
                optionals['text'] = input_.text
                self.log_message(chat_id, message_id, order_id, self, optionals['text'])
            elif 'location' in input_:
                optionals['location'] = f"{input_.location.latitude}|{input_.location.longitude}"
                self.log_message(chat_id, message_id, order_id, self, optionals['location'])
            elif 'contact' in input_:
                phone_number = input_.contact.phone_number
                if phone_number.startswith('+'):
                    optionals['phone_number'] = phone_number
                else:
                    optionals['phone_number'] = '+' + phone_number
                self.log_message(chat_id, message_id, order_id, self, optionals['phone_number'])
            else:
                self.log_message(chat_id, message_id, order_id, self, input_.content_type)
        else:
            self.log_message(chat_id, message_id, order_id, self, input_.content_type)
        return chat_id, message_id, order_id, optionals
    
    def log_info(self, chat_id, message_id, order_id, _self, message):
        self._db.log_message('INFO', chat_id, message_id, order_id, _self, message, 0)
    
    def log_message(self, chat_id, message_id, order_id, _self, message, shown=1):
        self._db.log_message('MESSAGE', chat_id, message_id, order_id, _self, message, shown)
    
    def log_error(self, chat_id, message_id, order_id, _self, message):
        self._db.log_message('ERROR', chat_id, message_id, order_id, _self, message, 0)

    def tg_user_link(self, chat_id, first_name):
        return f'<a href="tg://user?id={chat_id}">{first_name}</a>'
    
    async def answer_callback_query(self, callback_query):
        try:
            await self._bot.answer_callback_query(callback_query.id)
        except Exception as err:
            self.log_error(callback_query.from_user.id, None, None, self, err)
            
    def map_status(self, order_status):
        status_mapper = {
            70 : 'Ввод адреса отправления',
            80 : 'Ввод адреса назначения ',
            90 : 'Ввод цены              ',
            73 : 'Отмена пассажиром      ',
            83 : 'Отмена пассажиром      ',
            93 : 'Отмена пассажиром      ',
            100: 'Активный заказ         ',
            200: 'Взят в работу          ',
            250: 'Водитель ожидает       ',
            300: 'В пути                 ',
            400: 'Заказ завершен         ',
            103: 'Отмена пассажиром      ',
            203: 'Отмена пассажиром      ',
            253: 'Отмена пассажиром      ',
            303: 'Отмена пассажиром      ',
            107: 'Отмена водителем       ',
            207: 'Отмена водителем       ',
            257: 'Отмена водителем       ',
            307: 'Отмена водителем       ',
            50 : 'Отмена пассажиром      ',
            150: 'Отмена водителем       ',
        }
        if order_status in status_mapper.keys():
            return status_mapper[order_status]
        else:
            return order_status
    
    def get_referral_link(self, chat_id):
        return f"{self._config.BOT_LINK}?start={chat_id}"
    
    def get_url_link(self, text, url):
        from aiogram.utils.markdown import hlink
        return hlink(text, url)