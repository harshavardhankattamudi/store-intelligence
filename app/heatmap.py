from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import DBEvent

def compute_store_heatmap(store_id: str, db: Session) -> dict:
    total_sessions_count = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        DBEvent.is_staff == False
    ).distinct().count()

    data_confidence = "HIGH" if total_sessions_count >= 20 else "LOW"

    zone_stats = db.query(
        DBEvent.zone_id,
        func.count(func.distinct(DBEvent.visitor_id)).label("unique_visits"),
        func.avg(DBEvent.dwell_ms).label("avg_dwell")
    ).filter(
        DBEvent.store_id == store_id,
        DBEvent.is_staff == False,
        DBEvent.zone_id.isnot(None)
    ).group_by(DBEvent.zone_id).all()

    max_visits = max([s.unique_visits for s in zone_stats]) if zone_stats else 1
    max_dwell = max([s.avg_dwell for s in zone_stats if s.avg_dwell]) if zone_stats else 1

    heatmap_data = {}
    for stat in zone_stats:
        zone = stat.zone_id
        if not zone:
            continue
        
        norm_freq = round((stat.unique_visits / max_visits) * 100)
        norm_dwell = round((stat.avg_dwell / max_dwell) * 100) if stat.avg_dwell else 0

        heatmap_data[zone] = {
            "raw_visits": stat.unique_visits,
            "raw_avg_dwell_ms": round(stat.avg_dwell or 0),
            "normalized_frequency": norm_freq,
            "normalized_dwell": norm_dwell
        }

    return {
        "store_id": store_id,
        "data_confidence": data_confidence,
        "total_sessions": total_sessions_count,
        "zones": heatmap_data
    }
