from aiogram import types
from taxi_bot.handlers.base_handler import BaseHandler
from aiogram.dispatcher import FSMContext


class StartHandler(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        chat_id, message_id, order_id, optionals = await self.message_data(message)
        referral = optionals['text'].replace(r'/start', '').replace(r' ', '')
        referral = referral[:20] if referral else None
        await self.create_user(message, referral, False)
        await self.send_message(chat_id, order_id, self._config.messages['welcome_message'], delete_old=True)
        await self.send_message(chat_id, order_id, self._config.messages['call_taxi_message'], 'passenger_call_taxi')


class HelpHandler(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        chat_id, message_id, order_id, optionals = await self.message_data(message)
        text = self._config.messages['help_message'].format(self._config.BOT_SUPPORT, chat_id)
        await self.send_message(chat_id, order_id, text, 'passenger_call_taxi', delete_old=True)
        

class MemberStatus(BaseHandler):

    async def __call__(self, update: types.ChatMemberUpdated) -> None:
        chat_id = update.from_user.id
        activity_status = int(update.new_chat_member.is_chat_member())
        self._db.update_activity(chat_id, activity_status)
        self.log_info(chat_id, None, None, self, f'{activity_status}')
        

class ReferralProgram(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        chat_id, message_id, order_id, optionals = await self.message_data(message)
        link = self.get_referral_link(chat_id)
        await self.send_message(chat_id, order_id, self._config.messages['rp_text'], delete_old=True)
        await self.send_message(chat_id, order_id, link)
        

class ReferralProgramRules(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        chat_id, message_id, order_id, optionals = await self.message_data(message)
        await self.send_message(chat_id, order_id, self._config.messages['rp_rules'])
        

class UpdateContact(BaseHandler):

    async def __call__(self, message: types.contact.Contact) -> None:
        chat_id, message_id, order_id, optionals = await self.message_data(message)
        phone_number = optionals['phone_number']
        self._db.update_phone_number(chat_id, phone_number)
        await self.discard_reply_markup(chat_id, order_id)
        await self.send_message(chat_id, None, self._config.messages['check_phone_number'].format(phone_number), delete_old=True)
        await self.send_message(chat_id, None, self._config.messages['call_taxi_message'], 'passenger_call_taxi')
        

class HideMessage(BaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id, message_id, order_id, optionals = await self.message_data(callback_query)
        await self.delete_old_messages(message_id=message_id, force=True)
        

class UnexpectedInput(BaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        chat_id, message_id, order_id, optionals = await self.message_data(message)
        if await state.get_state():
            await state.finish()
        await self.send_message(chat_id, order_id, self._config.messages['call_taxi_message'], 'passenger_call_taxi')
        

class CancelHandler(BaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        chat_id, message_id, order_id, optionals = await self.message_data(message)
        await self.send_message(chat_id, order_id, self._config.messages['call_taxi_message'], 'passenger_call_taxi', delete_old=True)
        if await state.get_state():
            await state.finish()
