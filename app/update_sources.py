import asyncio
import argparse
import logging

from dotenv import load_dotenv
from sqlalchemy import func

load_dotenv()

from db import City, SessionLocal, TelegramChannelMessage, TelegramChannelSource
from providers import get_channel_messages_simple
from model import model_service, ModelService


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--city_id", help="City ID to update. If None, then all cities", type=int
    )
    parser.add_argument(
        "--number_of_hours", help="Number of hours to get updates", default=72
    )

    return parser.parse_args()


async def main():
    session = SessionLocal()

    args = parse_args()

    if args.city_id is None:
        cities = session.query(City).all()
    else:
        cities = [session.get(City, args.city_id)]

    all_messages = []

    for city in cities:
        print(f"Updating for {city}")

        channels = (
            session.query(TelegramChannelSource)
            .filter(TelegramChannelSource.city_id == city.id)
            .all()
        )

        for channel in channels:

            last_message_id_for_channel: int = (
                session.query(func.max(TelegramChannelMessage.message_id))
                .filter(TelegramChannelMessage.channel_id == channel.channel_id)
                .scalar()
            )
            print(f"last_message_id_for_channel is None")
            if last_message_id_for_channel is None:
                last_message_id_for_channel = 0

            print(
                f"Updating for {channel}, last_message_id_for_channel={last_message_id_for_channel}"
            )

            channel_messages = await get_channel_messages_simple(
                channel.channel_id,
                hours_back=args.number_of_hours,
                min_id=last_message_id_for_channel,
            )
            all_messages.extend(channel_messages)

    print(f"Gathered {len(all_messages)} messages. Converting to ORM style")

    messages_to_insert = []
    for msg in all_messages:
        msg_object = process_tg_message(msg, model_service=model_service)
        messages_to_insert.append(msg_object)

    print(f"Total {len(messages_to_insert)} messages to save in DB")
    session.add_all(messages_to_insert)
    session.commit()
    print("Saving finished")


def process_tg_message(msg, model_service: ModelService) -> TelegramChannelMessage:
    photo_id = None
    if msg.media is not None:
        if msg.media.photo is not None:
            photo_id = msg.media.photo.id

    embedding = None
    if msg.message is not None and len(msg.message) > 0:
        embedding = model_service.encode_text(msg.message)

    msg_object = TelegramChannelMessage(
        message_id=msg.id,
        grouped_id=msg.grouped_id,
        date=msg.date,
        channel_id=msg.peer_id.channel_id,
        photo_id=photo_id,
        message_text=msg.message,
        embedding=embedding,
    )
    return msg_object


if __name__ == "__main__":
    asyncio.run(main())
