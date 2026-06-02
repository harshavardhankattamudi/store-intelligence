import pandas as pd
from datetime import datetime
from dateutil import parser
from sqlalchemy.orm import Session
from app.models import DBEvent, DBSession, DBTransaction

def ingest_events_batch(events_payload: list[dict], db: Session) -> dict:
    success_count = 0
    failed_events = []
    
    for event_data in events_payload:
        event_id = event_data.get("event_id")
        if not event_id:
            failed_events.append({"error": "Missing event_id", "payload": event_data})
            continue

        exists = db.query(DBEvent).filter(DBEvent.event_id == event_id).first()
        if exists:
            success_count += 1
            continue

        try:
            timestamp = parser.parse(event_data["timestamp"]).replace(tzinfo=None)
            db_event = DBEvent(
                event_id=event_id,
                store_id=event_data["store_id"],
                camera_id=event_data["camera_id"],
                visitor_id=event_data["visitor_id"],
                event_type=event_data["event_type"],
                timestamp=timestamp,
                zone_id=event_data.get("zone_id"),
                dwell_ms=event_data.get("dwell_ms", 0),
                is_staff=event_data.get("is_staff", False),
                confidence=event_data.get("confidence", 1.0),
                metadata_json=event_data.get("metadata", {})
            )
            db.add(db_event)
            _upsert_session(db_event, db)
            success_count += 1
        except Exception as e:
            failed_events.append({"error": str(e), "event_id": event_id})

    db.commit()
    return {"success_count": success_count, "errors": failed_events}

def _upsert_session(db_event: DBEvent, db: Session):
    if db_event.is_staff:
        return

    visitor_id = db_event.visitor_id
    store_id = db_event.store_id
    timestamp = db_event.timestamp

    session = db.query(DBSession).filter(
        DBSession.visitor_id == visitor_id,
        DBSession.store_id == store_id
    ).first()

    if not session:
        for obj in db.new:
            if isinstance(obj, DBSession) and obj.visitor_id == visitor_id and obj.store_id == store_id:
                session = obj
                break
                
    if not session:
        session = db.get(DBSession, f"SESS_{visitor_id}")

    if not session:
        session = DBSession(
            session_id=f"SESS_{visitor_id}",
            store_id=store_id,
            visitor_id=visitor_id,
            start_time=timestamp,
            end_time=timestamp,
            is_staff=False,
            has_purchased=False
        )
        db.add(session)
    else:
        if timestamp < session.start_time:
            session.start_time = timestamp
        if timestamp > session.end_time:
            session.end_time = timestamp

        if db_event.event_type == "EXIT":
            session.end_time = timestamp

def import_pos_csv(csv_path: str, db: Session):
    df = pd.read_csv(csv_path)
    df_agg = df.groupby("order_id").agg({
        "store_id": "first",
        "order_time": "first",
        "NMV": "sum"
    }).reset_index()

    count = 0
    for _, row in df_agg.iterrows():
        txn_id = str(row["order_id"])
        exists = db.query(DBTransaction).filter(DBTransaction.transaction_id == txn_id).first()
        if not exists:
            dt_str = f"2026-04-10 {row['order_time']}"
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            except:
                dt = parser.parse(dt_str)
                
            txn = DBTransaction(
                transaction_id=txn_id,
                store_id=str(row["store_id"]),
                timestamp=dt,
                basket_value_inr=float(row["NMV"])
            )
            db.add(txn)
            count += 1
    db.commit()
    print(f"Imported {count} new POS transaction records.")
