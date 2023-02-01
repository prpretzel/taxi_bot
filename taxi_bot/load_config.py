from dataclasses import dataclass
import json
from typing import List

@dataclass(init=False)
class Config:
    
    API_TOKEN : str
    ADMIN_ID : str
    MODER_IDs : str
    messages : List
    buttons : List
    database_path : str

    def __init__(self, creds_path) -> None:
        with open('config.json', encoding='UTF-8') as f:
            self._config: dict = json.load(f)
        with open(creds_path, encoding='UTF-8') as f:
            self._creds: dict = json.load(f)
        
        self.API_TOKEN = self._creds.get('TOKEN')
        self.PAYMENT_TOKEN = self._creds.get('PAYMENT_TOKEN')
        self.ADMIN_ID = self._creds.get('ADMIN_ID')
        self.MODER_IDs = self._creds.get('MODER_IDs')
        self.messages = self._config.get('messages')
        self.buttons = self._config.get('buttons')

    def __repr__(self):
        
        return f"""Empty"""
