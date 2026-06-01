Markdown
# Apex Retail - Store Intelligence API 🛍️🎥

An end-to-end, edge-to-cloud analytical pipeline designed to mirror online e-commerce tracking within physical retail environments. 

This system uses a dedicated Edge AI pipeline to process CCTV footage, a highly resilient REST API to ingest the tracking data, and a live Streamlit dashboard to compute and visualize real-time business metrics like the **Offline Store Conversion Rate**.

---

## 🚀 Features

* **Advanced Computer Vision (Edge):** A dedicated Python pipeline utilizing YOLOv8 and Deep SORT to maintain persistent shopper track IDs through partial occlusions and overlapping camera angles.
* **Live Analytics Dashboard (UI):** A real-time Streamlit interface that polls the backend to visualize conversion funnels, shopper metrics, and queue abandonment on screen.
* **Idempotent Data Ingestion:** A Flask-based REST API designed to safely ingest batches of JSON events. Implements strict idempotency at the database layer to silently drop duplicate network events.
* **Real-time Aggregation:** Instantly calculates conversion funnels, queue abandonment, and dwell times via MongoDB aggregation pipelines.
* **Zero-Manual-Step Deployment:** Fully containerized backend and frontend architecture using Docker and Docker Compose.

## 🛠️ Tech Stack

* **Computer Vision:** PyTorch, Ultralytics (YOLOv8), Deep SORT, OpenCV
* **Backend API:** Python, Flask
* **Database:** MongoDB (Motor/PyMongo)
* **Frontend UI:** Streamlit, Pandas
* **Testing:** Pytest, mongomock, pytest-cov

## 📦 Project Structure

```text
apex-store-intelligence/
├── detection_pipeline/        
│   ├── pipeline.py            # Heavy YOLOv8 + Deep SORT edge execution script
│   └── schema.py              # Strict Pydantic models for API contract
├── frontend/
│   ├── dashboard.py           # Live Streamlit UI for visualizing API metrics
│   ├── Dockerfile             # Dashboard Container
├── api_server/
│   ├── app.py                 # Core Flask API & Analytics Engine
│   ├── test_app.py            # Pytest Suite (>70% Coverage)
│   ├── Dockerfile             # API Container Configuration
├── docker-compose.yml         # Multi-container orchestration (UI, API, MongoDB)
├── DESIGN.md                  # High-level architecture documentation
├── CHOICES.md                 # Technical trade-offs and AI collaboration log
└── README.md
⚙️ Quick Start (Docker)
The API, Database, and UI are fully containerized. You do not need to install Python or MongoDB locally to run the infrastructure.
1. Clone the repository:
Bash
git clone [https://github.com/saikeshavb/apex-store-intelligence.git](https://github.com/saikeshavb/apex-store-intelligence.git)
cd apex-store-intelligence
2. Spin up the infrastructure:
Bash
docker compose up --build -d
3. Access the Live Dashboard:
Open your browser and navigate to:
👉 http://localhost:8501
4. Run the CV Pipeline (Locally):
Bash
cd detection_pipeline
python pipeline.py --video sample.mp4
📡 API Reference
1. Ingest Events
POST /events/ingest
Accepts batches of structured JSON events from the CV pipeline. Idempotent by event_id.
Bash
curl -X POST [http://127.0.0.1:5000/events/ingest](http://127.0.0.1:5000/events/ingest) \
-H "Content-Type: application/json" \
-d '[{"event_id": "uuid-123", "store_id": "ST1008", "event_type": "ENTRY", "timestamp": "2026-04-10T16:50:00Z"}]'
2. Get Store Metrics
GET /stores/{id}/metrics
Calculates Unique Visitors, Average Dwell Time, Queue Depth, and Conversion Rate.
3. Get Conversion Funnel
GET /stores/{id}/funnel
Maps the spatial conversion funnel and computes drop-off rates: Entry -> Zone -> Billing -> Purchase.
🧪 Testing
The API includes a rigorous test suite utilizing mongomock to isolate database calls during CI/CD pipelines.
To run the tests locally:
Bash
cd api_server
pip install -r requirements.txt pytest pytest-cov mongomock
pytest test_app.py -v --cov=app
