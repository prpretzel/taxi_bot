from aiogram import Dispatcher, Bot
from taxi_bot.database_handler import DataBase
from taxi_bot.load_config import Config
from taxi_bot.logger import Logger


from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup


from taxi_bot.handlers.client import (
    StartHandler, 
    HelpHandler,
    JobHandler,
    UpdateContact,
    MemberStatus
)

from taxi_bot.handlers.driver_handler import (
    DriverForm,
    DriverJob,
    DriverContinueRegistration,
    DriverName,
    DriverCar,
    DriverEndRegistration,
    DriverCancelRegistration,
    DriverAccepted,
    DriverRefused,
    DriverStartWork,
    DriverStopWork,
    DriverTopUpMenu,
    DriverTopUp
)

from taxi_bot.handlers.order_handler import (
    OrderForm,
    NewOrderFrom,
    NewOrderTo,
    NewOrderPrice,
    DriverAccept,
    DriverRefuse,
    PassengerCancel,
    DriverCancel,
    DriverWait,
    DriverPick,
    DriverComplete
)


def register_handlers(
        db: DataBase, 
        bot: Bot, 
        config: Config, 
        kbs: dict, 
        dp: Dispatcher, 
        logger: Logger
    ):
    INSTANCES = db, bot, config, kbs, logger
    ADMIN_COND = lambda c: c.from_user.id == config.ADMIN_ID
    MODER_COND = lambda c: c.from_user.id in config.MODER_IDs
    
    def L(startswith):
        return lambda c: c.data.startswith(startswith)
    
    # main handlers
    dp.register_message_handler(StartHandler(*INSTANCES), commands=['start'])
    dp.register_message_handler(StartHandler(*INSTANCES), commands=['restart'])
    dp.register_message_handler(UpdateContact(*INSTANCES), content_types=['contact'])
    dp.register_message_handler(HelpHandler(*INSTANCES), commands=['help'])
    dp.register_message_handler(JobHandler(*INSTANCES), commands=['job'])
    dp.register_my_chat_member_handler(MemberStatus(*INSTANCES))

    # driver handlers
    dp.register_callback_query_handler(DriverJob(*INSTANCES), L('job'))
    dp.register_callback_query_handler(DriverContinueRegistration(*INSTANCES), L('driver_continue_registration'))
    dp.register_message_handler(DriverName(*INSTANCES), state=DriverForm.name)
    dp.register_message_handler(DriverCar(*INSTANCES), state=DriverForm.car)
    dp.register_callback_query_handler(DriverEndRegistration(*INSTANCES), L('driver_continue_registration'), state='*')
    dp.register_callback_query_handler(DriverCancelRegistration(*INSTANCES), L('driver_cancel_registration'), state='*')
    dp.register_callback_query_handler(DriverAccepted(*INSTANCES), L('driver_accepted'))
    dp.register_callback_query_handler(DriverRefused(*INSTANCES), L('driver_refused'))
    dp.register_callback_query_handler(DriverStartWork(*INSTANCES), L('driver_start_work'))
    dp.register_callback_query_handler(DriverStopWork(*INSTANCES), L('driver_end_work'))
    dp.register_callback_query_handler(DriverTopUpMenu(*INSTANCES), L('driver_topup_select'))
    dp.register_callback_query_handler(DriverTopUp(*INSTANCES), L('driver_topup'))

    # call a taxi handlers
    dp.register_message_handler(NewOrderFrom(*INSTANCES), content_types=['location'])
    dp.register_message_handler(NewOrderTo(*INSTANCES), content_types=['text'], state=OrderForm.location_from)
    dp.register_message_handler(NewOrderPrice(*INSTANCES), content_types=['text'], state=OrderForm.location_to)
    dp.register_callback_query_handler(DriverAccept(*INSTANCES), L('driver_accept'))
    dp.register_callback_query_handler(DriverRefuse(*INSTANCES), L('driver_refuse'))
    dp.register_callback_query_handler(DriverWait(*INSTANCES), L('driver_wait'))
    dp.register_callback_query_handler(DriverPick(*INSTANCES), L('driver_pick'))
    dp.register_callback_query_handler(DriverComplete(*INSTANCES), L('driver_complete'))
    dp.register_callback_query_handler(DriverCancel(*INSTANCES), L('driver_cancel'))
    dp.register_callback_query_handler(PassengerCancel(*INSTANCES), L('passenger_cancel'), state='*')
    
    logger.info('Handlers are registered')