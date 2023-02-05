from aiogram import types
from taxi_bot.handlers.base_handler import BaseHandler
from aiogram.dispatcher import FSMContext


class StartHandler(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(message)
        referral = optionals['text'].replace(r'/start', '').replace(r' ', '')
        referral = referral if referral else None
        await self.delete_old_messages(chat_id=chat_id)
        await self.send_message(chat_id, order_id, self._config.messages['welcome_message'])
        if not await self.create_user(message, referral):
            return
        await self.send_message(chat_id, order_id, self._config.messages['call_taxi_message'], 'passenger_call_taxi')


class HelpHandler(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(message)
        text = self._config.messages['help_message'] + f"\n Ваш ID: <code>{chat_id}</code>"
        await self.send_message(chat_id, order_id, text, 'passenger_call_taxi')
        

class MemberStatus(BaseHandler):

    async def __call__(self, update: types.ChatMemberUpdated) -> None:
        chat_id = update.from_user.id
        activity_status = int(update.new_chat_member.is_chat_member())
        self._db.update_activity(chat_id, activity_status)
        self.log_info(chat_id, None, None, self, f'{activity_status}')
        

class ReferralProgram(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(message)
        link = f"https://t.me/Taxi_boguchar_bot?start={chat_id}"
        await self.send_message(chat_id, order_id, 'Текст для реферальной программы')
        await self.send_message(chat_id, order_id, link)
        

class UpdateContact(BaseHandler):

    async def __call__(self, message: types.contact.Contact) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(message)
        phone_number = optionals['phone_number']
        self._db.update_phone_number(chat_id, phone_number)
        await self.discard_reply_markup(chat_id, order_id)
        await self.send_message(chat_id, None, f'Пожалуйста, удостовертись в том, что указанный Вами номер телефона ({phone_number}) является активным. В ином случае напишите в поддержку @Boguchar_taxi_support')
        await self.send_message(chat_id, None, self._config.messages['call_taxi_message'], 'passenger_call_taxi')
        

class HideMessage(BaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(callback_query)
        await self.delete_old_messages(message_id=message_id)
        

class UnexpectedInput(BaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(message)
        if await state.get_state():
            await state.finish()
        await self.send_message(chat_id, order_id, self._config.messages['call_taxi_message'], 'passenger_call_taxi')
        

class CancelHandler(BaseHandler):

    async def __call__(self, message: types.Message, state: FSMContext) -> None:
        chat_id, message_id, order_id, optionals = self.message_data(message)
        await self.delete_old_messages(chat_id=chat_id)
        await self.send_message(chat_id, order_id, self._config.messages['call_taxi_message'], 'passenger_call_taxi')
        if await state.get_state():
            await state.finish()
