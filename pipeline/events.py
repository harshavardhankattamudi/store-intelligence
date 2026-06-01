import json
import uuid
from datetime import datetime

class EventFactory:
    def __init__(self, store_id: str = "ST1008"):
        self.store_id = store_id
        self.session_sequences = {}

    def get_sequence(self, visitor_id: str) -> int:
        if visitor_id not in self.session_sequences:
            self.session_sequences[visitor_id] = 0
        self.session_sequences[visitor_id] += 1
        return self.session_sequences[visitor_id]

    def create_event(self, 
                     camera_id: str, 
                     visitor_id: str, 
                     event_type: str, 
                     timestamp: datetime, 
                     zone_id: str = None, 
                     dwell_ms: int = 0, 
                     is_staff: bool = False, 
                     confidence: float = 1.0, 
                     metadata: dict = None) -> dict:
        if metadata is None:
            metadata = {}
            
        if "queue_depth" not in metadata:
            metadata["queue_depth"] = None
        if "sku_zone" not in metadata:
            metadata["sku_zone"] = None
        if "session_seq" not in metadata:
            metadata["session_seq"] = self.get_sequence(visitor_id)

        ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")

        return {
            "event_id": str(uuid.uuid4()),
            "store_id": self.store_id,
            "camera_id": camera_id,
            "visitor_id": visitor_id,
            "event_type": event_type,
            "timestamp": ts_str,
            "zone_id": zone_id,
            "dwell_ms": dwell_ms,
            "is_staff": is_staff,
            "confidence": round(confidence, 2),
            "metadata": metadata
        }

    def write_event(self, event: dict, file_path: str = "data/events.jsonl"):
        with open(file_path, "a") as f:
            f.write(json.dumps(event) + "\n")
