import os
import uuid
from typing import Any
from decimal import Decimal

import bcrypt
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    String,
    ForeignKey,
    DateTime,
    Boolean,
    select,
    update,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
    relationship,
    Mapped,
    mapped_column,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from fastadmin import SqlAlchemyModelAdmin, register
from pgvector.sqlalchemy import Vector


POSTGRES_DB = os.environ.get("POSTGRES_DB", "db")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "changeme")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")

DATABASE_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
DATABASE_URL_ASYNC = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

async_engine = create_async_engine(DATABASE_URL_ASYNC)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


class City(Base):
    __tablename__ = "city"
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    def __repr__(self):
        return f"City<id={self.id}, name={self.name}>"


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    first_name = Column(String, nullable=False)
    top_k = Column(Integer, default=5)
    city_id = Column(BigInteger, ForeignKey("city.id"))
    city = relationship("City")

    def __repr__(self):
        return f"User<id={self.id}, first_name={self.first_name}>"


class TelegramChannelMessage(Base):
    __tablename__ = "telegram_channel_message"
    __table_args__ = (
        UniqueConstraint("message_id", "channel_id", name="uq_message_id_channel_id"),
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, nullable=False)
    grouped_id = Column(BigInteger, nullable=True)
    date = Column(DateTime, nullable=False)
    channel_id = Column(
        BigInteger, ForeignKey("telegram_channel_source.channel_id"), nullable=False
    )
    photo_id = Column(BigInteger, nullable=True)
    message_text = Column(String, nullable=False, default="")

    def __repr__(self):
        return f"TelegramChannelMessage<id={self.id}, message_id={self.message_id}, grouped_id={self.grouped_id}, date={self.date}>"


class TelegramChannelSource(Base):
    __tablename__ = "telegram_channel_source"
    id = Column(BigInteger, primary_key=True)
    city_id = Column(BigInteger, ForeignKey("city.id"))
    channel_id = Column(BigInteger, unique=True, nullable=False)

    city = relationship("City")

    def __repr__(self):
        return f"TelegramChannelSource<id={self.id}, city_id={self.city_id}>"


class UserForAuth(Base):
    __tablename__ = "user_for_auth"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    username: Mapped[str] = mapped_column(String(length=255), nullable=False)
    hash_password: Mapped[str] = mapped_column(String(length=255), nullable=False)
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=True
    )  # Must be True for admin access
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __str__(self):
        return self.username


class FixedSqlAlchemyModelAdmin(SqlAlchemyModelAdmin):
    """Custom admin class that fixes BigInteger serialization issues"""

    async def _deserialize_request_data(self, data: dict) -> dict:
        """Convert string IDs to integers before processing"""
        if not data:
            return data

        result = {}
        model_columns = {col.name: col for col in self.model_cls.__table__.columns}

        for key, value in data.items():
            if key in model_columns:
                column = model_columns[key]
                # Convert string to int for BigInteger columns
                if isinstance(column.type, BigInteger) and isinstance(value, str):
                    try:
                        result[key] = int(value)
                    except (ValueError, TypeError):
                        result[key] = value
                # Handle Decimal fields
                elif (
                    hasattr(column.type, "asdecimal")
                    and column.type.asdecimal
                    and isinstance(value, str)
                ):
                    try:
                        result[key] = Decimal(value)
                    except:
                        result[key] = value
                else:
                    result[key] = value
            else:
                result[key] = value

        return result

    async def save_model(self, obj_id: int | None, data: dict) -> int:
        """Override save to fix data types before saving"""
        fixed_data = await self._deserialize_request_data(data)
        return await super().save_model(obj_id, fixed_data)

    async def get_model(self, obj_id: int) -> dict | None:
        """Ensure BigInteger IDs are serialized as strings for JSON"""
        result = await super().get_model(obj_id)
        if result:
            model_columns = {col.name: col for col in self.model_cls.__table__.columns}
            for key, value in result.items():
                if key in model_columns and isinstance(
                    model_columns[key].type, BigInteger
                ):
                    # Convert BigInteger to string for JSON serialization
                    if value is not None:
                        result[key] = str(value)
        return result


@register(UserForAuth, sqlalchemy_sessionmaker=AsyncSessionLocal)
class UserAdmin(FixedSqlAlchemyModelAdmin):
    exclude = ("hash_password",)
    list_display = ("id", "username", "is_superuser", "is_active")
    list_display_links = ("id", "username")
    list_filter = ("id", "username", "is_superuser", "is_active")
    search_fields = ("username",)

    async def authenticate(
        self, username: str, password: str
    ) -> uuid.UUID | int | None:
        sessionmaker = self.get_sessionmaker()
        async with sessionmaker() as session:
            query = select(self.model_cls).filter_by(
                username=username, is_superuser=True
            )
            result = session.scalars(query)
            obj = result.first()
            if not obj:
                return None
            if not bcrypt.checkpw(password.encode(), obj.hash_password.encode()):
                return None
            return obj.id

    async def change_password(self, id: uuid.UUID | int, password: str) -> None:
        sessionmaker = self.get_sessionmaker()
        async with sessionmaker() as session:
            hash_password = hash_password(password)
            query = (
                update(self.model_cls)
                .where(UserForAuth.id.in_([id]))
                .values(hash_password=hash_password)
            )
            await session.execute(query)
            await session.commit()

    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    async def orm_save_upload_field(self, obj: Any, field: str, base64: str) -> None:
        sessionmaker = self.get_sessionmaker()
        async with sessionmaker() as session:
            # convert base64 to bytes, upload to s3/filestorage, get url and save or save base64 as is to db (don't recomment it)
            query = (
                update(self.model_cls)
                .where(UserForAuth.id.in_([obj.id]))
                .values(**{field: base64})
            )
            await session.execute(query)
            await session.commit()


@register(City, sqlalchemy_sessionmaker=AsyncSessionLocal)
class CityAdmin(FixedSqlAlchemyModelAdmin):
    list_display = ("id", "name")
    list_display_links = ("id", "name")
    search_fields = ("id", "name")
    list_filter = ("id", "name")

    form_fields = ("id", "name")


@register(TelegramChannelSource, sqlalchemy_sessionmaker=AsyncSessionLocal)
class TelegramChannelSourceAdmin(FixedSqlAlchemyModelAdmin):
    list_display = ("id", "city_id", "channel_id")
    list_display_links = ("id", "city_id", "channel_id")
    search_fields = ("id", "city_id", "channel_id")
    list_filter = ("id", "city_id", "channel_id")

    form_fields = ("id", "city_id", "channel_id")


@register(TelegramChannelMessage, sqlalchemy_sessionmaker=AsyncSessionLocal)
class TelegramChannelMessageAdmin(FixedSqlAlchemyModelAdmin):
    expand_relationships = False
    # Specify EXACTLY what you want to see (no magic relationship expansion)
    list_display = (
        "id",
        "message_id",
        "grouped_id",
        "date",
        "channel_id",  # Shows as number
        "photo_id",  # Shows as number
        "message_text",
    )

    # Don't link everything, just the ID
    list_display_links = ("id",)

    # Only search on text fields
    search_fields = ("message_text",)

    # Filter only on specific fields
    list_filter = ("date",)

    # Form configuration
    form_fields = list_display

    # Use this to prevent automatic relationship widgets
    form_widget_overrides = {
        "channel_id": {"type": "number", "min": 1, "step": 1},
        "photo_id": {"type": "number", "min": 1, "step": 1},
    }


Base.metadata.create_all(engine)
