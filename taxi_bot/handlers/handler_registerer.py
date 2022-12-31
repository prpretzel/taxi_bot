from aiogram import Dispatcher, Bot
from taxi_bot.database_handler import DataBase
from taxi_bot.load_config import Config
from taxi_bot.logger import Logger

from taxi_bot.handlers.client import (
    StartHandler, 
    HelpHandler,
    UpdateContact
)

from taxi_bot.handlers.driver_handler import (
    DriverMenu,
    DriverStatus
)

from taxi_bot.handlers.order_handler import (
    NewOrder,
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
    
    # main handlers
    dp.register_message_handler(StartHandler(*INSTANCES), commands=['start'])
    dp.register_message_handler(StartHandler(*INSTANCES), commands=['restart'])
    dp.register_message_handler(HelpHandler(*INSTANCES), commands=['help'])
    dp.register_message_handler(UpdateContact(*INSTANCES), content_types=['contact'])

    # driver handlers
    dp.register_callback_query_handler(DriverMenu(*INSTANCES), lambda c: c.data.startswith('job'))
    dp.register_callback_query_handler(DriverStatus(*INSTANCES), lambda c: c.data in ['driver_end_work', 'driver_start_work'])

    # call a taxi handlers
    dp.register_message_handler(NewOrder(*INSTANCES), content_types=['location'])
    dp.register_callback_query_handler(DriverAccept(*INSTANCES), lambda c: c.data.startswith('driver_accept'))
    dp.register_callback_query_handler(DriverRefuse(*INSTANCES), lambda c: c.data.startswith('driver_refuse'))
    dp.register_callback_query_handler(DriverWait(*INSTANCES), lambda c: c.data.startswith('driver_wait'))
    dp.register_callback_query_handler(DriverPick(*INSTANCES), lambda c: c.data.startswith('driver_pick'))
    dp.register_callback_query_handler(DriverComplete(*INSTANCES), lambda c: c.data.startswith('driver_complete'))
    dp.register_callback_query_handler(DriverCancel(*INSTANCES), lambda c: c.data.startswith('driver_cancel'))
    dp.register_callback_query_handler(PassengerCancel(*INSTANCES), lambda c: c.data.startswith('passenger_cancel'))
    
    logger.info('Handlers are registered')
