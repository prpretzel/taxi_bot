from aiogram import types
from aiogram.utils.markdown import hlink
from taxi_bot.handlers.base_handler import BaseHandler
from taxi_bot.database_handler import DataBase
from aiogram import Bot
from taxi_bot.load_config import Config
from taxi_bot.logger import Logger
from taxi_bot.buttons import keyboard_generator
from datetime import datetime

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

class DriverJobApplience(StatesGroup):
    name = State()
    car = State()
    driver_id = State()
    previous_message = State()

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
        self.link = "\n" + hlink('Перейти в чат водителей', 'https://t.me/+bNnsHC1MSQo0MzU0')
        
    
    def create_shift_report(self, shift):
        start_shift = shift.shift_start
        end_shift = shift.shift_end
        total_trips = shift.total_trips
        total_income = shift.total_income
        if end_shift:
            shift_duration = self.time_handler(end_shift, start_shift)
            text = '\n'.join([
                f"Статистика:",
                f"Вы работали с {start_shift.strftime('%H:%M')} до {end_shift.strftime('%H:%M')}",
                f"Продолжительность смены: {shift_duration}",
                f"Закрытых заказов: {total_trips}",
                f"Заработано: {total_income} рублей",
            ])
        else:
            shift_duration = self.time_handler(datetime.now(), start_shift)
            text = '\n'.join([
                f"Статистика:",
                f"Вы работаете с {start_shift.strftime('%H:%M')}",
                f"Продолжительность смены: {shift_duration}",
                f"Закрытых заказов: {total_trips}",
                f"Заработано: {total_income} рублей",
            ])
        return text
    
    def get_driver_menu(self, chat_id):
        if chat_id==self._config.ADMIN_ID:
            return 'driver_admin_menu'
        elif chat_id in self._config.MODER_IDs: 
            return 'driver_moder_menu'
        return 'driver_menu'
        

class JobHandler(DriverBaseHandler):

    async def __call__(self, message: types.Message) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(message)
        if not await self.create_user(message):
            return
        driver = self._db.get_user_by_id(chat_id)
        driver_status = driver.driver_status
        if driver_status:
            kb_name = self.get_driver_menu(chat_id)
            if driver_status in [100,150]:
                active_shift = self._db.get_active_shift_by_driver_id(chat_id)
                report = self.create_shift_report(active_shift)
                text = 'Вы сейчас на смене.\n' + report + self.link
            elif driver_status==50:
                text = "Вы сейчас не на смене. Нажмите 'Начать работу' чтобы получать заказы" + self.link
            elif driver_status==30:
                text = "Ваш аккаунт временно заблокирован. Напишите в поддержку @Boguchar_taxi_support"
        else:
            text = self._config.messages['job_message']
            kb_name = 'job_menu'
        await self.send_message(chat_id, order_id, text, kb_name)


class DriverJob(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        await self.remove_reply_markup(callback_query, order_id)
        text = f'Для регистрации в качестве водителя Вам необходимо указать своё имя, а также цвет, марку и регистрационный номер автомобиля'
        await self.send_message(chat_id, order_id, text, 'driver_continue_registration')
        await self.answer_callback_query(callback_query)


class DriverContinueRegistration(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        await self.remove_reply_markup(callback_query, order_id)
        await DriverJobApplience.name.set()
        text = 'Введите Ваше имя:'
        message = await self.send_message(chat_id, order_id, text, 'driver_cancel_registration')
        await self.set_state(state, 'previous_message', message)
        await self.answer_callback_query(callback_query)


class DriverName(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(message)
        previous_message = await self.get_state(state, 'previous_message')
        await self.remove_reply_markup(previous_message, order_id)
        if len(optionals['text']) > 30:
            text = "Краткость - сестра таланта 😉"
            message = await self.send_message(chat_id, order_id, text, 'driver_cancel_registration')
            await self.set_state(state, 'previous_message', message)
            return
        await self.set_state(state, 'name', optionals['text'])
        await DriverJobApplience.next()
        text = 'Введите цвет, марку и регистрационный номер автомобиля (пример: Зеленый Фольксваген А114КВ):'
        message = await self.send_message(chat_id, order_id, text, 'driver_cancel_registration')
        await self.set_state(state, 'previous_message', message)


class DriverCar(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(message)
        previous_message = await self.get_state(state, 'previous_message')
        await self.remove_reply_markup(previous_message, order_id)
        if len(optionals['text']) > 30:
            text = "Краткость - сестра таланта 😉"
            message = await self.send_message(chat_id, order_id, text, 'driver_cancel_registration')
            await self.set_state(state, 'previous_message', message)
            return
        await self.set_state(state, 'car', optionals['text'])
        await DriverJobApplience.next()
        name = await self.get_state(state, 'name')
        car = await self.get_state(state, 'car')
        text = '\n'.join([
            f'Проверьте правильность введенных данных',
            f'Ваше имя: {name}',
            f'Ваша машина: {car}'
        ])
        await self.send_message(chat_id, order_id, text, 'driver_continue_registration')


class DriverEndRegistration(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(message)
        name = await self.get_state(state, 'name')
        car = await self.get_state(state, 'car')
        await self.set_state(state, 'driver_id', chat_id)
        await state.finish()
        text = f'Заявка оставлена. Ожидайте подтверждения администратора.'
        await self.send_message(chat_id, order_id, text, delete_old=True)
        text = '\n'.join([
            f'Новый водитель: {self.tg_user_link(chat_id, name)} \n'
            f'Машина: {car} ',
            f'{chat_id}@{name}@{car}'
        ])
        await self.send_message(self._config.ADMIN_ID, order_id, text, 'admin_accept_refuse_driver')


class DriverAccepted(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        driver_id, first_name, car = callback_query.message.text.split('\n')[-1].split('@')
        driver_id = int(driver_id)
        self._db.create_driver(driver_id, first_name, car)
        await self.send_message(chat_id, order_id, 'Водитель принят', delete_old=True)
        text = f"Вы стали водителем. Вы можете выйти на работу использую меню 'Работа в такси' либо через команду /job" + self.link
        await self.send_message(driver_id, order_id, text, delete_old=True)
        await self.answer_callback_query(callback_query)


class DriverRefused(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        driver_id, _, _ = callback_query.message.text.split('\n')[-1].split('@')
        await self.send_message(chat_id, order_id, 'Водитель отклонен')
        await self.send_message(driver_id, order_id, 'Ваша заявка отклонена')
        await self.answer_callback_query(callback_query)


class DriverCancelRegistration(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        await self.send_message(chat_id, order_id, 'Регистрация отменена', delete_old=True)
        await self.send_message(chat_id, order_id, self._config.messages['call_taxi_message'], 'passenger_call_taxi')
        if await state.get_state():
            await state.finish()
        await self.answer_callback_query(callback_query)


class DriverStartWork(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        driver = self._db.get_user_by_id(chat_id)
        status = driver.driver_status
        if status in [100,150]:
            text = 'Вы уже на смене. Новые заказы будут приходить Вам автоматически.' + self.link
        elif status==50:
            text = 'Вы начали свой рабочий день. Новые заказы будут приходить вам автоматически' + self.link
            self._db.update_driver_status(chat_id, 100)
            self._db.driver_start_shift(chat_id)
        else:
            text = status
        await self.send_message(chat_id, order_id, text, delete_old=True)
        await self.show_active_orders(chat_id)
        await self.answer_callback_query(callback_query)


class DriverActiveOrder(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        active_order = self._db.get_drivers_active_order(chat_id)
        if active_order:
            order_id = active_order.order_id
            order_status = active_order.order_status
            kb_name = {200:'driver_cancel_wait', 250:'driver_cancel_pick', 300:'driver_complete'}[order_status]
            await self.delete_old_messages(chat_id=chat_id, order_id=order_id)
            await self.show_order(active_order, chat_id, kb_name)
        else:
            await self.send_message(chat_id, order_id, 'У вас нет активных заказов')
        await self.answer_callback_query(callback_query)
        

class DriverStopWork(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        driver = self._db.get_user_by_id(chat_id)
        status = driver.driver_status
        kb_name = None
        if status==150:
            active_order = self._db.get_drivers_active_order(chat_id)
            order_id = active_order.order_id
            order_status = active_order.order_status
            kb_name = {200:'driver_cancel_wait', 250:'driver_cancel_pick', 300:'driver_complete'}[order_status]
            await self.send_message(chat_id, order_id, 'Завершите или отмените свой текущий заказ', delete_old=True)
            await self.show_order(active_order, chat_id, kb_name)
        elif status==100:
            shift = self._db.driver_end_shift(chat_id)
            report = self.create_shift_report(shift)
            self._db.update_driver_status(chat_id, 50)
            await self.send_message(chat_id, None, f"Вы закончили свой рабочий день.\n" + report + self.link, self.get_driver_menu(chat_id), delete_old=True)
        elif status==50:
            await self.send_message(chat_id, None, 'Вы сейчас не работаете' + self.link, delete_old=True)
        await self.answer_callback_query(callback_query)


class DriverTopUpMenu(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        return
        chat_id = callback_query.from_user.id
        text = f"Выберите опцию:"
        await self.send_message(chat_id, -1, text, 'driver_topup_menu')


class DriverTopUp(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        return
        driver_id = callback_query.from_user.id
        amount = int(callback_query.data.split('@')[-1])
        PRICES = {
            100: types.LabeledPrice(label='10 Поездок', amount=10000),
            200: types.LabeledPrice(label='25 Поездок', amount=20000),
        }[amount]
        await self._bot.send_invoice(
            chat_id=driver_id,
            title='Пополнить кошелек title',
            description='Пополнить кошелек description',
            provider_token=self._config.PAYMENT_TOKEN,
            currency='rub',
            prices=[PRICES],
            payload='some_invoice'
        )
        # TODO: send_message