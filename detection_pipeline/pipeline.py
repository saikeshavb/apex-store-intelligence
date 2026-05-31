import cv2
import uuid
import numpy as np
import json
import argparse
import os
from datetime import datetime, timezone, timedelta
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from pydantic import ValidationError

# Import our strict schema contract
from schema import StoreEvent, EventType, EventMetadata

# ==========================================
# ARGUMENT PARSER & CONFIGURATION
# ==========================================
parser = argparse.ArgumentParser(description="Apex Retail Store Intelligence CV Inference Pipeline")
parser.add_argument("--input", type=str, required=True, help="Path to the raw input CCTV video file (.mp4/.avi)")
parser.add_argument("--store_id", type=str, default="STORE_BLR_002", help="Apex store code identifier")
parser.add_argument("--camera_id", type=str, default="CAM_ENTRY_01", help="Camera angle placement location tag")
parser.add_argument("--zone_id", type=str, default="MAIN_FLOOR", help="Physical layout zone identifier")
parser.add_argument("--output", type=str, default=None, help="Optional file path to save the annotated output video")
args = parser.parse_args()

# Validate that input file exists
if not os.path.exists(args.input):
    raise FileNotFoundError(f"Provided video source file not found: {args.input}")

# Base anchor timestamp representing the simulated absolute start time of the footage
BASE_FOOTAGE_START = datetime(2026, 5, 31, 9, 0, 0, tzinfo=timezone.utc)

# ==========================================
# INITIALIZATION
# ==========================================
print(f"Loading YOLOv8 model layers...")
model = YOLO("yolov8n.pt") 

print("Initializing Deep SORT Tracker engine tracking state...")
tracker = DeepSort(max_age=30, n_init=3, nms_max_overlap=1.0)

# State maps tracking unique visitor intervals
global_visitor_registry = {} 
track_history = {}  # local_track_id -> {"entry_time": datetime, "global_id": str, "is_staff": bool, "last_emitted": datetime}

def get_global_visitor_id(local_track_id):
    """Assigns or matches cross-camera global visitor identifiers."""
    if local_track_id not in global_visitor_registry:
        global_visitor_registry[local_track_id] = f"VIS_{uuid.uuid4().hex[:6].upper()}"
    return global_visitor_registry[local_track_id]

def classify_staff(frame_crop):
    """Heuristic logic to flag store staff members based on brand uniforms."""
    if frame_crop.size == 0: return False
    hsv = cv2.cvtColor(frame_crop, cv2.COLOR_BGR2HSV)
    lower_blue = np.array([100, 50, 50])
    upper_blue = np.array([130, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    blue_ratio = cv2.countNonZero(mask) / (frame_crop.shape[0] * frame_crop.shape[1])
    return blue_ratio > 0.2  

def emit_event(event_type, visitor_id, current_timestamp, dwell_ms, is_staff, confidence):
    """Serializes payloads matching the exact required JSON contract schema."""
    try:
        event = StoreEvent(
            event_id=uuid.uuid4(),
            store_id=args.store_id,
            camera_id=args.camera_id,
            visitor_id=visitor_id,
            event_type=event_type,
            timestamp=current_timestamp,
            zone_id=args.zone_id,
            dwell_ms=dwell_ms,
            is_staff=is_staff,
            confidence=confidence,
            metadata=EventMetadata(queue_depth=None, sku_zone=None, session_seq=1)
        )
        print(f"\n[API POST] Emitting {event_type.value}:\n{json.dumps(event.model_dump(mode='json'), indent=2)}")
    except ValidationError as e:
        print(f"Schema Validation Failure occurred: {e}")

def process_cctv_file():
    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        print(f"Error: Failed to open raw video file container: {args.input}")
        return

    # Extract source metadata dynamics
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0: fps = 15.0  # Fallback standard default
    
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Initialize output video writer if parameter provided
    video_writer = None
    if args.output:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(args.output, fourcc, fps, (frame_width, frame_height))
        print(f"Saving processing annotations layout to: {args.output}")

    frame_count = 0
    print(f"Starting frame sequence analysis processing loop context at {fps} FPS...")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("\nVideo file processing timeline finished completely or frame stream broken.")
            break

        frame_count += 1
        
        # Calculate context-aware deterministic timeline tracking relative to elapsed frames
        elapsed_seconds = frame_count / fps
        current_frame_time = BASE_FOOTAGE_START + timedelta(seconds=elapsed_seconds)

        # 1. Object Detection Step
        results = model(frame, classes=[0], verbose=False)
        detections = []
        
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                confidence = float(box.conf[0])
                w, h = x2 - x1, y2 - y1
                detections.append(([x1, y1, w, h], confidence, 'person'))

        # 2. Sequential Frame Deep SORT Association Step
        tracks = tracker.update_tracks(detections, frame=frame)

        # 3. State Engine Processing Loops
        for track in tracks:
            if not track.is_confirmed(): continue
                
            track_id = track.track_id
            x1, y1, x2, y2 = map(int, track.to_tlbr())
            
            # Bound boundaries within valid dimensions to prevent indexing faults
            frame_crop = frame[max(0, y1):min(frame_height, y2), max(0, x1):min(frame_width, x2)]

            # Scene Entry Management
            if track_id not in track_history:
                visitor_id = get_global_visitor_id(track_id)
                is_staff = classify_staff(frame_crop)
                confidence = track.det_conf if track.det_conf else 0.90
                
                track_history[track_id] = {
                    "entry_time": current_frame_time,
                    "global_id": visitor_id,
                    "is_staff": is_staff,
                    "last_emitted": current_frame_time,
                    "confidence": confidence
                }
                
                emit_event(EventType.ENTRY, visitor_id, current_frame_time, 0, is_staff, confidence)
            
            # Persistent Zone Dwell Computations
            else:
                state = track_history[track_id]
                dwell_ms = int((current_frame_time - state["entry_time"]).total_seconds() * 1000)
                
                # Emit metrics intervals spaced sequentially every 5 programmatic seconds
                time_since_last_emit = (current_frame_time - state["last_emitted"]).total_seconds()
                if time_since_last_emit >= 5.0:
                    emit_event(EventType.ZONE_DWELL, state["global_id"], current_frame_time, dwell_ms, state["is_staff"], state["confidence"])
                    state["last_emitted"] = current_frame_time

            # Layout annotations
            color = (255, 0, 0) if track_history[track_id]["is_staff"] else (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"ID: {track_history[track_id]['global_id']}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Write out frame visuals if configured
        if video_writer:
            video_writer.write(frame)

        # Render process preview frames natively
        cv2.imshow("Apex Retail - CCTV File Processing Pipeline Engine", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            print("Execution halted manually by user context.")
            break

    cap.release()
    if video_writer: video_writer.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    process_cctv_file()