import cv2
import torch
import numpy as np
from datetime import datetime, timedelta
from ultralytics import YOLO
from supervision import ByteTrack, Detections
from pipeline.zones import get_person_zone
from pipeline.tracker import StoreTracker
from pipeline.events import EventFactory

class VideoPipeline:
    def __init__(self, model_path: str = "yolov8n.pt", store_id: str = "ST1008"):
        self.model = YOLO(model_path)
        self.tracker = ByteTrack()
        self.store_tracker = StoreTracker()
        self.event_factory = EventFactory(store_id=store_id)
        self.active_zone_presence = {}

    def process_frame(self, frame: np.ndarray, camera_id: str, timestamp: datetime, frame_id: int):
        results = self.model(frame, classes=[0], verbose=False)
        
        if not results or len(results[0].boxes) == 0:
            self._handle_dwell_timeouts(timestamp, camera_id)
            return []

        boxes = results[0].boxes.xyxy.cpu().numpy()
        confidences = results[0].boxes.conf.cpu().numpy()
        class_ids = results[0].boxes.cls.cpu().numpy().astype(int)

        detections = Detections(
            xyxy=boxes,
            confidence=confidences,
            class_id=class_ids
        )

        tracked_detections = self.tracker.update_with_detections(detections)
        emitted_events = []
        active_visitor_ids_this_frame = set()

        for det in tracked_detections:
            try:
                box = det[0]
                confidence = float(det[2])
                class_id = int(det[3])
                tracker_id = det[4]
            except Exception:
                box = getattr(det, "xyxy", det[0])
                confidence = float(getattr(det, "confidence", det[2]))
                class_id = int(getattr(det, "class_id", det[3]))
                tracker_id = getattr(det, "tracker_id", det[4])

            if tracker_id is None:
                continue

            tracker_id_str = f"TRK_{tracker_id}"
            center_x = (box[0] + box[2]) / 2.0
            center_y = (box[1] + box[3]) / 2.0
            point = (center_x, center_y)

            visitor_id = self.store_tracker.get_visitor_id(tracker_id_str, point, timestamp, camera_id)
            active_visitor_ids_this_frame.add(visitor_id)

            self.store_tracker.update_trajectory(tracker_id_str, point, timestamp)

            if camera_id == "CAM3":
                crossing = self.store_tracker.detect_crossing(tracker_id_str, timestamp)
                if crossing == "ENTRY":
                    evt = self.event_factory.create_event(
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        event_type="ENTRY",
                        timestamp=timestamp,
                        confidence=confidence
                    )
                    emitted_events.append(evt)
                    self.event_factory.write_event(evt)
                elif crossing == "EXIT":
                    evt = self.event_factory.create_event(
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        event_type="EXIT",
                        timestamp=timestamp,
                        confidence=confidence
                    )
                    emitted_events.append(evt)
                    self.event_factory.write_event(evt)

            zone_id, is_staff = get_person_zone(camera_id, box)
            if zone_id:
                presence_key = (visitor_id, zone_id)
                
                if presence_key not in self.active_zone_presence:
                    self.active_zone_presence[presence_key] = timestamp
                    
                    evt = self.event_factory.create_event(
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        event_type="ZONE_ENTER",
                        timestamp=timestamp,
                        zone_id=zone_id,
                        is_staff=is_staff,
                        confidence=confidence
                    )
                    emitted_events.append(evt)
                    self.event_factory.write_event(evt)

                    if zone_id == "BILLING":
                        billing_count = sum(1 for (v, z) in self.active_zone_presence.keys() if z == "BILLING" and v != visitor_id)
                        if billing_count > 0:
                            queue_evt = self.event_factory.create_event(
                                camera_id=camera_id,
                                visitor_id=visitor_id,
                                event_type="BILLING_QUEUE_JOIN",
                                timestamp=timestamp,
                                zone_id=zone_id,
                                is_staff=is_staff,
                                confidence=confidence,
                                metadata={"queue_depth": billing_count}
                            )
                            emitted_events.append(queue_evt)
                            self.event_factory.write_event(queue_evt)
                else:
                    enter_time = self.active_zone_presence[presence_key]
                    elapsed_seconds = (timestamp - enter_time).total_seconds()
                    
                    if elapsed_seconds >= 30:
                        dwell_evt = self.event_factory.create_event(
                            camera_id=camera_id,
                            visitor_id=visitor_id,
                            event_type="ZONE_DWELL",
                            timestamp=timestamp,
                            zone_id=zone_id,
                            dwell_ms=int(elapsed_seconds * 1000),
                            is_staff=is_staff,
                            confidence=confidence
                        )
                        emitted_events.append(dwell_evt)
                        self.event_factory.write_event(dwell_evt)

        for (visitor_id, zone_id), enter_time in list(self.active_zone_presence.items()):
            zone_cam = "CAM1" if zone_id == "SKINCARE" else "CAM2" if zone_id == "MAKEUP" else "CAM5" if zone_id == "BILLING" else "CAM4" if zone_id == "STAFF_ROOM" else "CAM3"
            
            if zone_cam == camera_id and visitor_id not in active_visitor_ids_this_frame:
                dwell_ms = int((timestamp - enter_time).total_seconds() * 1000)
                
                evt = self.event_factory.create_event(
                    camera_id=camera_id,
                    visitor_id=visitor_id,
                    event_type="ZONE_EXIT",
                    timestamp=timestamp,
                    zone_id=zone_id,
                    dwell_ms=dwell_ms
                )
                emitted_events.append(evt)
                self.event_factory.write_event(evt)
                
                del self.active_zone_presence[(visitor_id, zone_id)]

        return emitted_events

    def _handle_dwell_timeouts(self, timestamp: datetime, camera_id: str):
        for (visitor_id, zone_id), enter_time in list(self.active_zone_presence.items()):
            zone_cam = "CAM1" if zone_id == "SKINCARE" else "CAM2" if zone_id == "MAKEUP" else "CAM5" if zone_id == "BILLING" else "CAM4" if zone_id == "STAFF_ROOM" else "CAM3"
            if zone_cam == camera_id:
                dwell_ms = int((timestamp - enter_time).total_seconds() * 1000)
                evt = self.event_factory.create_event(
                    camera_id=camera_id,
                    visitor_id=visitor_id,
                    event_type="ZONE_EXIT",
                    timestamp=timestamp,
                    zone_id=zone_id,
                    dwell_ms=dwell_ms
                )
                self.event_factory.write_event(evt)
                del self.active_zone_presence[(visitor_id, zone_id)]
