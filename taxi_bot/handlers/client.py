from aiogram import types
from taxi_bot.handlers.base_handler import BaseHandler


class StartHandler(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        if not await self.create_user(message):
            return

        await self._bot.send_message(
            chat_id=message.from_user.id,
            text=self._config.messages['call_taxi_message'],
            reply_markup=self._kbs['passenger_call_taxi']
        )
        self._logger.info(self, message.from_user.id, 'User start')


class HelpHandler(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        await self._bot.send_message(
            chat_id=message.from_user.id,
            text=self._config.messages['help_message']
        )
        self._logger.info(self, message.from_user.id, 'User help')
        

class MemberStatus(BaseHandler):

    async def __call__(self, update: types.ChatMemberUpdated) -> None:
        user_id = update.from_user.id
        activity_status = int(update.new_chat_member.is_chat_member())
        self._db.update_activity(user_id, activity_status)
        self._logger.info(self, update.from_user.id, 'User Member')
        

class UpdateContact(BaseHandler):

    async def __call__(self, message: types.Contact) -> None:
        user_id = message.from_user.id
        phone_number = '+' + str(message.contact.phone_number)
        self._db.update_phone_number(user_id, phone_number)

        await self._bot.send_message(
            chat_id=user_id,
            text=self._config.messages['call_taxi_message'],
            reply_markup=self._kbs['passenger_call_taxi']
        )