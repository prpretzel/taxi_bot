from aiogram import Dispatcher, Bot
from taxi_bot.database_handler import DataBase
from taxi_bot.load_config import Config
from taxi_bot.logger import Logger
from aiogram.dispatcher.filters import Text

from taxi_bot.handlers.client import (
    StartHandler, 
    HelpHandler,
    UpdateContact,
    MemberStatus,
    ReferralProgram,
    ReferralProgramRules,
    HideMessage,
    UnexpectedInput,
    CancelHandler
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
    DriverActiveOrder,
    DriverStopWork,
    DriverTopUpMenu,
    DriverTopUp
)

from taxi_bot.handlers.order_handler import (
    OrderForm,
    NewOrder,
    NewOrderFrom,
    NewOrderToText,
    NewOrderPrice,
    DriverAccept,
    DriverHide,
    DriverReturn,
    PassengerCancel,
    DriverCancel,
    DriverWait,
    DriverPick,
    DriverComplete
)

from taxi_bot.handlers.admin_menu import (
    InputMessage,
    AdminMenu,
    ModerMenu,
    DriversStatus,
    InviteBroadcastMessage,
    CheckBroadcastMessage,
    BroadcastMessage,
    OrderDetails,
    CancelBroadcast,
    DeleteOldLogs,
    UserInfo,
    OrderInfo,
    BanUser,
    BanDriver,
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
    
    # admin/moder menu
    dp.register_callback_query_handler(AdminMenu(*INSTANCES), MODER_COND, L('admin_menu'), state='*')
    dp.register_callback_query_handler(ModerMenu(*INSTANCES), MODER_COND, L('moder_menu'), state='*')
    dp.register_callback_query_handler(DriversStatus(*INSTANCES), MODER_COND, L('drivers_status'), state='*')
    dp.register_callback_query_handler(InviteBroadcastMessage(*INSTANCES), ADMIN_COND, L('invite_broadcast'))
    dp.register_message_handler(CheckBroadcastMessage(*INSTANCES), ADMIN_COND, state=InputMessage.invite_input)
    dp.register_callback_query_handler(BroadcastMessage(*INSTANCES), ADMIN_COND, L('broadcast'), state=InputMessage.message)
    dp.register_callback_query_handler(OrderDetails(*INSTANCES), ADMIN_COND, L('order_details'))
    dp.register_callback_query_handler(CancelBroadcast(*INSTANCES), ADMIN_COND, L('cancel_broadcast'), state='*')
    dp.register_callback_query_handler(DeleteOldLogs(*INSTANCES), ADMIN_COND, L('delete_old_logs'))
    dp.register_message_handler(UserInfo(*INSTANCES), ADMIN_COND, Text(startswith='user', ignore_case=True))
    dp.register_message_handler(OrderInfo(*INSTANCES), ADMIN_COND, Text(startswith='order', ignore_case=True))
    dp.register_callback_query_handler(BanUser(*INSTANCES), ADMIN_COND, L('ban_user'))
    dp.register_callback_query_handler(BanDriver(*INSTANCES), ADMIN_COND, L('ban_driver'))
    # main handlers
    dp.register_message_handler(StartHandler(*INSTANCES), commands=['start'], state='*')
    dp.register_message_handler(StartHandler(*INSTANCES), commands=['restart'], state='*')
    dp.register_message_handler(UpdateContact(*INSTANCES), content_types=['contact'])
    dp.register_message_handler(HelpHandler(*INSTANCES), commands=['help'], state='*')
    dp.register_message_handler(ReferralProgram(*INSTANCES), commands=['referral'], state='*')
    # dp.register_message_handler(ReferralProgramRules(*INSTANCES), commands=['rp_rules'], state='*')
    dp.register_message_handler(JobHandler(*INSTANCES), commands=['job'], state='*')
    dp.register_callback_query_handler(HideMessage(*INSTANCES), L('hide_message'), state='*')
    dp.register_message_handler(CancelHandler(*INSTANCES), commands=['cancel'], state='*')
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
    dp.register_callback_query_handler(DriverActiveOrder(*INSTANCES), L('driver_active_order'))
    dp.register_callback_query_handler(DriverStopWork(*INSTANCES), L('driver_end_work'))
    dp.register_callback_query_handler(DriverTopUpMenu(*INSTANCES), L('driver_topup_select'))
    dp.register_callback_query_handler(DriverTopUp(*INSTANCES), L('driver_topup'))

    # call a taxi handlers
    dp.register_callback_query_handler(NewOrder(*INSTANCES), L('call_taxi'), state='*')
    dp.register_message_handler(NewOrderFrom(*INSTANCES), content_types=['location', 'text'], state=OrderForm.order_id)
    dp.register_message_handler(NewOrderToText(*INSTANCES), content_types=['text'], state=OrderForm.location_from)
    dp.register_message_handler(NewOrderPrice(*INSTANCES), content_types=['text'], state=OrderForm.location_to)
    dp.register_callback_query_handler(DriverAccept(*INSTANCES), L('driver_accept'))
    dp.register_callback_query_handler(DriverHide(*INSTANCES), L('driver_hide'))
    dp.register_callback_query_handler(DriverReturn(*INSTANCES), L('driver_return'))
    dp.register_callback_query_handler(DriverWait(*INSTANCES), L('driver_wait'))
    dp.register_callback_query_handler(DriverPick(*INSTANCES), L('driver_pick'))
    dp.register_callback_query_handler(DriverComplete(*INSTANCES), L('driver_complete'))
    dp.register_callback_query_handler(DriverCancel(*INSTANCES), L('driver_cancel'))
    dp.register_callback_query_handler(PassengerCancel(*INSTANCES), L('passenger_cancel'), state='*')

    # unexpected input
    dp.register_message_handler(UnexpectedInput(*INSTANCES), content_types=['any'], state='*')
    dp.register_message_handler(CancelHandler(*INSTANCES), state='*')
    dp.register_callback_query_handler(CancelHandler(*INSTANCES), state='*')
    
    logger.info('Handlers are registered')
