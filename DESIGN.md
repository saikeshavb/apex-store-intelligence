# Apex Retail - Store Intelligence API Architecture

## 1. System Overview
This project implements a complete edge-to-cloud analytical pipeline designed to mirror online e-commerce tracking within physical retail environments. The system processes raw CCTV footage, extracts spatial trajectories, and correlates them with Point-of-Sale (POS) data to compute the North Star metric: **Offline Store Conversion Rate**.

## 2. Pipeline Stages
* **Detection & Tracking (Edge):** Utilizes YOLOv8n for high-FPS person detection, paired with Deep SORT to maintain tracking states through partial occlusions (e.g., shelving units). 
* **State Machine & Contract:** A local state machine translates tracking states into discrete JSON events (`ENTRY`, `ZONE_DWELL`, `BILLING_QUEUE_JOIN`), rigorously validated against a Pydantic schema to ensure data integrity.
* **Ingestion Engine (Cloud):** A Flask-based REST API processes event batches. Strict idempotency is enforced at the MongoDB storage layer via unique indexing on `event_id`.
* **Intelligence Layer:** Translates raw spatial data into business metrics using MongoDB Aggregation Pipelines to match anonymous `visitor_id` trajectories with POS transaction timestamps.

## 3. Edge Case Mitigations
* **Partial Occlusions:** Deep SORT's Kalman filter and appearance descriptors bridge tracking gaps.
* **Staff Exclusion:** Visual heuristics evaluate bounding box color profiles against Apex Retail uniforms, flagging `is_staff: true` to scrub them from the conversion funnel.
* **Camera Overlap / Re-entry:** The pipeline architecture includes stubbed OSNet Vector DB lookups to unify track IDs across multiple cameras and distinct sessions.

## 4. AI Assistance Strategy
* **LLM Used:** Google Gemini
* **Application:** Used iteratively to design robust MongoDB aggregation queries, write rigorous Pytest edge-case suites, and architect a zero-manual-step Docker Compose networking strategy.