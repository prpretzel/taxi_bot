from aiogram import executor
from taxi_bot.create_bot import CreateBot
import sys

if __name__ == '__main__': 
    
    try:
        creds_path = sys.argv[1]
    except:
        creds_path = 'credentials_test.json'

    print(f'USED CREDENTIALS: {creds_path}')

    bot = CreateBot(creds_path)
    executor.start_polling(
        bot.dp, 
        skip_updates=True, 
        on_startup=bot.startup, 
        on_shutdown=bot.shutdown
    )
    