
Markdown
# Apex Retail - Store Intelligence API 🛍️📊

An end-to-end, edge-to-cloud analytical pipeline designed to mirror online e-commerce tracking within physical retail environments. 

This system processes raw CCTV footage to extract anonymous spatial shopper trajectories, ingests the data via a highly resilient REST API, and correlates the physical tracking data with Point-of-Sale (POS) transaction records to compute real-time business metrics, including the North Star metric: **Offline Store Conversion Rate**.

---

## 🚀 Features

* **Computer Vision Pipeline (Edge):** Utilizes YOLOv8 for high-FPS object detection and Deep SORT to maintain persistent track IDs through partial occlusions and overlapping camera angles.
* **Idempotent Data Ingestion:** A Flask-based REST API designed to safely ingest batches of JSON events. Implements strict idempotency at the database level to silently drop duplicate events and prevent metric skewing.
* **Spatial-Temporal POS Matching:** Correlates anonymous physical shopper journeys with actual transaction data using time-windowed MongoDB aggregation pipelines.
* **Automated Anomaly Detection:** Real-time statistical thresholding to detect operational bottlenecks like `QUEUE_SPIKE`, `HIGH_ABANDONMENT`, and physical `DEAD_ZONE`s.
* **Zero-Manual-Step Deployment:** Fully containerized backend architecture using Docker and Docker Compose. 

---

## 🛠️ Tech Stack

* **Computer Vision:** PyTorch, Ultralytics (YOLOv8), Deep SORT, OpenCV
* **Backend API:** Python, Flask
* **Database:** MongoDB (Motor/PyMongo)
* **Infrastructure:** Docker, Docker Compose
* **Testing:** Pytest, mongomock, pytest-cov

---

## 📦 Project Structure

```text
apex-store-intelligence/
├── api_server/
│   ├── app.py                 # Core Flask API & Analytics Engine
│   ├── ingestion_db.py        # DB Initialization & Indexing Script
│   ├── ingest_pos.py          # POS CSV Data Loader
│   ├── test_app.py            # Pytest Suite (>70% Coverage)
│   ├── pos_data.csv           # Raw Point-of-Sale Transaction Data
│   ├── Dockerfile             # API Container Configuration
│   └── docker-compose.yml     # Multi-container orchestration (API + MongoDB)
├── detection_pipeline/
│   ├── pipeline.py            # YOLOv8 + Deep SORT execution script
│   └── schema.py              # Strict Pydantic models for API contract
├── DESIGN.md                  # High-level architecture documentation
├── CHOICES.md                 # Technical trade-offs and AI collaboration log
└── README.md
⚙️ Quick Start (Docker)
The backend API and Database are fully containerized. You do not need to install Python or MongoDB locally to run the cloud infrastructure.
1. Clone the repository:
Bash
git clone [https://github.com/saikeshavb/apex-store-intelligence.git](https://github.com/saikeshavb/apex-store-intelligence.git)
cd apex-store-intelligence/api_server
2. Spin up the infrastructure:
Bash
docker compose up --build -d
Note: The API is exposed on port 5001 to prevent binding conflicts with macOS AirPlay Receiver services on port 5000.
3. Verify the service is running:
Bash
curl [http://127.0.0.1:5001/health](http://127.0.0.1:5001/health)
📡 API Reference
1. Ingest Events
POST /events/ingest
Accepts batches of up to 500 structured JSON events from the CV pipeline. Idempotent by event_id.
Bash
curl -X POST [http://127.0.0.1:5001/events/ingest](http://127.0.0.1:5001/events/ingest) \
-H "Content-Type: application/json" \
-d '[{"event_id": "uuid...", "store_id": "ST1008", "event_type": "ENTRY", "timestamp": "2026-04-10T16:50:00Z" ...}]'
2. Get Store Metrics
GET /stores/{id}/metrics
Calculates Unique Visitors, Average Dwell Time, Queue Depth, Abandonment Rate, and the true Conversion Rate.
3. Get Conversion Funnel
GET /stores/{id}/funnel
Maps the spatial conversion funnel and computes drop-off rates: Entry -> Zone -> Billing -> Purchase.
4. Get Active Anomalies
GET /stores/{id}/anomalies
Scans for active operational anomalies based on statistical deviations (e.g., Queue > 10, Abandonment > 15%).
🧪 Testing
The API includes a rigorous test suite utilizing mongomock to isolate database calls during CI/CD pipelines.
To run the tests locally (requires virtual environment):
Bash
cd api_server
pip install -r requirements.txt pytest pytest-cov mongomock
pytest test_app.py -v --cov=app
Current Statement Coverage: 75%
📝 Design & Architecture Decisions
For a deep dive into the engineering trade-offs, schema choices, and AI collaboration strategy used during this build, please refer to the DESIGN.md and CHOICES.md files in the root directory.

### Final Step
Once you have pasted this into the `README.md` file, simply commit and push it to GitHub:

```bash
git add README.md
git commit -m "Add project README documentation"
git push
