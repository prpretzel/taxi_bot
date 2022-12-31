import os
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram import Bot, Dispatcher, types
from taxi_bot.database_handler import DataBase
from taxi_bot.load_config import Config
from taxi_bot.handlers.handler_registerer import register_handlers as RH
from taxi_bot.buttons import get_kbs
from taxi_bot.logger import Logger


class CreateBot:

    def __init__(self):
        self.config = Config()
        self.bot = Bot(token=self.config.API_TOKEN)
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.dp.middleware.setup(LoggingMiddleware())
        self.kbs = get_kbs(self.config.buttons)
        self.db = DataBase()
        self.logger = Logger()
        self.logger.info(self, '', 'Bot and Dispatcher are initiated <-------')

    def register_handlers(self):
        RH(self.db, self.bot, self.config, self.kbs, self.dp, self.logger)
        self.logger.info(self, '', 'Handler registerer is initiated')

    async def startup(self, _):
        bot_commands = [
            types.BotCommand(command='/start', description='Welcome Page'),
            types.BotCommand(command='/help', description='Help Page')
        ]
        await self.bot.set_my_commands(bot_commands)

    async def shutdown(self, _):
        await self.dp.storage.close()
        await self.dp.storage.wait_closed()
        self.logger.info(self, '', '----------Bot stopped----------')