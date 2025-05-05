from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from database.models import Base
from utils.config import get_db_url

engine = create_engine(get_db_url())
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def init_db():
    Base.metadata.create_all(engine)

def get_session():
    session = Session()
    try:
        yield session
    finally:
        session.close()
