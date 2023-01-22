from aiogram import types
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


class JobHandler(DriverBaseHandler):

    async def __call__(self, message: types.Message) -> None:
        chat_id = message.from_user.id
        self.log_message(chat_id, message.message_id, -1, self, 'job_command')
        if not await self.create_user(message):
            return
        if chat_id in self._db.get_drivers_id():
            driver = self._db.get_user_by_id(chat_id)
            status = driver.driver_status
            kb_name = 'driver_menu'
            if status in [100,150]:
                active_shift = self._db.get_active_shift_by_driver_id(chat_id)
                report = self.create_shift_report(active_shift)
                text = 'Вы сейчас на смене.\n' + report
            elif status==50:
                text = "Вы сейчас не на смене. Нажмите 'Начать работу' чтобы получать заказы"
        else:
            text = self._config.messages['job_message']
            kb_name = 'job_menu'
        await self.send_message(chat_id, -1, text, kb_name)


class DriverJob(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id = callback_query.from_user.id
        await self.remove_reply_markup(callback_query, -1)
        text = f'Для регистрации в качестве водителя Вам необходимо указать своё имя, а также цвет, марку и регистрационный номер автомобиля'
        await self.send_message(chat_id, -1, text, 'driver_continue_registration')
        await self._bot.answer_callback_query(callback_query.id)


class DriverContinueRegistration(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id = callback_query.from_user.id
        await self.remove_reply_markup(callback_query, -1)
        await DriverJobApplience.name.set()
        text = 'Введите Ваше имя:'
        await self.send_message(chat_id, -1, text, 'driver_cancel_registration')
        await self._bot.answer_callback_query(callback_query.id)


class DriverName(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        chat_id = message.from_user.id
        await self.set_state(state, 'name', message.text)
        self.log_message(chat_id, message.message_id, -1, self, f'name: {message.text}')
        await DriverJobApplience.next()
        text = 'Введите цвет, марку и регистрационный номер автомобиля (пример: Зеленый Фольксваген А114КВ):'
        await self.send_message(chat_id, -1, text, 'driver_cancel_registration')


class DriverCar(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        chat_id = message.from_user.id
        await self.set_state(state, 'car', message.text)
        self.log_message(chat_id, message.message_id, -1, self, f'car: {message.text}')
        await DriverJobApplience.next()
        name = await self.get_state(state, 'name')
        car = await self.get_state(state, 'car')
        text = '\n'.join([
            f'Проверьте правильность введенных данных',
            f'Ваше имя: {name}',
            f'Ваша машина: {car}'
        ])
        await self.send_message(chat_id, -1, text, 'driver_continue_registration')


class DriverEndRegistration(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        chat_id = message.from_user.id
        name = await self.get_state(state, 'name')
        car = await self.get_state(state, 'car')
        await self.set_state(state, 'driver_id', chat_id)
        await state.finish()
        await self.delete_old_messages(chat_id=chat_id)
        text = f'Заявка оставлена. Ожидайте подтверждения администратора.'
        await self.send_message(chat_id, -1, text)
        text = '\n'.join([
            f'Новый водитель: {self.tg_user_link(chat_id, name)} \n'
            f'Машина: {car} ',
            f'{chat_id}@{name}@{car}'
        ])
        await self.send_message(self._config.ADMIN_ID, -1, text, 'admin_accept_refuse_driver')


class DriverAccepted(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id, first_name, car = callback_query.message.text.split('\n')[-1].split('@')
        driver_id = int(driver_id)
        self._db.create_driver(driver_id, first_name, car)
        text = f'Водитель принят'
        await self.send_message(self._config.ADMIN_ID, -1, text)
        await self.delete_old_messages(chat_id=driver_id)
        text = f"Вы стали водителем. Вы можете выйти на работу использую меню 'Работа в такси' либо через команду /job"
        await self.remove_reply_markup(callback_query, -1)
        await self.send_message(driver_id, -1, text)
        await self._bot.answer_callback_query(callback_query.id)


class DriverRefused(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id, _, _ = callback_query.message.text.split('\n')[-1].split('@')
        await self.send_message(self._config.ADMIN_ID, -1, 'Водитель отклонен')
        await self.send_message(driver_id, -1, 'Ваша заявка отклонена')
        await self._bot.answer_callback_query(callback_query.id)


class DriverCancelRegistration(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        chat_id = callback_query.from_user.id
        await self.send_message(callback_query.from_user.id, -1, 'Регистрация отменена')
        await self.delete_old_messages(chat_id=chat_id)
        await self.send_message(chat_id, -1, self._config.messages['call_taxi_message'], 'passenger_call_taxi')
        await self._bot.answer_callback_query(callback_query.id)
        current_state = await state.get_state()
        if current_state is None:
            return
        await state.finish()


class DriverStartWork(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id = callback_query.from_user.id
        driver = self._db.get_user_by_id(chat_id)
        status = driver.driver_status
        if status in [100,150]:
            text = 'Вы уже на смене'
        elif status==50:
            text = 'Вы начали свой рабочий день'
            self._db.update_driver_status(chat_id, 100)
            self._db.driver_start_shift(chat_id)
        await self.send_message(chat_id, -1, text)
        await self.show_active_orders(chat_id)
        await self._bot.answer_callback_query(callback_query.id)


class DriverStopWork(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id = callback_query.from_user.id
        driver = self._db.get_user_by_id(chat_id)
        status = driver.driver_status
        kb_name = None
        if status==150:
            text = 'Завершите или отмените свой текущий заказ'
        elif status==100:
            shift = self._db.driver_end_shift(chat_id)
            report = self.create_shift_report(shift)
            text = f"Вы закончили свой рабочий день.\n" + report
            kb_name = 'driver_menu'
            self._db.update_driver_status(chat_id, 50)
            await self.delete_old_messages(chat_id=chat_id)
        elif status==50:
            text='Вы сейчас не работаете'
        await self.send_message(chat_id, -1, text, kb_name)
        await self._bot.answer_callback_query(callback_query.id)


class DriverTopUpMenu(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id = callback_query.from_user.id
        text = f"Выберите опцию:"
        await self.send_message(chat_id, -1, text, 'driver_topup_menu')


class DriverTopUp(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
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