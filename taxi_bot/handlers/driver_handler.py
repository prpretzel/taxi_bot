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


class DriverMenu(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id = callback_query.from_user.id
        if driver_id in self._db.get_drivers_id():
            await self._bot.send_message(
                chat_id=driver_id,
                text='Меню водителя',
                reply_markup=self._kbs['driver_menu']
            )
        else:
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
        print(await state.get_state(), '*'*40)
        async with state.proxy() as data:
            data['name'] = message.text
        await DriverForm.next()
        await self._bot.send_message(
            chat_id=message.from_user.id,
            text='Введите цвет, марку и регистрационный номер автомобиля (пример: Зеленый Фольксваген А114КВ):',
            reply_markup=self._kbs['driver_cancel_registration']
        )


class DriverCar(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        print(await state.get_state(), '*'*40)
        async with state.proxy() as data:
            data['car'] = message.text
        await DriverForm.next()
        async with state.proxy() as data:
            name = data['name']
            car = data['car']
        await self._bot.send_message(
            chat_id=message.from_user.id,
            text=f'Проверьте правильность введенных данных\n'
                 f'Ваше имя: {name}\n'
                 f'Ваша машина: {car}\n',
            reply_markup=self._kbs['driver_continue_registration']
        )


class DriverEndRegistration(DriverBaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        print(await state.get_state(), '*'*40)
        async with state.proxy() as data:
            name = data['name']
            car = data['car']
            data['driver_id'] = message.from_user.id
        await state.finish()
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
        await self._bot.send_message(
            chat_id=self._config.ADMIN_ID,
            text=f'Водитель принят'
        )
        await self._bot.send_message(
            chat_id=driver_id,
            text=f'Вы стали водителем'
        )
        await self._bot.answer_callback_query(callback_query.id)



class DriverRefused(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id, first_name, car = callback_query.message.text.split('\n')[-1].split('@')
        await self._bot.send_message(
            chat_id=self._config.ADMIN_ID,
            text=f'Водитель отклонен'
        )
        await self._bot.send_message(
            chat_id=driver_id,
            text=f'Ваша заявка отклонена'
        )
        await self._bot.answer_callback_query(callback_query.id)


class DriverCancelRegistration(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery, state: FSMContext) -> None:
        driver_id = callback_query.from_user.id
        current_state = await state.get_state()
        await self._bot.send_message(
            chat_id=driver_id,
            text='Регистрация отменена'
        )
        await self._bot.answer_callback_query(callback_query.id)
        if current_state is None:
            return

        await state.finish()

class DriverStatus(DriverBaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        driver_id = callback_query.from_user.id
        driver_info = self._db.get_driver_by_id(driver_id)
        status = driver_info.driver_status
        if status==150:
            await self._bot.send_message(
                chat_id=driver_id,
                text='Завершите или отмените свой заказ',
            )
            await self._bot.answer_callback_query(callback_query.id)
            return

        data = callback_query.data
        if data == 'driver_start_work':
            new_status = 100 
            text = 'Вы начали свой рабочий день'
        elif data == 'driver_end_work':
            new_status = 50
            text = 'Вы закончили свой рабочий день'
        await self._bot.send_message(
            chat_id=driver_id,
            text=text,
        )
        self._db.update_driver_status(driver_id, new_status)
        await self._bot.answer_callback_query(callback_query.id)