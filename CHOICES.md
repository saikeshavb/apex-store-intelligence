# Technical Decisions & AI Collaboration

## 1. Database: MongoDB over PostgreSQL
* **The Choice:** We selected MongoDB.
* **AI Collaboration:** The AI highlighted that while PostgreSQL handles relational POS data well, the highly nested and varied metadata payloads of computer vision events (e.g., changing confidence scores, arrays of features) are vastly superior in a document store.
* **Reasoning:** We enforce schema rigidity at the API boundary using Pydantic, but rely on MongoDB's flexible document structure and $O(N)$ aggregation pipelines to quickly compute real-time analytical funnels. Furthermore, MongoDB natively handles batch ingestion with `ordered=False`, easily fulfilling the idempotency requirement when duplicate `event_id`s are detected.

## 2. Vision Models: YOLOv8 + Deep SORT
* **The Choice:** YOLOv8 nano and Deep SORT.
* **AI Collaboration:** We discussed the trade-off between ByteTrack (faster) and Deep SORT (more robust).
* **Reasoning:** In a retail environment, shoppers constantly weave behind racks, creating partial occlusions. Deep SORT’s appearance feature extractor makes re-identifying a shopper after an occlusion significantly more reliable than purely spatial trackers like ByteTrack, directly preserving the integrity of our `dwell_ms` calculations. 

## 3. API Framework: Flask over Express/Node.js
* **The Choice:** Flask (Python).
* **AI Collaboration:** The AI suggested both Python and Node.js. 
* **Reasoning:** Since the upstream CV detection pipeline relies entirely on Python (PyTorch, OpenCV), utilizing Flask ensures seamless data serialization boundaries and simplifies the organizational tech stack.

## 4. Anomaly Detection: Statistical over ML 
* **The Choice:** Statistical thresholding for Dead Zones and Queue Spikes.
* **Reasoning:** Rather than implementing an over-engineered autoencoder, evaluating standard deviations (e.g., Queue Depth > 10, Abandonment > 15%) provides instant, interpretable, and computationally inexpensive operational alerts.