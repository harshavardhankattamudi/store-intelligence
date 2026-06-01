from sqlalchemy.orm import Session
from app.models import DBEvent, DBSession, DBTransaction

def compute_store_funnel(store_id: str, db: Session) -> dict:
    sessions = db.query(DBSession).filter(
        DBSession.store_id == store_id,
        DBSession.is_staff == False
    ).all()
    total_entries = len(sessions)
    visitor_ids = [s.visitor_id for s in sessions]

    if total_entries == 0:
        return {
            "stages": [
                {"stage_name": "Entry", "count": 0, "drop_off_pct": 0.0},
                {"stage_name": "Zone Visit", "count": 0, "drop_off_pct": 0.0},
                {"stage_name": "Billing Queue", "count": 0, "drop_off_pct": 0.0},
                {"stage_name": "Purchase", "count": 0, "drop_off_pct": 0.0}
            ]
        }

    visited_product_zones = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        DBEvent.zone_id.in_(["SKINCARE", "MAKEUP"]),
        DBEvent.is_staff == False,
        DBEvent.visitor_id.in_(visitor_ids)
    ).distinct().all()
    stage2_count = len(visited_product_zones)

    entered_billing = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        DBEvent.zone_id == "BILLING",
        DBEvent.is_staff == False,
        DBEvent.visitor_id.in_(visitor_ids)
    ).distinct().all()
    stage3_count = len(entered_billing)

    purchased = db.query(DBSession).filter(
        DBSession.store_id == store_id,
        DBSession.is_staff == False,
        DBSession.has_purchased == True
    ).all()
    stage4_count = len(purchased)

    drop_off_1_to_2 = round(((total_entries - stage2_count) / total_entries) * 100, 2) if total_entries > 0 else 0.0
    drop_off_2_to_3 = round(((stage2_count - stage3_count) / stage2_count) * 100, 2) if stage2_count > 0 else 0.0
    drop_off_3_to_4 = round(((stage3_count - stage4_count) / stage3_count) * 100, 2) if stage3_count > 0 else 0.0

    return {
        "stages": [
            {"stage_name": "Entry", "count": total_entries, "drop_off_pct": 0.0},
            {"stage_name": "Zone Visit", "count": stage2_count, "drop_off_pct": drop_off_1_to_2},
            {"stage_name": "Billing Queue", "count": stage3_count, "drop_off_pct": drop_off_2_to_3},
            {"stage_name": "Purchase", "count": stage4_count, "drop_off_pct": drop_off_3_to_4}
        ]
    }
