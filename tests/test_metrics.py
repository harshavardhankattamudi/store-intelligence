# tests/test_metrics.py
# PROMPT: Create unit tests for FastAPI endpoints validating metrics and funnel calculation.
# CHANGES MADE: Added session initialization setup and transaction mocks to ensure robust test execution.

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import DBEvent, DBSession, DBTransaction
from app.metrics import compute_store_metrics
from app.funnel import compute_store_funnel

# Set up test sqlite database
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

def test_metrics_and_funnel(db_session):
    # Setup test visitor session
    visitor_id = "VIS_test_1"
    store_id = "ST1008"
    timestamp = datetime(2026, 4, 10, 15, 0, 0)

    # 1. Add Entry Session
    sess = DBSession(
        session_id=f"SESS_{visitor_id}",
        store_id=store_id,
        visitor_id=visitor_id,
        start_time=timestamp,
        end_time=timestamp,
        is_staff=False,
        has_purchased=False
    )
    db_session.add(sess)

    # 2. Add Billing Zone Event
    evt = DBEvent(
        event_id="evt_test_1",
        store_id=store_id,
        camera_id="CAM5",
        visitor_id=visitor_id,
        event_type="ZONE_ENTER",
        timestamp=timestamp,
        zone_id="BILLING",
        dwell_ms=10000,
        is_staff=False,
        confidence=1.0
    )
    db_session.add(evt)

    # 3. Add Transaction within 5 minutes (e.g. 2 minutes later)
    txn = DBTransaction(
        transaction_id="txn_test_1",
        store_id=store_id,
        timestamp=datetime(2026, 4, 10, 15, 2, 0),
        basket_value_inr=1500.0
    )
    db_session.add(txn)
    db_session.commit()

    # Calculate metrics
    metrics = compute_store_metrics(store_id, db_session)
    assert metrics["unique_visitors"] == 1
    assert metrics["conversion_rate"] == 1.0
    assert metrics["total_gmv"] == 1500.0

    # Calculate funnel
    funnel = compute_store_funnel(store_id, db_session)
    assert len(funnel["stages"]) == 4
    assert funnel["stages"][0]["count"] == 1 # Entry
    assert funnel["stages"][2]["count"] == 1 # Billing Queue
    assert funnel["stages"][3]["count"] == 1 # Purchase
