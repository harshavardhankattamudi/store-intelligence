import uuid
import math
from datetime import datetime, timedelta

class StoreTracker:
    def __init__(self):
        self.tracker_to_visitor = {}
        self.trajectories = {}
        self.active_sessions = {}
        self.completed_visits = {}

    def get_visitor_id(self, tracker_id: str, point: tuple[float, float], timestamp: datetime, camera_id: str) -> str:
        for vis_id, visit_info in list(self.completed_visits.items()):
            time_diff = (timestamp - visit_info["exit_time"]).total_seconds()
            if 0 <= time_diff <= 300:
                self.tracker_to_visitor[tracker_id] = vis_id
                if vis_id in self.active_sessions:
                    self.active_sessions[vis_id]["last_seen"] = timestamp
                del self.completed_visits[vis_id]
                return vis_id

        if tracker_id in self.tracker_to_visitor:
            vis_id = self.tracker_to_visitor[tracker_id]
            if vis_id in self.active_sessions:
                self.active_sessions[vis_id]["last_seen"] = timestamp
            return vis_id

        new_visitor_id = f"VIS_{uuid.uuid4().hex[:6]}"
        self.tracker_to_visitor[tracker_id] = new_visitor_id
        
        self.active_sessions[new_visitor_id] = {
            "start_time": timestamp,
            "last_seen": timestamp,
            "is_staff": (camera_id == "CAM4"),
            "zones": set(),
            "history": []
        }
        return new_visitor_id

    def update_trajectory(self, tracker_id: str, center: tuple[float, float], timestamp: datetime):
        if tracker_id not in self.trajectories:
            self.trajectories[tracker_id] = []
        self.trajectories[tracker_id].append((center[0], center[1], timestamp))
        if len(self.trajectories[tracker_id]) > 100:
            self.trajectories[tracker_id].pop(0)

    def detect_crossing(self, tracker_id: str, timestamp: datetime) -> str:
        traj = self.trajectories.get(tracker_id, [])
        if len(traj) < 2:
            return None
        
        start_y = traj[0][1]
        end_y = traj[-1][1]
        
        if start_y < 800 and end_y >= 800:
            return "ENTRY"
        elif start_y >= 800 and end_y < 800:
            visitor_id = self.tracker_to_visitor.get(tracker_id)
            if visitor_id:
                self.completed_visits[visitor_id] = { "exit_time": timestamp }
            return "EXIT"
            
        return None
