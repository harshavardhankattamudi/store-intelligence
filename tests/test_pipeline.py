# tests/test_pipeline.py
# PROMPT: Create tests for tracker, zone lookup, crossing threshold logic.
# CHANGES MADE: Extracted mock coordinate inputs for box geometry tests.

import pytest
from datetime import datetime
from shapely.geometry import Polygon
from pipeline.zones import get_person_zone
from pipeline.tracker import StoreTracker

def test_tracker_crossing_and_reentry():
    tracker = StoreTracker()
    tracker_id = "TRK_test_1"
    timestamp = datetime(2026, 4, 10, 12, 0, 0)

    # 1. Update positions indicating entry crossing (start_y < 800 and end_y >= 800)
    tracker.update_trajectory(tracker_id, (960, 600), timestamp)
    tracker.update_trajectory(tracker_id, (960, 850), timestamp)

    crossing = tracker.detect_crossing(tracker_id, timestamp)
    assert crossing == "ENTRY"

    visitor_id = tracker.get_visitor_id(tracker_id, (960, 850), timestamp, "CAM3")
    assert visitor_id.startswith("VIS_")

    # 2. Update positions indicating exit crossing (start_y >= 800 and end_y < 800)
    tracker_id_2 = "TRK_test_2"
    tracker.tracker_to_visitor[tracker_id_2] = visitor_id
    tracker.update_trajectory(tracker_id_2, (960, 850), timestamp)
    tracker.update_trajectory(tracker_id_2, (960, 600), timestamp)

    crossing = tracker.detect_crossing(tracker_id_2, timestamp)
    assert crossing == "EXIT"
