from dataclasses import dataclass
import json
from xlrd import open_workbook_xls as open_xls
from typing import List, Dict

@dataclass(init=False)
class Config:
    
    API_TOKEN : str
    PAYMENT_TOKEN : str
    ADMIN_ID : str
    MODER_IDs : List[str]
    messages : Dict
    buttons : List

    def __init__(self, creds_path) -> None:
        with open('config.json', encoding='UTF-8') as f:
            self._config: dict = json.load(f)
        with open(creds_path, encoding='UTF-8') as f:
            self._creds: dict = json.load(f)
        
        self.API_TOKEN = self._creds.get('TOKEN')
        self.PAYMENT_TOKEN = self._creds.get('PAYMENT_TOKEN')
        self.ADMIN_ID = self._creds.get('ADMIN_ID')
        self.MODER_IDs = self._creds.get('MODER_IDs')
        self.BOT_LINK = self._creds.get('BOT_LINK')
        self.BOT_SUPPORT = self._creds.get('BOT_SUPPORT')
        self.VK_LINK = self._creds.get('VK_LINK')
        self.messages = {name.value: text.value for name, text in open_xls('messages.xls').sheet_by_index(0)}
        self.buttons = self._config.get('buttons')

    def __repr__(self):
        
        return f"""Empty"""
