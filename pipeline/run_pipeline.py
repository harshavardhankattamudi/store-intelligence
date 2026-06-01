import cv2
import os
import sys
from datetime import datetime, timedelta
from pipeline.detect import VideoPipeline

os.makedirs("data", exist_ok=True)
events_file = "data/events.jsonl"
if os.path.exists(events_file):
    os.remove(events_file)

def process_all_clips():
    video_dir = "data/videos"
    cameras = {
        "CAM1": "CAM 1.mp4",
        "CAM2": "CAM 2.mp4",
        "CAM3": "CAM 3.mp4",
        "CAM4": "CAM 4.mp4",
        "CAM5": "CAM 5.mp4"
    }

    start_time = datetime(2026, 4, 10, 12, 0, 0)
    pipeline = VideoPipeline(store_id="ST1008")

    print("Starting Store Intelligence detection pipeline...")

    caps = {}
    for cam_id, filename in cameras.items():
        filepath = os.path.join(video_dir, filename)
        if not os.path.exists(filepath):
            print(f"Warning: File {filepath} not found. Skipping...")
            continue
        caps[cam_id] = cv2.VideoCapture(filepath)

    if not caps:
        print("No video files found inside data/videos! Pipeline execution halted.")
        return

    frame_counter = 0
    fps = 15.0
    
    while True:
        active_caps = 0
        for cam_id, cap in caps.items():
            if not cap.isOpened():
                continue
                
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_counter * 30)
            ret, frame = cap.read()
            
            if ret:
                active_caps += 1
                time_offset = timedelta(seconds=int((frame_counter * 30) / fps))
                current_time = start_time + time_offset
                
                pipeline.process_frame(frame, cam_id, current_time, frame_counter)
        
        if active_caps == 0:
            break
            
        frame_counter += 1
        if frame_counter % 50 == 0:
            print(f"Processed {frame_counter} cycles of frames...")

    for cap in caps.values():
        cap.release()

    print(f"Pipeline complete! Events written to {events_file}")

if __name__ == "__main__":
    process_all_clips()
