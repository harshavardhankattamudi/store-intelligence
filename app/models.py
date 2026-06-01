from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON
from app.database import Base

class DBEvent(Base):
    __tablename__ = "events"

    event_id = Column(String, primary_key=True, index=True)
    store_id = Column(String, index=True)
    camera_id = Column(String)
    visitor_id = Column(String, index=True)
    event_type = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    zone_id = Column(String, nullable=True)
    dwell_ms = Column(Integer, default=0)
    is_staff = Column(Boolean, default=False)
    confidence = Column(Float)
    metadata_json = Column(JSON, nullable=True)

class DBSession(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    store_id = Column(String, index=True)
    visitor_id = Column(String, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime, nullable=True)
    is_staff = Column(Boolean, default=False)
    has_purchased = Column(Boolean, default=False)

class DBTransaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True, index=True)
    store_id = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    basket_value_inr = Column(Float)
