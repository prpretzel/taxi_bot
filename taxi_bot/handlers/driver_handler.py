from aiogram import types
from taxi_bot.handlers.base_handler import BaseHandler
from taxi_bot.database_handler import DataBase
from aiogram import Bot
from taxi_bot.load_config import Config
from taxi_bot.logger import Logger
from taxi_bot.buttons import keyboard_generator

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

class DriverForm(StatesGroup):
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
        await DriverForm.name.set()
        await self._bot.send_message(
            chat_id=driver_id,
            text='Введите Ваше имя:',
            reply_markup=self._kbs['driver_cancel_registration']
        )


class DriverName(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        await self.set_state(state, 'name', message.text)
        await DriverForm.next()
        await self._bot.send_message(
            chat_id=message.from_user.id,
            text='Введите цвет, марку и регистрационный номер автомобиля (пример: Зеленый Фольксваген А114КВ):',
            reply_markup=self._kbs['driver_cancel_registration']
        )


class DriverCar(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        await self.set_state(state, 'car', message.text)
        await DriverForm.next()
        name = await self.get_state(state, 'name')
        car = await self.get_state(state, 'car')
        await self._bot.send_message(
            chat_id=message.from_user.id,
            text=f'Проверьте правильность введенных данных\n'
                 f'Ваше имя: {name}\n'
                 f'Ваша машина: {car}\n',
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
            text=f'Заявка составлена. Ожидайте подтверждения администратора.',
        )
        await self._bot.send_message(
            chat_id=self._config.ADMIN_ID,
            text=f'Новый водитель\n'
                 f'ID: {message.from_user.id}\n'
                 f'Имя: {name}\n'
                 f'Машина: {car}\n'
                 f'{message.from_user.id}@{name}@{car}',
            reply_markup=self._kbs['admin_accept_refuse_driver']
        )


class DriverAccepted(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id, first_name, car = callback_query.message.text.split('\n')[-1].split('@')
        self._db.create_driver(driver_id, first_name, car)
        await self._bot.send_message(chat_id=self._config.ADMIN_ID, text=f'Водитель принят')
        await self._bot.send_message(chat_id=driver_id, text=f'Вы стали водителем')
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
        text = 'Вы начали свой рабочий день'
        await self._bot.send_message(
            chat_id=driver_id,
            text=text,
        )
        await self.show_active_orders(driver_id)
        self._db.update_driver_status(driver_id, 100)
        await self._bot.answer_callback_query(callback_query.id)


class DriverStopWork(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id = callback_query.from_user.id
        driver_info = self._db.get_driver_by_id(driver_id)
        status = driver_info.driver_status
        if status==150:
            await self._bot.send_message(chat_id=driver_id, text='Завершите или отмените свой заказ',)
            await self._bot.answer_callback_query(callback_query.id)
            return
        text = 'Вы закончили свой рабочий день'
        await self._bot.send_message(
            chat_id=driver_id,
            text=text,
        )
        await self.delete_old_messages(driver_id=driver_id)
        self._db.update_driver_status(driver_id, 50)
        await self._bot.answer_callback_query(callback_query.id)


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