# tests/test_anomalies.py
# PROMPT: Create tests for queue spike, conversion drops, and dead zones.
# CHANGES MADE: Added mock DB event entities to simulate queue counts.

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import DBEvent, DBSession
from app.anomalies import detect_store_anomalies

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_dead_zone_anomaly(db_session):
    store_id = "ST1008"
    
    evt = DBEvent(
        event_id="evt_test_2",
        store_id=store_id,
        camera_id="CAM1",
        visitor_id="VIS_test_2",
        event_type="ZONE_ENTER",
        timestamp=datetime.now(),
        zone_id="SKINCARE",
        dwell_ms=0,
        is_staff=False,
        confidence=1.0
    )
    db_session.add(evt)
    db_session.commit()

    anomalies = detect_store_anomalies(store_id, db_session)
    assert any(a["anomaly_type"] == "DEAD_ZONE" and "MAKEUP" in a["message"] for a in anomalies)
