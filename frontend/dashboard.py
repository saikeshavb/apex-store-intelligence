import streamlit as st
import requests
import pandas as pd
import tempfile
import cv2
import uuid
from datetime import datetime, timezone
from ultralytics import YOLO

# Connect to the backend API
API_BASE_URL = "http://api:5000"

st.set_page_config(page_title="Apex Live Intelligence", page_icon="🎥", layout="wide")

# Load YOLO Model (cached so it only loads once)
@st.cache_resource
def load_model():
    return YOLO("yolov8n.pt")  # 'n' is the nano model for blazing fast real-time speeds

model = load_model()

# ==========================================
# METRICS UI FUNCTION
# ==========================================
def render_metrics(placeholder, store_id="ST1008"):
    """Fetches data from the API and renders the metrics column."""
    try:
        metrics_res = requests.get(f"{API_BASE_URL}/stores/{store_id}/metrics").json()
        funnel_res = requests.get(f"{API_BASE_URL}/stores/{store_id}/funnel").json()
        
        m = metrics_res.get("metrics", {})
        f = funnel_res.get("funnel", {})
        
        with placeholder.container():
            st.subheader(f"📊 Live Metrics: {store_id}")
            
            # Top KPIs
            c1, c2 = st.columns(2)
            c1.metric("Unique Visitors", m.get("unique_visitors", 0))
            c2.metric("Purchases", f.get("4_purchases", 0))
            
            c3, c4 = st.columns(2)
            c3.metric("Conversion Rate", f"{m.get('conversion_rate_percent', 0)}%")
            c4.metric("Avg Dwell Time", f"{m.get('avg_dwell_seconds', 0)}s")
            
            st.divider()
            
            # Funnel Chart
            st.subheader("Live Conversion Funnel")
            df_funnel = pd.DataFrame({
                "Stage": ["1. Entry", "2. Zone", "3. Queue", "4. Bought"],
                "Count": [f.get("1_entries", 0), f.get("2_zone_visits", 0), f.get("3_billing_queue", 0), f.get("4_purchases", 0)]
            })
            st.bar_chart(df_funnel.set_index("Stage"))
    except Exception as e:
        placeholder.error("Waiting for API connection...")

# ==========================================
# MAIN LAYOUT
# ==========================================
st.title("🎥 Apex Retail: Live Edge Processing")

# Create two columns: 70% for Video, 30% for Metrics
col_video, col_metrics = st.columns([2.5, 1])

# Placeholders so we can update them in a loop
video_placeholder = col_video.empty()
metrics_placeholder = col_metrics.empty()

# Render initial metrics
render_metrics(metrics_placeholder)

# ==========================================
# SIDEBAR: VIDEO UPLOAD & PROCESSING
# ==========================================
st.sidebar.title("🎛️ Edge Camera Feed")
uploaded_file = st.sidebar.file_uploader("Upload Store Video (.mp4)", type=['mp4', 'avi', 'mov'])

if uploaded_file and st.sidebar.button("▶️ Start Live Processing"):
    # 1. Save uploaded video to a temporary file
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    
    cap = cv2.VideoCapture(tfile.name)
    
    if "seen_ids" not in st.session_state:
        st.session_state.seen_ids = set()
    
    frame_count = 0
    st.sidebar.success("Processing Video & Pushing to API...")
    
    # 2. Process Video Frame by Frame
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            st.sidebar.info("Video processing complete.")
            break
            
        # Run YOLOv8 Tracking (only looking for class 0: person)
        results = model.track(frame, persist=True, classes=[0], verbose=False)
        
        # 3. Handle Detections & Push to API
        if results[0].boxes is not None and results[0].boxes.id is not None:
            track_ids = results[0].boxes.id.int().cpu().tolist()
            
            for tid in track_ids:
                if tid not in st.session_state.seen_ids:
                    # WE FOUND A NEW PERSON! Push event to API.
                    st.session_state.seen_ids.add(tid)
                    
                    payload = {
                        "event_id": str(uuid.uuid4()),
                        "store_id": "ST1008",
                        "camera_id": "CAM_FRONT_DOOR",
                        "visitor_id": f"VIS_TRACK_{tid}",
                        "event_type": "ENTRY",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "zone_id": "MAIN_ENTRANCE",
                        "dwell_ms": 0,
                        "is_staff": False,
                        "confidence": 0.95,
                        "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
                    }
                    try:
                        requests.post(f"{API_BASE_URL}/events/ingest", json=payload)
                    except:
                        pass
        
        # 4. Draw bounding boxes and show live video
        annotated_frame = results[0].plot()
        # Convert BGR (OpenCV) to RGB (Streamlit)
        annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        video_placeholder.image(annotated_frame, channels="RGB", use_column_width=True)
        
        # 5. Refresh the UI metrics every 10 frames (so it doesn't slow down the video)
        if frame_count % 10 == 0:
            render_metrics(metrics_placeholder)
            
        frame_count += 1

    cap.release()