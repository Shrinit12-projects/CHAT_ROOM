from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import dotenv

dotenv.load_dotenv()

# SQLAlchemy setup
print(os.getenv("DATABASE_URL"))
DATABASE_URL =  os.getenv("DATABASE_URL") # SQLite database file in the current directory

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the ChatMessage model
class ChatMessage(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, index=True)
    message = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Create the database tables

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()