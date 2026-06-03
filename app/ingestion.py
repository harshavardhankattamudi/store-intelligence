import uuid
import pandas as pd
from datetime import datetime
from dateutil import parser
from sqlalchemy.orm import Session
from app.models import DBEvent, DBSession, DBTransaction

def normalize_event(event_data: dict) -> dict:
    normalized = {}
    
    if "event_id" in event_data:
        normalized["event_id"] = event_data["event_id"]
    elif "queue_event_id" in event_data:
        normalized["event_id"] = event_data["queue_event_id"]
    else:
        normalized["event_id"] = str(uuid.uuid4())
        
    if "store_id" in event_data:
        normalized["store_id"] = event_data["store_id"]
    elif "store_code" in event_data:
        normalized["store_id"] = event_data["store_code"]
    else:
        normalized["store_id"] = "UNKNOWN"
        
    if "visitor_id" in event_data:
        normalized["visitor_id"] = event_data["visitor_id"]
    elif "id_token" in event_data:
        normalized["visitor_id"] = event_data["id_token"]
    elif "track_id" in event_data:
        normalized["visitor_id"] = f"TRK_{event_data['track_id']}"
    else:
        normalized["visitor_id"] = "UNKNOWN"
        
    normalized["camera_id"] = event_data.get("camera_id", "UNKNOWN")
    
    raw_type = event_data.get("event_type", "").upper()
    if raw_type == "ENTRY":
        normalized["event_type"] = "ENTRY"
    elif raw_type == "EXIT":
        normalized["event_type"] = "EXIT"
    elif raw_type in ["ZONE_ENTERED", "ZONE_ENTER"]:
        normalized["event_type"] = "ZONE_ENTER"
    elif raw_type in ["ZONE_EXITED", "ZONE_EXIT"]:
        normalized["event_type"] = "ZONE_EXIT"
    elif raw_type == "QUEUE_COMPLETED":
        normalized["event_type"] = "BILLING_QUEUE_JOIN"
    elif raw_type == "QUEUE_ABANDONED":
        normalized["event_type"] = "BILLING_QUEUE_ABANDON"
    else:
        normalized["event_type"] = raw_type
        
    ts_val = None
    for k in ["timestamp", "event_timestamp", "event_time", "queue_exit_ts", "queue_join_ts"]:
        if k in event_data and event_data[k]:
            ts_val = event_data[k]
            break
    normalized["timestamp"] = ts_val
    
    normalized["zone_id"] = event_data.get("zone_id")
    
    if "dwell_ms" in event_data:
        normalized["dwell_ms"] = event_data["dwell_ms"]
    elif "wait_seconds" in event_data:
        normalized["dwell_ms"] = int(event_data["wait_seconds"] * 1000)
    else:
        normalized["dwell_ms"] = 0
        
    normalized["is_staff"] = event_data.get("is_staff", False)
    normalized["confidence"] = event_data.get("confidence", 1.0)
    
    if "metadata" in event_data:
        normalized["metadata"] = event_data["metadata"]
    else:
        normalized["metadata"] = {
            "queue_depth": event_data.get("queue_position_at_join"),
            "sku_zone": event_data.get("zone_name"),
            "session_seq": None
        }
        
    return normalized

def ingest_events_batch(events_payload: list[dict], db: Session) -> dict:
    success_count = 0
    failed_events = []
    
    for raw_event in events_payload:
        try:
            event_data = normalize_event(raw_event)
            event_id = event_data["event_id"]
            
            exists = db.query(DBEvent).filter(DBEvent.event_id == event_id).first()
            if exists:
                success_count += 1
                continue

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
            failed_events.append({"error": str(e), "payload": raw_event})

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
    amount_col = "total_amount" if "total_amount" in df.columns else "NMV"
    
    df_agg = df.groupby("order_id").agg({
        "store_id": "first",
        "order_time": "first",
        "order_date": "first" if "order_date" in df.columns else lambda x: None,
        amount_col: "sum"
    }).reset_index()

    count = 0
    for _, row in df_agg.iterrows():
        txn_id = str(row["order_id"])
        exists = db.query(DBTransaction).filter(DBTransaction.transaction_id == txn_id).first()
        if not exists:
            if "order_date" in row and pd.notna(row["order_date"]):
                dt_str = f"{row['order_date']} {row['order_time']}"
                try:
                    dt = datetime.strptime(dt_str, "%d-%m-%Y %H:%M:%S")
                except:
                    try:
                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        dt = parser.parse(dt_str, dayfirst=True)
            else:
                dt_str = f"2026-04-10 {row['order_time']}"
                try:
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                except:
                    dt = parser.parse(dt_str)
                
            txn = DBTransaction(
                transaction_id=txn_id,
                store_id=str(row["store_id"]),
                timestamp=dt.replace(tzinfo=None),
                basket_value_inr=float(row[amount_col])
            )
            db.add(txn)
            count += 1
    db.commit()
    print(f"Imported {count} new POS transaction records.")
