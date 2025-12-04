import os
from abc import ABC
from datetime import datetime, timedelta

from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel


TG_API_ID = os.environ["TG_API_ID"]
TG_API_HASH = os.environ["TG_API_HASH"]
TG_PHONE_NUMBER = os.environ["TG_PHONE_NUMBER"]

client = TelegramClient("session_name", TG_API_ID, TG_API_HASH)


async def get_channel_messages_simple(channel_name, hours_back=24, min_id=0):
    """Simple function to get channel messages"""
    await client.start(TG_PHONE_NUMBER)

    time_boundary = datetime.now() - timedelta(hours=hours_back)
    channel = await client.get_entity(channel_name)

    messages = []
    async for msg in client.iter_messages(channel, min_id=min_id):
        if msg.date.replace(tzinfo=None) < time_boundary:
            break
        messages.append(msg)

    return messages
