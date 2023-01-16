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
        user_id = message.from_user.id
        if user_id in self._db.get_drivers_id():
            driver = self._db.get_user_by_id(user_id)
            status = driver.driver_status
            if status in [100,150]:
                active_shift = self._db.get_active_shift_by_driver_id(user_id)
                report = self.create_shift_report(active_shift)
                text = 'Вы сейчас на смене.\n' + report
            elif status==50:
                text = "Вы сейчас не на смене. Нажмите 'Начать работу' чтобы получать заказы"
            await self._bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=self._kbs['driver_menu']
            )
            self._logger.info(self, message.from_user.id, 'Driver job')
        else:
            await self._bot.send_message(
                chat_id=message.from_user.id,
                text=self._config.messages['job_message'],
                reply_markup=self._kbs['job_menu']
            )
            self._logger.info(self, message.from_user.id, 'User job')


class DriverJob(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id = callback_query.from_user.id
        await self._bot.send_message(
            chat_id=driver_id,
            text=f'Для регистрации в качестве водителя Вам необходимо указать своё имя, '
                 f'а также цвет, марку и регистрационный номер автомобиля',
            reply_markup=self._kbs['driver_continue_registration']
        )
        await self._bot.answer_callback_query(callback_query.id)


class DriverContinueRegistration(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id = callback_query.from_user.id
        await DriverJobApplience.name.set()
        await self._bot.send_message(
            chat_id=driver_id,
            text='Введите Ваше имя:',
            reply_markup=self._kbs['driver_cancel_registration']
        )


class DriverName(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        await self.set_state(state, 'name', message.text)
        await DriverJobApplience.next()
        await self._bot.send_message(
            chat_id=message.from_user.id,
            text='Введите цвет, марку и регистрационный номер автомобиля (пример: Зеленый Фольксваген А114КВ):',
            reply_markup=self._kbs['driver_cancel_registration']
        )


class DriverCar(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        await self.set_state(state, 'car', message.text)
        await DriverJobApplience.next()
        name = await self.get_state(state, 'name')
        car = await self.get_state(state, 'car')
        text = '\n'.join([
            f'Проверьте правильность введенных данных',
            f'Ваше имя: {name}',
            f'Ваша машина: {car}'
        ])
        await self._bot.send_message(
            chat_id=message.from_user.id,
            text=text,
            reply_markup=self._kbs['driver_continue_registration']
        )


class DriverEndRegistration(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        name = await self.get_state(state, 'name')
        car = await self.get_state(state, 'car')
        await self.set_state(state, 'driver_id', message.from_user.id)
        await state.finish()
        await self._bot.send_message(
            chat_id=message.from_user.id,
            text=f'Заявка оставлена. Ожидайте подтверждения администратора.',
        )
        text = '\n'.join([
            f'Новый водитель',
            f'ID: {message.from_user.id}',
            f'Имя: {name}',
            f'Машина: {car}',
            f'{message.from_user.id}@{name}@{car}'
        ])
        await self._bot.send_message(
            chat_id=self._config.ADMIN_ID,
            text=text,
            reply_markup=self._kbs['admin_accept_refuse_driver']
        )


class DriverAccepted(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id, first_name, car = callback_query.message.text.split('\n')[-1].split('@')
        driver_id = int(driver_id)
        self._db.create_driver(driver_id, first_name, car)
        await self._bot.send_message(chat_id=self._config.ADMIN_ID, text=f'Водитель принят')
        await self._bot.send_message(chat_id=driver_id, text=f"Вы стали водителем. Вы можете выйти на маршрут использую меню 'Работа в такси' либо через команду /job")
        await self._bot.answer_callback_query(callback_query.id)


class DriverRefused(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id, _, _ = callback_query.message.text.split('\n')[-1].split('@')
        await self._bot.send_message(chat_id=self._config.ADMIN_ID, text=f'Водитель отклонен')
        await self._bot.send_message(chat_id=driver_id, text=f'Ваша заявка отклонена')
        await self._bot.answer_callback_query(callback_query.id)


class DriverCancelRegistration(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        driver_id = callback_query.from_user.id
        current_state = await state.get_state()
        await self._bot.send_message(chat_id=driver_id, text='Регистрация отменена')
        await self._bot.answer_callback_query(callback_query.id)
        if current_state is None:
            return
        await state.finish()


class DriverStartWork(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id = callback_query.from_user.id
        driver = self._db.get_user_by_id(driver_id)
        status = driver.driver_status
        if status in [100,150]:
            text = 'Вы уже на смене'
        elif status==50:
            text = 'Вы начали свой рабочий день'
            self._db.update_driver_status(driver_id, 100)
            self._db.driver_start_shift(driver_id)
        await self._bot.send_message(chat_id=driver_id, text=text)
        await self.show_active_orders(driver_id)
        await self._bot.answer_callback_query(callback_query.id)


class DriverStopWork(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id = callback_query.from_user.id
        driver = self._db.get_user_by_id(driver_id)
        status = driver.driver_status
        if status==150:
            await self._bot.send_message(chat_id=driver_id, text='Завершите или отмените свой текущий заказ')
            await self._bot.answer_callback_query(callback_query.id)
            return
        elif status==100:
            shift = self._db.driver_end_shift(driver_id)
            report = self.create_shift_report(shift)
            text = f"Вы закончили свой рабочий день.\n" + report
            await self._bot.send_message(chat_id=driver_id, text=text, reply_markup=self._kbs['driver_menu'])
            self._db.update_driver_status(driver_id, 50)
            await self.delete_old_messages(chat_id=driver_id)
            await self._bot.answer_callback_query(callback_query.id)
        elif status==50:
            await self._bot.send_message(chat_id=driver_id, text='Вы сейчас не работаете')


class DriverTopUpMenu(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id = callback_query.from_user.id
        text = f"Выберите опцию:"
        await self._bot.send_message(
            chat_id=driver_id,
            text=text,
            reply_markup=self._kbs['driver_topup_menu']
        )


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