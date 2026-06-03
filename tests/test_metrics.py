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

def test_flexible_schema_ingestion(db_session):
    from app.ingestion import ingest_events_batch, import_pos_csv
    import tempfile
    import os
    
    raw_events = [
        {"event_type":"entry","id_token":"ID_60001","store_code":"store_1076","camera_id":"cam1","event_timestamp":"2026-03-08T18:10:05.120000","is_staff":False,"gender_pred":"F","age_pred":28,"age_bucket":"25-34","is_face_hidden":False,"group_id":None,"group_size":None},
        {"event_type":"zone_entered","track_id":101,"store_id":"ST1076","camera_id":"CAM2","zone_id":"PURPLLE_MUM_1076_Z01","zone_name":"Left Shelf","zone_type":"SHELF","is_revenue_zone":"Yes","event_time":"2026-03-08T18:10:45.280000","zone_hotspot_x":412.6,"zone_hotspot_y":238.4,"gender":"F","age":28,"age_bucket":"25-34"},
        {"queue_event_id":"cfd8e3c5-7aa0-4ea3-9b59-692d50da8308","event_type":"queue_completed","track_id":102,"store_id":"ST1076","camera_id":"PURPLLE_MUM_1076_CAM6","zone_id":"PURPLLE_MUM_1076_Z_BILLING_01","zone_name":"Billing Counter Queue","zone_type":"BILLING","is_revenue_zone":"Yes","queue_join_ts":"2026-03-08T18:13:05.080000","queue_served_ts":"2026-03-08T18:13:13.240000","queue_exit_ts":"2026-03-08T18:15:31.840000","wait_seconds":8,"queue_position_at_join":2,"abandoned":False,"zone_hotspot_x":602.8,"zone_hotspot_y":183.4,"gender":"M","age":31,"age_bucket":"25-34"}
    ]
    
    result = ingest_events_batch(raw_events, db_session)
    assert result["success_count"] == 3
    assert len(result["errors"]) == 0
    
    csv_data = """order_id,order_date,order_time,store_id,product_id,brand_name,total_amount
1,10-04-2026,12:15:05,ST1008,399945,Faces Canada,302.33
1,10-04-2026,12:15:05,ST1008,353621,Faces Canada,491.77
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_data)
        temp_csv_path = f.name
        
    try:
        import_pos_csv(temp_csv_path, db_session)
        from app.models import DBTransaction
        txns = db_session.query(DBTransaction).all()
        assert len(txns) == 1
        assert txns[0].transaction_id == "1"
        assert round(txns[0].basket_value_inr, 2) == 794.10
    finally:
        os.remove(temp_csv_path)
