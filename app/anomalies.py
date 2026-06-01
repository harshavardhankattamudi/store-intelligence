from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import DBEvent, DBSession

def detect_store_anomalies(store_id: str, db: Session) -> list[dict]:
    anomalies = []
    now = datetime.now()

    last_event = db.query(DBEvent).filter(DBEvent.store_id == store_id).order_by(DBEvent.timestamp.desc()).first()
    if not last_event:
        return []

    ref_time = last_event.timestamp

    active_in_queue = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        DBEvent.zone_id == "BILLING",
        DBEvent.event_type == "ZONE_ENTER",
        DBEvent.is_staff == False
    ).distinct().all()

    active_exits = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        DBEvent.zone_id == "BILLING",
        DBEvent.event_type == "ZONE_EXIT",
        DBEvent.is_staff == False
    ).distinct().all()

    queue_depth = len(set([x[0] for x in active_in_queue]) - set([x[0] for x in active_exits]))

    if queue_depth > 3:
        anomalies.append({
            "anomaly_type": "BILLING_QUEUE_SPIKE",
            "severity": "WARN",
            "message": f"Queue buildup detected at billing! Current depth is {queue_depth}.",
            "suggested_action": "Deploy additional billing staff to counter zones immediately."
        })

    total_sess = db.query(DBSession).filter(DBSession.store_id == store_id).count()
    if total_sess >= 5:
        purchased = db.query(DBSession).filter(DBSession.store_id == store_id, DBSession.has_purchased == True).count()
        conv_rate = purchased / total_sess
        if conv_rate < 0.15:
            anomalies.append({
                "anomaly_type": "CONVERSION_DROP",
                "severity": "CRITICAL",
                "message": f"Conversion rate is critically low at {round(conv_rate * 100, 1)}%!",
                "suggested_action": "Verify if billing system or checkout counter is operating normally."
            })

    fifteen_min_ago = ref_time - timedelta(minutes=15)
    for zone in ["SKINCARE", "MAKEUP"]:
        recent_visits = db.query(DBEvent).filter(
            DBEvent.store_id == store_id,
            DBEvent.zone_id == zone,
            DBEvent.timestamp >= fifteen_min_ago
        ).count()

        if recent_visits == 0:
            anomalies.append({
                "anomaly_type": "DEAD_ZONE",
                "severity": "INFO",
                "message": f"No visitor presence recorded in {zone} zone for over 15 minutes.",
                "suggested_action": "Inspect if displays/shelves in the zone require restocking or visual adjustments."
            })

    return anomalies
