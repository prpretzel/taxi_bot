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
            self._config: dict = json.load(f)
        with open('credentials.json', encoding='UTF-8') as f:
            self._creds: dict = json.load(f)
        
        self.API_TOKEN = self._creds.get('TOKEN')
        self.PAYMENT_TOKEN = self._creds.get('PAYMENT_TOKEN')
        self.ADMIN_ID = self._creds.get('ADMIN_ID')
        self.MODER_IDs = self._creds.get('MODER_IDs')
        self.GCLOUD_CREDS_PATH = self._creds.get('GCLOUD_CREDS_PATH')
        self.INSTANCE_CONNECTION_NAME = self._creds.get('INSTANCE_CONNECTION_NAME')
        self.DB_HOST = self._creds.get('DB_HOST')
        self.DB_PORT = self._creds.get('DB_PORT')
        self.DB_USER = self._creds.get('DB_USER')
        self.DB_PASS = self._creds.get('DB_PASS')
        self.DB_NAME = self._creds.get('DB_NAME')
        self.messages = self._config.get('messages')
        self.buttons = self._config.get('buttons')
        self.database_path = self._config.get('database_path')

    def __repr__(self):
        
        return f"""
            ADMIN_ID: {self.ADMIN_ID}
            messages: {self.messages}
            buttons: {self.buttons}
            database_path: {self.database_path}
        """
