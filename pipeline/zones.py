from shapely.geometry import Polygon, Point

ZONES = {
    "CAM3": {
        "ENTRY_EXIT": Polygon([(0, 800), (1920, 800), (1920, 1080), (0, 1080)]),
        "ENTRY_GATEWAY": Polygon([(0, 600), (1920, 600), (1920, 800), (0, 800)])
    },
    "CAM1": {
        "SKINCARE": Polygon([(100, 100), (1800, 100), (1800, 980), (100, 980)])
    },
    "CAM2": {
        "MAKEUP": Polygon([(100, 100), (1800, 100), (1800, 980), (100, 980)])
    },
    "CAM5": {
        "BILLING": Polygon([(200, 200), (1700, 200), (1700, 980), (200, 980)]),
        "COUNTER_STAFF": Polygon([(1200, 200), (1700, 200), (1700, 700), (1200, 700)])
    },
    "CAM4": {
        "STAFF_ROOM": Polygon([(0, 0), (1920, 0), (1920, 1080), (0, 1080)])
    }
}

def get_person_zone(camera_id: str, box) -> tuple[str, bool]:
    if camera_id == "CAM4":
        return "STAFF_ROOM", True
    
    x = (box[0] + box[2]) / 2.0
    y = box[3]
    point = Point(x, y)
    
    zones_def = ZONES.get(camera_id, {})
    
    if camera_id == "CAM5":
        is_staff_zone = zones_def.get("COUNTER_STAFF").contains(point)
        if is_staff_zone:
            return "BILLING", True
        elif zones_def.get("BILLING").contains(point):
            return "BILLING", False
            
    for zone_id, polygon in zones_def.items():
        if zone_id in ["ENTRY_GATEWAY", "COUNTER_STAFF"]:
            continue
        if polygon.contains(point):
            return zone_id, False
            
    return None, False
