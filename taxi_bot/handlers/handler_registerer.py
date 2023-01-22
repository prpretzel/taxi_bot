from aiogram import Dispatcher, Bot
from taxi_bot.database_handler import DataBase
from taxi_bot.load_config import Config
from taxi_bot.logger import Logger

from taxi_bot.handlers.client import (
    StartHandler, 
    HelpHandler,
    UpdateContact,
    MemberStatus,
    HideMessage
)

from taxi_bot.handlers.driver_handler import (
    DriverJobApplience,
    JobHandler,
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

from taxi_bot.handlers.admin_menu import (
    InputMessage,
    AdminMenu,
    DriversStatus,
    InviteBroadcastMessage,
    CheckBroadcastMessage,
    BroadcastMessage,
    CancelBroadcast
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
    MODER_COND = lambda c: c.from_user.id in config.MODER_IDs + [config.ADMIN_ID]
    
    def L(startswith):
        return lambda c: c.data.startswith(startswith)

    # main handlers
    dp.register_message_handler(StartHandler(*INSTANCES), commands=['start'])
    dp.register_message_handler(StartHandler(*INSTANCES), commands=['restart'])
    dp.register_message_handler(UpdateContact(*INSTANCES), content_types=['contact'])
    dp.register_message_handler(HelpHandler(*INSTANCES), commands=['help'])
    dp.register_message_handler(JobHandler(*INSTANCES), commands=['job'])
    dp.register_callback_query_handler(HideMessage(*INSTANCES), L('hide_message'))
    dp.register_my_chat_member_handler(MemberStatus(*INSTANCES))

    # driver handlers
    dp.register_callback_query_handler(DriverJob(*INSTANCES), L('job'))
    dp.register_callback_query_handler(DriverContinueRegistration(*INSTANCES), L('driver_continue_registration'))
    dp.register_message_handler(DriverName(*INSTANCES), state=DriverJobApplience.name)
    dp.register_message_handler(DriverCar(*INSTANCES), state=DriverJobApplience.car)
    dp.register_callback_query_handler(DriverEndRegistration(*INSTANCES), L('driver_continue_registration'), state=DriverJobApplience.driver_id)
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
    
    # admin/moder menu
    dp.register_message_handler(AdminMenu(*INSTANCES), MODER_COND, commands=['admin'])
    dp.register_callback_query_handler(DriversStatus(*INSTANCES), MODER_COND, L('drivers_status'))
    dp.register_callback_query_handler(InviteBroadcastMessage(*INSTANCES), ADMIN_COND, L('invite_broadcast'))
    dp.register_message_handler(CheckBroadcastMessage(*INSTANCES), ADMIN_COND, state=InputMessage.invite_input)
    dp.register_callback_query_handler(BroadcastMessage(*INSTANCES), ADMIN_COND, L('broadcast'), state=InputMessage.message)
    dp.register_callback_query_handler(CancelBroadcast(*INSTANCES), ADMIN_COND, L('cancel_broadcast'), state='*')

    logger.info('Handlers are registered')

    