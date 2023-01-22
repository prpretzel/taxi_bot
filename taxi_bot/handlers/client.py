from aiogram import types
from taxi_bot.handlers.base_handler import BaseHandler


class StartHandler(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        chat_id = message.from_user.id
        self.log_message(chat_id, message.message_id, -1, self, 'start_command')
        await self.send_message(chat_id, -1, self._config.messages['welcome_message'])
        if not await self.create_user(message):
            return
        text = self._config.messages['call_taxi_message']
        kb_name = 'passenger_call_taxi'
        await self.send_message(chat_id, -1, text, kb_name)


class HelpHandler(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        chat_id=message.from_user.id
        self.log_message(chat_id, message.message_id, -1, self, 'help_command')
        text=self._config.messages['help_message']
        await self.send_message(chat_id, -1, text)
        

class MemberStatus(BaseHandler):

    async def __call__(self, update: types.ChatMemberUpdated) -> None:
        chat_id = update.from_user.id
        activity_status = int(update.new_chat_member.is_chat_member())
        self._db.update_activity(chat_id, activity_status)
        self.log_info(chat_id, -1, -1, self, f'{activity_status}')
        

class UpdateContact(BaseHandler):

    async def __call__(self, message: types.Contact) -> None:
        chat_id = message.from_user.id
        phone_number = f'+{message.contact.phone_number}'
        self._db.update_phone_number(chat_id, phone_number)
        self.log_message(chat_id, message.message_id, -1, self, f'phone_number: {phone_number}')
        text=self._config.messages['call_taxi_message']
        kb_name='passenger_call_taxi'
        await self.send_message(chat_id, -1, text, kb_name)
        

class HideMessage(BaseHandler):

    async def __call__(self, callback_query: types.CallbackQuery) -> None:
        await self.delete_old_messages(message_id=callback_query.message.message_id)