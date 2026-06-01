```markdown
# System Architecture & Design

The Apex Retail Intelligence platform is designed as a highly scalable microservice architecture. It cleanly separates heavy computer vision processing from lightweight data ingestion, all visualized through a live Dashboard.

## 🎥 1. Edge Computer Vision Layer (`detection_pipeline`)
* **Role:** Acts as the physical edge node (camera gateway) in the store.
* **Mechanism:** A standalone Python process parses CCTV video files using YOLOv8 for object detection and Deep SORT for temporal tracking across frames.
* **Behavior:** When a track crosses a designated spatial coordinate (e.g., the front door), the pipeline dynamically generates a unique JSON payload and pushes it via HTTP POST to the backend API.

## ⚙️ 2. API Server Layer (Flask)
* **Role:** The central nervous system for data validation, ingestion, and analytical aggregations.
* **Endpoints:**
  * `POST /events/ingest`: A high-throughput endpoint for accepting shopper movement data from the edge pipeline.
  * `GET /stores/<store_id>/metrics`: Aggregates top-level KPIs.
  * `GET /stores/<store_id>/funnel`: Maps the customer journey through distinct store zones.
* **Data Integrity:** Enforces idempotency. If an edge device loses connection and resends the same payload, the API recognizes the collision and safely ignores it.

## 🗄️ 3. Database Layer (MongoDB)
* **Role:** Persistent storage for high-velocity time-series event data.
* **Indexes:** We utilize a unique index on `event_id` to enforce data integrity natively at the database layer, preventing duplicate visitor counts.

## 📊 4. Frontend Layer (Streamlit)
* **Role:** The live user interface for store managers.
* **Mechanism:** A Streamlit application that continuously polls the Flask API's `/metrics` and `/funnel` endpoints to render live charts, graphs, and KPIs as shoppers move through the store.

## 🔄 The Data Flow
1. **Raw Video** -> 2. **YOLO/Deep SORT Script** -> 3. **JSON HTTP POST** -> 4. **Flask API** -> 5. **MongoDB** -> 6. **Streamlit UI Data Pull**.
