from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import DBEvent, DBSession, DBTransaction

def compute_store_metrics(store_id: str, db: Session) -> dict:
    visitors = db.query(DBSession).filter(
        DBSession.store_id == store_id,
        DBSession.is_staff == False
    ).all()
    unique_visitors_count = len(visitors)

    txns = db.query(DBTransaction).filter(DBTransaction.store_id == store_id).all()
    
    billing_events = db.query(DBEvent).filter(
        DBEvent.store_id == store_id,
        DBEvent.zone_id == "BILLING",
        DBEvent.is_staff == False
    ).all()

    converted_visitors = set()
    total_gmv = 0.0

    for txn in txns:
        total_gmv += txn.basket_value_inr
        txn_time = txn.timestamp
        for evt in billing_events:
            time_diff = (txn_time - evt.timestamp).total_seconds()
            if 0 <= time_diff <= 300:
                converted_visitors.add(evt.visitor_id)
                sess = db.query(DBSession).filter(DBSession.visitor_id == evt.visitor_id).first()
                if sess and not sess.has_purchased:
                    sess.has_purchased = True
                    db.commit()

    conversion_rate = 0.0
    if unique_visitors_count > 0:
        conversion_rate = len(converted_visitors) / unique_visitors_count

    dwells = db.query(
        DBEvent.zone_id,
        func.avg(DBEvent.dwell_ms)
    ).filter(
        DBEvent.store_id == store_id,
        DBEvent.is_staff == False,
        DBEvent.dwell_ms > 0
    ).group_by(DBEvent.zone_id).all()
    
    avg_dwell_pct = {zone: round(avg_dwell / 1000.0, 1) for zone, avg_dwell in dwells if zone}

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

    queue_ids = set([x[0] for x in active_in_queue]) - set([x[0] for x in active_exits])
    queue_depth = len(queue_ids)

    queue_joins = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        DBEvent.event_type == "BILLING_QUEUE_JOIN",
        DBEvent.is_staff == False
    ).distinct().all()
    
    queue_join_ids = set([x[0] for x in queue_joins])
    
    abandoned_count = 0
    for vis_id in queue_join_ids:
        if vis_id not in converted_visitors:
            exited = db.query(DBEvent).filter(
                DBEvent.visitor_id == vis_id,
                DBEvent.event_type == "ZONE_EXIT",
                DBEvent.zone_id == "BILLING"
            ).first()
            if exited:
                abandoned_count += 1

    abandonment_rate = 0.0
    if len(queue_join_ids) > 0:
        abandonment_rate = abandoned_count / len(queue_join_ids)

    return {
        "unique_visitors": unique_visitors_count,
        "conversion_rate": round(conversion_rate, 4),
        "avg_dwell_seconds": avg_dwell_pct,
        "queue_depth": queue_depth,
        "abandonment_rate": round(abandonment_rate, 4),
        "total_gmv": round(total_gmv, 2)
    }
