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

    def __init__(self) -> None:
        with open('config.json', encoding='UTF-8') as f:
            self._config = json.load(f)
        with open('credentials.json', encoding='UTF-8') as f:
            self._creds = json.load(f)
        
        self.API_TOKEN = self._creds['TOKEN']
        self.ADMIN_ID = self._creds['ADMIN_ID']
        self.MODER_IDs = self._creds['MODER_IDs']
        self.messages = self._config['messages']
        self.buttons = self._config['buttons']
        self.database_path = self._config['database_path']

    def __repr__(self):
        
        return f"""
            ADMIN_ID: {self.ADMIN_ID}
            messages: {self.messages}
            buttons: {self.buttons}
            database_path: {self.database_path}
        """
