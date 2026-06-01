from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models import DBEvent

def run_health_check(db: Session) -> dict:
    try:
        db.execute(text("SELECT 1"))
        db_status = "HEALTHY"
    except Exception as e:
        return {
            "status": "UNHEALTHY",
            "error": f"Database connection failure: {str(e)}",
            "feeds": {}
        }

    stores = db.query(DBEvent.store_id).distinct().all()
    feeds = {}
    overall_status = "HEALTHY"
    now = datetime.now()

    for (store_id,) in stores:
        last_evt = db.query(DBEvent).filter(DBEvent.store_id == store_id).order_by(DBEvent.timestamp.desc()).first()
        if last_evt:
            lag_seconds = (now - last_evt.timestamp).total_seconds()
            status = "HEALTHY"
            
            if lag_seconds > 600:
                status = "STALE_FEED"
                overall_status = "WARN"
                
            feeds[store_id] = {
                "last_event_timestamp": last_evt.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lag_seconds": round(lag_seconds),
                "status": status
            }

    return {
        "status": overall_status,
        "database": db_status,
        "feeds": feeds
    }
