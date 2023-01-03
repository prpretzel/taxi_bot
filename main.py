from aiogram import executor
from taxi_bot.create_bot import CreateBot
from taxi_bot.database_handler import DataBase

if __name__ == '__main__': 
    db = DataBase()
    bot = CreateBot()
    bot.register_handlers()
    executor.start_polling(
        bot.dp, 
        skip_updates=True, 
        on_startup=bot.startup, 
        on_shutdown=bot.shutdown
    )