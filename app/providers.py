from abc import ABC
from datetime import datetime


class Post:
    date: datetime
    content: str


class SourceProvider(ABC):
    def get_last_messages():
        pass
