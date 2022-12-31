from aiogram import executor
from taxi_bot.create_bot import CreateBot
from taxi_bot.database_handler import DataBase

if __name__ == '__main__': 
    db = DataBase()
    db.create_driver(402112818, 'pr_pretzel', '', '', '+79042105840', 'Вишневая девятка Е777КХ')
    db.create_driver(5513163225, 'Nikita', '', '', '88005553535', 'Белый Мерседес В195КН')

    bot = CreateBot()
    bot.register_handlers()
    executor.start_polling(
        bot.dp, 
        skip_updates=True, 
        on_startup=bot.startup, 
        on_shutdown=bot.shutdown
    )