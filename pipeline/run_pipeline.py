import cv2
import os
import sys
import argparse
from datetime import datetime, timedelta
from pipeline.detect import VideoPipeline

os.makedirs("data", exist_ok=True)
events_file = "data/events.jsonl"
if os.path.exists(events_file):
    os.remove(events_file)

def process_store_clips():
    parser = argparse.ArgumentParser(description="Run Store Intelligence Detection Pipeline")
    parser.add_argument("--store", type=str, default="Store1", choices=["Store1", "Store2"], help="Store to process (Store1 or Store2)")
    args = parser.parse_args()

    start_time = datetime(2026, 4, 10, 12, 0, 0)
    
    if args.store == "Store1":
        video_dir = "data/videos/Store1"
        store_id = "ST1008"
        cameras = {
            "CAM1": "CAM 1 - zone.mp4",
            "CAM2": "CAM 2 - zone.mp4",
            "CAM3": "CAM 3 - entry.mp4",
            "CAM5": "CAM 5 - billing.mp4"
        }
    else:
        video_dir = "data/videos/Store2"
        store_id = "ST1076"
        cameras = {
            "CAM1": "zone.mp4",
            "CAM3_1": "entry 1.mp4",
            "CAM3_2": "entry 2.mp4",
            "CAM5": "billing_area.mp4"
        }

    pipeline = VideoPipeline(store_id=store_id)
    print(f"Starting Store Intelligence detection pipeline for {args.store} (Store ID: {store_id})...")

    caps = {}
    for logical_cam, filename in cameras.items():
        filepath = os.path.join(video_dir, filename)
        if not os.path.exists(filepath):
            print(f"Warning: File {filepath} not found. Skipping...")
            continue
        caps[logical_cam] = cv2.VideoCapture(filepath)

    if not caps:
        print(f"No video files found inside {video_dir}! Pipeline execution halted.")
        return

    frame_counter = 0
    fps = 15.0
    
    while True:
        active_caps = 0
        for logical_cam, cap in caps.items():
            if not cap.isOpened():
                continue
                
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_counter * 30)
            ret, frame = cap.read()
            
            if ret:
                active_caps += 1
                time_offset = timedelta(seconds=int((frame_counter * 30) / fps))
                current_time = start_time + time_offset
                
                api_cam_id = logical_cam.split("_")[0]
                pipeline.process_frame(frame, api_cam_id, current_time, frame_counter)
        
        if active_caps == 0:
            break
            
        frame_counter += 1
        if frame_counter % 50 == 0:
            print(f"Processed {frame_counter} cycles of frames...")

    for cap in caps.values():
        cap.release()

    print(f"Pipeline complete! Events written to {events_file}")

if __name__ == "__main__":
    process_store_clips()
