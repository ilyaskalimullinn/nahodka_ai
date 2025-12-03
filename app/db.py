import os

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship


POSTGRES_DB = os.environ.get("POSTGRES_DB", "db")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "changeme")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")

DATABASE_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(DATABASE_URL)
Base = declarative_base()


class City(Base):
    __tablename__ = "city"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)
    top_k = Column(Integer, default=5)
    city_id = Column(Integer, ForeignKey("city.id"))
    city = relationship("City")


Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)
