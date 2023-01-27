# from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import Dict


def keyboard_generator(kb_config: dict, suffix: str=''):
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

    suffix = '@' + str(suffix) if suffix else ''
    kb_type = kb_config.get('type')
    kb_layout = kb_config.get('layout')
    buttons = kb_config.get('buttons')
    placeholder = kb_config.get('placeholder')
    if kb_type=='inline':
        keyboard = InlineKeyboardMarkup()
        button_type = InlineKeyboardButton
    elif kb_type=='reply':
        keyboard = ReplyKeyboardMarkup(
            resize_keyboard=True, 
            input_field_placeholder=placeholder
        )
        button_type = KeyboardButton
    else:
        print('Keyboard error')
    buttons_list = list()
    for button in buttons:
        options = button.get('options')
        options = options if options else list()
        request_contact = True if 'request_contact' in options else False
        request_location = True if 'request_location' in options else False
        buttons_list.append(button_type(
            button.get('text'), 
            callback_data=button.get('data')+suffix,
            request_contact=request_contact,
            request_location=request_location,
            )
        )    
    shift = 0
    for i in kb_layout:
        keyboard.row(*buttons_list[shift:shift+i])
        shift += i
    
    return keyboard



def get_kbs(keyboard_configs: dict, data_suffix: str=''):
    return {kb_id:keyboard_generator(kb_config, data_suffix) for kb_id, kb_config in keyboard_configs.items()}