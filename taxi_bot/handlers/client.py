from aiogram import types
from taxi_bot.handlers.base_handler import BaseHandler


class StartHandler(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        """Shows welcome message and welcome keyboard. Creates user in db
        Args:
            message (types.Message)
        """
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        self._db.create_passenger(user_id, username, first_name, last_name, '')

        await self._bot.send_message(
            chat_id=user_id,
            text=self._config.messages['welcome_message'],
            reply_markup=self._kbs['passenger_call_taxi']
        )
        self._logger.info(self, message.from_user.id, 'User start')


class HelpHandler(BaseHandler):

    async def __call__(self, message: types.Message) -> None:
        """Shows help message and welcome keyboard
        Args:
            message (types.Message)
        """
        await self._bot.send_message(
            chat_id=message.from_user.id,
            text=self._config.messages['help_message'],
            reply_markup=self._kbs['help_menu']
        )
        self._logger.info(self, message.from_user.id, 'User help')
        




class UpdateContact(BaseHandler):

    async def __call__(self, message: types.Contact) -> None:
        user_id = message.from_user.id
        phone_number = '+' + str(message.contact.phone_number)
        self._db.update_phone_number(user_id, phone_number)